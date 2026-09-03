
from django.views import View
from django.views.generic import ListView, DetailView, FormView, CreateView, TemplateView
from django.views.generic.edit import FormMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Case, Count, IntegerField, Q, When
from django.utils import timezone

from .forms import *
from .models import *
from .services.printing import TicketPrintingService
from printer.models import Printer
from radio.models import *
from datetime import timedelta



class HelpdeskDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "helpdesk/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        stale_before = timezone.now() - timedelta(days=7)
        priority_order = Case(
            When(priority=Ticket.TicketPriority.HIGH, then=0),
            When(priority=Ticket.TicketPriority.MEDIUM, then=1),
            default=2,
            output_field=IntegerField(),
        )

        open_tickets = Ticket.objects.exclude(status__code="CLOSED")
        assigned_open_tickets = (
            open_tickets
            .filter(assigned_to=user)
            .select_related("ticket_type", "status", "radio", "assigned_to")
            .annotate(priority_order=priority_order)
        )

        context["assigned_tickets"] = assigned_open_tickets.order_by("priority_order", "updated_at", "-id")[:12]
        context["high_priority_tickets"] = assigned_open_tickets.filter(
            priority=Ticket.TicketPriority.HIGH
        ).order_by("updated_at", "-id")[:8]
        context["stale_tickets"] = assigned_open_tickets.filter(
            updated_at__lte=stale_before
        ).order_by("updated_at", "-id")[:8]
        context["recent_logs"] = (
            TicketLog.objects
            .filter(ticket__assigned_to=user)
            .select_related("ticket", "ticket__status", "ticket__ticket_type", "user", "status_after")
            .order_by("-timestamp")[:8]
        )
        context["unassigned_tickets"] = (
            open_tickets
            .filter(assigned_to__isnull=True)
            .select_related("ticket_type", "status", "radio")
            .annotate(priority_order=priority_order)
            .order_by("priority_order", "updated_at", "-id")[:8]
        )
        context["created_by_me_tickets"] = (
            open_tickets
            .filter(created_by=user)
            .exclude(assigned_to=user)
            .select_related("ticket_type", "status", "radio", "assigned_to")
            .order_by("-updated_at", "-id")[:6]
        )
        context["status_breakdown"] = (
            assigned_open_tickets
            .values("status_id", "status__name", "status__code")
            .annotate(total=Count("id"))
            .order_by("status__order", "status__name")
        )
        context["metrics"] = {
            "assigned_open": assigned_open_tickets.count(),
            "high_priority": assigned_open_tickets.filter(priority=Ticket.TicketPriority.HIGH).count(),
            "stale": assigned_open_tickets.filter(updated_at__lte=stale_before).count(),
            "created_by_me": open_tickets.filter(created_by=user).count(),
            "unassigned": open_tickets.filter(assigned_to__isnull=True).count(),
            "all_open": open_tickets.count(),
        }
        return context


class TicketDetailView(LoginRequiredMixin, DetailView):
    model = Ticket
    template_name = "helpdesk/ticket_detail.html"
    context_object_name = "ticket"

    def get_success_url(self):
        return reverse("helpdesk:ticket_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["logs"] = self.object.logs.select_related("user", "status_before", "status_after")
        context["log_form"] = TicketLogForm(ticket=self.object)  # logformulier
        context["edit_form"] = TicketEditForm(instance=self.object, user=self.request.user)
        context["decommissioning_ticket"] = RadioDecommissioningTicket.objects.filter(pk=self.object.pk).first()
        printers = Printer.objects.all()
        context["printers"] = printers
        context["printer_count"] = printers.count()
        context["default_printer"] = printers.first()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        if "print_ticket_label" in request.POST:
            printer_id = request.POST.get("printer_id")
            try:
                printer = Printer.objects.get(pk=printer_id)
                message = TicketPrintingService(self.object, printer).print_ticket_number_label()
                messages.success(request, message)
            except Printer.DoesNotExist:
                messages.error(request, "Selected printer does not exist.")
            except Exception as e:
                messages.error(request, f"Printing failed: {str(e)}")
            return redirect(self.get_success_url())

        if "approve_decommissioning" in request.POST:
            if not request.user.has_perm("radio.can_approve_decommission_requests"):
                raise PermissionDenied

            decommissioning_ticket = get_object_or_404(RadioDecommissioningTicket, pk=self.object.pk)
            decommissioning_ticket.approve_decommissioning(user=request.user)
            messages.success(request, "Radio buiten dienst gesteld en ticket gesloten.")
            return redirect(self.get_success_url())

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

                if original_ticket.external_reference != updated_ticket.external_reference:
                    changes.append(
                        f"Externe referentie gewijzigd van '{original_ticket.external_reference or '—'}' naar '{updated_ticket.external_reference or '—'}'"
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



class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Ticket
    form_class = TicketCreateForm
    template_name = "helpdesk/ticket_detail.html"  # dezelfde template

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ticket"] = None
        context["logs"] = None
        context["radio_pk"] = self.kwargs.get("radio_pk")
        return context

    def form_valid(self, form):
        ticket = form.save(commit=False)
        ticket.created_by = self.request.user
        ticket.save()
        return redirect("helpdesk:ticket_detail", pk=ticket.pk)





class TicketListView(ListView):
    model = Ticket
    template_name = "helpdesk/ticket_list.html"
    context_object_name = "tickets"
    #paginate_by = 50

    def get_queryset(self):
        qs = Ticket.objects.select_related("ticket_type", "status", "radio", "assigned_to")

        show_closed = self.request.GET.get("show_closed") == "1"
        
        if not show_closed:
            qs = qs.exclude(status__code="CLOSED")

        priority = self.request.GET.get("priority")
        ticket_type = self.request.GET.get("type")
        status = self.request.GET.get("status")

        if priority:
            qs = qs.filter(priority=priority)

        if ticket_type:
            qs = qs.filter(ticket_type_id=ticket_type)

        if status:
            qs = qs.filter(status_id=status)

        if self.request.GET.get("assigned") == "me":
            qs = qs.filter(assigned_to=self.request.user)

        sort = self.request.GET.get("sort", "-id")

        allowed = {"id", "title", "ticket_type__name", "status__name", "priority", "updated_at", "assigned_to__username"}
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
            ("assigned_to__username", "Toegewezen aan"),
            ("updated_at", "Laatst bijgewerkt"),
        ]
        ctx["prio_selected"] = self.request.GET.get("priority", "")
        ctx["type_selected"] = self.request.GET.get("type", "")
        ctx["status_selected"] = self.request.GET.get("status", "")
        ctx["assigned_selected"] = self.request.GET.get("assigned", "")
        ctx["current_sort"] = self.request.GET.get("sort", "-id")
        ctx["show_closed"] = self.request.GET.get("show_closed") == "1"

        return ctx
