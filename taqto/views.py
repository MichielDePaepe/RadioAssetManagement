from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views import View

from radio.models import *

class ContactsDownloadView(View):
    def get(self, request, *args, **kwargs):

        context = dict()
        context["issi_list"] = ISSI.objects.exclude(alias__isnull=True).exclude(alias__exact='')

        content = render_to_string('taqto/contacts.csv', context).replace('\n', '\r\n')

        response = HttpResponse(content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="contacts.csv"'
        
        return response
