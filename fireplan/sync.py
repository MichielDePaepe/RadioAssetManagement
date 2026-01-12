from .client import FireplanClient
from .models import *
from radio.models import *
import requests
from django.conf import settings
import json
from django.utils.timezone import make_aware
from django.db.models import Q

import datetime
import re
from dateutil import parser


def sync_fireplan_fleet():
    fp = FireplanClient()   # login gebeurt automatisch

    path = "/fr/api/charroi/view"

    payload = {
        "page": 1,
        "size": 5000,
        "sortby": "number",
        "sortdesc": False,
    }

    r = fp.post(path, json=payload)
    r.raise_for_status()

    data = r.json()
    records = data.get("records", [])

    count = 0

    for rec in records:
        Vehicle.objects.update_or_create(
            id=rec["id"],
            defaults={
                "number": rec.get("number", ""),
                "num_letter": rec.get("numLettre", "") or "",
                "num_value": rec.get("num", 0) or 0,
                "plate": rec.get("plate", "") or "",
                "utilisation": rec.get("utilisation", "") or "",
                "chassis": rec.get("chassis", "") or "",
                "status": rec.get("statut", None),
            },
        )
        count += 1

    return count




def test_resourcesoff():
    BASE = "http://resourcesoff.firebru2k8.local"
    LOGIN_URL = BASE + "/php/login_resources.php"
    AJAX_URL = BASE + "/php/vehicule_ajax.php"

    session = requests.Session()

    payload = {
        "username": settings.FIREPLAN_USERNAME,
        "password": settings.FIREPLAN_PASSWORD,
    }

    resp = session.post(LOGIN_URL, data=payload)

    if "Login" in resp.text:
        raise(exception("❌ Login fout op resourcesoff"))

    params = {
        "mode": "resources",
        "servicetype": "atelier",
        "version": "cnd",
        "lang": "fr",
    }

    r = session.get(AJAX_URL, params=params)

    data = r.json()

    dump_path = "resourcesoff_dump.json"
    with open(dump_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)








def sync_vectors():
    BASE = "http://resourcesoff.firebru2k8.local"
    LOGIN_URL = BASE + "/php/login_resources.php"
    AJAX_URL = BASE + "/php/vehicule_ajax.php"

    def _match_vehicle(name: str):

        return Vehicle.objects.filter(
            Q(number=name) | 
            Q(number__startswith=name + " -")
        ).first()


    STATUS_PRIORITY = {
        None: -1,  # geen status = laagste voorkeur
    }


    def _get_priority(status_obj):
        """Status object → ranking integer."""
        if status_obj is None:
            return -1
        return int(status_obj.code) if status_obj.code.isdigit() else 0



    session = requests.Session()

    # --------------------------- LOGIN ---------------------------
    resp = session.post(LOGIN_URL, data={
        "username": settings.FIREPLAN_USERNAME,
        "password": settings.FIREPLAN_PASSWORD,
    })
    if "Login" in resp.text:
        raise Exception("❌ Foute login op resourcesoff")

    # --------------------------- DATA ---------------------------
    r = session.get(AJAX_URL, params={
        "mode": "resources",
        "servicetype": "atelier",
        "version": "cnd",
        "lang": "fr",
    })
    root = r.json()
    stations = root.get("data", {})

    # Verzamel alle records *eerder*, zodat we duplicates per voertuig kunnen samenvoegen
    per_vehicle = {}

    for station_code, groups in stations.items():
        for veh_group, content in groups.items():

            if isinstance(content, dict):
                iterator = content.values()
            else:
                iterator = content

            for item in iterator:

                name = item.get("Name")
                if not name:
                    continue

                # match voertuig
                vehicle = _match_vehicle(name)
                Vehicle.objects.filter(call_sign=name).first()
                if not vehicle:
                    continue

                # skip als geen pResourceCode → dit voertuig heeft GEEN vector
                pcode = item.get("pResourceCode")
                if not pcode:
                    continue

                status_code = item.get("StatusCode")                

                entry = {
                    "item": item,
                    "status": status_code,
                }

                # append in lijst → elke vehicle kan meerdere vector records hebben
                per_vehicle.setdefault(vehicle.id, []).append(entry)

    seen_pcodes = set()

    # --------------------------- BESTE RECORD SELECTEREN ---------------------------
    for vehicle_id, records in per_vehicle.items():

        # kies record met hoogste status
        best = max(
            records,
            key=lambda rec: _get_priority(
                StatusCode.objects.filter(code=rec["status"]).first()
            )
        )

        item = best["item"]
        pcode = item["pResourceCode"]

        seen_pcodes.add(pcode)

        # -------- lookup tables --------
        svc = None
        if item.get("pServiceAbbreviation"):
            svc, _ = Service.objects.get_or_create(
                code=item["pServiceAbbreviation"],
                defaults={"description": item["pServiceAbbreviation"]},
            )

        rtype = None
        if item.get("pResourceTypeCode"):
            rtype, _ = ResourceTypeCode.objects.get_or_create(
                code=item["pResourceTypeCode"],
                defaults={"description": item["pResourceTypeCode"]},
            )

        st = None
        if item.get("StatusCode"):
            st, _ = StatusCode.objects.get_or_create(
                code=item["StatusCode"],
                defaults={"description": item["StatusCode"]},
            )

        Vector.objects.filter(vehicle_id=vehicle_id).exclude(resourceCode=pcode).update(vehicle=None)

        # -------- save --------
        Vector.objects.update_or_create(
            resourceCode=pcode,  # PRIMARY KEY
            defaults={
                "vehicle_id": vehicle_id,
                "name": item.get("pName") or "",
                "abbreviation": item.get("pAbbreviation") or "",
                "service": svc,
                "resourceTypeCode": rtype,
                "statusCode": st,
                "orderServiceAbbreviation": item.get("orderServiceAbbreviation"),
            },
        )

    # --------------------------- DELETE old ---------------------------
    Vector.objects.exclude(resourceCode__in=seen_pcodes).delete()

    return len(seen_pcodes)


