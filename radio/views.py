from django.views import View
from django.views.generic import ListView, TemplateView
from django.http import JsonResponse, Http404, HttpResponseBadRequest, HttpResponse
from django.template.loader import render_to_string
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.detail import DetailView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.utils.translation import gettext as _
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils.http import url_has_allowed_host_and_scheme
from itertools import chain



from io import BytesIO
import openpyxl
import json
import re
import logging
logger = logging.getLogger(__name__)

from .models import *
from astrid.models import Request
from fireplan.client import FireplanClient
from .forms import *
from printer.models import *
from .services.printing import RadioPrintingService
from .services.image_service import ImageGenerator


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
        try:
            fireplan_id, created = FireplanClient().get_or_create_radio_fireplan_id(
                form.cleaned_data["fireplan_serial_number"]
            )
            form.instance.fireplan_id = fireplan_id
            if created:
                messages.info(
                    self.request,
                    _("Radio aangemaakt in Fireplan met ID {fireplan_id}.").format(
                        fireplan_id=fireplan_id
                    ),
                )
        except Exception as exc:
            form.add_error(
                None,
                _("Radio kon niet aangemaakt worden in Fireplan: {error}").format(
                    error=exc
                ),
            )
            return self.form_invalid(form)

        response = super().form_valid(form)
        messages.success(self.request, f"{self.object.model} with TEI {self.object.TEI} added successfully!")
        return response


class ISSIAliasListView(LoginRequiredMixin, ListView):
    model = ISSI
    template_name = "radio/issi_alias_list.html"
    context_object_name = "issis"
    paginate_by = 100

    def get_queryset(self):
        qs = ISSI.objects.select_related(
            "customer",
            "discipline",
            "subscription__radio__model",
        )

        query = self.request.GET.get("q", "").strip()
        if query:
            filters = (
                Q(alias__icontains=query)
                | Q(customer__name__icontains=query)
                | Q(discipline__name__icontains=query)
            )
            if query.isdigit():
                filters |= Q(number=int(query))
            qs = qs.filter(filters)

        sort = self.request.GET.get("sort", "number")
        allowed_sorts = {
            "number",
            "-number",
            "alias",
            "-alias",
            "customer__name",
            "-customer__name",
            "discipline__name",
            "-discipline__name",
            "subscription__radio__model__name",
            "-subscription__radio__model__name",
            "subscription__radio__TEI",
            "-subscription__radio__TEI",
        }
        if sort not in allowed_sorts:
            sort = "number"

        return qs.order_by(sort)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "").strip()
        context["current_sort"] = self.request.GET.get("sort", "number")
        context["columns"] = [
            ("number", _("ISSI")),
            ("alias", _("Alias")),
            ("customer__name", _("Customer")),
            ("discipline__name", _("Discipline")),
            ("subscription__radio__model__name", _("Type radio")),
            ("subscription__radio__TEI", _("TEI")),
        ]
        return context


class ISSICreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = ISSI
    form_class = ISSIForm
    template_name = "radio/issi_form.html"
    context_object_name = "issi"
    permission_required = "radio.add_issi"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("ISSI {issi} toegevoegd.").format(issi=self.object.number))
        return response

    def get_success_url(self):
        return reverse("radio:issi_alias_edit", kwargs={"pk": self.object.pk})


class ISSIAliasUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = ISSI
    form_class = ISSIAliasForm
    template_name = "radio/issi_alias_form.html"
    context_object_name = "issi"
    permission_required = "radio.change_issi"

    def form_valid(self, form):
        messages.success(self.request, _("Alias voor ISSI {issi} bijgewerkt.").format(issi=self.object.number))
        return super().form_valid(form)

    def get_success_url(self):
        next_url = self.request.POST.get("next") or self.request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={self.request.get_host()}):
            return next_url
        return reverse("radio:issi_alias_edit", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        next_url = self.request.GET.get("next", "")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={self.request.get_host()}):
            context["next_url"] = next_url
        else:
            context["next_url"] = reverse("radio:issi_aliases")
        return context


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
            try:
                radio = Radio.objects.get(pk=tei_value)
            except Radio.DoesNotExist:
                messages.error(request, f"Radio met dit TEI {tei_value} nummer niet gevonden")

        if radio:
            return redirect("radio:detail", pk=radio.pk)

        return render(request, self.template_name)



class RadioDetailView(DetailView):
    model = Radio
    template_name = 'radio/detail.html'
    context_object_name = 'radio'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        radio = self.object

        # Tickets die rechtstreeks gelinkt zijn aan de radio
        direct_tickets = Ticket.objects.filter(
            radio=radio
        ).select_related("ticket_type", "status")

        # Requests waar deze radio als old_radio voorkomt
        related_requests = Request.objects.filter(
            Q(old_radio=radio)
        ).select_related("ticket_type", "status")

        # Combineer beide querysets
        all_tickets = sorted(
            chain(direct_tickets, related_requests),
            key=lambda t: t.updated_at,
            reverse=True,
        )

        context["tickets"] = all_tickets
        context["printers"] = Printer.objects.all()
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
            elif action == "alias":
                res = print_service.print_alias_label(copies)
            else:
                raise Exception("No action selected")
            messages.success(request, res)

        except Printer.DoesNotExist:
            messages.error(request, "Selected printer does not exist.")
        except Exception as e:
            messages.error(request, f"Printing failed: {str(e)}")

        return redirect('radio:detail', pk=radio.pk)






