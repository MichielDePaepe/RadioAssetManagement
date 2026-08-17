import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import ListView, DetailView, FormView, TemplateView

from fireplan.models import FireplanInventory, FireplanInventoryRadio, Vehicle
from radio.models import Radio
from .models import RadioContainer, RadioEndpoint, RadioAssignment
from .forms import SwitchRadioForm


class EndpointLookupView(TemplateView):
    template_name = "inventory/endpoint_search.html"


class EndpointDetailView(DetailView):
    model = RadioEndpoint
    template_name = "inventory/endpoint_detail.html"
    context_object_name = "endpoint"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_assignment"] = (
            RadioAssignment.objects
            .filter(endpoint=self.object, end_at__isnull=True)
            .select_related("radio")
            .first()
        )
        return ctx


class EndpointSwitchRadioView(FormView):
    template_name = "inventory/endpoint_switch.html"
    form_class = SwitchRadioForm

    def dispatch(self, request, *args, **kwargs):
        self.endpoint = get_object_or_404(RadioEndpoint, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {"endpoint": self.endpoint}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["endpoint"] = self.endpoint
        return ctx

    def form_valid(self, form):
        radio = form.cleaned_data["radio"]
        note = form.cleaned_data.get("note", "")

        # Nieuwe assignment maken; je model.save() sluit de vorige af (zoals je wilde)
        RadioAssignment.objects.create(
            endpoint=self.endpoint,
            radio=radio,
            note=note,
            created_by=self.request.user if self.request.user.is_authenticated else None,
        )
        # Optioneel: primary_radio updaten als je dat wil
        # self.endpoint.primary_radio = radio
        # self.endpoint.save(update_fields=["primary_radio"])

        return redirect("inventory:endpoint_detail", pk=self.endpoint.pk)


def endpoint_search(request):
    q = (request.GET.get("q") or "").strip()
    qs = RadioEndpoint.objects.select_related("container").order_by("container__label", "name")
    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(container__label__icontains=q)
        )[:20]
    else:
        qs = qs[:20]

    data = [
        {
            "id": ep.id,
            "label": f"{ep.container.label} – {ep.name}",
            "url": reverse("inventory:endpoint_detail", kwargs={"pk": ep.id}),
        }
        for ep in qs
    ]
    return JsonResponse({"results": data})


def radio_search(request):
    q = (request.GET.get("q") or "").strip()
    qs = Radio.objects.select_related("subscription__issi").order_by("TEI")
    if q:
        # TEI of ISSI of alias
        qs = qs.filter(
            Q(TEI__icontains=q) |
            Q(subscription__issi__number__icontains=q) |
            Q(subscription__issi__alias__icontains=q)
        )[:20]
    else:
        qs = qs[:20]

    data = []
    for r in qs:
        issi = r.ISSI
        alias = r.alias
        data.append({
            "tei": r.TEI,
            "label": f"TEI {r.tei_str} / ISSI {issi or '-'} / {alias or ''}".strip(),
        })
    return JsonResponse({"results": data})


class FireplanInventoryStartView(LoginRequiredMixin, TemplateView):
    template_name = "inventory/fireplan_inventory_start.html"


@login_required
@require_GET
def vehicle_search(request):
    q = (request.GET.get("q") or "").strip()
    qs = Vehicle.objects.select_related("vector__statusCode").order_by("number")
    if q:
        qs = qs.filter(
            Q(number__icontains=q) |
            Q(call_sign__icontains=q) |
            Q(plate__icontains=q) |
            Q(utilisation__icontains=q) |
            Q(vector__name__icontains=q) |
            Q(vector__abbreviation__icontains=q)
        )[:20]
    else:
        qs = qs[:20]

    data = []
    for vehicle in qs:
        vector = getattr(vehicle, "vector", None)
        data.append({
            "id": vehicle.id,
            "label": vehicle.number,
            "indicatif": vehicle.call_sign or vehicle.number,
            "vehicle_alpha_code": vehicle.number,
            "plate": vehicle.plate,
            "utilisation": vehicle.utilisation,
            "vector": vector.name if vector else "",
            "vector_code": vector.resourceCode if vector else "",
            "vector_status": str(vector.statusCode) if vector and vector.statusCode else "",
        })
    return JsonResponse({"results": data})


@login_required
def fireplan_inventory_scan(request, vehicle_id):
    vehicle = get_object_or_404(
        Vehicle.objects.select_related("vector__statusCode"),
        pk=vehicle_id,
    )

    if request.method == "POST":
        return close_fireplan_inventory(request, vehicle)

    return render(
        request,
        "inventory/fireplan_inventory_scan.html",
        {"vehicle": vehicle, "vector": getattr(vehicle, "vector", None)},
    )


@require_POST
def close_fireplan_inventory(request, vehicle):
    try:
        scanned_radios = json.loads(request.POST.get("radios", "[]"))
    except json.JSONDecodeError:
        scanned_radios = []

    tei_values = []
    seen = set()
    for item in scanned_radios:
        tei = str(item.get("tei") or item.get("TEI") or "").strip()
        if not tei.isdigit():
            continue
        tei_int = int(tei)
        if tei_int not in seen:
            seen.add(tei_int)
            tei_values.append(tei_int)

    if not tei_values:
        messages.error(request, "Scan minstens een radio voor je de inventaris afsluit.")
        return redirect("inventory:fireplan_inventory_scan", vehicle_id=vehicle.pk)

    radios = {
        radio.TEI: radio
        for radio in Radio.objects.filter(TEI__in=tei_values).select_related("subscription__issi")
    }

    missing_teis = [str(tei).zfill(15) for tei in tei_values if tei not in radios]
    if missing_teis:
        messages.error(
            request,
            "Deze radio's werden niet gevonden: " + ", ".join(missing_teis),
        )
        return redirect("inventory:fireplan_inventory_scan", vehicle_id=vehicle.pk)

    user_full_name = request.user.get_full_name() or request.user.get_username()
    vector = getattr(vehicle, "vector", None)

    with transaction.atomic():
        inventory = FireplanInventory.objects.create(
            vehicle_alpha_code=vehicle.number,
            vehicle=vehicle,
            vector=vector,
            closed_at=timezone.now(),
            done_by_full_name=user_full_name,
        )

        for tei in tei_values:
            radio = radios[tei]
            FireplanInventoryRadio.objects.create(
                inventory=inventory,
                tracked_item_id=radio.fireplan_id,
                tei=radio.tei_str,
                radio=radio,
            )

    messages.success(
        request,
        f"Inventaris voor {vehicle.number} afgesloten met {len(tei_values)} radio's.",
    )
    if vector:
        return redirect("fireplan:vector_inventory_history", resource_code=vector.pk)
    return redirect("inventory:fireplan_inventory_start")
