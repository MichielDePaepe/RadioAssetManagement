import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

logger = logging.getLogger("TrakaWeb")
logging.basicConfig(level=logging.DEBUG)


BASE_URL = "http://traka.firebru2k8.local/TrakaWeb/"
LOGIN_PATH = "Account/LogOn"
USERNAME = "michiel.depaepe"
PASSWORD = "Hoofdletter007!"

# Start session
session = requests.Session()

# --- LOGIN ---
logger.debug("Login")
login_url = urljoin(BASE_URL, LOGIN_PATH)
resp = session.get(login_url)
soup = BeautifulSoup(resp.text, "html.parser")

token = soup.find("input", {"name": "__RequestVerificationToken"})["value"]
logger.debug(f"CRFR token: {token}")

payload = {
    "__RequestVerificationToken": token,
    "UserName": USERNAME,
    "Password": PASSWORD,
    "timezoneOffset": "0"
}

session.post(login_url, data=payload)
logger.debug(f"Session created")


# --- GENERIC GET REQUEST ---
def get_page(path, params=None):
    url = urljoin(BASE_URL, path)
    resp = session.get(url, params=params)
    resp.raise_for_status()
    return resp

# Voorbeeld: SystemViewer met parameters
params = {
    "RegionID": "00000000-0000-0000-0000-000000000001",
    "SystemID": "07f158b3-c84f-45a1-b509-67db0138fee3"
}
resp = get_page("SystemViewer", params=params)

print(resp.url)     # volledige URL met parameters

with open("result.html", "w", encoding="utf-8") as f:
    f.write(resp.text)

