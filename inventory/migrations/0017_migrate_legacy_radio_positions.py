from django.db import migrations
from django.utils import timezone


def _create_assignment(Assignment, position, radio_id, role, assigned_at=None, ended_at=None, replaces=None, note=""):
    if not radio_id:
        return None
    if ended_at is None and Assignment.objects.filter(radio_id=radio_id, ended_at__isnull=True).exists():
        return None
    if ended_at is None and Assignment.objects.filter(position=position, role=role, ended_at__isnull=True).exists():
        return None
    return Assignment.objects.create(
        position=position,
        radio_id=radio_id,
        role=role,
        assigned_at=assigned_at or timezone.now(),
        ended_at=ended_at,
        replaces=replaces,
        note=note,
    )


def _location_for_name(Location, name, location_type="OTHER", parent=None):
    location, created = Location.objects.get_or_create(
        parent=parent,
        name=name or "Location",
        defaults={"location_type": location_type},
    )
    if created:
        return location
    if location.location_type == "OTHER" and location_type != "OTHER":
        location.location_type = location_type
        location.save(update_fields=["location_type"])
    return location


def _position_for_parent(Position, name, vector_id=None, vehicle_id=None, location=None, order=0):
    kwargs = {"name": name or "Position"}
    if vector_id:
        kwargs["vector_id"] = vector_id
    elif vehicle_id:
        kwargs["vehicle_id"] = vehicle_id
    else:
        kwargs["location"] = location
    position, _ = Position.objects.get_or_create(defaults={"order": order or 0}, **kwargs)
    return position


def _migrate_inventory_endpoints(apps, schema_editor):
    Location = apps.get_model("inventory", "Location")
    Position = apps.get_model("inventory", "RadioPosition")
    Assignment = apps.get_model("inventory", "RadioPositionAssignment")
    RadioEndpoint = apps.get_model("inventory", "RadioEndpoint")
    RadioAssignment = apps.get_model("inventory", "RadioAssignment")
    VectorContainer = apps.get_model("inventory", "VectorContainer")
    LocationContainer = apps.get_model("inventory", "LocationContainer")
    RadioContainer = apps.get_model("inventory", "RadioContainer")

    location_type_map = {
        "DISPATCH": "DISPATCH",
        "RESERVE": "STOCK",
        "STOCK": "STOCK",
        "OTHER": "OTHER",
    }

    for endpoint in RadioEndpoint.objects.select_related("container").order_by("id"):
        vector_id = None
        location = None
        container_id = endpoint.container_id

        vector_container = VectorContainer.objects.filter(pk=container_id).first()
        if vector_container and vector_container.vector_id:
            vector_id = vector_container.vector_id
        else:
            location_container = LocationContainer.objects.filter(pk=container_id).first()
            if location_container:
                location = _location_for_name(
                    Location,
                    location_container.label,
                    location_type_map.get(location_container.location_type, "OTHER"),
                )
            else:
                container = RadioContainer.objects.filter(pk=container_id).first()
                location = _location_for_name(Location, getattr(container, "label", "") or "Legacy container")

        position = _position_for_parent(
            Position,
            endpoint.name,
            vector_id=vector_id,
            location=location,
        )

        legacy_assignments = RadioAssignment.objects.filter(endpoint=endpoint).order_by("start_at", "id")
        for legacy in legacy_assignments:
            role = "SUBSTITUTE" if legacy.reason == "TEMP" else "PRIMARY"
            replaces = None
            if role == "SUBSTITUTE":
                replaces = Assignment.objects.filter(
                    position=position,
                    role="PRIMARY",
                    ended_at__isnull=True,
                ).first()
                if not replaces:
                    continue
            note = ""
            if legacy.reason not in ("PRIMARY", "TEMP"):
                note = f"Migrated from legacy assignment reason: {legacy.reason}"
            _create_assignment(
                Assignment,
                position,
                legacy.radio_id,
                role,
                assigned_at=legacy.start_at,
                ended_at=legacy.end_at,
                replaces=replaces,
                note=note,
            )

        if endpoint.primary_radio_id:
            _create_assignment(
                Assignment,
                position,
                endpoint.primary_radio_id,
                "PRIMARY",
                note="Migrated from legacy endpoint primary_radio.",
            )


def _organization_location(apps, Location, container, cache):
    if container.pk in cache:
        return cache[container.pk]

    parent_location = None
    if container.parent_id:
        parent = container.__class__.objects.filter(pk=container.parent_id).first()
        if parent:
            parent_location = _organization_location(apps, Location, parent, cache)

    location_type = "OTHER"
    try:
        Post = apps.get_model("organization", "Post")
        if Post.objects.filter(pk=container.pk).exists():
            location_type = "POST"
    except LookupError:
        pass

    location = _location_for_name(Location, container.name, location_type, parent=parent_location)
    cache[container.pk] = location
    return location


def _migrate_organization_links(apps, schema_editor):
    Location = apps.get_model("inventory", "Location")
    Position = apps.get_model("inventory", "RadioPosition")
    Assignment = apps.get_model("inventory", "RadioPositionAssignment")
    Container = apps.get_model("organization", "Container")
    RadioContainerLink = apps.get_model("organization", "RadioContainerLink")
    Cabinet = apps.get_model("traca", "Cabinet")
    CabinetSlot = apps.get_model("traca", "CabinetSlot")

    migrated_link_ids = set()

    for cabinet in Cabinet.objects.order_by("name"):
        location_name = cabinet.name
        if cabinet.location:
            location_name = f"{cabinet.location} – {cabinet.name}"
        location = _location_for_name(Location, location_name, "SMART_CABINET")
        for slot in CabinetSlot.objects.filter(cabinet=cabinet).order_by("name"):
            migrated_link_ids.add(slot.pk)
            position = _position_for_parent(
                Position,
                slot.name,
                location=location,
                order=getattr(slot, "order", 0) or 0,
            )
            if slot.radio_id:
                _create_assignment(
                    Assignment,
                    position,
                    slot.radio_id,
                    "PRIMARY",
                    assigned_at=getattr(slot, "updated_at", None),
                    note="Migrated from legacy intelligent cabinet slot.",
                )

    location_cache = {}
    for link in RadioContainerLink.objects.exclude(pk__in=migrated_link_ids).order_by("container_id", "order", "name"):
        container = Container.objects.filter(pk=link.container_id).first()
        if not container:
            continue
        if container.vector_id:
            position = _position_for_parent(
                Position,
                link.name,
                vector_id=container.vector_id,
                order=link.order,
            )
        else:
            location = _organization_location(apps, Location, container, location_cache)
            position = _position_for_parent(
                Position,
                link.name,
                location=location,
                order=link.order,
            )
        if link.radio_id:
            _create_assignment(
                Assignment,
                position,
                link.radio_id,
                "PRIMARY",
                assigned_at=link.updated_at,
                note="Migrated from legacy radio container link.",
            )


def migrate_legacy_radio_positions(apps, schema_editor):
    _migrate_inventory_endpoints(apps, schema_editor)
    _migrate_organization_links(apps, schema_editor)


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0016_location_radioposition_radiopositionassignment_and_more"),
        ("organization", "0016_container_vector"),
        ("traca", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(migrate_legacy_radio_positions, reverse_noop),
    ]
