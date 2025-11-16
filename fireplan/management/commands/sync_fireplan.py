# fireplan/management/commands/sync_fireplan.py

from django.core.management.base import BaseCommand
from fireplan.sync import sync_fireplan_fleet 

class Command(BaseCommand):
    help = "Synchroniseert Fireplan voertuigen"

    def handle(self, *args, **options):
        self.stdout.write("▶ Sync Fireplan fleet...")
        sync_fireplan_fleet()
        self.stdout.write(self.style.SUCCESS("✔ Fireplan sync ready"))
