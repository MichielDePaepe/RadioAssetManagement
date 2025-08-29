from django.urls import path
from .views import *

app_name = 'helpdesk'

urlpatterns = [
    path('', TicketListView.as_view(), name='ticket_list'),
    path('ticket/<int:pk>/', TicketDetailView.as_view(), name='ticket_detail'),
    path('search/', TicketSearchView.as_view(), name='ticket_search'),
    path('create/', TicketCreateView.as_view(), name='ticket_create'),
    path('create_scan/', TicketCreateScanView.as_view(), name='ticket_create_scan'),

]