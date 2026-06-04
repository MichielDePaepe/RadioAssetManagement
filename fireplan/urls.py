# fireplan/urls.py

from django.urls import path
from .views import *

app_name = 'fireplan'

urlpatterns = [
    path(
        "inventories/",
        LatestInventoryPerVectorView.as_view(),
        name="latest_inventory_per_vector",
    ),
    path(
        "inventories/vector/<str:resource_code>/",
        VectorInventoryHistoryView.as_view(),
        name="vector_inventory_history",
    ),
]
