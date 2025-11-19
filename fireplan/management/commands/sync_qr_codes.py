# fireplan/management/commands/sync_fireplan_id.py

from django.core.management.base import BaseCommand
from fireplan.sync import sync_fireplan_id 

class Command(BaseCommand):
    help = "Synchroniseert id's voor radio's uit fireplan"

    def handle(self, *args, **options):
        self.stdout.write("▶ Sync Fireplan id's...")
        sync_fireplan_id()
        self.stdout.write(self.style.SUCCESS("✔ Fireplan sync ready"))
