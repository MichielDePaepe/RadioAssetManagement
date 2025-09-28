from django.urls import path
from .views import *

app_name = 'helpdesk'

urlpatterns = [
	path("ticket/<int:pk>/", TicketDetailView.as_view(), name="ticket_detail"),
]