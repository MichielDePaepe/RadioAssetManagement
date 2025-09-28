from django.views import View
from django.views.generic import ListView, DetailView, FormView, CreateView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from .models import *
from radio.models import *


class TicketDetailView(DetailView):
    model = Ticket
    template_name = "helpdesk/ticket_detail.html"
    context_object_name = "ticket"

    def get_context_data(self, **kwargs):
        # Add related logs for this ticket
        context = super().get_context_data(**kwargs)
        context["logs"] = self.object.logs.select_related("user", "status_before", "status_after")
        return context
