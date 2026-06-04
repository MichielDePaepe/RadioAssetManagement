from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.timezone import now
from django.utils.translation import gettext as _
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
            "translations": {
                "suggestion_pending": _("Voorstel wordt bepaald na uitlezen van ISSI."),
                "manual_choice": _("Handmatig gekozen."),
                "insecure_serial": _("Deze interne site draait via HTTP. Browsers laten Web Serial alleen toe via HTTPS of localhost."),
                "unsupported_serial": _("Deze browser ondersteunt Web Serial niet. Gebruik Chrome of Edge op desktop; Safari, Firefox en iOS ondersteunen dit niet."),
                "not_connected": _("Niet verbonden"),
                "serial_available": _("Web Serial beschikbaar"),
                "copy_failed": _("Kopiëren mislukt: {error}"),
                "done": _("Klaar"),
                "eta_empty": _("ETA -"),
                "remaining": _("{duration} resterend"),
                "read_loop_stopped": _("Leeslus gestopt: {error}"),
                "no_serial_connection": _("Geen seriële verbinding"),
                "command_error": _("{command} gaf ERROR"),
                "command_timeout": _("{command} timeout"),
                "radio_absent": _("Geen antwoord meer op AT; radio afwezig"),
                "port_open": _("Poort open"),
                "waiting_radio": _("Wachten op radio..."),
                "radio_detected": _("Radio gedetecteerd"),
                "reading_status": _("Radio gedetecteerd, status uitlezen..."),
                "command_unusable": _("{command} niet bruikbaar: {error}"),
                "connecting": _("Verbinden..."),
                "choose_port": _("Kies een seriële poort in de browser..."),
                "opening_port": _("Seriële poort openen..."),
                "port_waiting_radio": _("Seriële poort open, wachten op radio..."),
                "port_open_log": _("Seriële poort open op 9600 8N1 RTS/CTS"),
                "no_port_selected": _("Geen seriële poort gekozen. Klik opnieuw op verbinden en selecteer de radio."),
                "connect_failed": _("Verbinden mislukt: {error}"),
                "not_found_database": _("Niet gevonden in database"),
                "medical_phonebook": _("geel medisch"),
                "fire_phonebook": _("rood brandweer"),
                "suggestion_for_issi": _("Voorstel op basis van ISSI: {label}."),
                "no_contacts": _("Geen contacten om te schrijven"),
                "phonebook_capacity_error": _("Phonebook heeft {slots} plaatsen, maar {contacts} contacten moeten geschreven worden"),
                "start_writing_log": _("Start schrijven {label} phonebook ({contacts} contacten)"),
                "start_writing_status": _("Start schrijven {label} phonebook"),
                "write_contact": _("Schrijf {index}/{total}"),
                "delete_old_entry": _("Wis oude entry {index}"),
                "phonebook_updated": _("{label} phonebook bijgewerkt"),
                "update_stopped": _("Update gestopt"),
                "status_read_failed": _("Status lezen mislukt: {error}"),
                "phonebook_write_failed": _("Phonebook schrijven mislukt: {error}"),
            },
        }
        return context
