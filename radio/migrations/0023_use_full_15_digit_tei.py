from django.db import migrations


RADIO_RELATIONS = [
    ("radio", "Subscription", "radio"),
    ("helpdesk", "Ticket", "radio"),
    ("astrid", "Request", "old_radio"),
    ("fireplan", "Vehicle", "radio"),
    ("fireplan", "FireplanInventoryRadio", "radio"),
    ("inventory", "RadioEndpoint", "primary_radio"),
    ("inventory", "RadioAssignment", "radio"),
    ("inventory", "RadioAssignment", "replaces_radio"),
    ("organization", "RadioContainerLink", "radio"),
    ("traca", "CabinetLog", "radio_in"),
    ("traca", "CabinetLog", "radio_out"),
]


def tei_is_in_range(tei, ranges):
    return any(min_tei <= tei <= max_tei for min_tei, max_tei in ranges)


def forwards(apps, schema_editor):
    Radio = apps.get_model("radio", "Radio")
    TEIRange = apps.get_model("radio", "TEIRange")

    old_ranges = list(TEIRange.objects.values_list("min_tei", "max_tei"))
    radios_to_move = [
        radio
        for radio in Radio.objects.all().order_by("TEI")
        if tei_is_in_range(radio.TEI, old_ranges)
    ]

    new_teis = {radio.TEI * 10 for radio in radios_to_move}
    collisions = list(
        Radio.objects.filter(TEI__in=new_teis)
        .exclude(TEI__in=[radio.TEI for radio in radios_to_move])
        .values_list("TEI", flat=True)
    )
    if collisions:
        raise RuntimeError(
            "Kan TEI-migratie niet uitvoeren: volgende 15-cijferige TEI's bestaan al: "
            + ", ".join(str(tei) for tei in collisions)
        )

    for radio in radios_to_move:
        Radio.objects.create(
            TEI=radio.TEI * 10,
            fireplan_id=radio.fireplan_id,
            model_id=radio.model_id,
            decommissioned=radio.decommissioned,
        )

    for radio in radios_to_move:
        old_tei = radio.TEI
        new_tei = old_tei * 10
        for app_label, model_name, field_name in RADIO_RELATIONS:
            model = apps.get_model(app_label, model_name)
            model.objects.filter(**{f"{field_name}_id": old_tei}).update(
                **{f"{field_name}_id": new_tei}
            )

    Radio.objects.filter(TEI__in=[radio.TEI for radio in radios_to_move]).delete()

    for tei_range in TEIRange.objects.all():
        tei_range.min_tei = tei_range.min_tei * 10
        tei_range.max_tei = tei_range.max_tei * 10 + 9
        tei_range.save(update_fields=["min_tei", "max_tei"])


def backwards(apps, schema_editor):
    Radio = apps.get_model("radio", "Radio")
    TEIRange = apps.get_model("radio", "TEIRange")

    for tei_range in TEIRange.objects.all():
        tei_range.min_tei = tei_range.min_tei // 10
        tei_range.max_tei = tei_range.max_tei // 10
        tei_range.save(update_fields=["min_tei", "max_tei"])

    old_ranges = list(TEIRange.objects.values_list("min_tei", "max_tei"))
    radios_to_move = [
        radio
        for radio in Radio.objects.all().order_by("-TEI")
        if radio.TEI % 10 == 0 and tei_is_in_range(radio.TEI // 10, old_ranges)
    ]

    old_teis = {radio.TEI // 10 for radio in radios_to_move}
    collisions = list(
        Radio.objects.filter(TEI__in=old_teis)
        .exclude(TEI__in=[radio.TEI for radio in radios_to_move])
        .values_list("TEI", flat=True)
    )
    if collisions:
        raise RuntimeError(
            "Kan TEI-migratie niet terugdraaien: volgende 14-cijferige TEI's bestaan al: "
            + ", ".join(str(tei) for tei in collisions)
        )

    for radio in radios_to_move:
        Radio.objects.create(
            TEI=radio.TEI // 10,
            fireplan_id=radio.fireplan_id,
            model_id=radio.model_id,
            decommissioned=radio.decommissioned,
        )

    for radio in radios_to_move:
        old_tei = radio.TEI
        new_tei = old_tei // 10
        for app_label, model_name, field_name in RADIO_RELATIONS:
            model = apps.get_model(app_label, model_name)
            model.objects.filter(**{f"{field_name}_id": old_tei}).update(
                **{f"{field_name}_id": new_tei}
            )

    Radio.objects.filter(TEI__in=[radio.TEI for radio in radios_to_move]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("radio", "0022_discipline_discipline_type"),
        ("astrid", "0004_alter_request_request_type"),
        ("fireplan", "0008_fireplaninventory_vector"),
        ("helpdesk", "0008_alter_ticket_options"),
        ("inventory", "0015_alter_locationcontainer_radiocontainer_ptr_and_more"),
        ("organization", "0016_container_vector"),
        ("traca", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
