from django.urls import re_path
from .consumers.wordduel import WordDuelConsumer

websocket_urlpatterns = [
    re_path(r"ws/wordduel/$", WordDuelConsumer.as_asgi()),
]
