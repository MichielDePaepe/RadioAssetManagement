from django.urls import path
from .views import *

app_name = 'astrid'

urlpatterns = [
    path('request/vtei', VTEIRequestCreateView.as_view(), name='vtei_request'),
    path('requests', RequestsOverviewView.as_view(), name='requests_overview'),

]