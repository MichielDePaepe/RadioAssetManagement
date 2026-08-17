# fireplan/views.py

from __future__ import annotations

from datetime import timedelta

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import TemplateView

from .models import FireplanInventory, Vector


def inventory_radio_identity(inventory_radio):
    if inventory_radio.radio_id:
        return ("radio", inventory_radio.radio_id)
    tei = (inventory_radio.tei or "").strip().lstrip("0")
    if tei:
        return ("tei", tei)
    return None


class LatestInventoryPerVectorView(TemplateView):
    template_name = "fireplan/latest_inventory_per_vector.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        stale_before = timezone.now() - timedelta(days=14)

        inventories = (
            FireplanInventory.objects.filter(closed_at__isnull=False)
            .select_related("vehicle", "vehicle__vector", "vector")
            .prefetch_related("radios", "radios__radio", "radios__radio__subscription__issi")
            .order_by("-closed_at")  # newest first
        )

        latest_per_vector: dict[str, dict] = {}

        for inv in inventories:
            veh = inv.vehicle
            vector = inv.vector or (getattr(veh, "vector", None) if veh else None)
            if not vector:
                continue
            key = vector.resourceCode if vector else None

            if key not in latest_per_vector:
                latest_per_vector[key] = {
                    "vector": vector,
                    "vehicle": veh,
                    "inventory": inv,
                    "is_stale": inv.closed_at < stale_before,
                }


        latest_rows = sorted(
            latest_per_vector.values(),
            key=lambda r: (
                r["vector"].orderServiceAbbreviation or "",
                r["vector"].name or "",
                r["vector"].resourceCode or "",
            )
        )

        latest_seen_by_radio = {}
        for row in latest_rows:
            inv = row["inventory"]
            for inventory_radio in inv.radios.all():
                identity = inventory_radio_identity(inventory_radio)
                if not identity:
                    continue
                seen_at = inv.closed_at
                if identity not in latest_seen_by_radio or seen_at > latest_seen_by_radio[identity]:
                    latest_seen_by_radio[identity] = seen_at

        superseded_inventory_radio_ids = set()
        for row in latest_rows:
            inv = row["inventory"]
            for inventory_radio in inv.radios.all():
                identity = inventory_radio_identity(inventory_radio)
                if identity and inv.closed_at < latest_seen_by_radio[identity]:
                    superseded_inventory_radio_ids.add(inventory_radio.id)

        ctx["stale_before"] = stale_before
        ctx["latest_rows"] = latest_rows
        ctx["superseded_inventory_radio_ids"] = superseded_inventory_radio_ids
        return ctx


class VectorInventoryHistoryView(TemplateView):
    template_name = "fireplan/vector_inventory_history.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        vector = get_object_or_404(Vector, pk=kwargs["resource_code"])
        inventories = (
            FireplanInventory.objects.filter(
                Q(vector=vector) | Q(vehicle__vector=vector)
            )
            .select_related("vehicle", "vector")
            .prefetch_related("radios", "radios__radio", "radios__radio__subscription__issi")
            .order_by("-closed_at", "-synced_at")
            .distinct()
        )

        ctx["vector"] = vector
        ctx["inventories"] = inventories
        return ctx
