from django.views import View
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.shortcuts import render, redirect
from django.views.generic.edit import CreateView
from django.views.generic.detail import DetailView
from django.urls import reverse, reverse_lazy
from django.contrib import messages

from .models import *
from .forms import *


class RadioCardView(View):
    def get(self, request, tei):
        context = dict()
        context["radio"] = Radio.objects.get(TEI=int(tei))
        return render(request, "radio/radio_card.html", context)


class RadioCardExampleView(TemplateView):
    template_name = "radio/radio_card_example.html"


class RadioCreateView(CreateView):
    model = Radio
    form_class = RadioForm
    template_name = 'radio/radio_form.html'
    success_url = reverse_lazy('radio:create')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"{self.object.model} with TEI {self.object.TEI} added successfully!")
        return response

