# fireplan/sync_inventory.py

from __future__ import annotations

import re
from typing import Optional

from dateutil import parser
from django.db import transaction
from django.utils.timezone import make_aware
import logging
logger = logging.getLogger(__name__)

from radio.models import Radio
from .client import FireplanClient
from .models import FireplanInventory, FireplanInventoryRadio, Vehicle


ROOT_UUID_RE = re.compile(
    r"rootInventoriedContainerUuid\s*:\s*'(?P<uuid>[0-9a-fA-F-]{36})'"
)


def extract_root_container_uuid(html: str) -> str:
    m = ROOT_UUID_RE.search(html)
    if not m:
        raise ValueError("Could not find rootInventoriedContainerUuid in HTML.")
    return m.group("uuid")


def parse_fireplan_datetime(value: Optional[str]):
    if not value:
        return None
    dt = parser.parse(value)
    if dt.tzinfo is None:
        dt = make_aware(dt)
    return dt


def sync_closed_inventories_portable_radio_teis(
    *,
    container_name_fr: str = "Cabine de conduite",
    item_type_name_fr: str = "Radio portable Astrid",
    page_size: int = 200,
    max_pages: int = 10000,
    full_sync: bool = False,
) -> int:
    """
    If full_sync=False: incremental sync, stop when records are older/equal than latest closed_at in DB.
    If full_sync=True: scan all pages, only insert missing UUIDs (no stop on date).
    """
    fp = FireplanClient()

    last_closed_at = (
        FireplanInventory.objects.exclude(closed_at__isnull=True)
        .order_by("-closed_at")
        .values_list("closed_at", flat=True)
        .first()
    )

    inserted = 0
    first = 0

    for _ in range(max_pages):
        filters = "{}"
        sort = '[{"field":"closedAt","order":-1}]'

        list_path = (
            f"/fr/api/inventory/inventories-type/close"
            f"?first={first}&rows={page_size}"
            f"&filters={filters}"
            f"&multiSortMeta={sort}"
        )
        r = fp.get(list_path)
        r.raise_for_status()

        records = (r.json() or {}).get("records", [])

        if not records:
            break

        records.sort(key=lambda x: x.get("closedAt") or "", reverse=True)

        for rec in records:
            pass#print(rec)

        page_uuids = [rec.get("uuid") for rec in records if rec.get("uuid")]
        existing = set(
            FireplanInventory.objects.filter(uuid__in=page_uuids).values_list("uuid", flat=True)
        )

        should_stop = False

        for rec in records:
            #print(rec)

            inventory_uuid = rec["uuid"]
            if not inventory_uuid:
                continue

            # always skip existing inventories, but NEVER stop because of that
            if FireplanInventory.objects.filter(uuid=inventory_uuid).exists():
                continue

            closed_at = parse_fireplan_datetime(rec.get("closedAt"))

            # incremental stop condition: we reached already-processed time range
            if (not full_sync) and last_closed_at and closed_at and closed_at <= last_closed_at:
                should_stop = True
                break   # sorted desc → everything after this is older

            vehicle_alpha_code = rec.get("vehicleAlphaCode") or ""
            done_by_full_name = rec.get("doneByFullName") or ""
            overseen_by_full_name = rec.get("overseenByFullName") or ""

            vehicle_obj = None
            if vehicle_alpha_code:
                vehicle_obj = Vehicle.objects.filter(number=vehicle_alpha_code).first()

            html_path = f"/fr/inventory/close/{inventory_uuid}/inventoried-item/list"
            r2 = fp.get(html_path)
            r2.raise_for_status()
            root_uuid = extract_root_container_uuid(r2.text)

            containers_path = (
                f"/fr/api/inventory/close/{root_uuid}/inventoried-item/inventoried-container/list"
            )
            r3 = fp.get(containers_path)
            r3.raise_for_status()
            container_records = (r3.json() or {}).get("records", [])
            container = next(
                (c for c in container_records if c.get("nameFr") == container_name_fr),
                None,
            )

            with transaction.atomic():
                inv_obj = FireplanInventory.objects.create(
                    uuid=inventory_uuid,
                    vehicle_alpha_code=vehicle_alpha_code,
                    vehicle=vehicle_obj,
                    closed_at=closed_at,
                    done_by_full_name=done_by_full_name,
                    overseen_by_full_name=overseen_by_full_name,
                    root_inventoried_container_uuid=root_uuid,
                )

                if container:
                    container_uuid = container["uuid"]

                    items_path = f"/fr/api/inventory/close/{container_uuid}/inventoried-item/list"
                    r4 = fp.get(items_path)
                    r4.raise_for_status()
                    item_records = (r4.json() or {}).get("records", [])

                    for item in item_records:
                        itype = item.get("itemType") or {}
                        if itype.get("nameFr") != item_type_name_fr:
                            continue

                        tracked = item.get("trackedItem") or {}
                        tracked_item_id = tracked.get("id")
                        tei = tracked.get("serialNumber")
                        if not tei:
                            continue

                        radio_obj = None
                        if tracked_item_id is not None:
                            radio_obj = Radio.objects.filter(fireplan_id=tracked_item_id).first()

                        FireplanInventoryRadio.objects.create(
                            inventory=inv_obj,
                            container_uuid=container_uuid,
                            item_uuid=item["uuid"],
                            tracked_item_id=tracked_item_id,
                            tei=str(tei),
                            radio=radio_obj,
                        )

            inserted += 1
            
        if should_stop:
            break

        first += page_size

    return inserted