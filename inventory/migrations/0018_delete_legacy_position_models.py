from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0017_migrate_legacy_radio_positions"),
    ]

    operations = [
        migrations.DeleteModel(name="RadioAssignment"),
        migrations.DeleteModel(name="RadioEndpoint"),
        migrations.DeleteModel(name="LocationContainer"),
        migrations.DeleteModel(name="VectorContainer"),
        migrations.DeleteModel(name="RadioContainer"),
        migrations.DeleteModel(name="Post"),
    ]
