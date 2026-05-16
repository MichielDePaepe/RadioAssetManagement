from django.urls import path
from .views import *

app_name = 'taqto'

urlpatterns = [
    path('phonebook/serial/', PhonebookSerialView.as_view(), name='phonebook_serial'),
    path('contacts/', ContactsDownloadView.as_view(), name='contacts_download'),
    path('contacts/<str:discipline_filter>/', ContactsDownloadView.as_view(), name='contacts_download_by_discipline'),
]
