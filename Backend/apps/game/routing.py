from django.urls import path
from apps.game.consumers.lobby import LobbyConsumer
from apps.game.consumers.game import GameConsumer
from apps.game.consumers.wordduel import WordDuelConsumer

websocket_urlpatterns = [
    path('ws/lobby/',              LobbyConsumer.as_asgi()),
    path('ws/game/<int:match_id>/', GameConsumer.as_asgi()),
    path('ws/wordduel/',           WordDuelConsumer.as_asgi()),
]