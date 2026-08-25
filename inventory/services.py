from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from .models import RadioPosition, RadioPositionAssignment


def _active_assignments_for_update(position):
    return (
        RadioPositionAssignment.objects
        .select_for_update()
        .filter(position=position, ended_at__isnull=True)
        .select_related("radio", "position")
    )


def _radio_has_active_assignment(radio, exclude_position=None):
    qs = RadioPositionAssignment.objects.filter(radio=radio, ended_at__isnull=True)
    if exclude_position is not None:
        qs = qs.exclude(position=exclude_position)
    return qs.exists()


@transaction.atomic
def change_primary(position, radio, user=None, note=""):
    position = RadioPosition.objects.select_for_update().get(pk=position.pk)
    active_assignments = list(_active_assignments_for_update(position))
    active_primary = next(
        (assignment for assignment in active_assignments if assignment.role == RadioPositionAssignment.Role.PRIMARY),
        None,
    )
    active_substitute = next(
        (assignment for assignment in active_assignments if assignment.role == RadioPositionAssignment.Role.SUBSTITUTE),
        None,
    )

    if active_primary and active_primary.radio_id == radio.pk:
        return active_primary

    if _radio_has_active_assignment(radio, exclude_position=position):
        raise ValidationError(_("This radio already has an active position assignment."))

    now = timezone.now()
    if active_substitute:
        active_substitute.ended_at = now
        active_substitute.save(update_fields=["ended_at"])

    if active_primary:
        active_primary.ended_at = now
        active_primary.save(update_fields=["ended_at"])

    assignment = RadioPositionAssignment(
        position=position,
        radio=radio,
        role=RadioPositionAssignment.Role.PRIMARY,
        assigned_at=now,
        created_by=user if getattr(user, "is_authenticated", False) else None,
        note=note,
    )
    assignment.full_clean()
    assignment.save()
    return assignment


@transaction.atomic
def assign_substitute(position, radio, user=None, note=""):
    position = RadioPosition.objects.select_for_update().get(pk=position.pk)
    active_assignments = list(_active_assignments_for_update(position))
    active_primary = next(
        (assignment for assignment in active_assignments if assignment.role == RadioPositionAssignment.Role.PRIMARY),
        None,
    )
    active_substitute = next(
        (assignment for assignment in active_assignments if assignment.role == RadioPositionAssignment.Role.SUBSTITUTE),
        None,
    )

    if not active_primary:
        raise ValidationError(_("A substitute can only be assigned when the position has an active primary radio."))

    if active_substitute:
        raise ValidationError(_("This position already has an active substitute radio."))

    if active_primary.radio_id == radio.pk:
        raise ValidationError(_("The substitute radio must be different from the primary radio."))

    if _radio_has_active_assignment(radio):
        raise ValidationError(_("This radio already has an active position assignment."))

    assignment = RadioPositionAssignment(
        position=position,
        radio=radio,
        role=RadioPositionAssignment.Role.SUBSTITUTE,
        replaces=active_primary,
        created_by=user if getattr(user, "is_authenticated", False) else None,
        note=note,
    )
    assignment.full_clean()
    assignment.save()
    return assignment


@transaction.atomic
def release_substitute(position, user=None, note=""):
    position = RadioPosition.objects.select_for_update().get(pk=position.pk)
    active_substitute = (
        _active_assignments_for_update(position)
        .filter(role=RadioPositionAssignment.Role.SUBSTITUTE)
        .first()
    )
    if not active_substitute:
        raise ValidationError(_("This position has no active substitute radio."))

    active_substitute.ended_at = timezone.now()
    if note:
        active_substitute.note = "\n".join(filter(None, [active_substitute.note, note]))
        active_substitute.save(update_fields=["ended_at", "note"])
    else:
        active_substitute.save(update_fields=["ended_at"])
    return active_substitute


@transaction.atomic
def release_primary(position, user=None, note=""):
    position = RadioPosition.objects.select_for_update().get(pk=position.pk)
    active_assignments = list(_active_assignments_for_update(position))
    active_primary = next(
        (assignment for assignment in active_assignments if assignment.role == RadioPositionAssignment.Role.PRIMARY),
        None,
    )

    if not active_primary:
        raise ValidationError(_("This position has no active primary radio."))

    active_primary.ended_at = timezone.now()
    if note:
        active_primary.note = "\n".join(filter(None, [active_primary.note, note]))
        active_primary.save(update_fields=["ended_at", "note"])
    else:
        active_primary.save(update_fields=["ended_at"])
    return active_primary
