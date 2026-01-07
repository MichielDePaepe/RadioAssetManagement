# RadioAssetManagement/tasks.py
from __future__ import annotations

import logging
from typing import Any, Iterable, Union

from celery import shared_task
from django.apps import apps
from django.db import transaction
import requests
from django.conf import settings

log = logging.getLogger(__name__)


def enqueue_roip_sync_for_tei(teI_or_list: Union[int, Iterable[int]]) -> None:
    # Normalize to list[int]
    if isinstance(teI_or_list, int):
        tei_list = [teI_or_list]
    else:
        tei_list = [int(x) for x in teI_or_list]

    # Deduplicate, keep stable order
    seen: set[int] = set()
    tei_list = [x for x in tei_list if not (x in seen or seen.add(x))]

    if not tei_list:
        return

    transaction.on_commit(lambda: roip_sync_radios_snapshot.delay(tei_list))


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 5, "countdown": 10})
def roip_sync_radios_snapshot(self, tei_list: list[int]) -> dict[str, int]:
    """
    Build one payload line per TEI, in a single task run.
    """
    Radio = apps.get_model("radio", "Radio")

    radios = (
        Radio.objects
        .filter(TEI__in=tei_list)
        .select_related("subscription__issi", "vehicle__vector")
    )

    payload_lines: list[dict[str, Any]] = []
    for r in radios:
        sub = getattr(r, "subscription", None)
        issi = getattr(sub, "issi", None) if sub else None

        vehicle = getattr(r, "vehicle", None)
        vector = getattr(vehicle, "vector", None) if vehicle else None

        payload_lines.append(
            {
                "tei": int(r.TEI),
                "issi": int(issi.number) if issi else None,
                "issi_alias": (issi.alias or None) if issi else None,
                "vehicle_call_sign": (vehicle.call_sign or None) if vehicle else None,
                "vector_abbreviation": (vector.abbreviation or None) if vector else None,
            }
        )

    log.info("ROIP sync batch size=%s", len(payload_lines))

    payload = {"items": payload_lines}

    resp = requests.post(
        settings.ROIP_INGEST_URL,
        json=payload,
        headers={
            "X-RAM-TOKEN": settings.ROIP_INGEST_TOKEN,
            "Content-Type": "application/json",
        },
        timeout=getattr(settings, "ROIP_HTTP_TIMEOUT", 5),
    )

    resp.raise_for_status()

    return {"requested": len(tei_list), "built": len(payload_lines)}