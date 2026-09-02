from django.urls import path
from .views import *

app_name = 'inventory'

urlpatterns = [
    path("fireplan/", FireplanInventoryStartView.as_view(), name="fireplan_inventory_start"),
    path("scanner-configuratie/", ScannerConfigurationView.as_view(), name="scanner_configuration"),
    path("fireplan/vehicles/search/", vehicle_search, name="vehicle_search"),
    path("fireplan/<int:vehicle_id>/scan/", fireplan_inventory_scan, name="fireplan_inventory_scan"),
    path("vehicles/", VehicleRadioListView.as_view(), name="vehicle_radio_list"),
    path("vehicles/<int:pk>/", VehicleRadioDetailView.as_view(), name="vehicle_radio_detail"),

    path("locations/", LocationListView.as_view(), name="location_list"),
    path("locations/new/", LocationCreateView.as_view(), name="location_create"),
    path("locations/<int:pk>/", LocationDetailView.as_view(), name="location_detail"),
    path("locations/<int:pk>/edit/", LocationUpdateView.as_view(), name="location_edit"),

    path("parents/<str:parent_type>/<str:pk>/positions/", ParentPositionListView.as_view(), name="parent_positions"),

    path("positions/", RadioPositionListView.as_view(), name="position_list"),
    path("positions/unassigned-subscriptions/", UnassignedSubscriptionRadioListView.as_view(), name="unassigned_subscription_radios"),
    path("positions/new/", RadioPositionCreateView.as_view(), name="position_create"),
    path("positions/<int:pk>/", RadioPositionDetailView.as_view(), name="position_detail"),
    path("positions/<int:pk>/edit/", RadioPositionUpdateView.as_view(), name="position_edit"),
    path("positions/<int:pk>/delete/", RadioPositionDeleteView.as_view(), name="position_delete"),
    path("positions/<int:pk>/primary/change/", ChangePrimaryView.as_view(), name="position_change_primary"),
    path("positions/<int:pk>/substitute/assign/", AssignSubstituteView.as_view(), name="position_assign_substitute"),
    path("positions/<int:pk>/substitute/release/", ReleaseSubstituteView.as_view(), name="position_release_substitute"),

    path("radios/search/", radio_search, name="radio_search"),
]
