# fireplan/backends.py

import re
import requests
from bs4 import BeautifulSoup

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.utils import translation
from django.db import IntegrityError

from .auth_models import (
    FireplanProfile,
    FireplanLanguage,
    FireplanGrade,
    FireplanGroup,
    FireplanSubGroup,
    FireplanFiliere,
)

User = get_user_model()

FIREPLAN_BASE_URL = "http://fireplan"
FIREPLAN_LOGIN_URL = f"{FIREPLAN_BASE_URL}/fr/login"
FIREPLAN_HOME_URL = f"{FIREPLAN_BASE_URL}/fr/"
PERSON_LINK_RE = re.compile(r"/fr/personne/view/(?P<id>\d+)")


class FireplanBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        try:
            session = self._fireplan_login(username, password)
        except Exception:
            return None

        if session is None:
            return None

        person_url = self._get_person_url(session)
        if not person_url:
            return None

        data = self._fetch_personal_data(session, person_url)
        if not data:
            return None

        return self._get_or_update_user(username, data)

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    # ------- helpers voor login / scraping -------

    def _fireplan_login(self, username, password):
        """
        Login on Fireplan, using the same flow as your working helper.
        Returns an authenticated requests.Session or None if login fails.
        """
        session = requests.Session()

        # 1) GET login page to fetch CSRF token
        r = session.get(FIREPLAN_LOGIN_URL, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        csrf_el = soup.find("input", {"name": "_csrf_token"})
        if not csrf_el or not csrf_el.get("value"):
            # Layout changed or no CSRF found
            return None

        csrf = csrf_el["value"]

        # 2) POST login with correct field names
        data = {
            "auth_login[login]": username,
            "auth_login[password]": password,
            "_csrf_token": csrf,
            "auth_login[submit]": "Se connecter",
        }

        resp = session.post(FIREPLAN_LOGIN_URL, data=data, timeout=10)
        resp.raise_for_status()

        # 3) Check for invalid credentials text
        if "Identifiants invalides" in resp.text:
            return None

        # 4) Zoek 'Dossier personnel' link (soms staat die al in resp, anders op /fr/)
        html = resp.text
        if "Dossier personnel" not in html:
            home = session.get(FIREPLAN_HOME_URL, timeout=10)
            home.raise_for_status()
            html = home.text

        soup_home = BeautifulSoup(html, "html.parser")
        person_link = None
        for a in soup_home.select("a.nav-link"):
            href = a.get("href") or ""
            if "Dossier personnel" in a.get_text(strip=True) and PERSON_LINK_RE.match(
                href
            ):
                person_link = href
                break

        if not person_link:
            # login ok maar geen personeelslink gevonden
            return None

        session.person_link = person_link
        return session

    def _get_person_url(self, session):
        href = getattr(session, "person_link", None)
        if not href:
            return None
        return f"{FIREPLAN_BASE_URL}{href}"

    def _fetch_personal_data(self, session, person_url):
        resp = session.get(person_url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        def input_value(selector: str) -> str:
            el = soup.select_one(selector)
            if not el:
                return ""
            return el.get("value", "").strip()

        last_name = input_value("#nom")
        first_name = input_value("#prenom")
        language = input_value("#Langue")
        email = input_value("#email")

        grade = self._extract_single_under_label(soup, "Grade")
        groups = self._extract_single_under_label(soup, "Groupes")
        subgroups = self._extract_single_under_label(soup, "Sous-groupes")
        filiere = self._extract_single_under_label(soup, "Filière")

        return {
            "last_name": last_name,
            "first_name": first_name,
            "language": language,
            "email": email,
            "grade": grade,
            "groups": groups,
            "subgroups": subgroups,
            "filiere": filiere,
        }

    def _extract_single_under_label(self, soup, label_text: str) -> str:
        rows = soup.select("div.row.form-group")
        for row in rows:
            label = row.find("label")
            if not label:
                continue
            if label_text in label.get_text(strip=True):
                inp = row.select_one("input.form-control")
                if inp:
                    return inp.get("value", "").strip()
        return ""

    # ------- user en FK’s aanmaken -------

    def _get_or_update_user(self, fireplan_username: str, data: dict) -> User:
        user, created = User.objects.get_or_create(
            username=fireplan_username,
            defaults={
                "first_name": data["first_name"],
                "last_name": data["last_name"],
                "email": data["email"],
            },
        )

        changed = False
        if user.first_name != data["first_name"]:
            user.first_name = data["first_name"]
            changed = True
        if user.last_name != data["last_name"]:
            user.last_name = data["last_name"]
            changed = True
        if data["email"] and user.email != data["email"]:
            user.email = data["email"]
            changed = True

        if changed:
            user.save()

        profile, _ = FireplanProfile.objects.get_or_create(user=user)
        profile.fireplan_username = fireplan_username

        profile.language = self._get_language(data.get("language"))
        profile.grade = self._get_grade(data.get("grade"))
        profile.groups = self._get_group(data.get("groups"))
        profile.subgroups = self._get_subgroup(data.get("subgroups"))
        profile.filiere = self._get_filiere(data.get("filiere"))

        profile.save()
        return user

    # ------- deze helpers staan ONDERAAN in dezelfde class -------

    def _get_language(self, code: str | None):
        if not code:
            return None
        obj, _ = FireplanLanguage.objects.get_or_create(code=code)
        return obj

    def _get_grade(self, name_fr: str | None):
        if not name_fr:
            return None

        name_fr = name_fr.strip()
        manager = FireplanGrade._base_manager  # om modeltranslation-gedoe te omzeilen

        kwargs = {"name_fr": name_fr}

        # 1) proberen opvragen op basis van FR-kolom
        try:
            return manager.get(**kwargs)
        except FireplanGrade.DoesNotExist:
            pass

        # 2) bestaat nog niet → proberen maken
        try:
            return manager.create(**kwargs)
        except IntegrityError:
            # 3) als DB zegt dat hij al bestaat, nog eens gewoon ophalen
            try:
                return manager.get(**kwargs)
            except FireplanGrade.DoesNotExist:
                return None


    def _get_group(self, name: str | None):
        if not name:
            return None
        obj, _ = FireplanGroup.objects.get_or_create(name=name)
        return obj

    def _get_subgroup(self, name: str | None):
        if not name:
            return None
        obj, _ = FireplanSubGroup.objects.get_or_create(name=name)
        return obj

    def _get_filiere(self, code: str | None):
        if not code:
            return None
        obj, _ = FireplanFiliere.objects.get_or_create(code=code)
        return obj
