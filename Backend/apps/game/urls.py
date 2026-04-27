from django.urls import path
from .views import (
    MatchDetailView,
    MatchHistoryView,
    MatchRoundsView,
    ActiveMatchView,
)

urlpatterns = [
    path('match/<int:match_id>/',              MatchDetailView.as_view(),  name='match-detail'),
    path('match/<int:match_id>/rounds/',       MatchRoundsView.as_view(),  name='match-rounds'),
    path('match/history/<int:player_id>/',     MatchHistoryView.as_view(), name='match-history'),
    path('match/active/<int:player_id>/',      ActiveMatchView.as_view(),  name='match-active'),
]