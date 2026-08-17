# Radio Asset Management

Een webapplicatie voor het beheren, traceren en onderhouden van draagbare radio's binnen de brandweer.


## Vertalingen

De site is voorzien voor gebruik van 3 talen: Nederlands, Frans en Engels.

### Doen van vertalingen

Alle te vertalen strings moeten in de templates en Python-code voorzien zijn van Django's vertaal-tags:

- In templates:
    - Voeg bovenaar de tag `{% load i18n%}` toe
    -  `{% trans "Text to translate" %}` of `{% blocktrans %}Text{% endblocktrans %}`
- In Python-code: `from django.utils.translation import gettext as _` en dan `_('Text to translate')`

### Compilen van vertalingen

1. Maak de `.po` bestanden aan of update ze:
```bash
python manage.py makemessages -l nl
python manage.py makemessages -l fr
python manage.py makemessages -l en
```

2. Compileer de `.po` bestanden tot `.mo` bestanden
```bash
python manage.py compilemessages
```

## Deployment

Development: commit en push eerst de lokale wijzigingen:
```bash
./commit_and_push "Beschrijf de wijziging"
```

Production: voer daarna het deployscript uit op de prod server:
```bash
./deploy
```

Het deployscript maakt alleen een database dump via `./dump_db` wanneer er Django
migratiebestanden gewijzigd zijn tussen de huidige prod-versie en `origin/main`.
Zonder migraties wordt de dump overgeslagen om de deploy kort te houden. Na het
updaten van de code voert het script `migrate` alleen uit wanneer
`manage.py migrate --plan` effectieve migratie-operaties toont.

## Environment

Maak een `.env` file aan in de base directory van het project.

### Development
```dotenv
ENVIRONMENT=dev
DEBUG=True
SECRET_KEY=***
FIREPLAN_USERNAME=***
FIREPLAN_PASSWORD=***
ROIP_API_KEYS=***
```

### Production
```dotenv
ENVIRONMENT=prod
DEBUG=False
SECRET_KEY=***
DATABASE_URL=postgres://<pg username>:<pg password>@localhost:5432/<db name>
ALLOWED_PROD_HOST=<host 1>, <host 2>
HTTPS_ENABLED=True
FIREPLAN_USERNAME=***
FIREPLAN_PASSWORD=***
ROIP_API_KEYS=<lange random api key 1>, <lange random api key 2>
ROIP_RECORDINGS_BASE_URL=/media/recordings/
```

## RoIP REST API

De RoIP API is bedoeld voor snelle server-to-server lookups vanuit live tooling.
Authenticatie gebeurt met een API key via `X-API-Key` of `Authorization: Bearer`.

```http
GET /api/roip/issi/1234567/
X-API-Key: <key uit ROIP_API_KEYS>
```

De response bevat de ISSI-alias, gekoppelde radio/TEI, voertuig, vector en
vectorstatus. Niet-gekoppelde onderdelen worden als `null` teruggegeven.

### Secret key

Je kan als volgt een secret key genereren

1. Open de shell
```bash
$ django-admin shell
```
2. voor onderstaande code uit
```python
from django.core.management.utils import get_random_secret_key  
get_random_secret_key()
```

## Nginx HTTPS Setup voor Django

De Nginx configuratie voor de Django-app staat in:

`/etc/nginx/sites-available/django`

### Configuratie

Deze configuratie zet HTTP door naar HTTPS en laat Nginx TLS afhandelen.
Django blijft via gunicorn op `127.0.0.1:8000` draaien.

```nginx
server {
    listen 80;
    server_name <host>;

    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name <host>;

    ssl_certificate /etc/ssl/certs/ram-lan.crt;
    ssl_certificate_key /etc/ssl/private/ram-lan.key;

    location /static/ {
        alias /home/taqto/RadioAssetManagement/RadioAssetManagement/staticfiles/;
    }

    location /media/ {
        alias /home/taqto/RadioAssetManagement/RadioAssetManagement/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Als de RoIP-opnames op een apart toestel staan, vermijd dan `http://...` links op
de HTTPS-site. Zet `ROIP_RECORDINGS_BASE_URL` naar een HTTPS URL, of proxy de
opnames via Nginx onder `/media/recordings/`.

