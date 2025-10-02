from django.db import models
from helpdesk.models import Ticket, TicketType
from django.utils.translation import gettext_lazy as _



class Radio(models.Model):
    TEI = models.BigIntegerField(primary_key=True)
    fireplan_id = models.IntegerField(null=True, blank=True)
    model = models.ForeignKey('RadioModel', null=True, blank=True, on_delete=models.PROTECT)
    decommissioned = models.BooleanField(default=False)

    @property
    def ISSI(self):
        return self.subscription.issi.number if hasattr(self, 'subscription') else None

    @property
    def tei_str(self):
        return f"{self.TEI:014d}"

    @property
    def tei_15_str(self):
        return f"{self.tei_str}0"

    @property
    def alias(self):
        return self.subscription.issi.alias if hasattr(self, 'subscription') else None

    @property
    def is_active(self):
        return self.subscription.active if hasattr(self, 'subscription') else False

    def save(self, *args, **kwargs):
        matching_range = TEIRange.objects.filter(min_tei__lte=self.TEI, max_tei__gte=self.TEI).first()
        if not matching_range:
            raise ValueError(f"Geen RadioModel gevonden voor TEI {self.TEI}")
        self.model = matching_range.model
        super().save(*args, **kwargs)

    def __str__(self):
        tei = f"{self.TEI:014d}"
        if hasattr(self, 'subscription'):
            return "%s - %s" % (tei, str(self.subscription.issi))
        return tei

class RadioModel(models.Model):
    class RadioType(models.TextChoices):
        PORTABLE = "PORTABLE", "Portable"
        MOBILE = "MOBILE", "Mobile"

    name = models.CharField(max_length=100, blank=True)
    is_atex = models.BooleanField(default=False)
    radio_type = models.CharField(
        max_length=10,
        choices=RadioType.choices,
        default=RadioType.PORTABLE,
    )


    def __str__(self):
        return self.name


class TEIRange(models.Model):
    model = models.ForeignKey(RadioModel, on_delete=models.CASCADE)
    min_tei = models.BigIntegerField()
    max_tei = models.BigIntegerField()

    def __str__(self):
        return f"{self.model.name}: {self.min_tei} - {self.max_tei}"



class ISSI(models.Model):
    number = models.BigIntegerField(primary_key=True) 
    alias = models.CharField(max_length=12, blank=True)
    customer = models.ForeignKey('Customer', null=True, blank=True, on_delete=models.CASCADE)
    discipline = models.ForeignKey('Discipline', null=True, blank=True, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        matching_range = ISSICustomerRange.objects.filter(min_issi__lte=self.number, max_issi__gte=self.number).first()
        if matching_range:
            self.customer = matching_range.customer
        else:
            self.customer = None

        matching_range = ISSIDisciplineRange.objects.filter(min_issi__lte=self.number, max_issi__gte=self.number).first()
        if matching_range:
            self.discipline = matching_range.discipline
        else:
            self.discipline = None

        super().save(*args, **kwargs)

    def __str__(self):
        if self.alias:
            return f"{self.number} ({self.alias})"
        return str(self.number)


class Customer(models.Model):
    name = models.CharField(max_length=100)
    owner = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class ISSICustomerRange(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE)
    min_issi = models.BigIntegerField()
    max_issi = models.BigIntegerField()

    def __str__(self):
        return f"{self.customer.name}: {self.min_issi} - {self.max_issi}"


class Discipline(models.Model):
    name = models.CharField(max_length=100)
    bootstrap_class = models.CharField(max_length=100, null=True, blank=True)
    
    def __str__(self):
        return self.name


class ISSIDisciplineRange(models.Model):
    discipline = models.ForeignKey('Discipline', on_delete=models.CASCADE)
    min_issi = models.BigIntegerField()
    max_issi = models.BigIntegerField()

    def __str__(self):
        return f"{self.discipline.name}: {self.min_issi} - {self.max_issi}"


class Subscription(models.Model):
    radio = models.OneToOneField(Radio, on_delete=models.CASCADE, related_name="subscription")
    issi = models.OneToOneField(ISSI, on_delete=models.CASCADE, related_name="subscription")
    astrid_alias = models.CharField(max_length=100, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('radio', 'issi')
        permissions = [
            ("can_upload_subscriptions", "Can upload a subscriptions export from Astrid"),
        ]


class RadioDecommissioningTicket(Ticket):
    """
    Ticket subclass for decommissioning a radio.
    """

    def save(self, *args, **kwargs):
        # Ensure a radio is attached to the ticket
        if not hasattr(self, "radio") or self.radio is None:
            raise ValueError("RadioDecommissioningTicket requires a 'radio' instance.")

        # Ensure the correct TicketType exists
        decommissioning_type, _ = TicketType.objects.get_or_create(
            code="DECOMMISSIONING",
            defaults={"name_en": "Decommissioning"},
        )
        self.ticket_type = decommissioning_type

        # Only set the title on creation, not on every update
        if not self.pk:
            self.title = f"Decommissioning of a {self.radio.model} witgh TEI {self.radio.tei_str}"

        super().save(*args, **kwargs)

    class Meta:
        permissions = [
            (
                "can_create_decommission_requests",
                _("Can create a decommission request"),
            ),
            (
                "can_approve_decommission_requests",
                _("Can approve a decommission request"),
            ),
        ]

