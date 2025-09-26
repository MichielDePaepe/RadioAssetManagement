from django.urls import path
from .views import *

app_name = 'astrid'

urlpatterns = [
    path('request/vtei', VTEIRequestCreateView.as_view(), name='vtei_request'),
    path('request/activation', ActivationRequestCreateView.as_view(), name='activation_request'),

    path('request/<int:pk>', RequestDetailView.as_view(), name='request_detail'),

    path('requests', RequestOverviewView.as_view(), name='request_overview'),

    path('subscritpions/upload', UploadSubscriptionsView.as_view(), name='upload_subscriptions'),

]