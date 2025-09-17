from django.db import models
from organization.models import RadioContainerLink
from django.utils.translation import gettext_lazy as _

class Cabinet(models.Model):
    name = models.CharField(max_length=50, unique=True)
    location = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class CabinetSlot(RadioContainerLink):
    class State(models.TextChoices):
        EMPTY = "empty", _("Empty")
        SPARE = "spare", _("Spare radio")
        DEFECT = "defect", _("Defecte radio")
        IN_USE = "in_use", _("In use")

    cabinet = models.ForeignKey(Cabinet, on_delete=models.CASCADE, related_name="slots")
    state = models.CharField(max_length=20, choices=State.choices, default=State.EMPTY)

    class Meta:
        ordering = ["cabinet", "name"]

    def __str__(self):
        return f"{self.name} ({self.cabinet})"


class CabinetLog(models.Model):
    class Type(models.TextChoices):
        TAKEN = "taken", _("Taken")
        RETURNED = "returned", _("Returned")
        SWAP = "swap", _("Swap")

    slot = models.ForeignKey(CabinetSlot, on_delete=models.CASCADE, related_name="logs")
    radio_in = models.ForeignKey("radio.Radio", on_delete=models.SET_NULL, null=True, blank=True, related_name="log_in")
    radio_out = models.ForeignKey("radio.Radio", on_delete=models.SET_NULL, null=True, blank=True, related_name="log_out")
    type = models.CharField(max_length=20, choices=Type.choices)
    user = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.log_type} - {self.slot} @ {self.timestamp}"
