from django.views import View
from django.views.generic import ListView, DetailView, FormView, CreateView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from .models import *
from radio.models import *
from django.db.models import Q


class TicketDetailView(DetailView):
    model = Ticket
    template_name = "helpdesk/ticket_detail.html"
    context_object_name = "ticket"

    def get_context_data(self, **kwargs):
        # Add related logs for this ticket
        context = super().get_context_data(**kwargs)
        context["logs"] = self.object.logs.select_related("user", "status_before", "status_after")
        return context


class TicketListView(ListView):
    model = Ticket
    template_name = "helpdesk/ticket_list.html"
    context_object_name = "tickets"
    paginate_by = 50

    def get_queryset(self):
        qs = Ticket.objects.select_related("ticket_type", "status", "radio")

        sort = self.request.GET.get("sort", "id")

        allowed = {"id", "title", "ticket_type__name", "status__name", "priority", "updated_at"}
        if sort.lstrip("-") not in allowed:
            sort = "id"

        return qs.order_by(sort)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["types"] = TicketType.objects.all()
        ctx["statuses"] = TicketStatus.objects.all()
        ctx["priorities"] = Ticket.TicketPriority.choices
        ctx["columns"] = [
            ("id", "#"),
            ("title", "Titel"),
            ("ticket_type__name", "Type"),
            ("status__name", "Status"),
            ("priority", "Prioriteit"),
            ("updated_at", "Laatst bijgewerkt"),
        ]
        ctx["prio_selected"] = self.request.GET.get("priority", "")
        ctx["type_selected"] = self.request.GET.get("type", "")
        ctx["status_selected"] = self.request.GET.get("status", "")
        ctx["current_sort"] = self.request.GET.get("sort", "id")
        return ctx

