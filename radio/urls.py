from django.urls import path
from django.views.generic import TemplateView
from .views import *


app_name = 'radio'

urlpatterns = [
    path('find/', FindRadioView.as_view(), name='find'),
    path('<int:pk>/', RadioDetailView.as_view(), name='detail'),
    path('create/', RadioCreateView.as_view(), name='create'),
    path('<int:tei>/card/', RadioCardView.as_view(), name='card'),
    path('example/card/', RadioCardExampleView.as_view(), name='example_card'),
    path('scan/', ScanQRCodeView.as_view(), name='scan'),

    path('lookup/', LookupView.as_view(), name='lookup'),
    path('selector/test', TemplateView.as_view(template_name="radio/selector/test.html"), name='selector_test'),
    path('selector/result/<int:pk>/', SelectorResultView.as_view(), name='selector_result'),

    path('image/<int:pk>_<str:type>.png/', QRImageView.as_view(), name='label_image'),

    
]
