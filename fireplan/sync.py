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


def _vehicle_defaults_from_fireplan_record(rec):
    return {
        "number": rec.get("alphacode", "") or "",
        "num_letter": rec.get("numLettre", "") or "",
        "num_value": rec.get("num", 0) or 0,
        "plate": rec.get("plate", "") or "",
        "utilisation": rec.get("utilisation", "") or "",
        "chassis": rec.get("chassis", "") or "",
        "status": rec.get("statut", None),
    }


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
        fireplan_id = rec.get("id")
        if not fireplan_id:
            continue

        defaults = _vehicle_defaults_from_fireplan_record(rec)

        vehicle = Vehicle.objects.filter(fireplan_id=fireplan_id).first()
        if not vehicle and defaults["number"]:
            vehicle = Vehicle.objects.filter(
                Q(number=defaults["number"]) |
                Q(call_sign=defaults["number"]) |
                Q(number__startswith=defaults["number"] + " -")
            ).first()

        if vehicle:
            for field, value in defaults.items():
                setattr(vehicle, field, value)
            vehicle.fireplan_id = fireplan_id
            vehicle.save()
        else:
            Vehicle.objects.create(
                fireplan_id=fireplan_id,
                **defaults,
            )

        count += 1

    return count


def _split_vehicle_name(name):
    match = re.match(r"^([A-Za-z]+)(\d+)$", name or "")
    if not match:
        return "", 0
    return match.group(1), int(match.group(2))


def _vehicle_defaults_from_vector_item(item):
    name = item.get("Name") or item.get("ResourceCode") or item.get("pAbbreviation") or ""
    first_letter = item.get("firstLetter") or ""
    parsed_letter, parsed_number = _split_vehicle_name(name)

    numerical_alpha_code = item.get("numericalAlphaCode")
    try:
        num_value = int(numerical_alpha_code) if numerical_alpha_code is not None else parsed_number
    except (TypeError, ValueError):
        num_value = parsed_number

    utilisation_parts = [
        item.get("pName") or "",
        item.get("orderServiceAbbreviation") or "",
    ]
    utilisation = " - ".join(part for part in utilisation_parts if part)

    return {
        "number": name,
        "num_letter": (first_letter or parsed_letter)[:5],
        "num_value": num_value or 0,
        "plate": "",
        "utilisation": utilisation[:200],
        "chassis": "",
        "status": VehicleStatus.ACTIF if item.get("IsActive") else None,
    }


