from django import forms
from django.db.models import CharField, Value
from django.db.models.functions import Coalesce, Lower, NullIf
from django.utils.translation import gettext_lazy as _

from fireplan.models import Vector, Vehicle
from radio.models import Radio
from .models import Location, RadioPosition


def _ordered_vectors():
    return (
        Vector.objects
        .annotate(
            sort_label=Coalesce(
                NullIf("display_name", Value("")),
                NullIf("name", Value("")),
                "resourceCode",
                output_field=CharField(),
            )
        )
        .order_by(Lower("sort_label"), "resourceCode")
    )


class LocationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["dashboard_vectors"].queryset = _ordered_vectors()
        self.fields["dashboard_locations"].queryset = Location.objects.order_by(Lower("name"), "id")
        self.fields["parent"].queryset = Location.objects.order_by(Lower("name"), "id")

    class Meta:
        model = Location
        fields = [
            "name",
            "location_type",
            "service",
            "parent",
            "dashboard_vectors",
            "dashboard_locations",
            "active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "location_type": forms.Select(attrs={"class": "form-select"}),
            "service": forms.Select(attrs={"class": "form-select"}),
            "parent": forms.Select(attrs={"class": "form-select"}),
            "dashboard_vectors": forms.SelectMultiple(attrs={"class": "form-select", "size": 8}),
            "dashboard_locations": forms.SelectMultiple(attrs={"class": "form-select", "size": 8}),
            "active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class RadioPositionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vector"].queryset = _ordered_vectors()
        self.fields["vehicle"].queryset = Vehicle.objects.order_by(Lower("number"), "id")
        self.fields["location"].queryset = Location.objects.order_by(Lower("name"), "id")

    class Meta:
        model = RadioPosition
        fields = ["name", "order", "active", "vector", "vehicle", "location"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "vector": forms.Select(attrs={"class": "form-select"}),
            "vehicle": forms.Select(attrs={"class": "form-select"}),
            "location": forms.Select(attrs={"class": "form-select"}),
        }


class PositionAssignmentForm(forms.Form):
    radio = forms.ModelChoiceField(
        queryset=Radio.objects.select_related("model", "subscription__issi").order_by("TEI"),
        required=True,
        empty_label=None,
        label=_("Radio"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    note = forms.CharField(
        required=False,
        label=_("Note"),
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )
