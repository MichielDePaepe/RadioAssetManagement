import hmac

from django.conf import settings
from django.http import JsonResponse
from django.views import View

from radio.models import ISSI


def _configured_api_keys():
    return [key for key in getattr(settings, "ROIP_API_KEYS", []) if key]


def _request_api_key(request):
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ").strip()
    return request.headers.get("X-API-Key", "").strip()


def _is_authorized(request):
    supplied_key = _request_api_key(request)
    if not supplied_key:
        return False

    return any(
        hmac.compare_digest(supplied_key, configured_key)
        for configured_key in _configured_api_keys()
    )


def _json_response(data, status=200):
    response = JsonResponse(data, status=status)
    response["Cache-Control"] = "no-store"
    return response


def _object_payload(obj, fields):
    if obj is None:
        return None
    return {field: getattr(obj, field) for field in fields}


def _vehicle_payload(vehicle):
    if vehicle is None:
        return None

    return {
        "id": vehicle.id,
        "number": vehicle.number,
        "call_sign": vehicle.call_sign,
        "plate": vehicle.plate,
        "status": vehicle.status,
        "status_label": vehicle.get_status_display() if vehicle.status is not None else None,
    }


def _vector_payload(vector):
    if vector is None:
        return None

    status = vector.statusCode
    return {
        "resource_code": vector.resourceCode,
        "name": vector.name,
        "abbreviation": vector.abbreviation,
        "service": _object_payload(vector.service, ["code", "description"]),
        "resource_type": _object_payload(vector.resourceTypeCode, ["code", "description"]),
        "status": (
            {
                "code": status.code,
                "description": status.description,
                "color": status.color,
            }
            if status
            else None
        ),
    }


class IssiLookupApiView(View):
    http_method_names = ["get", "head", "options"]

    def dispatch(self, request, *args, **kwargs):
        if not _is_authorized(request):
            return _json_response({"detail": "Unauthorized"}, status=401)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, issi):
        try:
            issi_number = int(issi)
        except (TypeError, ValueError):
            return _json_response({"detail": "ISSI must be numeric"}, status=400)

        issi_obj = (
            ISSI.objects.select_related(
                "customer",
                "discipline",
                "subscription__radio__model",
                "subscription__radio__vehicle__vector__service",
                "subscription__radio__vehicle__vector__resourceTypeCode",
                "subscription__radio__vehicle__vector__statusCode",
            )
            .filter(number=issi_number)
            .first()
        )

        if issi_obj is None:
            return _json_response({"detail": "ISSI not found"}, status=404)

        subscription = getattr(issi_obj, "subscription", None)
        radio = subscription.radio if subscription else None
        vehicle = getattr(radio, "vehicle", None) if radio else None
        vector = getattr(vehicle, "vector", None) if vehicle else None

        data = {
            "issi": {
                "number": issi_obj.number,
                "alias": issi_obj.alias,
                "customer": _object_payload(issi_obj.customer, ["id", "name", "owner"]),
                "discipline": (
                    {
                        "id": issi_obj.discipline.id,
                        "name": issi_obj.discipline.name,
                        "type": issi_obj.discipline.discipline_type,
                    }
                    if issi_obj.discipline
                    else None
                ),
            },
            "subscription": (
                {
                    "active": subscription.active,
                    "dmo_only": subscription.DMO_only,
                    "astrid_alias": subscription.astrid_alias,
                }
                if subscription
                else None
            ),
            "radio": (
                {
                    "tei": radio.TEI,
                    "tei_15": radio.tei_15_str,
                    "model": radio.model.name if radio.model else None,
                    "model_type": radio.model.radio_type if radio.model else None,
                    "decommissioned": radio.decommissioned,
                    "is_active": radio.is_active,
                    "is_dmo_only": radio.is_DMO_only,
                }
                if radio
                else None
            ),
            "vehicle": _vehicle_payload(vehicle),
            "vector": _vector_payload(vector),
        }

        return _json_response(data)
