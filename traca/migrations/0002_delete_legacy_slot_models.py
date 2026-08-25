from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("traca", "0001_initial"),
    ]

    operations = [
        migrations.DeleteModel(name="CabinetLog"),
        migrations.DeleteModel(name="CabinetSlot"),
    ]
