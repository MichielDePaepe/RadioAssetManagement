from django.urls import path
from .views import *

app_name = 'organization'

urlpatterns = [
    path('container/list/', ContainerListView.as_view(), name='container_root_list'),
    path('container/list/<int:container_id>/', ContainerListView.as_view(), name='container_list'),
    path('radiocontainerlink/list/<int:container_id>/', RadioContainerLinkListView.as_view(), name='rcl_list'),
    path('radiocontainerlink/<int:pk>/', RadioContainerLinkDetailView.as_view(), name='rcl_detail'),
    path('radiocontainerlink/submit/', RadioContainerLinkSubmitView.as_view(), name='rcl_submit'),

    path('list/', OverviewPostListView.as_view(), name='list_posts'),
    path('list/<int:pk>/', OverviewPostDetailView.as_view(), name='list_detail'),
]