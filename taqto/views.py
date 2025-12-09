from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.timezone import now
from django.views import View
from django.db.models import Q

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

from radio.models import ISSI, Discipline


class ContactsDownloadView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'taqto.can_download_contacts'

    def get(self, request, *args, **kwargs):
        discipline_filter = kwargs.get("discipline_filter", "").lower()

        issi_qs = ISSI.objects.exclude(alias__isnull=True).exclude(alias__exact='')

        if discipline_filter in ("fire", "medical"):
            discipline_type_map = {
                "fire": Discipline.DisciplineType.FIRE,
                "medical": Discipline.DisciplineType.MEDICAL,
            }
            selected_type = discipline_type_map[discipline_filter]

            issi_qs = issi_qs.filter(
                Q(discipline__discipline_type=selected_type) |
                Q(discipline__discipline_type=Discipline.DisciplineType.OTHER)
            )

            filename_suffix = discipline_filter
        else:
            # Geen filter: alles (of eventueel hier nog POLICE uitsluiten als je dat wilt)
            filename_suffix = "all"

        context = {
            "issi_list": issi_qs,
        }

        filename = f"contacts_{filename_suffix}_{now().strftime('%Y%m%d_%H%M')}.csv"
        content = render_to_string('taqto/contacts.csv', context).replace('\n', '\r\n')

        response = HttpResponse(content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response
