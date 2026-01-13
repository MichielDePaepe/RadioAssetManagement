# fireplan/signals.py
from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from RadioAssetManagement.tasks import enqueue_roip_sync_for_tei
from fireplan.models import Vehicle, Vector


@receiver(post_save, sender=Vehicle)
def on_vehicle_saved(sender, instance: Vehicle, **kwargs) -> None:
    if instance.radio_id:
        pass
        # enqueue_roip_sync_for_tei(instance.radio_id)


@receiver(post_save, sender=Vector)
def on_vector_saved(sender, instance: Vector, **kwargs) -> None:
    vehicle = instance.vehicle
    if vehicle and vehicle.radio_id:
        pass
        # enqueue_roip_sync_for_tei(vehicle.radio_id)