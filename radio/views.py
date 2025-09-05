from django.views import View
from django.views.generic import TemplateView
from django.http import JsonResponse, Http404
from django.template.loader import render_to_string
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.edit import CreateView
from django.views.generic.detail import DetailView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.urls import reverse, reverse_lazy
from django.contrib import messages

import json
import re

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


@method_decorator(csrf_exempt, name='dispatch')
class ScanQRCodeView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            scanned_line = data.get("scanned_line")

            pattern = re.compile(r"https://infoscan\.firebru\.brussels\?data[=-](?P<arg1>\d+),(?P<arg2>\d+),(?P<fireplan_id>\d+),(?P<arg4>\d+)")

            match = pattern.match(scanned_line)

            if not match:
                # scanner is set to qwerty, try converting if input was on an azerty system
                mapping = str.maketrans({'a': 'q', 'A': 'Q', 'z': 'w', 'Z': 'W', 'q': 'a', 'Q': 'A', 'm': ';', 'M': ':', 'w': 'z', 'W': 'Z', '&': '1', 'é': '2', '"': '3', '\'': '4', '’': '4', '(': '5', '§': '6', 'è': '7', '!': '8', 'ç': '9', 'à': '0', '=': '/', ':': '.', '+': '?', '-': '=', ';': ','})
                match = pattern.match(scanned_line.translate(mapping))

            if match:
                fireplan_id = int(match.group("fireplan_id"))
                radio = Radio.objects.get(fireplan_id=fireplan_id)

                res = {
                    "status": "ok", 
                    "TEI": radio.TEI, 
                    "ISSI": radio.ISSI, 
                    "alias": radio.alias,
                    "fireplan_id": fireplan_id,
                    "radio": str(radio)
                }

                return JsonResponse(res)

            return JsonResponse({"status": "error", "message": "TIE not found"}, status=404)

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
            if len(tei_value) == 15 and int(tei_value[-1]) == 0:
                tei_value = tei_value[:-1]
            try:
                radio = Radio.objects.get(pk=tei_value)
            except Radio.DoesNotExist:
                messages.error(request, f"Radio met dit TEI {tie_value} nummer niet gevonden")

        if radio:
            return redirect("radio:detail", pk=radio.pk)

        return render(request, self.template_name)



class RadioDetailView(DetailView):
    model = Radio
    template_name = 'radio/detail.html'
    context_object_name = 'radio'
