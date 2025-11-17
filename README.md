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

Voorbeeld van een bash script om te deployen:
```bash
source ../bin/activate
git fetch origin
git reset --hard origin
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo supervisorctl restart django
sudo systemctl restart nginx
```


## Environment

Maak een `.env` file aan in de base directory van het project.

### Development
```dotenv
ENVIRONMENT=dev
DEBUG=True
SECRET_KEY=***
FIREPLAN_USERNAME=***
FIREPLAN_PASSWORD=***
```

### Production
```dotenv
ENVIRONMENT=prod
DEBUG=False
SECRET_KEY=***
DATABASE_URL=postgres://<pg username>:<pg password>@localhost:5432/<db name>
ALLOWED_PROD_HOST=<host 1>, <host 2>
FIREPLAN_USERNAME=***
FIREPLAN_PASSWORD=***
```

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

## Nginx Setup voor Django

De Nginx configuratie voor de Django-app staat in:

`/etc/nginx/sites-available/django`

### Configuratie

```nginx
server {
    listen 80;
    server_name _;

    location /static/ {
        alias /home/taqto/RadioAssetManagement/RadioAssetManagement/staticfiles/;
        autoindex on;  # alleen om te testen
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Activeren

```bash
sudo ln -s /etc/nginx/sites-available/django /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
go
Code kopiëren
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

### Supervisor commands

* Herlaad configuraties:

```bash
sudo supervisorctl reread
sudo supervisorctl update
```

* Starten / stoppen van je project:

```bash
sudo supervisorctl start radioassetmanagement
sudo supervisorctl stop radioassetmanagement
```
