# RoIP API documentatie

Deze API geeft live informatie terug over een ISSI: alias, gekoppelde radio
(TEI), voertuig, vector en vectorstatus.

## Basisgegevens

- Base URL productie: `https://<radio-asset-management-host>/api/roip/`
- Formaat: JSON
- Authenticatie: gedeelde API key
- Caching: responses bevatten `Cache-Control: no-store`

Gebruik de API alleen via HTTPS.

## Authenticatie

De server verwacht een API key die ook in de `.env` van Radio Asset Management
staat:

```dotenv
ROIP_API_KEYS=<lange-random-key>
```

De client stuurt dezelfde key mee bij elke request. Dat kan op twee manieren.

Voorkeur:

```http
X-API-Key: <lange-random-key>
```

Alternatief:

```http
Authorization: Bearer <lange-random-key>
```

Voor keyrotatie kunnen tijdelijk meerdere keys geconfigureerd worden:

```dotenv
ROIP_API_KEYS=<oude-key>,<nieuwe-key>
```

## Endpoint

### ISSI lookup

```http
GET /api/roip/issi/{issi}/
```

Voorbeeld:

```bash
curl \
  -H "X-API-Key: <lange-random-key>" \
  "https://<radio-asset-management-host>/api/roip/issi/1234567/"
```

De `{issi}` moet numeriek zijn.

## Succesresponse

Status: `200 OK`

```json
{
  "issi": {
    "number": 1234567,
    "alias": "P101",
    "customer": {
      "id": 1,
      "name": "SIAMU",
      "owner": true
    },
    "discipline": {
      "id": 1,
      "name": "Fire",
      "type": "FIRE"
    }
  },
  "subscription": {
    "active": true,
    "dmo_only": false,
    "astrid_alias": "ASTRID P101"
  },
  "radio": {
    "tei": 75000000001,
    "tei_15": "000075000000001",
    "model": "MTP850",
    "model_type": "MOBILE",
    "decommissioned": false,
    "is_active": true,
    "is_dmo_only": false
  },
  "vehicle": {
    "id": 42,
    "number": "P101 - Autopomp",
    "call_sign": "P101",
    "plate": "1-ABC-123",
    "status": 1,
    "status_label": "Actif"
  },
  "vector": {
    "resource_code": "P101",
    "name": "Autopomp 101",
    "abbreviation": "AP101",
    "service": {
      "code": "H1",
      "description": "Hoofdkazerne"
    },
    "resource_type": {
      "code": "AP",
      "description": "Autopomp"
    },
    "status": {
      "code": "AVL",
      "description": "Available",
      "color": "#00AA00"
    }
  }
}
```

## Velden

### `issi`

- `number`: ISSI als nummer
- `alias`: alias zoals gekend in Radio Asset Management
- `customer`: klant/eigenaar van de ISSI, of `null`
- `discipline`: discipline van de ISSI, of `null`

### `subscription`

`null` als de ISSI niet aan een radio gekoppeld is.

- `active`: abonnement actief
- `dmo_only`: DMO-only abonnement
- `astrid_alias`: alias uit ASTRID-export

### `radio`

`null` als er geen gekoppelde radio is.

- `tei`: TEI als nummer
- `tei_15`: TEI als 15-cijferige string met voorloopnullen
- `model`: radiomodel
- `model_type`: `PORTABLE` of `MOBILE`
- `decommissioned`: radio is uit dienst
- `is_active`: berekende status: subscription actief en niet DMO-only
- `is_dmo_only`: berekende DMO-only status

### `vehicle`

`null` als de radio niet aan een voertuig gekoppeld is.

- `id`: interne Fireplan vehicle ID
- `number`: voertuigomschrijving
- `call_sign`: roepnaam, afgeleid uit `number`
- `plate`: nummerplaat
- `status`: numerieke voertuigstatus
- `status_label`: leesbare voertuigstatus

### `vector`

`null` als er geen vector gekoppeld is aan het voertuig.

- `resource_code`: unieke vectorcode
- `name`: vectornaam
- `abbreviation`: afkorting
- `service`: post/dienst, of `null`
- `resource_type`: type resource, of `null`
- `status`: actuele vectorstatus, of `null`

## Foutresponses

### Ontbrekende of foute API key

Status: `401 Unauthorized`

```json
{
  "detail": "Unauthorized"
}
```

### Ongeldige ISSI

Status: `400 Bad Request`

```json
{
  "detail": "ISSI must be numeric"
}
```

### ISSI niet gevonden

Status: `404 Not Found`

```json
{
  "detail": "ISSI not found"
}
```

## Integratieadvies voor RoIP

- Gebruik `tei_15` als je TEI als tekst toont of vergelijkt met scan/AT-output.
- Gebruik `radio.is_active` als snelle indicator dat de radio operationeel op TMO
  zou moeten zijn.
- Behandel `vehicle` en `vector` altijd als optioneel. Een geldige ISSI kan bestaan
  zonder gekoppeld voertuig of vector.
- Cache de response niet in de RoIP-client voor live beslissingen.
- Zet timeouts kort, bijvoorbeeld 1 tot 2 seconden, zodat RoIP niet blokkeert als
  Radio Asset Management tijdelijk niet bereikbaar is.
- Log HTTP-status, ISSI en latency aan clientzijde, maar log de API key nooit.

## Python voorbeeld

```python
import requests

BASE_URL = "https://<radio-asset-management-host>/api/roip"
API_KEY = "<lange-random-key>"


def lookup_issi(issi):
    response = requests.get(
        f"{BASE_URL}/issi/{issi}/",
        headers={"X-API-Key": API_KEY},
        timeout=2,
    )

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json()


data = lookup_issi(1234567)
if data:
    print(data["issi"]["alias"], data["radio"]["tei_15"] if data["radio"] else None)
```
