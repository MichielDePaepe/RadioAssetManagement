from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0019_location_dashboard_locations_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="radiopositionassignment",
            name="assignment_replaces_by_role",
        ),
        migrations.AddConstraint(
            model_name="radiopositionassignment",
            constraint=models.CheckConstraint(
                check=(
                    Q(role="PRIMARY", replaces__isnull=True)
                    | Q(role="SUBSTITUTE")
                ),
                name="assignment_replaces_by_role",
            ),
        ),
    ]
