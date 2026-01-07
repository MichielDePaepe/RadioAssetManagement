# radio/tasks.py
from __future__ import annotations

import logging
from celery import shared_task

from .models import ISSI

log = logging.getLogger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 5, "countdown": 10})
def issi_changed_task(self, pk: int) -> None:
    issi = ISSI.objects.get(pk=pk)
    return issi.alias