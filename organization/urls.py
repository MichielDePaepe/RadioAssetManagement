from django.urls import path
from .views import *

app_name = 'organization'

urlpatterns = [
    path('container/list/', ContainerListView.as_view(), name='container_root_list'),
    path('container/list/<int:container_id>/', ContainerListView.as_view(), name='container_list'),

    path('list/', OverviewPostListView.as_view(), name='list_posts'),
    path('list/<int:pk>/', OverviewPostDetailView.as_view(), name='list_detail'),
]
