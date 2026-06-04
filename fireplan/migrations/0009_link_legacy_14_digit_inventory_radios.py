from django.db import migrations


def find_radio_for_fireplan_tei(Radio, raw_tei):
    tei = str(raw_tei or "").strip()
    if not tei.isdigit():
        return None

    radio = Radio.objects.filter(TEI=int(tei)).first()
    if radio:
        return radio

    if len(tei) == 14:
        return Radio.objects.filter(TEI=int(f"{tei}0")).first()

    return None


def forwards(apps, schema_editor):
    Radio = apps.get_model("radio", "Radio")
    FireplanInventoryRadio = apps.get_model("fireplan", "FireplanInventoryRadio")

    for inventory_radio in FireplanInventoryRadio.objects.filter(radio__isnull=True):
        radio = find_radio_for_fireplan_tei(Radio, inventory_radio.tei)
        if not radio:
            continue

        inventory_radio.radio_id = radio.TEI
        inventory_radio.tracked_item_id = radio.fireplan_id
        inventory_radio.save(update_fields=["radio", "tracked_item_id"])


class Migration(migrations.Migration):
    dependencies = [
        ("fireplan", "0008_fireplaninventory_vector"),
        ("radio", "0023_use_full_15_digit_tei"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
