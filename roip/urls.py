# roip/urls.py
from django.urls import path
from .views import LiveTxView

urlpatterns = [
    path("roip/live/", LiveTxView.as_view(), name="roip-live-tx"),
]