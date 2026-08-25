import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import ListView, DetailView, FormView, TemplateView, CreateView, UpdateView, DeleteView

from fireplan.models import FireplanInventory, FireplanInventoryRadio, Vehicle
from radio.models import Radio
from .models import Location, RadioPosition, RadioPositionAssignment
from .forms import LocationForm, PositionAssignmentForm, RadioPositionForm
from .services import assign_substitute, change_primary, release_primary, release_substitute


def _radio_label(radio):
    if not radio:
        return "-"
    return radio.inventory_label


def _latest_inventory_by_vector(vectors):
    vector_ids = [vector.pk for vector in vectors]
    latest = {}
    if not vector_ids:
        return latest

    inventories = (
        FireplanInventory.objects
        .filter(vector_id__in=vector_ids, closed_at__isnull=False)
        .select_related("vector", "vehicle")
        .prefetch_related("radios__radio__subscription__issi", "radios__radio__model")
        .order_by("vector_id", "-closed_at", "-synced_at", "-id")
    )
    for inventory in inventories:
        latest.setdefault(inventory.vector_id, inventory)
    return latest


def _build_location_dashboard(location):
    own_locations = [location]
    child_locations = list(location.children.filter(active=True).order_by("name"))
    manual_locations = list(location.dashboard_locations.filter(active=True).order_by("name"))
    locations_by_id = {item.pk: item for item in own_locations + child_locations + manual_locations}
    locations = list(locations_by_id.values())
    displayed_locations_by_id = {item.pk: item for item in child_locations + manual_locations}
    displayed_locations_by_id.pop(location.pk, None)
    displayed_locations = list(displayed_locations_by_id.values())

    vectors = list(
        location.dashboard_vectors
        .select_related("vehicle", "service", "statusCode", "resourceTypeCode")
        .order_by("display_name", "name", "resourceCode")
    )
    vector_ids = [vector.pk for vector in vectors]
    vehicle_ids = [vector.vehicle_id for vector in vectors if vector.vehicle_id]
    location_ids = [item.pk for item in locations]

    positions = list(
        RadioPosition.objects
        .filter(active=True)
        .filter(
            Q(location_id__in=location_ids)
            | Q(vector_id__in=vector_ids)
            | Q(vehicle_id__in=vehicle_ids)
        )
        .select_related("location", "vector", "vehicle")
        .prefetch_related("assignments__radio__subscription__issi", "assignments__radio__model")
        .order_by("location__name", "vector__display_name", "vector__name", "vehicle__number", "order", "name")
    )

    latest_inventories = _latest_inventory_by_vector(vectors)
    scanned_radio_ids = set()
    scan_rows = []
    for vector in vectors:
        inventory = latest_inventories.get(vector.pk)
        radios = []
        if inventory:
            for inventory_radio in inventory.radios.all():
                radio = inventory_radio.radio
                if radio:
                    scanned_radio_ids.add(radio.pk)
                radios.append({
                    "inventory_radio": inventory_radio,
                    "radio": radio,
                    "label": _radio_label(radio) if radio else inventory_radio.tei,
                })
        scan_rows.append({
            "vector": vector,
            "inventory": inventory,
            "radios": radios,
        })

    expected_rows = []
    expected_radio_ids = set()
    for position in positions:
        primary = position.active_primary
        substitute = position.active_substitute
        operational = substitute or primary
        radio = operational.radio if operational else None
        latest_scan = radio.latest_fireplan_inventory_radio if radio else None
        radio_id = radio.pk if radio else None
        if radio_id:
            expected_radio_ids.add(radio_id)

        if not radio:
            status = "unassigned"
        elif radio_id in scanned_radio_ids:
            status = "present"
        elif latest_scan and latest_scan.inventory.vector_id not in vector_ids:
            status = "elsewhere"
        else:
            status = "missing"

        expected_rows.append({
            "position": position,
            "primary": primary,
            "substitute": substitute,
            "operational": operational,
            "radio": radio,
            "status": status,
            "latest_scan": latest_scan,
        })

    dashboard_items = []
    for vector in vectors:
        item_positions = [
            row for row in expected_rows
            if row["position"].vector_id == vector.pk
            or (vector.vehicle_id and row["position"].vehicle_id == vector.vehicle_id)
        ]
        vector_indicative = vector.vehicle.call_sign if vector.vehicle_id and vector.vehicle.call_sign else ""
        if not vector_indicative and vector.vehicle_id:
            vector_indicative = vector.vehicle.number
        vector_label = str(vector)
        if vector_indicative:
            vector_label = f"{vector_label} - {vector_indicative}"
        dashboard_items.append({
            "kind": "vector",
            "object": vector,
            "label": vector_label,
            "positions": item_positions,
            "inventory": latest_inventories.get(vector.pk),
        })

    for item in displayed_locations:
        item_positions = [
            row for row in expected_rows
            if row["position"].location_id == item.pk
        ]
        dashboard_items.append({
            "kind": "location",
            "object": item,
            "label": str(item),
            "positions": item_positions,
            "inventory": None,
        })

    unexpected_rows = []
    for scan_row in scan_rows:
        inventory = scan_row["inventory"]
        for scanned in scan_row["radios"]:
            radio = scanned["radio"]
            if radio and radio.pk in expected_radio_ids:
                continue
            unexpected_rows.append({
                "vector": scan_row["vector"],
                "inventory": inventory,
                "radio": radio,
                "label": scanned["label"],
                "inventory_radio": scanned["inventory_radio"],
                "assignment": radio.active_position_assignment if radio else None,
            })

    counts = {
        "expected": len(expected_rows),
        "present": sum(1 for row in expected_rows if row["status"] == "present"),
        "missing": sum(1 for row in expected_rows if row["status"] in ("missing", "elsewhere")),
        "unexpected": len(unexpected_rows),
    }
    return {
        "dashboard_locations": locations,
        "dashboard_vectors": vectors,
        "dashboard_items": dashboard_items,
        "scan_rows": scan_rows,
        "expected_rows": expected_rows,
        "unexpected_rows": unexpected_rows,
        "counts": counts,
    }


