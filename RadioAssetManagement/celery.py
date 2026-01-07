# RadioAssetManagement/celery.py
import os
from celery import Celery

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "RadioAssetManagement.settings",
)

app = Celery("RadioAssetManagement")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.imports = ("RadioAssetManagement.tasks",)