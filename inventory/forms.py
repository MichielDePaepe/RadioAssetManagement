from django import forms
from django.utils.translation import gettext_lazy as _

from radio.models import Radio
from .models import Location, RadioPosition


class LocationForm(forms.ModelForm):
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
