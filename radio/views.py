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
from django.db.models import Case, Count, IntegerField, Prefetch, Q, Value, When
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
from fireplan.models import FireplanInventoryRadio
from .forms import *
from printer.models import *
from .services.printing import RadioPrintingService
from .services.image_service import ImageGenerator
from inventory.models import RadioPositionAssignment

SCANNER_KEYBOARD_TRANSLATION = str.maketrans({
    'a': 'q', 'A': 'Q', 'z': 'w', 'Z': 'W', 'q': 'a', 'Q': 'A',
    'm': ';', 'M': ':', 'w': 'z', 'W': 'Z', '&': '1', 'é': '2',
    '"': '3', '\'': '4', '’': '4', '(': '5', '§': '6', 'è': '7',
    '!': '8', 'ç': '9', 'à': '0', '=': '/', ':': '.', '+': '?',
    '-': '=', ';': ',',
})

SCANNER_QWERTY_TO_AZERTY_TRANSLATION = str.maketrans({
    'q': 'a', 'Q': 'A', '.': ':', '>': '/',
    '<': '.', 'M': '?', 'd': 'd', '/': '=', '!': '1', '@': '2',
    '*': '8', ')': '0', 'm': ',',
})

SCANNER_QWERTY_SHIFTED_DIGITS_TRANSLATION = str.maketrans({
    'q': 'a', 'Q': 'A', '.': ':', '>': '/',
    '<': '.', 'M': '?', 'd': 'd', '/': '=', '!': '1', '&': '2',
    '$': '8', '*': '1', ')': '0', 'm': ',',
})

SCANNER_STANDARD_SHIFTED_DIGITS_TRANSLATION = str.maketrans({
    ')': '0', '!': '1', '@': '2', '#': '3', '$': '4',
    '%': '5', '^': '6', '&': '7', '*': '8', '(': '9',
})

SCANNER_KEYBOARD_TRANSLATIONS = (
    SCANNER_KEYBOARD_TRANSLATION,
    SCANNER_QWERTY_TO_AZERTY_TRANSLATION,
    SCANNER_QWERTY_SHIFTED_DIGITS_TRANSLATION,
    SCANNER_STANDARD_SHIFTED_DIGITS_TRANSLATION,
)

QR_CODE_PATTERN = re.compile(
    r"https?://infoscan\.firebru\.brussels\?data[=-](?P<arg1>\d+),(?P<arg2>\d+),(?P<fireplan_id>\d+),(?P<arg4>\d+)"
)


class RadioLookupError(Exception):
    def __init__(self, message, status=404):
        super().__init__(message)
        self.message = message
        self.status = status


def scanner_input_variants(value):
    value = (value or "").strip()
    variants = []

    def add_variant(candidate):
        half_length = len(candidate) // 2
        if half_length and len(candidate) % 2 == 0 and candidate[:half_length] == candidate[half_length:]:
            half = candidate[:half_length]
            if half not in variants:
                variants.append(half)
        if candidate and candidate not in variants:
            variants.append(candidate)

    add_variant(value)
    for candidate in list(variants):
        for translation in SCANNER_KEYBOARD_TRANSLATIONS:
            add_variant(candidate.translate(translation))
    return variants


def radio_lookup_payload(radio, status="success"):
    return {
        "status": status,
        "TEI": radio.TEI,
        "tei": radio.tei_str,
        "tei_str": radio.tei_str,
        "ISSI": radio.ISSI,
        "issi": radio.ISSI,
        "alias": radio.alias,
        "fireplan_id": radio.fireplan_id,
        "model": str(radio.model) if radio.model else "",
        "is_active": radio.is_active,
        "is_DMO_only": radio.is_DMO_only,
        "decommissioned": radio.decommissioned,
        "radio": str(radio),
        "result_html": render_to_string("radio/selector/result.html", {"radio": radio}),
    }


def radio_from_qr_code(value):
    for candidate in scanner_input_variants(value):
        match = QR_CODE_PATTERN.search(candidate)
        if match:
            fireplan_id = int(match.group("fireplan_id"))
            try:
                return Radio.objects.get(fireplan_id=fireplan_id)
            except Radio.DoesNotExist:
                raise RadioLookupError(
                    _("Geen radio gevonden voor Fireplan ID {fireplan_id}").format(fireplan_id=fireplan_id)
                )
    return None


def radio_from_tei(value):
    value = (value or "").strip()
    if not value.isdigit():
        raise RadioLookupError(_("TEI mag enkel uit cijfers bestaan"), status=400)

    tei_value = int(value)
    try:
        return Radio.objects.get(pk=tei_value)
    except Radio.DoesNotExist:
        raise RadioLookupError(
            _("Radio met dit TEI {tei} nummer niet gevonden").format(tei=str(tei_value).zfill(15))
        )


