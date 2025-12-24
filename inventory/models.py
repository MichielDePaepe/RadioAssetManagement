from django.db import models
from django.db.models import Q
from django.utils import timezone
from polymorphic.models import PolymorphicModel
from django.utils.translation import gettext as _




class RadioContainer(PolymorphicModel):
    """High-level place grouping endpoints (vector, dispatch, stock, reserve cabinet)."""
    label = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.label


class VectorContainer(RadioContainer):
    vector = models.OneToOneField(
        "fireplan.Vector",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    post = models.ForeignKey(
        "inventory.Post",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    def save(self, *args, **kwargs):
        if self.vector_id and not self.label:
            self.label = str(self.vector)

        # Auto-fill post from vector.service if post not explicitly provided
        if self.vector and not self.post_id:
            service = getattr(self.vector, "service", None)  # adapt if your field name differs
            if service:
                post, _ = Post.objects.get_or_create(
                    service=service,
                    defaults={"label": str(service)},
                )
                self.post = post

        super().save(*args, **kwargs)



class LocationContainer(RadioContainer):
    class LocationType(models.TextChoices):
        DISPATCH = "DISPATCH", _("Dispatching")
        RESERVE = "RESERVE", _("Reserve cabinet")
        STOCK = "STOCK", _("Stock")
        OTHER = "OTHER", _("Other")

    location_type = models.CharField(max_length=20, choices=LocationType.choices)

    def __str__(self) -> str:
        return self.label or self.location_type


class RadioEndpoint(models.Model):
    """
    Concrete slot in a container (chauffeur, chef, console 1, BULK, ...).
    primary_radio = what should be there normally.
    """
    container = models.ForeignKey(RadioContainer, on_delete=models.CASCADE, related_name="endpoints")
    name = models.CharField(max_length=50)
    allows_multiple = models.BooleanField(default=False)

    primary_radio = models.OneToOneField(
        "radio.Radio",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_for_endpoint",
    )

    @property
    def current_assignment(self):
        """
        Radio currently assigned to this endpoint (open assignment).
        Returns None if empty.
        """
        assignment = (
            self.assignments
            .filter(end_at__isnull=True)
            .order_by("-start_at")
            .first()
        )
        return assignment if assignment else None

    @property
    def current_radio(self):
        return self.current_assignment.radio

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["container", "name"], name="uniq_endpoint_per_container"),
        ]

    def __str__(self) -> str:
        return f"{self.container} – {self.name}"


class RadioAssignment(models.Model):
    """
    History of which radio is currently plugged into an endpoint.
    For non-bulk endpoints: at most 1 open assignment.
    """
    class Reasons(models.TextChoices):
        PRIMARY = "PRIMARY", _("Primary")
        TEMP = "TEMP", _("Temporary replacement")
        STORAGE = "STORAGE", _("Storage")
        REPAIR = "REPAIR", _("Repair")

    radio = models.ForeignKey("radio.Radio", on_delete=models.CASCADE, related_name="assignments")
    endpoint = models.ForeignKey(RadioEndpoint, on_delete=models.CASCADE, related_name="assignments")

    start_at = models.DateTimeField(default=timezone.now)
    end_at = models.DateTimeField(null=True, blank=True)

    reason = models.CharField(max_length=20, choices=Reasons.choices)
    ticket = models.ForeignKey("helpdesk.Ticket", null=True, blank=True, on_delete=models.SET_NULL)

    replaces_radio = models.ForeignKey(
        "radio.Radio",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replaced_by_assignments",
        help_text="If TEMP: which primary radio is being replaced.",
    )

    class Meta:
        indexes = [
            models.Index(fields=["radio", "end_at"]),
            models.Index(fields=["endpoint", "end_at"]),
        ]
        constraints = [
            # A radio can only be current in one place (globally).
            models.UniqueConstraint(
                fields=["radio"],
                condition=Q(end_at__isnull=True),
                name="uniq_open_assignment_per_radio",
            ),
            # For endpoints that are not bulk, we enforce 1 open assignment via service layer
            # (because DB constraints can't easily reference endpoint.allows_multiple).
        ]

    def __str__(self) -> str:
        status = "OPEN" if self.end_at is None else "CLOSED"
        return f"{self.radio} -> {self.endpoint} ({status})"


class Post(models.Model):
    service = models.OneToOneField(
        "fireplan.Service",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inventory_post",
    )
    label = models.CharField(max_length=100)

    def __str__(self):
        return self.label
