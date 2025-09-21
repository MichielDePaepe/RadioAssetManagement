from django.views import View
from django.views.generic import TemplateView
from django.http import JsonResponse, Http404, HttpResponseBadRequest
from django.template.loader import render_to_string
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.edit import CreateView
from django.views.generic.detail import DetailView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.utils.translation import gettext as _


import openpyxl
import json
import re
import logging
logger = logging.getLogger(__name__)

from .models import *
from .forms import *
from printer.models import *
from .services.printing import RadioPrintingService


class RadioCardView(View):
    def get(self, request, tei):
        context = dict()
        context["radio"] = Radio.objects.get(TEI=int(tei))
        return render(request, "radio/radio_card.html", context)


class RadioCardExampleView(TemplateView):
    template_name = "radio/radio_card_example.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['printers'] = Printer.objects.all()  # pass printers to template
        return context


class RadioCreateView(CreateView):
    model = Radio
    form_class = RadioForm
    template_name = 'radio/radio_create.html'
    success_url = reverse_lazy('radio:create')

    def get_success_url(self):
        return reverse('radio:detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"{self.object.model} with TEI {self.object.TEI} added successfully!")
        return response


@method_decorator(csrf_exempt, name='dispatch')
class ScanQRCodeView(View):

    def get(self, request, *args, **kwargs):
        return JsonResponse({"status": "error", "message":"GET not allowed"}, status=500)
    
    def post(self, request, *args, **kwargs):
        if True:
            data = json.loads(request.body)
            scanned_line = data.get("scanned_line")

            logger.debug(f"QR code input: {scanned_line}")

            pattern = re.compile(r"https://infoscan\.firebru\.brussels\?data[=-](?P<arg1>\d+),(?P<arg2>\d+),(?P<fireplan_id>\d+),(?P<arg4>\d+)")

            match = pattern.match(scanned_line)

            if not match:
                # scanner is set to qwerty, try converting if input was on an azerty system
                mapping = str.maketrans({'a': 'q', 'A': 'Q', 'z': 'w', 'Z': 'W', 'q': 'a', 'Q': 'A', 'm': ';', 'M': ':', 'w': 'z', 'W': 'Z', '&': '1', 'é': '2', '"': '3', '\'': '4', '’': '4', '(': '5', '§': '6', 'è': '7', '!': '8', 'ç': '9', 'à': '0', '=': '/', ':': '.', '+': '?', '-': '=', ';': ','})
                translated_scanned_line = scanned_line.translate(mapping)
                logger.debug(f"Try AZERTY to QWERTY translation. Result: {scanned_line}")
                match = pattern.match(translated_scanned_line)

            if match:
                fireplan_id = int(match.group("fireplan_id"))
                logger.debug(f"fireplan id: {fireplan_id}")

                radio = Radio.objects.get(fireplan_id=fireplan_id)
                logger.debug(f"radio: {radio}")

                res = {
                    "status": "ok", 
                    "TEI": radio.TEI, 
                    "ISSI": radio.ISSI, 
                    "alias": radio.alias,
                    "fireplan_id": fireplan_id,
                    "radio": str(radio)
                }

                return JsonResponse(res)

            return JsonResponse({"status": "error", "message": "TIE not found"}, status=404)

        try:
            pass
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)


class FindRadioView(TemplateView):
    template_name = "radio/find.html"

    def post(self, request, *args, **kwargs):
        issi_value = request.POST.get("issi")
        tei_value = request.POST.get("tei")
        radio = None

        if issi_value:
            try:
                issi_int = int(issi_value)
                issi = ISSI.objects.get(number=issi_int)
                radio = issi.subscription.radio
            except ValueError:
                messages.error(request, f"{issi_value} is geen geldig ISSI nummer")
            except ISSI.DoesNotExist:
                messages.error(request, f"ISSI {issi_value} niet gevonden")
            except ISSI.subscription.RelatedObjectDoesNotExist:
                messages.error(request, f"Geen radio met ISSI {issi_value}")


        elif tei_value:
            if len(tei_value) == 15 and int(tei_value[-1]) == 0:
                tei_value = tei_value[:-1]
            try:
                radio = Radio.objects.get(pk=tei_value)
            except Radio.DoesNotExist:
                messages.error(request, f"Radio met dit TEI {tie_value} nummer niet gevonden")

        if radio:
            return redirect("radio:detail", pk=radio.pk)

        return render(request, self.template_name)