def _match_or_create_vehicle_from_vector_item(item):
    name = item.get("Name")
    if not name:
        return None

    vehicle = Vehicle.objects.filter(
        Q(number=name) |
        Q(call_sign=name) |
        Q(number__startswith=name + " -")
    ).first()

    if vehicle:
        return vehicle

    return Vehicle.objects.create(**_vehicle_defaults_from_vector_item(item))


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

                # skip als geen pResourceCode → dit voertuig heeft GEEN vector
                pcode = item.get("pResourceCode")
                if not pcode:
                    continue

                vehicle = _match_or_create_vehicle_from_vector_item(item)
                if not vehicle:
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
    fp = FireplanClient()

    url = f"{fp.BASE}/fr/api/inventory/qr-codes"

    headers = {
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{fp.BASE}/fr/inventory/qr-codes",
    }

    pattern = re.compile(
        r"https://infoscan\.firebru\.brussels\?data[=-](?P<arg1>\d+),(?P<arg2>\d+),(?P<fireplan_id>\d+),(?P<arg4>\d+)$"
    )

    radio_names = [
        "Radio mobile Astrid",
        "Radio portable Astrid",
        "Portable ATEX",
    ]

    result = []

    for radio_name in radio_names:
        filters = {
            "id": {
                "operator": "and",
                "constraints": [{"value": None, "matchMode": "contains"}],
            },
            "name": {
                "value": [radio_name],
                "matchMode": "in",
            },
            "serialNumber": {
                "value": None,
                "matchMode": "in",
            },
            "type": {
                "value": None,
                "matchMode": "in",
            },
            "qrCode": {
                "operator": "and",
                "constraints": [{"value": None, "matchMode": "contains"}],
            },
            "createdAt": {
                "operator": "and",
                "constraints": [{"value": None, "matchMode": "dateIs"}],
            },
        }

        params = {
            "first": 0,
            "rows": 5000,
            "filters": json.dumps(filters, separators=(",", ":")),
            "multiSortMeta": "[]",
        }

        r = fp.session.get(url, params=params, headers=headers)

        if r.status_code >= 500:
            logger.warning(
                "Fireplan API error for %s: %s - %s",
                radio_name,
                r.status_code,
                r.text[:500],
            )
            continue

        r.raise_for_status()

        data = r.json()
        records = data.get("records", [])

        for rec in records:
            qr_code = rec.get("qrCode") or ""
            match = pattern.match(qr_code)

            if not match:
                continue

            serial_number = rec.get("serialNumber")
            if not serial_number:
                continue

            fireplan_id = int(match.group("fireplan_id"))

            try:
                radio, created = Radio.objects.get_or_create(
                    TEI=serial_number,
                    defaults={"fireplan_id": fireplan_id},
                )
            except ValueError:
                continue

            if not created and radio.fireplan_id != fireplan_id:
                radio.fireplan_id = fireplan_id
                radio.save(update_fields=["fireplan_id"])

            result.append({
                "TEI": serial_number,
                "fireplan_id": fireplan_id,
                "name": radio_name,
            })

    return result




# def sync_fireplan_id():
#     fp = FireplanClient()   # login automatisch

#     url = f"{fp.BASE}/fr/api/inventory/qr-codes"

#     payload = {
#         "first": 0,
#         "rows": 5000,
#         "filters": '%7B%22id%22:%7B%22operator%22:%22and%22,%22constraints%22:[%7B%22value%22:null,%22matchMode%22:%22contains%22%7D]%7D,%22name%22:%7B%22value%22:null,%22matchMode%22:%22in%22%7D,%22serialNumber%22:%7B%22value%22:null,%22matchMode%22:%22in%22%7D,%22type%22:%7B%22value%22:null,%22matchMode%22:%22in%22%7D,%22qrCode%22:%7B%22operator%22:%22and%22,%22constraints%22:[%7B%22value%22:null,%22matchMode%22:%22contains%22%7D]%7D,%22createdAt%22:%7B%22operator%22:%22and%22,%22constraints%22:[%7B%22value%22:null,%22matchMode%22:%22dateIs%22%7D]%7D%7D',
#         "multiSortMeta": "[]",
#     }

#     r = fp.session.get(url, params=payload)
#     r.raise_for_status()

#     data = r.json()
#     records = data.get("records", [])

#     result = []

#     pattern = re.compile(r"https://infoscan\.firebru\.brussels\?data[=-](?P<arg1>\d+),(?P<arg2>\d+),(?P<fireplan_id>\d+),(?P<arg4>\d+)")
    
#     for rec in records:
#         if rec.get("name") in ["Radio mobile Astrid", "Radio portable Astrid", "Portable ATEX"]:
#             match = pattern.match(rec["qrCode"])
#             if not match:
#                 continue

#             fireplan_id = int(match.group("fireplan_id"))
#             tei = rec["serialNumber"]

#             try:
#                 radio, created = Radio.objects.get_or_create(
#                     TEI=tei,
#                     defaults={"fireplan_id": fireplan_id},
#                 )
#             except ValueError:
#                 continue

#             if not created:
#                 if radio.fireplan_id != fireplan_id:
#                     radio.fireplan_id = fireplan_id
#                     radio.save()

#             result.append({"TEI": tei, "fireplan_id": fireplan_id})


#     return result
