# fireplan/views.py

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from django.views.generic import TemplateView

from .models import FireplanInventory


class LatestInventoryPerVectorView(TemplateView):
    template_name = "fireplan/latest_inventory_per_vector.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        since = timezone.now() - timedelta(days=7)

        inventories = (
            FireplanInventory.objects.filter(closed_at__gte=since)
            .select_related("vehicle", "vehicle__vector")
            .prefetch_related("radios", "radios__radio", "radios__radio__subscription__issi")
            .order_by("-closed_at")  # newest first
        )

        latest_per_vector: dict[str, dict] = {}

        for inv in inventories:
            veh = inv.vehicle
            vector = getattr(veh, "vector", None) if veh else None
            if not vector:
                continue
            key = vector.resourceCode if vector else None

            if key not in latest_per_vector:
                latest_per_vector[key] = {"vector": vector, "vehicle": veh, "inventory": inv}


        ctx["since"] = since
        ctx["latest_rows"] = sorted(
            latest_per_vector.values(),
            key=lambda r: (r["vector"].resourceCode if r["vector"] else "")
        )
        return ctx