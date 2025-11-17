# models.py
from django.db import models
from django.utils.html import format_html


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

    radio = models.ForeignKey(        
        "radio.Radio",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
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
