# RadioAssetManagement/asgi.py

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

import roip.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "RadioAssetManagement.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(roip.routing.websocket_urlpatterns)
    ),
})