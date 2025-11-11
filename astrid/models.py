from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from helpdesk.models import Ticket, TicketType, TicketLog, TicketStatus
from django.utils.translation import gettext as _
from radio.models import *

class Request(Ticket):
    class RequestType(models.TextChoices):
        VTEI = "VTEI", _("VTEI")
        VISSI = "VISSI", _("VISSI")
        VISSI_VTEI = "VISSI & VTEI", _("VISSI & VTEI")
        ACTIVATION = "ACTIVATION", _("Activation")

    old_radio = models.ForeignKey("radio.Radio", on_delete=models.SET_NULL, null=True, blank=True, related_name="requests_as_old")
    old_issi = models.ForeignKey("radio.ISSI", on_delete=models.SET_NULL, null=True, blank=True, related_name="requests_as_old")
    new_issi = models.ForeignKey("radio.ISSI", on_delete=models.SET_NULL, null=True, blank=True, related_name="requests_as_new")
    request_type = models.CharField(max_length=20, choices=RequestType.choices)

    @property
    def new_radio(self):
        return self.radio

    def save(self, *args, **kwargs):
        astrid_type, created = TicketType.objects.get_or_create(
            code="ASTRID_REQUEST",
            defaults={"name": "Astrid Request"},
        )
        self.ticket_type = astrid_type

        title = ""
        if self.request_type == self.RequestType.VTEI:
            title = f"VTEI – from {self.old_radio.tei_str} {self.old_radio.model} to {self.new_radio.tei_str} {self.new_radio.model}, ISSI {self.old_issi}"
        elif self.request_type == self.RequestType.VISSI:
            title = f"VISSI – from {self.old_issi} to {self.new_issi} on {self.new_radio.tei_str} {self.new_radio.model}"
        elif self.request_type == self.RequestType.VISSI_VTEI:
            title = f"VISSI & VTEI - from {self.old_radio.tei_str} {self.old_radio.model}, ISSI {self.old_issi} to {self.new_radio.tei_str} {self.new_radio.model}, ISSI {self.new_issi}"
        elif self.request_type == self.RequestType.ACTIVATION:
            title = f"Activation - {self.new_radio.tei_str} {self.new_radio.model} with ISSI {self.new_issi}"

        self.title = title

        super().save(*args, **kwargs)


    def clean(self):
        errors = {}

        if self.request_type == self.RequestType.VTEI:
            if not self.old_radio or not self.new_radio:
                errors["old_radio"] = _("Both old and new radio must be set for VTEI.")

        elif self.request_type == self.RequestType.VISSI:
            if not self.old_issi or not self.new_issi or not self.new_radio:
                errors["old_radio"] = _("ISSI old, ISSI new and radio must be set for VISSI.")

        elif self.request_type == self.RequestType.VISSI_VTEI:
            if not (self.old_radio and self.new_radio and self.old_issi and self.new_issi):
                errors["old_radio"] = _("All radio and ISSI fields must be set for VISSI & VTEI.")

        if errors:
            raise ValidationError(errors)

    def set_open(self, user=None, note=""):
        in_progress, created = TicketStatus.objects.get_or_create(
            code="IN_PROGRESS",
            defaults={"name_en": "In progress"},
        )
        TicketLog.objects.create(
            ticket=self,
            user=user,
            status_after=in_progress,
            note=note or _("Execution started"),
        )


    def start_execution(self, user=None, note=""):
        in_progress, created = TicketStatus.objects.get_or_create(
            code="IN_PROGRESS",
            defaults={"name_en": "In progress"},
        )
        TicketLog.objects.create(
            ticket=self,
            user=user,
            status_after=in_progress,
            note=note or _("Execution started"),
        )

    def mark_waiting_verification(self, user=None, note=""):
        waiting, created = TicketStatus.objects.get_or_create(
            code="WAITING_VERIFICATION",
            defaults={"name_en": "Waiting for verification"},
        )
        TicketLog.objects.create(
            ticket=self,
            user=user,
            status_after=waiting,
            note=note or _("Waiting for verification"),
        )

    def mark_verified(self, user=None, note=""):
        closed, created = TicketStatus.objects.get_or_create(
            code="CLOSED",
            defaults={"name_en": "Closed"},
        )

        # Remove old subscription
        old_subscription = getattr(self.old_radio, "subscription", None)
        if old_subscription:
            old_subscription.delete()
        
        # Add new subscription
        if self.request_type == self.RequestType.VTEI:
            Subscription.objects.create(
                radio = self.new_radio,
                issi = self.old_issi
            )

        if self.request_type == self.RequestType.VISSI:
            Subscription.objects.create(
                radio = self.old_radio,
                issi = self.new_issi
            )

        if self.request_type == self.RequestType.VISSI_VTEI:
            Subscription.objects.create(
                radio = self.new_radio,
                issi = self.new_issi
            )

        TicketLog.objects.create(
            ticket=self,
            user=user,
            status_after=closed,
            note=note or _("Request verified and closed"),
        )


    def mark_closed(self, user=None, note=""):
        closed, created = TicketStatus.objects.get_or_create(
            code="CLOSED",
            defaults={"name_en": "Closed"},
        )
        TicketLog.objects.create(
            ticket=self,
            user=user,
            status_after=closed,
            note=note or _("Request verified and closed"),
        )

    def add_log(self, user=None, note=""):
        """Add a log entry without changing the ticket status."""
        TicketLog.objects.create(
            ticket=self,
            user=user,
            status_after=self.status,
            note=note,
        )

    class Meta:
        permissions = [
            ("has_access_to_myastrid", _("Heeft toegang tot MyAstrid")),
            ("can_verify_requests", _("Kan een aanvraag valideren")),
        ]

