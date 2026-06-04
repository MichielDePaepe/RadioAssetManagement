import json
import re
import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.utils import timezone


class FireplanClient:
    BASE = "http://fireplan.firebru2k8.local"
    LOGIN_URL = BASE + "/fr/login"
    RADIO_CREATE_PATH = "/fr/api/inventory/tracked-items/radio"
    QR_CODES_PATH = "/fr/api/inventory/qr-codes"
    RADIO_ITEM_TYPE_ID = 1010
    RADIO_QR_NAME = "Radio portable Astrid"
    RADIO_TYPE = "PORTABLE"
    QR_CODE_PATTERN = re.compile(
        r"https://infoscan\.firebru\.brussels\?data[=-]\d+,\d+,(?P<fireplan_id>\d+),\d+$"
    )
    LOCATION_ID_PATTERN = re.compile(r"/(\d+)(?:/)?$")

    def __init__(self):
        self.session = requests.Session()
        self.login()

    def login(self):
        # GET login page
        r = self.session.get(self.LOGIN_URL)
        soup = BeautifulSoup(r.text, "html.parser")
        csrf = soup.find("input", {"name": "_csrf_token"})["value"]

        # POST login
        payload = {
            "auth_login[login]": settings.FIREPLAN_USERNAME,
            "auth_login[password]": settings.FIREPLAN_PASSWORD,
            "_csrf_token": csrf,
            "auth_login[submit]": "Se connecter",
        }
        resp = self.session.post(self.LOGIN_URL, data=payload)

        if "Identifiants invalides" in resp.text:
            raise Exception("❌ Foute Fireplan login")

    def get(self, path, **kwargs):
        return self.session.get(self.BASE + path, **kwargs)

    def post(self, path, data=None, json=None, **kwargs):
        return self.session.post(self.BASE + path, data=data, json=json, **kwargs)

    def get_radio_qr_code_record(self, serial_number):
        filters = {
            "id": {
                "operator": "and",
                "constraints": [{"value": None, "matchMode": "contains"}],
            },
            "name": {
                "value": [self.RADIO_QR_NAME],
                "matchMode": "in",
            },
            "serialNumber": {
                "value": str(serial_number),
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
            "rows": 10,
            "filters": json.dumps(filters, separators=(",", ":")),
            "multiSortMeta": "[]",
        }
        headers = {
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.BASE}/fr/inventory/qr-codes",
        }

        response = self.get(self.QR_CODES_PATH, params=params, headers=headers)
        response.raise_for_status()

        for record in response.json().get("records", []):
            if str(record.get("serialNumber")) == str(serial_number):
                return record
        return None

    def get_radio_fireplan_id(self, serial_number):
        record = self.get_radio_qr_code_record(serial_number)
        if not record:
            return None

        qr_code = record.get("qrCode") or ""
        match = self.QR_CODE_PATTERN.match(qr_code)
        if match:
            return int(match.group("fireplan_id"))

        fireplan_id = record.get("id")
        return int(fireplan_id) if fireplan_id else None

    def create_radio(self, serial_number):
        payload = {
            "serialNumber": str(serial_number),
            "sapNumber": None,
            "internalReference": None,
            "itemTypeId": self.RADIO_ITEM_TYPE_ID,
            "issiSubscriptionId": None,
            "radioType": self.RADIO_TYPE,
            "radioHasSubscription": True,
            "startAt": timezone.localdate().isoformat(),
            "endAt": None,
        }
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": self.BASE,
            "Referer": f"{self.BASE}/fr/inventory/tracked-items/radio/form/create",
            "X-Deferred-Message": "true",
            "X-Requested-With": "XMLHttpRequest",
        }

        response = self.post(self.RADIO_CREATE_PATH, json=payload, headers=headers)
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError:
            data = {}

        record = data.get("record") or {}
        records = data.get("records") or []
        first_record = records[0] if isinstance(records, list) and records else {}
        fireplan_id = data.get("id") or record.get("id") or first_record.get("id")
        if fireplan_id:
            return int(fireplan_id)

        location = response.headers.get("Location", "")
        location_match = self.LOCATION_ID_PATTERN.search(location)
        if location_match:
            return int(location_match.group(1))

        return self.get_radio_fireplan_id(serial_number)

    def get_or_create_radio_fireplan_id(self, serial_number):
        fireplan_id = self.get_radio_fireplan_id(serial_number)
        if fireplan_id:
            return fireplan_id, False

        fireplan_id = self.create_radio(serial_number)
        if not fireplan_id:
            raise Exception("Fireplan radio aangemaakt, maar Fireplan ID kon niet bepaald worden.")

        return fireplan_id, True
