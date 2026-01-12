# roip/urls.py
from django.urls import path
from .views import LiveTxView

app_name = "roip"

urlpatterns = [
    path("live/", LiveTxView.as_view(), name="roip-live-tx"),
]