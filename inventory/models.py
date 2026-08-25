from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _


class Location(models.Model):
    class LocationType(models.TextChoices):
        POST = "POST", _("Post")
        DISPATCH = "DISPATCH", _("Dispatching")
        STOCK = "STOCK", _("Stock")
        SMART_CABINET = "SMART_CABINET", _("Intelligent cabinet")
        OTHER = "OTHER", _("Other")

    name = models.CharField(max_length=100)
    location_type = models.CharField(
        max_length=20,
        choices=LocationType.choices,
        default=LocationType.OTHER,
    )
    service = models.ForeignKey(
        "fireplan.Service",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="locations",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    dashboard_vectors = models.ManyToManyField(
        "fireplan.Vector",
        blank=True,
        related_name="dashboard_locations",
        help_text=_("Vectors that belong to this dashboard/location."),
    )
    dashboard_locations = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        related_name="included_in_dashboards",
        help_text=_("Additional locations that belong to this dashboard/location."),
    )
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "name"],
                name="uniq_location_name_per_parent",
            ),
        ]

    def __str__(self):
        if self.parent_id:
            return f"{self.parent} – {self.name}"
        return self.name


class RadioPosition(models.Model):
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    vector = models.ForeignKey(
        "fireplan.Vector",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="radio_positions",
    )
    vehicle = models.ForeignKey(
        "fireplan.Vehicle",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="radio_positions",
    )
    location = models.ForeignKey(
        "inventory.Location",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="radio_positions",
    )

    class Meta:
        ordering = ["order", "name"]
        indexes = [
            models.Index(fields=["vector", "order", "name"]),
            models.Index(fields=["vehicle", "order", "name"]),
            models.Index(fields=["location", "order", "name"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(vector__isnull=False, vehicle__isnull=True, location__isnull=True)
                    | Q(vector__isnull=True, vehicle__isnull=False, location__isnull=True)
                    | Q(vector__isnull=True, vehicle__isnull=True, location__isnull=False)
                ),
                name="position_exactly_one_parent",
            ),
            models.UniqueConstraint(
                fields=["vector", "name"],
                condition=Q(vector__isnull=False),
                name="uniq_position_name_per_vector",
            ),
            models.UniqueConstraint(
                fields=["vehicle", "name"],
                condition=Q(vehicle__isnull=False),
                name="uniq_position_name_per_vehicle",
            ),
            models.UniqueConstraint(
                fields=["location", "name"],
                condition=Q(location__isnull=False),
                name="uniq_position_name_per_location",
            ),
        ]

    @property
    def parent(self):
        return self.vector or self.vehicle or self.location

    @property
    def parent_label(self):
        parent = self.parent
        return str(parent) if parent else ""

    @property
    def active_primary(self):
        return (
            self.assignments
            .filter(role=RadioPositionAssignment.Role.PRIMARY, ended_at__isnull=True)
            .select_related("radio", "radio__model", "radio__subscription__issi")
            .first()
        )

    @property
    def active_substitute(self):
        return (
            self.assignments
            .filter(role=RadioPositionAssignment.Role.SUBSTITUTE, ended_at__isnull=True)
            .select_related("radio", "radio__model", "radio__subscription__issi")
            .first()
        )

    @property
    def operational_assignment(self):
        return self.active_substitute or self.active_primary

    @property
    def operational_radio(self):
        assignment = self.operational_assignment
        return assignment.radio if assignment else None

    def __str__(self):
        label = self.parent_label
        if label:
            return f"{label} – {self.name}"
        return self.name


class RadioPositionAssignment(models.Model):
    class Role(models.TextChoices):
        PRIMARY = "PRIMARY", _("Primary")
        SUBSTITUTE = "SUBSTITUTE", _("Substitute")

    radio = models.ForeignKey(
        "radio.Radio",
        on_delete=models.PROTECT,
        related_name="position_assignments",
    )
    position = models.ForeignKey(
        "inventory.RadioPosition",
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    assigned_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    replaces = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="substitute_assignments",
        help_text=_("Primary assignment replaced by this substitute."),
    )
    created_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_position_assignments",
    )
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-assigned_at", "-id"]
        indexes = [
            models.Index(fields=["radio", "ended_at"]),
            models.Index(fields=["position", "role", "ended_at"]),
            models.Index(fields=["position", "-assigned_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(ended_at__isnull=True) | Q(ended_at__gt=models.F("assigned_at")),
                name="assignment_ends_after_start",
            ),
            models.CheckConstraint(
                check=(
                    Q(role="PRIMARY", replaces__isnull=True)
                    | Q(role="SUBSTITUTE", replaces__isnull=False)
                ),
                name="assignment_replaces_by_role",
            ),
            models.UniqueConstraint(
                fields=["radio"],
                condition=Q(ended_at__isnull=True),
                name="uniq_active_assignment_per_radio",
            ),
            models.UniqueConstraint(
                fields=["position"],
                condition=Q(role="PRIMARY", ended_at__isnull=True),
                name="uniq_active_primary_per_position",
            ),
            models.UniqueConstraint(
                fields=["position"],
                condition=Q(role="SUBSTITUTE", ended_at__isnull=True),
                name="uniq_active_sub_per_position",
            ),
        ]

    @property
    def is_active(self):
        return self.ended_at is None

    def clean(self):
        super().clean()

        if self.role == self.Role.SUBSTITUTE:
            if not self.replaces_id:
                raise ValidationError(_("A substitute assignment must replace an active primary assignment."))
            if self.replaces.role != self.Role.PRIMARY:
                raise ValidationError(_("A substitute assignment can only replace a primary assignment."))
            if self.replaces.position_id != self.position_id:
                raise ValidationError(_("A substitute assignment must replace a primary assignment on the same position."))
            if self.replaces.ended_at is not None:
                raise ValidationError(_("A substitute assignment must replace an active primary assignment."))
            if self.replaces.radio_id == self.radio_id:
                raise ValidationError(_("A substitute radio must be different from the primary radio."))
        elif self.replaces_id:
            raise ValidationError(_("Only substitute assignments can replace another assignment."))

    def __str__(self):
        status = _("active") if self.is_active else _("ended")
        return f"{self.radio} -> {self.position} ({self.role}, {status})"
