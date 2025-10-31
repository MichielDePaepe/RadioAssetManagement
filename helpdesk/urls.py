from django.urls import path
from .views import *

app_name = 'helpdesk'

urlpatterns = [
	path("tickets/", TicketListView.as_view(), name="ticket_list"),
	path("ticket/<int:pk>/", TicketDetailView.as_view(), name="ticket_detail"),
]