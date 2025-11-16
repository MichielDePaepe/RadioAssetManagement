import requests
from bs4 import BeautifulSoup
from django.conf import settings


class FireplanClient:
    BASE = "http://fireplan.firebru2k8.local"
    LOGIN_URL = BASE + "/fr/login"

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

