from django.urls import path
from .views import *

app_name = 'taqto'

urlpatterns = [
    path('contacts/', ContactsDownloadView.as_view(), name='contacts_download'),
]
