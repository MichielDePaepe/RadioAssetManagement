# Login gegevens
username = "xxx"
password = "xxx"


import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

login_url = "http://fireplan/fr/login"

session = requests.Session()

def login():
    # GET loginpagina
    resp = session.get(login_url)
    soup = BeautifulSoup(resp.text, "html.parser")
    csrf_token_tag = soup.find("input", {"name": "_csrf_token"})
    if not csrf_token_tag:
        raise Exception("CSRF token niet gevonden")
    csrf_token = csrf_token_tag["value"]

    # POST login
    login_data = {
        "auth_login[login]": username,
        "auth_login[password]": password,
        "_csrf_token": csrf_token,
        "auth_login[submit]": "Se connecter"
    }
    login_resp = session.post(login_url, data=login_data)
    return login_resp



resp = login()
