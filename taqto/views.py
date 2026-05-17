from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.timezone import now
from django.views import View
from django.views.generic import TemplateView

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

from .services import (
    get_phonebook_contacts,
    get_phonebook_issi_queryset,
    get_issi_radio_lookup,
    get_radio_detail_lookup,
)


class ContactsDownloadView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'taqto.can_download_contacts'

    def get(self, request, *args, **kwargs):
        discipline_filter = kwargs.get("discipline_filter", "").lower()
        issi_qs = get_phonebook_issi_queryset(discipline_filter)
        filename_suffix = discipline_filter if discipline_filter in ("fire", "medical") else "all"

        context = {
            "issi_list": issi_qs,
        }

        filename = f"contacts_{filename_suffix}_{now().strftime('%Y%m%d_%H%M')}.csv"
        content = render_to_string('taqto/contacts.csv', context).replace('\n', '\r\n')

        response = HttpResponse(content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response


class PhonebookSerialView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = 'taqto.can_download_contacts'
    template_name = "taqto/phonebook_serial.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["phonebook_payload"] = {
            "contacts": {
                "fire": get_phonebook_contacts("fire"),
                "medical": get_phonebook_contacts("medical"),
            },
            "issi_lookup": get_issi_radio_lookup(),
            "radio_detail_lookup": get_radio_detail_lookup(),
        }
        return context
