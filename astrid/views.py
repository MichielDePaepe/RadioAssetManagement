from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.views.generic import TemplateView
from django.urls import reverse
from django.utils.translation import gettext as _


from radio.models import Radio
from .models import *

class VTEIRequestCreateView(View):
    template_name = "astrid/vtei_request.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        try:
            old_radio_pk = request.POST.get("old-radio")
            new_radio_pk = request.POST.get("new-radio")

            if not (old_radio_pk and new_radio_pk):
                raise(Exception(_("Both an old and a new radio need to be selected.")))
                
            old_radio = Radio.objects.get(pk=int(old_radio_pk))
            new_radio = Radio.objects.get(pk=int(new_radio_pk))

            if not old_radio.is_active:
                raise(Exception(_("The radio selected as old radio has no subscription.")))

            if new_radio.is_active:
                raise(Exception(_("The radio selected as new radio already has a subscription.")))

            requests = Request.objects.filter(old_radio = old_radio, ticket_type__code = "ASTRID_REQUEST").exclude(status__code = "CLOSED")
            if requests:
                raise(Exception(_("The old radio has an open request ticket: {tickets}").format(tickets = ", ".join([f"#{r.pk}" for r in requests]))))

            requests = Request.objects.filter(radio = new_radio, ticket_type__code = "ASTRID_REQUEST").exclude(status__code = "CLOSED")
            if requests:
                raise(Exception(_("The new radio has an open request ticket: {tickets}").format(tickets = ", ".join([f"#{r.pk}" for r in requests]))))


            Request.objects.create(
                request_type = Request.RequestType.VTEI,
                old_radio = old_radio,
                old_issi = old_radio.subscription.issi,
                new_issi = old_radio.subscription.issi,
                radio = new_radio,
                description = request.POST.get("request_description"),
            )

            messages.success(request, _("VTEI request successful"))

  
        except Exception as e:
            messages.error(request, str(e))


        return redirect(request.path)


class RequestsOverviewView(TemplateView):
    template_name = "astrid/request_overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["requests"] = Request.objects.filter(ticket_type__code = "ASTRID_REQUEST").exclude(status__code = "CLOSED")
        return context