class RadioDetailView(DetailView):
    model = Radio
    template_name = 'radio/detail.html'
    context_object_name = 'radio'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['printers'] = Printer.objects.all()
        return context

    def post(self, request, *args, **kwargs):
        radio = self.get_object()

        printer_id = request.POST.get('printer_id')
        copies = request.POST.get('copies', 2)
        action = request.POST.get("action")

        try:
            printer = Printer.objects.get(id=printer_id)
            print_service = RadioPrintingService(radio, printer)
            if action == "qr":
                res = print_service.print_qr(copies)
            elif action == "tei":
                res = print_service.print_tei(copies)
            elif action == "label":
                res = print_service.print_mobile_label(copies)
            else:
                raise Exception("No action selected")
            messages.success(request, res)

        except Printer.DoesNotExist:
            messages.error(request, "Selected printer does not exist.")
        except Exception as e:
            messages.error(request, f"Printing failed: {str(e)}")

        return redirect('radio:detail', pk=radio.pk)




class UploadSubscriptionsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = 'radio.can_upload_subscriptions'
    template_name = "radio/upload_subscriptions.html"

    def post(self, request):
        if True:
            excel_file = request.FILES["excelFile"]

            wb = openpyxl.load_workbook(excel_file, data_only=True)
            ws = wb.active

            header = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
            col = {name: idx for idx, name in enumerate(header)}

            with transaction.atomic():
                excel_subs = set()
                existing_subs = set(Subscription.objects.values_list('radio__TEI', 'issi__number'))

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
        try:
            pass
        except KeyError as e:
            messages.error(request, f"Kolom ontbreekt in Excel: {e}")
        except Exception as e:
            messages.error(request, f"Er is een fout opgetreden: {e} (ISSI: {issi_cell}, TEI: {tei_cell})")

        return self.get(request)



class LookupView(View):

    def post(self, request, *args, **kwargs):
        if True:
            lookup_type = request.POST.get('type')
            value = request.POST.get('value').strip()

            if not lookup_type or not value:
                return HttpResponseBadRequest(_("type and value required"))

            radio = None

            if lookup_type == 'issi':
                try:
                    issi_value = int(value)
                    if len(str(issi_value)) != 7:
                        return JsonResponse({"status": "error", "message":_("Lengte van een ISSI-nummer moet 7 digits zijn")}, status=500)
                    issi = ISSI.objects.get(number=int(issi_value))
                    radio = issi.subscription.radio
                except ValueError:
                    return JsonResponse({"status": "error", "message": _("ISSI-nummer mag enkel uit cijfers bestaan")}, status=500)
                except ISSI.DoesNotExist:
                    return JsonResponse({"status": "error", "message": _("ISSI-nummer niet gevonden")}, status=404)
                except ISSI.subscription.RelatedObjectDoesNotExist:
                    return JsonResponse({"status": "error", "message": _("Geen radio gevonden met dit ISSI-nummer")}, status=404)

            elif lookup_type == 'tei':
                tei_value = value
                if len(tei_value) == 15 and tei_value[-1] == "0":
                    tei_value = tei_value[:-1]
                try:
                    radio = Radio.objects.get(pk=tei_value)
                except Radio.DoesNotExist:
                    return JsonResponse({"status": "error", "message": _("Radio met dit TEI {tei} nummer niet gevonden").format(tei=tei_value.zfill(14))}, status=404)

            elif lookup_type in ('qr', 'serial'):
                logger.debug(value)

            else:
                return HttpResponseBadRequest(_('invalid lookup type'))

            if radio:
                data = {
                    "status": "success", 
                    "TEI": radio.TEI, 
                    "tei_str": radio.tei_str, 
                    "ISSI": radio.ISSI, 
                    "alias": radio.alias,
                    "fireplan_id": radio.fireplan_id,
                    "radio": str(radio),
                    "result_html": render_to_string("radio/selector/result.html", {"radio": radio})
                }
                return JsonResponse(data)
            else:
                return JsonResponse({"status": "error", "message": _("Radio not found")}, status=404)

        try:
            pass
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)



class SelectorResultView(TemplateView):
    template_name = "radio/selector/result.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['radio'] = Radio.objects.get(pk=self.kwargs.get('pk'))
        return context



