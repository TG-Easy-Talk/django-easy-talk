from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Todas as conexões que chegarem em /ws/ serão direcionadas para ChatConsumer
    re_path(r"", consumers.ChatConsumer.as_asgi()),
]