class LocationListView(LoginRequiredMixin, ListView):
    model = Location
    template_name = "inventory/location_list.html"
    context_object_name = "locations"

    def get_queryset(self):
        qs = Location.objects.select_related("service", "parent").order_by("name")
        self.type_filter = (self.request.GET.get("type") or "").strip()
        if self.type_filter:
            qs = qs.filter(location_type=self.type_filter)
        query = (self.request.GET.get("q") or "").strip()
        if query:
            qs = qs.filter(
                Q(name__icontains=query)
                | Q(service__code__icontains=query)
                | Q(service__description__icontains=query)
                | Q(parent__name__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["type_filter"] = getattr(self, "type_filter", "")
        ctx["location_types"] = Location.LocationType.choices
        return ctx


class LocationCreateView(LoginRequiredMixin, CreateView):
    model = Location
    form_class = LocationForm
    template_name = "inventory/location_form.html"

    def get_success_url(self):
        return reverse("inventory:location_detail", kwargs={"pk": self.object.pk})


class LocationUpdateView(LoginRequiredMixin, UpdateView):
    model = Location
    form_class = LocationForm
    template_name = "inventory/location_form.html"

    def get_success_url(self):
        return reverse("inventory:location_detail", kwargs={"pk": self.object.pk})


class LocationDetailView(LoginRequiredMixin, DetailView):
    model = Location
    template_name = "inventory/location_detail.html"
    context_object_name = "location"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["positions"] = (
            self.object.radio_positions
            .prefetch_related("assignments__radio__subscription__issi", "assignments__radio__model")
            .order_by("order", "name")
        )
        ctx.update(_build_location_dashboard(self.object))
        return ctx


class RadioPositionListView(LoginRequiredMixin, ListView):
    model = RadioPosition
    template_name = "inventory/position_list.html"
    context_object_name = "positions"
    paginate_by = 100

    def get_queryset(self):
        qs = (
            RadioPosition.objects
            .select_related("vector", "vector__vehicle", "vehicle", "location")
            .prefetch_related("assignments__radio__subscription__issi", "assignments__radio__model")
            .order_by("location__name", "vehicle__number", "vector__name", "order", "name")
        )
        self.status_filter = (self.request.GET.get("status") or "active").strip()
        if self.status_filter == "inactive":
            qs = qs.filter(active=False)
        else:
            self.status_filter = "active"
            qs = qs.filter(active=True)

        query = (self.request.GET.get("q") or "").strip()
        if query:
            qs = qs.filter(
                Q(name__icontains=query)
                | Q(vector__name__icontains=query)
                | Q(vector__abbreviation__icontains=query)
                | Q(vector__resourceCode__icontains=query)
                | Q(vector__vehicle__number__icontains=query)
                | Q(vector__vehicle__call_sign__icontains=query)
                | Q(vector__vehicle__plate__icontains=query)
                | Q(vehicle__number__icontains=query)
                | Q(vehicle__call_sign__icontains=query)
                | Q(vehicle__plate__icontains=query)
                | Q(location__name__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = (self.request.GET.get("q") or "").strip()
        ctx["status_filter"] = getattr(self, "status_filter", (self.request.GET.get("status") or "active").strip())
        return ctx


class RadioPositionCreateView(LoginRequiredMixin, CreateView):
    model = RadioPosition
    form_class = RadioPositionForm
    template_name = "inventory/position_form.html"

    def get_success_url(self):
        return reverse("inventory:position_detail", kwargs={"pk": self.object.pk})


class RadioPositionUpdateView(LoginRequiredMixin, UpdateView):
    model = RadioPosition
    form_class = RadioPositionForm
    template_name = "inventory/position_form.html"

    def get_success_url(self):
        return reverse("inventory:position_detail", kwargs={"pk": self.object.pk})


class RadioPositionDeleteView(LoginRequiredMixin, DeleteView):
    model = RadioPosition
    template_name = "inventory/position_confirm_delete.html"
    context_object_name = "position"

    def get_success_url(self):
        location_id = self.object.location_id
        if location_id:
            return reverse("inventory:location_detail", kwargs={"pk": location_id})
        return reverse("inventory:position_list")

    def form_valid(self, form):
        position_label = str(self.object)
        response = super().form_valid(form)
        messages.success(self.request, _("Position %(position)s deleted.") % {"position": position_label})
        return response


class RadioPositionDetailView(LoginRequiredMixin, DetailView):
    model = RadioPosition
    template_name = "inventory/position_detail.html"
    context_object_name = "position"

    def get_queryset(self):
        return (
            RadioPosition.objects
            .select_related("vector", "vector__vehicle", "vehicle", "location")
            .prefetch_related("assignments__radio__subscription__issi", "assignments__radio__model")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        assignments = (
            self.object.assignments
            .select_related(
                "radio",
                "radio__model",
                "radio__subscription__issi",
                "replaces",
                "replaces__radio",
                "created_by",
            )
            .order_by("-assigned_at", "-id")
        )
        ctx["active_primary"] = next(
            (assignment for assignment in assignments if assignment.role == RadioPositionAssignment.Role.PRIMARY and assignment.ended_at is None),
            None,
        )
        ctx["active_substitute"] = next(
            (assignment for assignment in assignments if assignment.role == RadioPositionAssignment.Role.SUBSTITUTE and assignment.ended_at is None),
            None,
        )
        ctx["assignments"] = assignments
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get("position_action")
        radio_pk = request.POST.get("radio")

        try:
            if action == "change_primary":
                if not radio_pk:
                    raise ValidationError(_("A radio needs to be selected."))
                radio = get_object_or_404(Radio, pk=int(radio_pk))
                change_primary(self.object, radio, user=request.user)
                messages.success(request, _("Primary radio changed."))
            elif action == "assign_substitute":
                if not radio_pk:
                    raise ValidationError(_("A radio needs to be selected."))
                radio = get_object_or_404(Radio, pk=int(radio_pk))
                assign_substitute(self.object, radio, user=request.user)
                messages.success(request, _("Substitute radio assigned."))
            elif action == "release_substitute":
                release_substitute(self.object, user=request.user, note=request.POST.get("note", ""))
                messages.success(request, _("Substitute radio released."))
            elif action == "release_primary":
                release_primary(self.object, user=request.user, note=request.POST.get("note", ""))
                messages.success(request, _("Primary radio removed."))
            else:
                raise ValidationError(_("Invalid position action."))
        except (TypeError, ValueError):
            messages.error(request, _("A radio needs to be selected."))
        except ValidationError as exc:
            messages.error(request, str(exc))

        return redirect("inventory:position_detail", pk=self.object.pk)


class PositionAssignmentActionView(LoginRequiredMixin, FormView):
    template_name = "inventory/position_assignment_form.html"
    form_class = PositionAssignmentForm
    action_label = ""

    def dispatch(self, request, *args, **kwargs):
        self.position = get_object_or_404(RadioPosition, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["position"] = self.position
        ctx["action_label"] = self.action_label
        return ctx

    def get_success_url(self):
        return reverse("inventory:position_detail", kwargs={"pk": self.position.pk})


class ChangePrimaryView(PositionAssignmentActionView):
    action_label = _("Change primary radio")

    def form_valid(self, form):
        try:
            change_primary(
                self.position,
                form.cleaned_data["radio"],
                user=self.request.user,
                note=form.cleaned_data.get("note", ""),
            )
            messages.success(self.request, _("Primary radio changed."))
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        return super().form_valid(form)


class AssignSubstituteView(PositionAssignmentActionView):
    action_label = _("Assign substitute radio")

    def form_valid(self, form):
        try:
            assign_substitute(
                self.position,
                form.cleaned_data["radio"],
                user=self.request.user,
                note=form.cleaned_data.get("note", ""),
            )
            messages.success(self.request, _("Substitute radio assigned."))
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        return super().form_valid(form)


class ReleaseSubstituteView(LoginRequiredMixin, TemplateView):
    template_name = "inventory/position_release_substitute.html"

    def dispatch(self, request, *args, **kwargs):
        self.position = get_object_or_404(RadioPosition, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["position"] = self.position
        ctx["active_substitute"] = self.position.active_substitute
        return ctx

    def post(self, request, *args, **kwargs):
        try:
            release_substitute(
                self.position,
                user=request.user,
                note=request.POST.get("note", ""),
            )
            messages.success(request, _("Substitute radio released."))
        except ValidationError as exc:
            messages.error(request, str(exc))
        return redirect("inventory:position_detail", pk=self.position.pk)


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
            "vector": str(vector) if vector else "",
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
