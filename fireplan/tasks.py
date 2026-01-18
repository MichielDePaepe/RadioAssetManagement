# fireplan/tasks.py
from celery import shared_task
from .sync_inventory import sync_closed_inventories_portable_radio_teis


@shared_task
def sync_inventories():
    sync_closed_inventories_portable_radio_teis()