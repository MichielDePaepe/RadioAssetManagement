from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
from django.urls import reverse
from django.utils.translation import gettext as _
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponseBadRequest, HttpResponseForbidden

from django.db import transaction
import openpyxl

from radio.models import Radio, ISSI, Subscription
from .models import *

import logging
logger = logging.getLogger(__name__)


class UploadSubscriptionsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = 'radio.can_upload_subscriptions'
    template_name = "astrid/upload_subscriptions.html"

    def post(self, request):
        try:
            excel_file = request.FILES["excelFile"]

            wb = openpyxl.load_workbook(excel_file, data_only=True)
            ws = wb.active

            header = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
            col = {name: idx for idx, name in enumerate(header)}

            with transaction.atomic():
                excel_subs = set()
                existing_subs = set(Subscription.objects.filter(issi__customer__owner = True).values_list('radio__TEI', 'issi__number'))

                for row in ws.iter_rows(min_row=2):
                    tei_cell = row[col['TEI']].value
                    issi_cell = row[col['ISSI']].value
                    alias_cell = row[col['CICAlias']].value
                    model_type_cell = row[col['ModelType']].value

                    if tei_cell is None or issi_cell is None:
                        continue

                    if model_type_cell == "Spare subscription":
                        continue

                    try:
                        tei_str = str(tei_cell).strip()
                        if len(tei_str) == 15 and tei_str[-1] == "0":
                            tei_str = tei_str[0:-1]
                        tei = int(tei_str)
                        issi_number = int(str(issi_cell).strip())
                    except ValueError:
                        messages.error(request, f"Onjuiste waarde TEI={tei_cell}, ISSI={issi_cell}")
                        continue

                    alias = str(alias_cell).strip() if alias_cell else ""

                    try:
                        radio, _ = Radio.objects.get_or_create(TEI=tei)
                    except ValueError as e:
                        messages.error(request, f"{e}")
                        continue

                    issi, _ = ISSI.objects.get_or_create(number=issi_number)

                    print(f"{tei_cell} - {issi_cell}")

                    if (tei, issi_number) not in existing_subs:
                        # if issi existis in another subscription, delete that subscription
                        other_subscirption_with_issi = Subscription.objects.filter(issi=issi)
                        if other_subscirption_with_issi:
                            other_subscirption_with_issi.delete()

                        Subscription.objects.create(
                            radio=radio,
                            issi=issi,
                            astrid_alias=alias
                        )
                    else:
                        sub = Subscription.objects.get(radio=radio, issi=issi_number)
                        if sub.astrid_alias != alias:
                            sub.astrid_alias = alias
                            sub.save()

                    excel_subs.add((tei, issi_number))

                # Verwijder alle records die niet meer in Excel zitten
                to_delete = existing_subs - excel_subs
                for tei_del, issi_del in to_delete:
                    subscription_to_delete = Subscription.objects.filter(radio__TEI=tei_del, issi__number=issi_del)
                    logger.info(f"Delete subscripton: {subscription_to_delete}")
                    subscription_to_delete.delete()

            messages.success(request, f"Succesvol verwerkt. {len(excel_subs)} abonnomenten geregistreerd, {len(to_delete)} abonnomenten verwijderd.")

        except KeyError as e:
            messages.error(request, f"Kolom ontbreekt in Excel: {e}")
        except Exception as e:
            messages.error(request, f"Er is een fout opgetreden: {e} (ISSI: {issi_cell}, TEI: {tei_cell})")

        return self.get(request)



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


class RequestOverviewView(TemplateView):
    template_name = "astrid/request_overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["requests"] = Request.objects.filter(ticket_type__code = "ASTRID_REQUEST").exclude(status__code = "CLOSED")
        return context


class RequestDetailView(DetailView):
    model = Request
    template_name = "astrid/request_detail.html"

    def post(self, request, *args, **kwargs):
        obj = self.get_object()

        request_type = request.POST.get("type")
        action = request.POST.get("action")
        note = request.POST.get("note")

        if request_type == "astrid_request_submitted":
            if not request.user.has_perm("astrid.has_access_to_myastrid"):
                raise PermissionDenied

            if action == "request_submitted":
                astrid_ticket = request.POST.get("astrid_ticket")

                if not astrid_ticket:
                    messages.error(request, _("Geen astrid ticket nummer opgegeven"))
                    return redirect(request.path)

                obj.external_reference = astrid_ticket
                obj.save() 
                obj.start_execution(user=request.user, note=note)

            elif action == "refused":
                if not note:
                    messages.error(request, _("Geef een reden op waarom de aanvraag geweigerd werd"))
                    return redirect(request.path)
                obj.mark_closed(user=request.user, note=note)
        
        elif request_type == "feedback_from_astrid":
            if not request.user.has_perm("astrid.has_access_to_myastrid"):
                raise PermissionDenied

            if action == "precessed":
                obj.mark_waiting_verification(user=request.user, note=note)
            elif action == "refused":
                obj.mark_closed(user=request.user, note=note or _("Request refused by astrid"))

        elif request_type == "validate_activation":
            if not request.user.has_perm("astrid.can_verify_requests"):
                raise PermissionDenied

            if not note:
                messages.error(request, _("Opmerking mag niet leeg zijn"))
                return redirect(request.path)

            if action == "radio_is_working":
                obj.mark_verified(user=request.user, note=note)

            if action == "radio_is_not_working":
                obj.mark_verified(user=request.user, note=note)
        
        else:
            return HttpResponseBadRequest("Invalid POST")

        return redirect("astrid:request_overview")