def sync_fireplan_id():
    fp = FireplanClient()   # login automatisch

    url = f"{fp.BASE}/fr/api/inventory/qr-codes"

    payload = {
        "first": 0,
        "rows": 5000,
        "filters": '%7B%22id%22:%7B%22operator%22:%22and%22,%22constraints%22:[%7B%22value%22:null,%22matchMode%22:%22contains%22%7D]%7D,%22name%22:%7B%22value%22:null,%22matchMode%22:%22in%22%7D,%22serialNumber%22:%7B%22value%22:null,%22matchMode%22:%22in%22%7D,%22type%22:%7B%22value%22:null,%22matchMode%22:%22in%22%7D,%22qrCode%22:%7B%22operator%22:%22and%22,%22constraints%22:[%7B%22value%22:null,%22matchMode%22:%22contains%22%7D]%7D,%22createdAt%22:%7B%22operator%22:%22and%22,%22constraints%22:[%7B%22value%22:null,%22matchMode%22:%22dateIs%22%7D]%7D%7D',
        "multiSortMeta": "[]",
    }

    r = fp.session.get(url, params=payload)
    r.raise_for_status()

    data = r.json()
    records = data.get("records", [])

    result = []

    pattern = re.compile(r"https://infoscan\.firebru\.brussels\?data[=-](?P<arg1>\d+),(?P<arg2>\d+),(?P<fireplan_id>\d+),(?P<arg4>\d+)")
    
    for rec in records:
        if rec.get("name") in ["Radio mobile Astrid", "Radio portable Astrid", "Portable ATEX"]:
            match = pattern.match(rec["qrCode"])
            if not match:
                continue

            fireplan_id = int(match.group("fireplan_id"))
            tei = rec["serialNumber"]

            try:
                radio, created = Radio.objects.get_or_create(
                    TEI=tei,
                    defaults={"fireplan_id": fireplan_id},
                )
            except ValueError:
                continue

            if not created:
                if radio.fireplan_id != fireplan_id:
                    radio.fireplan_id = fireplan_id
                    radio.save()

            result.append({"TEI": tei, "fireplan_id": fireplan_id})


    return result
