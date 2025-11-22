from django.urls import path
from .views import *

app_name = 'helpdesk'

urlpatterns = [
	path("tickets/", TicketListView.as_view(), name="ticket_list"),
	path("ticket/<int:pk>/", TicketDetailView.as_view(), name="ticket_detail"),
	path("ticket/new/", TicketCreateView.as_view(), name="ticket_new"),
	path("ticket/new/<int:radio_pk>", TicketCreateView.as_view(), name="ticket_new_with_radio"),

]