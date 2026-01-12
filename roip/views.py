# roip/views.py
from django.views.generic import TemplateView


class LiveTxView(TemplateView):
    template_name = "roip/live_tx.html"