class LookupView(View):

    def post(self, request, *args, **kwargs):
        try:
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
                try:
                    radio = Radio.objects.get(pk=tei_value)
                except Radio.DoesNotExist:
                    return JsonResponse({"status": "error", "message": _("Radio met dit TEI {tei} nummer niet gevonden").format(tei=tei_value.zfill(15))}, status=404)

            elif lookup_type == 'alias':
                try:
                    issi = ISSI.objects.filter(alias__iexact=value).first()
                    if not issi:
                        return JsonResponse(
                            {"status": "error", "message": _("Geen ISSI gevonden met alias “{alias}”").format(alias=value)},
                            status=404
                        )
                    if hasattr(issi, "subscription") and hasattr(issi.subscription, "radio"):
                        radio = issi.subscription.radio
                    else:
                        return JsonResponse(
                            {"status": "error", "message": _("Geen radio gekoppeld aan deze alias")},
                            status=404
                        )
                except Exception as e:
                    logger.error(f"Alias lookup error: {e}")
                    return JsonResponse({"status": "error", "message": _("Fout bij het zoeken op alias")}, status=500)


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

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)



class SelectorResultView(TemplateView):
    template_name = "radio/selector/result.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['radio'] = Radio.objects.get(pk=self.kwargs.get('pk'))
        return context




class QRImageView(View):

    def get(self, request, pk, type):
        # get the Radio object
        radio = Radio.objects.get(pk=pk)

        # map grayscale to black/yellow
        ig = ImageGenerator(radio)

        img = None
        if type == "qr":
            img = ig.qr_image(color_dark=(0, 0, 0), color_light=(255, 255, 0))
        elif type == "tei_label":
            img = ig.portable_radio_tei_label(color_dark=(0, 0, 0), color_light=(255, 255, 0))
        elif type == "mobile_label":
            img = ig.mobile_radio_label(color_dark=(255,255,255), color_light=(0,102,204))
        elif type == "alias_label":
            img = ig.alias_label(color_dark=(0, 0, 0), color_light=(255, 255, 255))
        else:
            return Http404()

        # save image to in-memory bytes buffer
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        # return as HttpResponse
        return HttpResponse(buffer.getvalue(), content_type="image/png")



class DecommissioningRequestView(PermissionRequiredMixin, TemplateView):
    template_name = "radio/decommissioning_request.html"
    permission_required ="radio.can_create_decommission_requests"

    def post(self, request):
        try:

            # Get the selected radio primary key from the POST data
            radio_pk = request.POST.get("radio")

            # A radio must be selected, otherwise raise an exception
            if not radio_pk:
                raise Exception(_("A radio needs to be selected."))

            # Fetch the radio object from the database
            radio = Radio.objects.get(pk=int(radio_pk))

            radio_url = reverse("radio:detail", kwargs={"pk": radio.pk})

            # Prevent decommissioning of an active radio
            if radio.is_active:
                url = reverse("radio:detail", kwargs={"pk": radio.pk})
                raise Exception(_("The selected <a href='{url}'>radio</a> is still active.").format(url=url))

            # Check if there is already an open ASTRID request ticket linked to this radio
            req = Request.objects.filter(
                (Q(radio=radio) | Q(old_radio=radio)) & Q(ticket_type__code="ASTRID_REQUEST")
            ).exclude(status__code="CLOSED").first()

            if req:
                ticket_url = reverse("astrid:request_detail", kwargs={"pk": req.pk})
                raise Exception(
                    _("The <a href='{radio_url}'>radio</a> has an open request ticket: <a href='{ticket_url}'>#{ticket_id}</a>")
                    .format(radio_url=radio_url, ticket_url=ticket_url, ticket_id=req.pk)
                )

            # Check if there is already an open DECOMMISSIONING request ticket linked to this radio
            req = Request.objects.filter(radio=radio, ticket_type__code="DECOMMISSIONING").exclude(status__code="CLOSED").first()
            if req:
                raise Exception(_("There is an open decommissioning request (#{ticket_id}) for this <a href='{url}'>radio</a>").format(ticket_id=req.pk, url=radio_url))
            
            # Check if there is a description
            description = request.POST.get("description")
            if not description:
                raise Exception(_("A reason for the decommissioning request is required."))

            # If no conflicts are found, create a new decommissioning request
            RadioDecommissioningTicket.objects.create(
                radio=radio,
                description=description,
            )

            # Show a success message to the user
            messages.success(request, _("Decommissioning request successful"))

        except PermissionDenied as e:
            # Permission error -> return 403
            raise
        except Exception as e:
            # Catch all raised exceptions and show them as error messages
            messages.error(request, str(e))

        # Redirect back to the same page after handling the request
        return redirect(request.path)
