from django.urls import path
from .views import *

app_name = 'taqto'

urlpatterns = [
    path('contacts/', ContactsDownloadView.as_view(), name='contacts_download'),
    path('contacts/<str:discipline_filter>/', ContactsDownloadView.as_view(), name='contacts_download_by_discipline'),
]
