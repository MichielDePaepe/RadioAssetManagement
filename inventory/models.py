from django.db import models

class InventoryEntry(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    radio = models.ForeignKey('radio.Radio', on_delete=models.CASCADE, related_name="inventory_entries")
    container = models.ForeignKey('organization.Container', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.radio} in {self.container} @ {self.timestamp}'

    class Meta:
        get_latest_by = 'timestamp'
        ordering = ['timestamp']
