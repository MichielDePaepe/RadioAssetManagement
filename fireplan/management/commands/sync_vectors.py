# fireplan/management/commands/sync_vectors.py

from django.core.management.base import BaseCommand
from fireplan.sync import sync_vectors

class Command(BaseCommand):
    help = "Synchroniseert vectoren"

    def handle(self, *args, **options):
        self.stdout.write("▶ Sync vectors...")
        sync_vectors()
        self.stdout.write(self.style.SUCCESS("✔ Vector sync ready"))
