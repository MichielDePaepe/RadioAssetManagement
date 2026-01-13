# radio/signals.py
from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from RadioAssetManagement.tasks import enqueue_roip_sync_for_tei
from radio.models import ISSI, Subscription


@receiver(post_save, sender=ISSI)
def on_issi_saved(sender, instance: ISSI, **kwargs) -> None:
    sub = (
        Subscription.objects
        .filter(issi=instance)
        .select_related("radio")
        .first()
    )
    if sub and sub.radio_id:
        pass
        # enqueue_roip_sync_for_tei(sub.radio_id)