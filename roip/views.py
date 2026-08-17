from django.conf import settings
from django.views.generic import TemplateView


class LiveTxView(TemplateView):
    template_name = "roip/live_tx.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recordings_base_url"] = settings.ROIP_RECORDINGS_BASE_URL
        return context
