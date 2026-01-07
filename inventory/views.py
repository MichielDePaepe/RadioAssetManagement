from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import ListView, DetailView, FormView, TemplateView

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
