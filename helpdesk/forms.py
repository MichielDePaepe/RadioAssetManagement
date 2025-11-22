# helpdesk/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import *


class TicketLogForm(forms.ModelForm):
    class Meta:
        model = TicketLog
        fields = ["note", "status_after"]
        widgets = {
            "note": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Voeg een nota toe…", "class": "form-control"}
            ),
            "status_after": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        ticket = kwargs.pop("ticket", None)
        super().__init__(*args, **kwargs)

        # Zet volgorde
        self.order_fields(["note", "status_after"])

        # Label aanpassen
        self.fields["status_after"].label = "Nieuwe status"

        # Dropdown met eerste optie "Status niet wijzigen"
        choices = [("", "Status niet wijzigen")]
        choices += [(s.pk, s.name) for s in TicketStatus.objects.all()]
        self.fields["status_after"].choices = choices

        # Opslaan van huidig ticket (voor fallback)
        self.ticket = ticket




class TicketEditForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["ticket_type", "priority", "siamu_ticket", "assigned_to"]
        widgets = {
            "ticket_type": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "siamu_ticket": forms.TextInput(attrs={"class": "form-control", "placeholder": "SIAMU-nummer"}),
            "assigned_to": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # ASTRID_REQUEST niet selecteerbaar
        self.fields["ticket_type"].queryset = TicketType.objects.exclude(code="ASTRID_REQUEST")

        # Controle op rechten
        if user:
            if not user.has_perm("helpdesk.can_edit_ticket_fields"):
                for f in ["ticket_type", "priority", "siamu_ticket"]:
                    self.fields[f].widget.attrs["readonly"] = True
                    self.fields[f].widget.attrs["disabled"] = True

            if not user.has_perm("helpdesk.can_assign_ticket"):
                self.fields["assigned_to"].widget.attrs["readonly"] = True
                self.fields["assigned_to"].widget.attrs["disabled"] = True


class TicketCreateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = [
            "title",
            "description",
            "ticket_type",
            "priority",
            "radio",
            "external_reference",
            "siamu_ticket",
            "assigned_to",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Titel"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Beschrijving"}),
            "ticket_type": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "radio": forms.Select(attrs={"class": "form-select"}),
            "external_reference": forms.TextInput(attrs={"class": "form-control", "placeholder": "Extern referentie"}),
            "siamu_ticket": forms.TextInput(attrs={"class": "form-control", "placeholder": "SIAMU-nummer"}),
            "assigned_to": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ASTRID_REQUEST niet als type aanbieden bij nieuwe tickets
        self.fields["ticket_type"].queryset = TicketType.objects.exclude(code="ASTRID_REQUEST")