### Intern LAN zonder IT-certificaat

Voor camera en Web Serial moet de browser de site als secure context zien.
Een HTTPS-pagina met een certificaatwaarschuwing is vaak niet genoeg. Maak
daarom een kleine eigen LAN-CA en installeer het CA-certificaat als vertrouwde
root op de pc's die de scanner of seriele kabel gebruiken.

Maak het certificaat lokaal, met de echte hostnaam en het LAN-IP van de server:

```bash
chmod +x scripts/make_lan_https_cert.sh
scripts/make_lan_https_cert.sh <host> <server-ip>
```

Kopieer daarna het servercertificaat en de private key naar Nginx:

```bash
sudo cp certs/ram-lan.crt /etc/ssl/certs/ram-lan.crt
sudo cp certs/ram-lan.key /etc/ssl/private/ram-lan.key
sudo chmod 600 /etc/ssl/private/ram-lan.key
```

Installeer `certs/ram-lan-ca.crt` op elke client-pc als vertrouwde root-CA.
Daarna moet de site zonder certificaatwaarschuwing openen via `https://<host>/`.

Als installeren van een vertrouwde CA op de client-pc's echt niet kan, blijft er
alleen een browser workaround over. In Chrome/Edge kan je voor tests
`chrome://flags/#unsafely-treat-insecure-origin-as-secure` gebruiken met de
origin van de site, bijvoorbeeld `http://<host>`. Dat is minder proper en moet
per client-browser ingesteld worden.

### Activeren

```bash
sudo ln -s /etc/nginx/sites-available/django /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## PostgreSQL Setup voor Django

### Installatie (Ubuntu voorbeeld)

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib libpq-dev
```

### Database aanmaken

```bash
sudo -u postgres psql
```
```sql
CREATE DATABASE radio_db;
CREATE USER django WITH PASSWORD '<pg password>';
ALTER ROLE django SET client_encoding TO 'utf8';
ALTER ROLE django SET default_transaction_isolation TO 'read committed';
ALTER ROLE django SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE radio_db TO django;
\q
```

### Django instellingen

Dit project maakt gebruik van `dj-database-url`. De instellingen voor de database staan in een `.env` file

```dotenv
DATABASE_URL=postgres://django:<pg password>@localhost:5432/radio_db
```


## Supervisor voor gunicorn

Supervisor kan gebruikt worden om dit project en andere processen (bijv. Celery) als service te draaien en automatisch te herstarten bij fouten of server-herstarts.

### Installatie

```bash
sudo apt install supervisor
```

### Configuratie

Maak een config-file aan in `/etc/supervisor/conf.d/django.conf`, bijvoorbeeld:

```ini
[program:django]
directory=/home/taqto/RadioAssetManagement/RadioAssetManagement/
command=/home/taqto/RadioAssetManagement/bin/gunicorn RadioAssetManagement.wsgi:application --bind 127.0.0.1:8000
autostart=true
autorestart=true
stderr_logfile=/var/log/django.err.log
stdout_logfile=/var/log/django.out.log
user=taqto
environment=PATH="/home/taqto/RadioAssetManagement/bin/"
```

`/etc/supervisor/conf.d/ram-celery-worker.conf`
```ini
[program:ram-celery-worker]
directory=/home/taqto/RadioAssetManagement/RadioAssetManagement
command=/home/taqto/RadioAssetManagement/bin/celery -A RadioAssetManagement worker -l INFO
user=taqto
autostart=true
autorestart=true
startsecs=5
stopsignal=TERM
stopwaitsecs=60
killasgroup=true
stdout_logfile=/var/log/ram/celery_worker.out.log
stderr_logfile=/var/log/ram/celery_worker.err.log
environment=DJANGO_SETTINGS_MODULE="RadioAssetManagement.settings",PYTHONUNBUFFERED="1
```

### Supervisor commands

* Herlaad configuraties:

```bash
sudo supervisorctl reread
sudo supervisorctl update
```

* Starten / stoppen van je project:

```bash
sudo supervisorctl start django
sudo supervisorctl stop django
sudo supervisorctl start ram-celery-worker
sudo supervisorctl stop ram-celery-worker
```
