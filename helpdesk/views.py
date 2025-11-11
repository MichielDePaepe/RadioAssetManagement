
from django.views import View
from django.views.generic import ListView, DetailView, FormView, CreateView
from django.views.generic.edit import FormMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import *
from .models import *
from radio.models import *
from django.db.models import Q



class TicketDetailView(LoginRequiredMixin, DetailView):
    model = Ticket
    template_name = "helpdesk/ticket_detail.html"
    context_object_name = "ticket"

    def get_success_url(self):
        return reverse("helpdesk:ticket_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["logs"] = self.object.logs.select_related("user", "status_before", "status_after")
        context["form"] = TicketLogForm(ticket=self.object)  # logformulier
        context["edit_form"] = TicketEditForm(instance=self.object, user=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        # --- Bewerken van ticketmeta ---
        if "update_ticket" in request.POST:
            form = TicketEditForm(request.POST, instance=self.object, user=request.user)
            if form.is_valid():
                original_ticket = Ticket.objects.get(pk=self.object.pk)

                updated_ticket = form.save()

                changes = []
                if original_ticket.ticket_type != updated_ticket.ticket_type:
                    changes.append(f"Type gewijzigd van '{original_ticket.ticket_type}' naar '{updated_ticket.ticket_type}'")

                if original_ticket.priority != updated_ticket.priority:
                    original_label = dict(Ticket.TicketPriority.choices).get(original_ticket.priority, original_ticket.priority)
                    new_label = dict(Ticket.TicketPriority.choices).get(updated_ticket.priority, updated_ticket.priority)
                    changes.append(f"Prioriteit gewijzigd van '{original_label}' naar '{new_label}'")

                if original_ticket.siamu_ticket != updated_ticket.siamu_ticket:
                    changes.append(
                        f"SIAMU-nummer gewijzigd van '{original_ticket.siamu_ticket or '—'}' naar '{updated_ticket.siamu_ticket or '—'}'"
                    )

                if original_ticket.assigned_to != updated_ticket.assigned_to:
                    original_user = original_ticket.assigned_to.username if original_ticket.assigned_to else "—"
                    new_user = updated_ticket.assigned_to.username if updated_ticket.assigned_to else "—"
                    changes.append(f"Toegewezen aan gewijzigd van '{original_user}' naar '{new_user}'")

                if changes:
                    TicketLog.objects.create(
                        ticket=updated_ticket,
                        user=request.user,
                        status_after=updated_ticket.status,
                        note="\n".join(changes),
                    )

            return redirect(self.get_success_url())

        # --- Toevoegen van log ---
        elif "add_log" in request.POST:
            form = TicketLogForm(request.POST, ticket=self.object)
            if form.is_valid():
                log = form.save(commit=False)
                log.ticket = self.object
                log.user = request.user
                if not log.status_after:
                    log.status_after = self.object.status
                log.save()

            return redirect(self.get_success_url())

        # fallback — niets herkend
        return redirect(self.get_success_url())







class TicketListView(ListView):
    model = Ticket
    template_name = "helpdesk/ticket_list.html"
    context_object_name = "tickets"
    #paginate_by = 50

    def get_queryset(self):
        qs = Ticket.objects.select_related("ticket_type", "status", "radio")

        show_closed = self.request.GET.get("show_closed") == "1"
        
        if not show_closed:
            qs = qs.exclude(status__code="CLOSED")

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
        ctx["show_closed"] = self.request.GET.get("show_closed") == "1"

        return ctx
