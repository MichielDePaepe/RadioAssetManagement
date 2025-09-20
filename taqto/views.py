from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from datetime import datetime


from radio.models import *

class ContactsDownloadView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'taqto.can_download_contacts'

    def get(self, request, *args, **kwargs):
        context = dict()
        context["issi_list"] = ISSI.objects.exclude(alias__isnull=True).exclude(alias__exact='')

        filename = f"contacts_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        content = render_to_string('taqto/contacts.csv', context).replace('\n', '\r\n')

        response = HttpResponse(content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
