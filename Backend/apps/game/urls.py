from django.urls import path

from .views import ActiveMatchView, MatchDetailView, MatchHistoryView, MatchRoundsView

urlpatterns = [
    path("match/<int:match_id>/", MatchDetailView.as_view(), name="match-detail"),
    path("match/history/<int:player_id>/", MatchHistoryView.as_view(), name="match-history"),
    path("match/<int:match_id>/rounds/", MatchRoundsView.as_view(), name="match-rounds"),
    path("match/active/<int:player_id>/", ActiveMatchView.as_view(), name="active-match"),
]
