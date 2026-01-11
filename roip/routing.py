from django.urls import path
from .consumers import LiveTxConsumer

websocket_urlpatterns = [
    path("ws/live/tx/", LiveTxConsumer.as_asgi()),
]