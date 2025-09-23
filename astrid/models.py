from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from helpdesk.models import Ticket, TicketType, TicketLog, TicketStatus
from django.utils.translation import gettext as _


class Request(Ticket):
    class RequestType(models.TextChoices):
        VTEI = "VTEI", _("VTEI")
        VISSI = "VISSI", _("VISSI")
        VISSI_VTEI = "VISSI & VTEI", _("VISSI & VTEI")

    old_radio = models.ForeignKey("radio.Radio", on_delete=models.SET_NULL, null=True, blank=True, related_name="requests_as_old")
    old_issi = models.ForeignKey("radio.ISSI", on_delete=models.SET_NULL, null=True, blank=True, related_name="requests_as_old")
    new_issi = models.ForeignKey("radio.ISSI", on_delete=models.SET_NULL, null=True, blank=True, related_name="requests_as_new")
    request_type = models.CharField(max_length=20, choices=RequestType.choices)

    @property
    def new_radio(self):
        return self.radio

    def __str__(self):
        if self.request_type == self.RequestType.VTEI:
            return f"VTEI – from {self.old_radio} to {self.new_radio}"
        elif self.request_type == self.RequestType.VISSI:
            return f"VISSI – from {self.issi_old} to {self.issi_new} on {self.new_radio}"
        elif self.request_type == self.RequestType.VISSI_VTEI:
            return (
                f"VISSI & VTEI – from {self.issi_old} / {self.old_radio} "
                f"to {self.issi_new} / {self.new_radio}"
            )
        return str(self.request_type)

    def save(self, *args, **kwargs):
        astrid_type, created = TicketType.objects.get_or_create(
            code="ASTRID_REQUEST",
            defaults={"name": "Astrid Request"},
        )
        self.ticket_type = astrid_type
        self.title = str(self)

        super().save(*args, **kwargs)


    def clean(self):
        errors = {}

        if self.request_type == self.RequestType.VTEI:
            if not self.old_radio or not self.new_radio:
                errors["old_radio"] = _("Both old and new radio must be set for VTEI.")

        elif self.request_type == self.RequestType.VISSI:
            if not self.issi_old or not self.issi_new or not self.new_radio:
                errors["old_radio"] = _("ISSI old, ISSI new and radio must be set for VISSI.")

        elif self.request_type == self.RequestType.VISSI_VTEI:
            if not (self.radio_old and self.new_radio and self.issi_old and self.issi_new):
                errors["old_radio"] = _("All radio and ISSI fields must be set for VISSI & VTEI.")

        if errors:
            raise ValidationError(errors)

    def start_execution(self, user=None):
        in_progress, created = TicketStatus.objects.get_or_create(
            code="IN_PROGRESS",
            defaults={"name": "In progress"},
        )
        TicketLog.objects.create(
            ticket=self,
            user=user,
            status_after=in_progress,
            note=_("Execution started"),
        )

    def mark_waiting_verification(self, user=None):
        waiting, created = TicketStatus.objects.get_or_create(
            code="WAITING_VERIFICATION",
            defaults={"name": "Waiting for verification"},
        )
        TicketLog.objects.create(
            ticket=self,
            user=user,
            status_after=waiting,
            note=_("Waiting for verification"),
        )

    def mark_verified(self, user=None):
        closed, created = TicketStatus.objects.get_or_create(
            code="CLOSED",
            defaults={"name": "Closed"},
        )
        if self.request_type == self.RequestType.VTEI:
            subscritpion = self.old_radio.subscription
            subscritpion.radio = self.new_radio
            subscritpion.save()

        if self.request_type == self.RequestType.VISSI:
            subscritpion = self.radio.subscription
            subscritpion.issi = self.new_issi
            subscritpion.save()

        TicketLog.objects.create(
            ticket=self,
            user=user,
            status_after=closed,
            note=_("Request verified and closed"),
        )
        issi = self.old_radio.subscription.issi

    def mark_done(self, user=None):
        closed, created = TicketStatus.objects.get_or_create(
            code="CLOSED",
            defaults={"name": "Closed"},
        )
        TicketLog.objects.create(
            ticket=self,
            user=user,
            status_after=closed,
            note=_("Request verified and closed"),
        )

    class Meta:
        permissions = [
            ("has_access_to_myastrid", _("Heeft toegang tot MyAstrid")),
            ("can_verify_requests", _("Kan een aanvraag valideren")),
        ]