def radio_from_issi(value):
    value = (value or "").strip()
    try:
        issi_value = int(value)
    except ValueError:
        raise RadioLookupError(_("ISSI-nummer mag enkel uit cijfers bestaan"), status=400)

    if len(str(issi_value)) != 7:
        raise RadioLookupError(_("Lengte van een ISSI-nummer moet 7 digits zijn"), status=400)

    try:
        issi = ISSI.objects.get(number=issi_value)
        return issi.subscription.radio
    except ISSI.DoesNotExist:
        raise RadioLookupError(_("ISSI-nummer niet gevonden"))
    except ISSI.subscription.RelatedObjectDoesNotExist:
        raise RadioLookupError(_("Geen radio gevonden met dit ISSI-nummer"))


def radio_from_alias(value):
    issi = ISSI.objects.filter(alias__iexact=(value or "").strip()).first()
    if not issi:
        raise RadioLookupError(_("Geen ISSI gevonden met alias “{alias}”").format(alias=value))
    if hasattr(issi, "subscription") and hasattr(issi.subscription, "radio"):
        return issi.subscription.radio
    raise RadioLookupError(_("Geen radio gekoppeld aan deze alias"))


def find_radio_by_any_input(value, lookup_type="auto"):
    value = (value or "").strip()
    if not value:
        raise RadioLookupError(_("Vul een waarde in."), status=400)

    if lookup_type in ("auto", "qr", "serial"):
        radio = radio_from_qr_code(value)
        if radio:
            return radio
        if lookup_type in ("qr", "serial"):
            for candidate in scanner_input_variants(value):
                if candidate.isdigit():
                    return radio_from_tei(candidate)
            raise RadioLookupError(_("QR-code of TEI niet gevonden"))

    if lookup_type == "tei":
        return radio_from_tei(value)
    if lookup_type == "issi":
        return radio_from_issi(value)
    if lookup_type == "alias":
        return radio_from_alias(value)

    if lookup_type != "auto":
        raise RadioLookupError(_("invalid lookup type"), status=400)

    for candidate in scanner_input_variants(value):
        if candidate.isdigit():
            try:
                return radio_from_tei(candidate)
            except RadioLookupError as tei_error:
                if len(str(int(candidate))) != 7:
                    raise tei_error
            return radio_from_issi(candidate)

    return radio_from_alias(value)


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


