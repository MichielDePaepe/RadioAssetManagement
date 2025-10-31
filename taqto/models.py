from django.db import models

class Permissions(models.Model):
    """
    Dummy model to attach custom permissions without creating a database table.
    """
    class Meta:
        managed = False  # Django will not create a table for this model
        default_permissions = ()  # remove default add/change/delete/view permissions
        permissions = [
            ("tacto_user", "Is allowed to use taqto"),
            ("can_download_contacts", "Can download contacts CSV"),
        ]
