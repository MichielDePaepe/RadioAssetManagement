from django.urls import path
from .views import *

app_name = 'inventory'

urlpatterns = [
    path("endpoints/", EndpointLookupView.as_view(), name="entpoint_lookup"),
    
    path("endpoints/<int:pk>/", EndpointDetailView.as_view(), name="endpoint_detail"),
    path("endpoints/<int:pk>/switch/", EndpointSwitchRadioView.as_view(), name="endpoint_switch"),

    path("endpoints/search/", endpoint_search, name="endpoint_search"),
    path("radios/search/", radio_search, name="radio_search"),
]
