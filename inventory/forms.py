from django import forms
from radio.models import Radio

class SwitchRadioForm(forms.Form):
    endpoint = forms.IntegerField(widget=forms.HiddenInput)
    radio = forms.ModelChoiceField(
        queryset=Radio.objects.all(),
        required=True,
        empty_label=None,
    )
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
