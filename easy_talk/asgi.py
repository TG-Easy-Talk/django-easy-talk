"""
ASGI config for easy_talk project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from chat.routing import websocket_urlpatterns

# 1) Define a variável antes de qualquer uso
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "easy_talk.settings")
django_asgi_app = get_asgi_application()

# 2) Importe seu roteamento de WebSocket
import chat.routing

# 3) Combine HTTP e WebSocket
application = ProtocolTypeRouter({
    "http": django_asgi_app,  # aplica Django padrão
    "websocket": AuthMiddlewareStack(
        URLRouter(
            chat.routing.websocket_urlpatterns
        )
    ),
})