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

2. Compileer de `.po` bestanden tot `.po` bestanden
```bash
python manage.py compilemessages
```