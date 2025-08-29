from django.views import View
from django.views.generic import ListView, DetailView, FormView, CreateView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from .models import *
from .forms import * 
from radio.models import Radio


class TicketListView(ListView):
    model = Ticket
    template_name = 'helpdesk/ticket_list.html'
    context_object_name = 'tickets'

    def get_queryset(self):
        return Ticket.objects.exclude(status='closed')

class TicketDetailView(FormView, DetailView):
    model = Ticket
    template_name = 'helpdesk/ticket_detail.html'
    context_object_name = 'ticket'
    form_class = TicketMessageForm

    def get_object(self):
        return get_object_or_404(Ticket, id=self.kwargs['pk'])

    def form_valid(self, form):
        ticket = self.get_object()
        msg = form.save(commit=False)
        msg.ticket = ticket
        msg.save()
        if msg.status_after:
            ticket.status = msg.status_after
            ticket.save()
        return redirect('helpdesk:ticket_detail', pk=ticket.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.get_form()
        return context

class TicketSearchView(FormView):
    template_name = 'helpdesk/ticket_search.html'
    form_class = TicketSearchForm

    def form_valid(self, form):
        tei = form.cleaned_data['tei']
        ref = form.cleaned_data['external_reference']
        if tei:
            results = Ticket.objects.filter(radio__TEI=tei)
        elif ref:
            results = Ticket.objects.filter(external_reference=ref)
        else:
            results = Ticket.objects.none()
        return self.render_to_response(self.get_context_data(form=form, results=results))


class TicketCreateView(CreateView):
    model = Ticket
    form_class = TicketCreateForm
    template_name = 'helpdesk/ticket_create.html'
    success_url = reverse_lazy('helpdesk:ticket_list')


class TicketCreateScanView(View):
    def get(self, request):
        form = TicketCreateForm()
        return render(request, 'helpdesk/ticket_create_scan.html', {'form': form})

    def post(self, request):
        form = TicketCreateForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('helpdesk:ticket_list')
        return render(request, 'helpdesk/ticket_create_scan.html', {'form': form})
