from django.urls import path

from .views import LeaderboardView, PlayerJoinView, PlayerProfileView

urlpatterns = [
    path("join/", PlayerJoinView.as_view(), name="player-join"),
    path("player/<int:player_id>/", PlayerProfileView.as_view(), name="player-profile"),
    path("leaderboard/", LeaderboardView.as_view(), name="leaderboard"),
]
