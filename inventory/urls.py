from django.urls import path
from inventory.views import *

app_name = 'inventory'

urlpatterns = [
    path('post/', PostListView.as_view(), name='posts_list'),
    path('post/<int:container_id>/', ContainerListView.as_view(), name='container_list'),
    path('inventory/<int:container_id>/', ContainerInventoryView.as_view(), name='inventory'),
    path('scan/', ScanCodeView.as_view(), name='scan'),
    path('submit/', ScanSubmitView.as_view(), name='submit'),

]
