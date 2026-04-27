from django.urls import path
from game.consumers.lobby import LobbyConsumer
from game.consumers.game import GameConsumer

websocket_urlpatterns = [
    path('ws/lobby/',              LobbyConsumer.as_asgi()),
    path('ws/game/<int:match_id>/', GameConsumer.as_asgi()),
]