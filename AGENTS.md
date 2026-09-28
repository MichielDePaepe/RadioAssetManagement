# Radio Asset Management — context voor agents

## Werkwijze en onderhoud

- Communiceer met de gebruiker in het Nederlands, kort en concreet.
- Gebruik dit bestand als startpunt in een nieuwe chat. Inspecteer daarna alleen
  de bestanden die relevant zijn voor de opdracht; inventariseer niet telkens
  opnieuw het hele project.
- Onderhoud dit bestand zelf wanneer een taak blijvende projectkennis oplevert:
  architectuur, werkende ontwikkelcommando's, afspraken of belangrijke valkuilen.
  De gebruiker hoeft daar niet opnieuw om te vragen. Werk achterhaalde informatie
  bij in plaats van steeds notities toe te voegen.
- Bewaar hier alleen bevestigde, duurzame informatie. Geen chatlog, tijdelijke
  taakstatus, geheimen, persoonsgegevens of volledige codekopieën. Verwijs voor
  uitgebreide uitleg naar de bestaande documentatie.
- Controleer bij aanvang kort `git status --short`; respecteer bestaande wijzigingen.
  De actuele code en de huidige gebruikersopdracht gaan voor op verouderde notities.

## Project en indeling

Webapplicatie voor beheer, tracering en onderhoud van brandweerradio's.
Deze map is de Git-root en bevat `manage.py`. In de huidige lokale werkruimte
staat ze één niveau onder de geopende map met dezelfde naam.

- `RadioAssetManagement/`: Django-configuratie, centrale URL's, Celery-configuratie.
- Domeinapps: `radio`, `inventory`, `organization`, `helpdesk`, `astrid`,
  `fireplan`, `roip`, `taqto`, `printer`, `traca`.
- Begin bij de relevante app: `urls.py`, `views.py`, `models.py`, `forms.py`,
  `services/` of `services.py` waar aanwezig; tests staan onder meer in `tests.py`.
- `templates/`: gedeelde pagina's, `base.html` en `navbar.html`.
  App-specifieke templates staan in de apps.
- `static/`: bronassets; `staticfiles/`: verzamelde statische bestanden.
  Pas bronbestanden aan, niet de verzamelde kopieën.
- `locale/`: vertalingen Nederlands, Frans en Engels.
- `requirements.txt`: vastgelegde Python-dependencies; bevat Django 4.2.23,
  Celery, Redis, Channels, Bootstrap-integraties en django-modeltranslation.
  De gegenereerde commentaar bovenaan settings noemt Django 5.2.3; gebruik
  requirements en de werkelijk geïnstalleerde versie om de runtime te bepalen.

## Lokaal werken en controleren

Voer onderstaande commando's uit vanuit deze Git-root. De bestaande lokale
Python-omgeving staat in de bovenliggende map; controleer of die bruikbaar is.

```sh
../bin/python manage.py check
../bin/python manage.py test <app>
../bin/python manage.py runserver
```

Bevestigd op 2026-09-28: met `ENVIRONMENT=dev` werken `manage.py check`,
`manage.py test astrid --noinput` en `manage.py makemigrations --check --dry-run`
via `../bin/python`. Rapporteer de daadwerkelijk uitgevoerde controles en
eventuele blokkades. Test gericht wat door de wijziging geraakt wordt.

- `.env` wordt relatief aan de werkdirectory gelezen: starten vanuit deze map
  is belangrijk. Zie `README.md` voor de configuratie.
- Settings vereisen `SECRET_KEY`, `FIREPLAN_USERNAME` en `FIREPLAN_PASSWORD`.
  `ENVIRONMENT` valt standaard terug op `prod`; stel voor lokale ontwikkeling
  bewust `ENVIRONMENT=dev` in.
- Development gebruikt standaard SQLite, tenzij de `PG*`-omgevingsvariabelen
  PostgreSQL selecteren. Productie gebruikt `DATABASE_URL`.
- Lees of kopieer geen `.env`-waarden, dumps of echte databasegegevens naar
  documentatie. Start synchronisatie-, hardware- of productieacties alleen
  wanneer die binnen de gebruikersopdracht vallen.

## Bestaande conventies

- Gebruik Django-templates en bestaande Bootstrap-componenten als uitgangspunt.
- Houd nieuwe zichtbare teksten vertaalbaar via `{% trans %}` / `{% blocktrans %}`
  en Django gettext. Vertaalcommando's staan in `README.md`.
- Hergebruik de bestaande radio-selector; gebruik en callbacks staan in
  `radio/readme.md`.
- De RoIP API is gemount op `/api/roip/`, buiten de taalprefixen. Authenticatie
  gebeurt via een API-key; details staan in `docs/roip-api.md`.
- Maak bij modelwijzigingen passende migraties en controleer de gevolgen voor
  bestaande data.

## Documentatie gericht raadplegen

- `README.md`: omgeving, vertalingen, deployment, PostgreSQL, Nginx en Supervisor.
- `SYNC_PROD_TO_DEV.md`: synchronisatie van productie naar development.
- `docs/roip-api.md`: RoIP-integratie.
- `docs/lan-certificaat-installeren.md`: vertrouwd LAN-certificaat.
- `fireplan/sync_vectors_timer.md`: Fireplan-vectorsynchronisatie.
- `radio/readme.md`: herbruikbare radio-selector.
- In de bovenliggende lokale map, indien aanwezig:
  `graphic charter SIUAMU.md` voor huisstijl en
  `AT_COMMANDS_FULL_REFERENCE.md` voor TETRA/seriële commando's.

Deployment gebruikt `commit_and_push` lokaal en `deploy` op productie.
Deze scripts zijn geen testcommando's. Het deployscript maakt volgens de README
een databasedump bij gewijzigde migratiebestanden en voert migraties uit wanneer
het migratieplan operaties bevat. Raadpleeg script en README vóór deployment.

## ASTRID-desactivatie

- `astrid:deactivation_request` maakt voor een ingelogde gebruiker een aanvraag
  voor een actieve radio aan, met de huidige ISSI als `old_issi`.
- Bestaande rechten: `astrid.has_access_to_myastrid` voor indienen en feedback;
  `astrid.can_verify_requests` voor de onafhankelijke validatiestap.
- Flow: `NEW` → `IN_PROGRESS` → `WAITING_VERIFICATION` → `CLOSED`.
  Weigering sluit zonder abonnementswijziging; een negatieve validatie logt het
  resultaat en blijft wachten op validatie.
- Positieve validatie verwijdert daadwerkelijk de `Subscription`, niet de radio
  of ISSI. Een inmiddels gewijzigde ISSI blokkeert verwijdering. Een abonnement
  dat al door import verwijderd is, verhindert afsluiten niet.
- De desactivatie-POST-afhandeling in `RequestDetailView.post_deactivation`
  bewaakt rechten, volgorde en dubbele verzending binnen een transactie.
