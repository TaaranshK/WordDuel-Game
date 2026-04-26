from django.urls import path

from .views import DictionaryStatsView, WordCreateView, WordListView, WordToggleView

urlpatterns = [
    path("words/", WordListView.as_view(), name="dictionary-words"),
    path("words/add/", WordCreateView.as_view(), name="dictionary-word-add"),
    path("words/<int:word_id>/toggle/", WordToggleView.as_view(), name="dictionary-word-toggle"),
    path("stats/", DictionaryStatsView.as_view(), name="dictionary-stats"),
]
