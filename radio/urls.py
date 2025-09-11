from django.urls import path
from .views import *

app_name = 'radio'

urlpatterns = [
    path('find/', FindRadioView.as_view(), name='find'),
    path('<int:pk>/', RadioDetailView.as_view(), name='detail'),
    path('create/', RadioCreateView.as_view(), name='create'),
    path('<int:tei>/card/', RadioCardView.as_view(), name='card'),
    path('example/card/', RadioCardExampleView.as_view(), name='example_card'),
    path('scan/', ScanQRCodeView.as_view(), name='scan'),
    path('subscritpions/upload', UploadSubscriptionsView.as_view(), name='upload_subscriptions'),

    path('radio-lookup/', RadioLookupView.as_view(), name='radio_lookup'),


]
