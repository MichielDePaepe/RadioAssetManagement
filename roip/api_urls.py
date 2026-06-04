from django.urls import path

from .api import IssiLookupApiView

app_name = "roip_api"

urlpatterns = [
    path("issi/<str:issi>/", IssiLookupApiView.as_view(), name="issi_lookup"),
]
