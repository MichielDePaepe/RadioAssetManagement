# roip/management/commands/mqtt_to_channels.py

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import paho.mqtt.client as mqtt
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.management.base import BaseCommand
from django.conf import settings


from fireplan.models import Vehicle, Vector
from radio.models import ISSI, Subscription

log = logging.getLogger(__name__)


def enrich_event(payload: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(payload)

    issi_number = payload.get("issi")
    if not issi_number:
        return enriched

    # Best path: subscription exists -> 1 query gets everything (ISSI + Radio + Vehicle + Vector)
    sub = (
        Subscription.objects.select_related(
            "issi",
            "issi__customer",
            "issi__discipline",
            "radio",
            "radio__model",
            "radio__vehicle",
            "radio__vehicle__vector",
            "radio__vehicle__vector__service",
            "radio__vehicle__vector__resourceTypeCode",
            "radio__vehicle__vector__statusCode",
        )
        .filter(issi_id=issi_number)
        .first()
    )

    if sub is not None:
        issi = sub.issi
        enriched["issi"] = {
            "number": issi.number,
            "alias": issi.alias,
            "customer": getattr(issi.customer, "name", None),
            "discipline": getattr(issi.discipline, "name", None),
        }
        enriched["alias"] = issi.alias

        radio = sub.radio
        enriched["radio"] = {
            "TEI": radio.TEI,
            "tei_str": radio.tei_str,
            "fireplan_id": radio.fireplan_id,
            "model": getattr(radio.model, "name", None),
            "decommissioned": radio.decommissioned,
            "is_active": radio.is_active,
            "is_dmo_only": radio.is_DMO_only,
        }
        enriched["TEI"] = radio.TEI
        enriched["fireplan_id"] = radio.fireplan_id

        v: Vehicle | None = getattr(radio, "vehicle", None)
        if v is not None:
            enriched["vehicle"] = {
                "id": v.id,
                "number": v.number,
                "call_sign": v.call_sign,
                "plate": v.plate,
                "status": v.status,
                "utilisation": v.utilisation,
                "chassis": v.chassis,
            }

            vec: Vector | None = getattr(v, "vector", None)
            if vec is not None:
                sc = vec.statusCode
                enriched["vector"] = {
                    "resourceCode": vec.resourceCode,
                    "name": vec.name,
                    "abbreviation": vec.abbreviation,
                    "orderServiceAbbreviation": vec.orderServiceAbbreviation,
                    "service": getattr(vec.service, "code", None),
                    "resourceTypeCode": getattr(vec.resourceTypeCode, "code", None),
                    "statusCode": getattr(sc, "code", None),
                    "statusDescription": getattr(sc, "description", None),
                    "statusColor": getattr(sc, "color", None),
                }

        return enriched

    # Fallback: ISSI exists without subscription
    issi = ISSI.objects.select_related("customer", "discipline").filter(number=issi_number).first()
    if issi is not None:
        enriched["issi"] = {
            "number": issi.number,
            "alias": issi.alias,
            "customer": getattr(issi.customer, "name", None),
            "discipline": getattr(issi.discipline, "name", None),
        }
        enriched["alias"] = issi.alias

    return enriched


class Command(BaseCommand):
    help = "Subscribe to MQTT RoIP events and forward enriched events to Django Channels."

    def handle(self, *args: Any, **options: Any) -> None:
        mqtt_host = settings.MQTT_HOST
        mqtt_port = settings.MQTT_PORT
        mqtt_user = settings.MQTT_USERNAME
        mqtt_pass = settings.MQTT_PASSWORD

        topic = settings.ROIP_MQTT_TOPIC
        group_name = settings.ROIP_CHANNEL_GROUP

        channel_layer = get_channel_layer()
        if channel_layer is None:
            raise RuntimeError("CHANNEL_LAYERS not configured")

        client = mqtt.Client(client_id=f"ram-mqtt-bridge-{int(time.time())}", clean_session=True)
        if mqtt_user:
            client.username_pw_set(mqtt_user, mqtt_pass)

        client.reconnect_delay_set(min_delay=1, max_delay=30)

        def on_connect(_client: mqtt.Client, _userdata: Any, _flags: dict[str, Any], rc: int) -> None:
            if rc == 0:
                log.info("MQTT connected; subscribing topic=%s", topic)
                _client.subscribe(topic, qos=1)
            else:
                log.error("MQTT connect failed rc=%s", rc)

        def on_message(_client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage) -> None:
            try:
                payload = json.loads(msg.payload.decode("utf-8"))
            except Exception:
                log.exception("Invalid JSON on %s", msg.topic)
                return

            payload["mqtt_topic"] = msg.topic
            enriched = enrich_event(payload)

            async_to_sync(channel_layer.group_send)(
                group_name,
                {"type": "tx_event", "data": enriched},
            )

        client.on_connect = on_connect
        client.on_message = on_message

        log.info("Connecting to MQTT %s:%s", mqtt_host, mqtt_port)
        client.connect(mqtt_host, mqtt_port, keepalive=30)
        client.loop_forever()