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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "easy_talk.settings")

# ASGI app padrão do Django para requisições HTTP
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    # Roteamento das requisições HTTP
    "http": django_asgi_app,
    # Roteamento das conexões WebSocket com suporte a sessions/auth
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})