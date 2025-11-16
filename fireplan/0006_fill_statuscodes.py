from django.db import migrations, models


def fill_codes(apps, schema_editor):
    StatusCode = apps.get_model("fireplan", "StatusCode")

    translations = {
        "0":  {"nl": "Vrij", "fr": "Disponible", "en": "Available"},
        "1":  {"nl": "Gealarmeerd", "fr": "Alarme", "en": "Alerted"},
        "2":  {"nl": "Vertrek", "fr": "Départ", "en": "Departing"},
        "3":  {"nl": "Ter plaatse", "fr": "Sur place", "en": "On scene"},
        "4":  {"nl": "Vertrek ziekenhuis", "fr": "Départ hôpital", "en": "Leaving hospital"},
        "5":  {"nl": "Aankomst ziekenhuis", "fr": "Arrivée hôpital", "en": "Arrived at hospital"},
        "6":  {"nl": "Radiofonisch beschikbaar", "fr": "Disponible radio", "en": "Available (radio)"},
        "7":  {"nl": "Tel. beschikbaar vertrekpunt", "fr": "Disponible tél. départ", "en": "Phone available (station)"},
        "8":  {"nl": "Tel. beschikbaar elders", "fr": "Disponible tél. ailleurs", "en": "Phone available (off-station)"},
        "15": {"nl": "Andere 112", "fr": "Autre 112", "en": "Other 112 action"},
        "9":  {"nl": "Buiten dienst", "fr": "Hors service", "en": "Out of service"},
        "11": {"nl": "Onbeschikbaar (personeel)", "fr": "Non disponible (personnel)", "en": "Unavailable (staff)"},
        "90": {"nl": "Buitendienststelling (personeel)", "fr": "Hors service (personnel)", "en": "Out of service (staff)"},
        "91": {"nl": "Buitendienststelling (technisch)", "fr": "Hors service (technique)", "en": "Out of service (technical)"},
        "92": {"nl": "Buitendienststelling (materiaal)", "fr": "Hors service (matériel)", "en": "Out of service (material)"},
        "93": {"nl": "Buitendienststelling (permanentie)", "fr": "Hors service (permanence)", "en": "Out of service (duty)"},
        "98": {"nl": "Geblokkeerd", "fr": "Bloqué", "en": "Blocked"},
        "99": {"nl": "Geprepositioneerd", "fr": "Pré-positionné", "en": "Pre-positioned"},
    }

    colors = {
        "0":  "#badc58",
        "1":  "#f9ca24",
        "2":  "#f0932b",
        "3":  "#eb4d4b",
        "4":  "#ff7979",
        "5":  "#4834d4",
        "6":  "#be2edd",
        "7":  "#badc58",
        "8":  "#6ab04c",
        "9":  "#535c68",
        "11": "#535c68",
        "90": "#535c68",
        "91": "#535c68",
        "92": "#535c68",
        "93": "#535c68",
        "98": "#30336b",
        "99": "#6ab04c",
        "15": "#686de0",
    }

    for code, trans in translations.items():
        obj, _ = StatusCode.objects.get_or_create(code=code)
        obj.description_nl = trans["nl"]
        obj.description_fr = trans["fr"]
        obj.description_en = trans["en"]
        obj.color = colors.get(code)
        obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ("fireplan", "0005_remove_vector_laststatustimeupdated_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="statuscode",
            name="color",
            field=models.CharField(max_length=20, null=True, blank=True),
        ),
        migrations.RunPython(fill_codes),
    ]