class RadioListView(LoginRequiredMixin, ListView):
    model = Radio
    template_name = "radio/radio_list.html"
    context_object_name = "radios"
    paginate_by = 100

    def get_base_queryset(self):
        latest_fireplan_radios = (
            FireplanInventoryRadio.objects
            .filter(inventory__closed_at__isnull=False)
            .select_related("inventory", "inventory__vector", "inventory__vehicle")
            .order_by("-inventory__closed_at", "-inventory__synced_at", "-id")
        )
        return Radio.objects.select_related(
            "model",
            "subscription__issi",
            "subscription__issi__customer",
            "subscription__issi__discipline",
        ).prefetch_related(
            Prefetch(
                "fireplan_inventory_radios",
                queryset=latest_fireplan_radios,
                to_attr="_latest_fireplan_inventory_radios",
            ),
        ).annotate(
            direct_ticket_count=Count("tickets", distinct=True),
            old_radio_request_count=Count("requests_as_old", distinct=True),
            ticket_count=Count("tickets", distinct=True) + Count("requests_as_old", distinct=True),
            status_rank=Case(
                When(decommissioned=True, then=Value(4)),
                When(subscription__DMO_only=True, then=Value(2)),
                When(subscription__active=True, then=Value(1)),
                default=Value(3),
                output_field=IntegerField(),
            ),
        )

    def get_queryset(self):
        qs = self.get_base_queryset()

        query = self.request.GET.get("q", "").strip()
        if query:
            filters = (
                Q(model__name__icontains=query)
                | Q(subscription__issi__alias__icontains=query)
                | Q(subscription__issi__customer__name__icontains=query)
                | Q(subscription__issi__discipline__name__icontains=query)
            )
            if query.isdigit():
                filters |= Q(TEI=int(query)) | Q(subscription__issi__number=int(query))
            qs = qs.filter(filters)

        status = self.request.GET.get("status", "").strip()
        if status == "active":
            qs = qs.filter(subscription__active=True, subscription__DMO_only=False, decommissioned=False)
        elif status == "dmo":
            qs = qs.filter(subscription__DMO_only=True, decommissioned=False)
        elif status == "decommissioned":
            qs = qs.filter(decommissioned=True)
        elif status == "inactive":
            qs = qs.filter(decommissioned=False).filter(
                Q(subscription__isnull=True) | Q(subscription__active=False, subscription__DMO_only=False)
            )

        model = self.request.GET.get("model", "").strip()
        if model.isdigit():
            qs = qs.filter(model_id=int(model))

        sort = self.request.GET.get("sort", "TEI")
        allowed_sorts = {
            "TEI",
            "-TEI",
            "model__name",
            "-model__name",
            "subscription__issi__number",
            "-subscription__issi__number",
            "subscription__issi__alias",
            "-subscription__issi__alias",
            "status_rank",
            "-status_rank",
            "ticket_count",
            "-ticket_count",
        }
        if sort not in allowed_sorts:
            sort = "TEI"

        return qs.order_by(sort, "TEI")

    def get_status_counts(self):
        qs = self.get_base_queryset()
        model = self.request.GET.get("model", "").strip()
        if model.isdigit():
            qs = qs.filter(model_id=int(model))
        return {
            "all": qs.count(),
            "active": qs.filter(subscription__active=True, subscription__DMO_only=False, decommissioned=False).count(),
            "dmo": qs.filter(subscription__DMO_only=True, decommissioned=False).count(),
            "decommissioned": qs.filter(decommissioned=True).count(),
            "inactive": qs.filter(decommissioned=False).filter(
                Q(subscription__isnull=True) | Q(subscription__active=False, subscription__DMO_only=False)
            ).count(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "").strip()
        context["current_sort"] = self.request.GET.get("sort", "TEI")
        context["status"] = self.request.GET.get("status", "").strip()
        context["selected_model"] = self.request.GET.get("model", "").strip()
        context["radio_models"] = RadioModel.objects.filter(radio__isnull=False).distinct().order_by("name")
        context["status_counts"] = self.get_status_counts()
        context["base_query"] = self.request.GET.copy()
        context["base_query"].pop("page", None)
        context["base_query"].pop("status", None)
        context["base_query"].pop("model", None)
        context["base_query_string"] = context["base_query"].urlencode()
        context["columns"] = [
            ("TEI", _("TEI")),
            ("model__name", _("Type")),
            ("status_rank", _("Status")),
            ("subscription__issi__number", _("ISSI")),
            ("subscription__issi__alias", _("Alias")),
            ("ticket_count", _("Tickets")),
        ]
        return context


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
        try:
            data = json.loads(request.body)
            scanned_line = data.get("scanned_line", "")
            logger.debug(f"Radio scan input: {scanned_line}")

            radio = find_radio_by_any_input(scanned_line, lookup_type="qr")
            return JsonResponse(radio_lookup_payload(radio, status="ok"))
        except RadioLookupError as e:
            return JsonResponse({"status": "error", "message": e.message}, status=e.status)
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
        context["active_position_assignments"] = (
            RadioPositionAssignment.objects
            .filter(radio=radio, ended_at__isnull=True)
            .select_related(
                "position",
                "position__vector",
                "position__vehicle",
                "position__location",
                "replaces",
                "replaces__radio",
            )
        )
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
            lookup_type = request.POST.get('type', 'auto')
            value = request.POST.get('value', '').strip()

            if not lookup_type or not value:
                return HttpResponseBadRequest(_("type and value required"))

            radio = find_radio_by_any_input(value, lookup_type=lookup_type)
            return JsonResponse(radio_lookup_payload(radio))

        except RadioLookupError as e:
            return JsonResponse({"status": "error", "message": e.message}, status=e.status)
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
    permission_required = "radio.can_create_decommission_requests"

    def get_radio(self):
        radio_pk = self.kwargs.get("pk")
        if radio_pk:
            return get_object_or_404(Radio, pk=radio_pk)
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["radio"] = self.get_radio()
        context["form"] = kwargs.get("form") or DecommissioningRequestForm()
        return context

    def post(self, request, *args, **kwargs):
        form = DecommissioningRequestForm(request.POST)
        radio = self.get_radio()

        try:

            if not form.is_valid():
                raise Exception(form.errors.as_text())

            if not radio:
                # Get the selected radio primary key from the POST data
                radio_pk = request.POST.get("radio")

                # A radio must be selected, otherwise raise an exception
                if not radio_pk:
                    raise Exception(_("A radio needs to be selected."))

                # Fetch the radio object from the database
                radio = Radio.objects.get(pk=int(radio_pk))

            radio_url = reverse("radio:detail", kwargs={"pk": radio.pk})

            if radio.decommissioned:
                raise Exception(_("The selected <a href='{url}'>radio</a> is already decommissioned.").format(url=radio_url))

            # Prevent decommissioning of an active radio
            if radio.is_active:
                raise Exception(_("The selected <a href='{url}'>radio</a> is still active.").format(url=radio_url))

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
            req = RadioDecommissioningTicket.objects.filter(
                radio=radio,
                ticket_type__code="DECOMMISSIONING",
            ).exclude(status__code="CLOSED").first()
            if req:
                ticket_url = reverse("helpdesk:ticket_detail", kwargs={"pk": req.pk})
                raise Exception(
                    _("There is an open decommissioning request for this <a href='{radio_url}'>radio</a>: <a href='{ticket_url}'>#{ticket_id}</a>")
                    .format(radio_url=radio_url, ticket_url=ticket_url, ticket_id=req.pk)
                )

            # If no conflicts are found, create a new decommissioning request
            ticket = RadioDecommissioningTicket.objects.create(
                radio=radio,
                description=form.cleaned_data["description"],
                created_by=request.user,
            )

            # Show a success message to the user
            messages.success(request, _("Decommissioning request created."))
            return redirect("helpdesk:ticket_detail", pk=ticket.pk)

        except PermissionDenied as e:
            # Permission error -> return 403
            raise
        except Exception as e:
            # Catch all raised exceptions and show them as error messages
            messages.error(request, str(e))

        return self.render_to_response(self.get_context_data(form=form))
