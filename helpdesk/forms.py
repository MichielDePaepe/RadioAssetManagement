from django import forms
from .models import *

class TicketMessageForm(forms.ModelForm):
    class Meta:
        model = TicketMessage
        fields = ['message', 'status_after']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'status_after': forms.Select(attrs={'class': 'form-select'}),
        }

class TicketSearchForm(forms.Form):
    tei = forms.CharField(required=False, label="TEI", widget=forms.TextInput(attrs={'class': 'form-control'}))
    astrid_ticket = forms.CharField(required=False, label="Astrid ticket", widget=forms.TextInput(attrs={'class': 'form-control'}))

class TicketCreateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['radio', 'title', 'description', 'astrid_ticket']
        widgets = {
            'radio': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'external_reference': forms.TextInput(attrs={'class': 'form-control'}),
        }
