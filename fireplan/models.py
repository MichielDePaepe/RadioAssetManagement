# fireplan/models.py

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.html import format_html

from .auth_models import *


class VehicleStatus(models.IntegerChoices):
    ACTIF = 1, "Actif"
    REBUTE = 2, "Rebuté"
    PREPARATION = 3, "Préparation"



class Vehicle(models.Model):
    id = models.IntegerField(primary_key=True)
    number = models.CharField(max_length=50)
    call_sign = models.CharField(max_length=50, blank=True)
    num_letter = models.CharField(max_length=5)
    num_value = models.IntegerField()
    plate = models.CharField(max_length=20)
    utilisation = models.CharField(max_length=200)
    chassis = models.CharField(max_length=100)
    status = models.IntegerField(
        choices=VehicleStatus.choices,
        null=True,
    )

    radio = models.OneToOneField(
        "radio.Radio",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vehicle",
    )

    def save(self, *args, **kwargs):
        if self.number:
            self.call_sign = self.number.split(" - ")[0]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.number



class Service(models.Model):
    code = models.CharField(max_length=20, primary_key=True)
    description = models.CharField(max_length=100)

    def __str__(self):
        return self.code


class ResourceTypeCode(models.Model):
    code = models.CharField(max_length=20, primary_key=True)
    description = models.CharField(max_length=100)

    def __str__(self):
        return self.code


class StatusCode(models.Model):
    code = models.CharField(max_length=20, primary_key=True)
    description = models.CharField(max_length=100)
    color = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.code} – {self.description}"

    def as_html(self):
        """HTML weergave met bol + tekst (voor admin/templates)."""
        col = self.color or "#999"

        return format_html(
            '<span style="display:inline-flex; align-items:center;">'
            '  <span style="width:12px; height:12px; border-radius:50%; '
            '        background-color:{}; display:inline-block; margin-right:6px;"></span>'
            '  {}'
            '</span>',
            col,
            str(self),
        )

    def status_icon_html(self):
        col = self.color or "#999"
        text = self.description or self.code

        return format_html(
            '<span style="width:12px; height:12px; border-radius:50%; '
            'display:inline-block; background-color:{}; margin-right:6px; position:relative;" '
            'onmouseover="this.nextElementSibling.style.display=\'inline-block\'" '
            'onmouseout="this.nextElementSibling.style.display=\'none\'"></span>'
            '<span style="display:none; background:#333; color:#fff; padding:2px 6px; '
            'font-size:11px; border-radius:4px; position:absolute; white-space:nowrap; '
            'transform:translateY(150%);">{}</span>',
            col,
            text,
        )



class Vector(models.Model):
    resourceCode = models.CharField(max_length=50, primary_key=True)

    vehicle = models.OneToOneField(
        "fireplan.Vehicle",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vector"
    )

    name = models.CharField(max_length=100, blank=True)
    abbreviation = models.CharField(max_length=50, blank=True)

    service = models.ForeignKey(
        "Service",
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    resourceTypeCode = models.ForeignKey(
        "ResourceTypeCode",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    statusCode = models.ForeignKey(
        "StatusCode",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    orderServiceAbbreviation = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.resourceCode} ({self.name})"


class FireplanInventory(models.Model):
    uuid = models.UUIDField(primary_key=True)

    vehicle_alpha_code = models.CharField(max_length=16, db_index=True)

    vehicle = models.ForeignKey(
        "fireplan.Vehicle",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventories",
    )

    closed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    done_by_full_name = models.CharField(max_length=128, blank=True, default="")
    overseen_by_full_name = models.CharField(max_length=128, blank=True, default="")

    root_inventoried_container_uuid = models.UUIDField(null=True, blank=True, db_index=True)

    synced_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.closed_at:
            return f"{self.vehicle_alpha_code} – {self.closed_at:%Y-%m-%d %H:%M}"
        return f"{self.vehicle_alpha_code} – {self.uuid}"


class FireplanInventoryRadio(models.Model):
    """
    0..N radios per inventory.
    We store:
      - tracked_item_id (Fireplan trackedItem.id) so you can link to radio.models.Radio.fireplan_id
      - optional FK to Radio if found at sync time
      - TEI (trackedItem.serialNumber)
    """
    inventory = models.ForeignKey(
        FireplanInventory,
        on_delete=models.CASCADE,
        related_name="radios",
    )

    container_uuid = models.UUIDField(db_index=True)
    item_uuid = models.UUIDField(db_index=True)

    tracked_item_id = models.IntegerField(db_index=True, null=True, blank=True)
    tei = models.CharField(max_length=64, db_index=True)

    radio = models.ForeignKey(
        "radio.Radio",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fireplan_inventory_radios",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["inventory", "item_uuid"],
                name="uniq_fireplan_inventory_radio_item",
            ),
        ]

    def __str__(self):
        return f"{self.tei} ({self.inventory.vehicle_alpha_code})"