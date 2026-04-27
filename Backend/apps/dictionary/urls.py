from django.urls import path
from .views import (
    WordListView,
    WordCreateView,
    WordToggleView,
    DictionaryStatsView,
)

urlpatterns = [
    path('words/',                    WordListView.as_view(),    name='word-list'),
    path('words/add/',                WordCreateView.as_view(),  name='word-add'),
    path('words/<int:word_id>/toggle/', WordToggleView.as_view(), name='word-toggle'),
    path('stats/',                    DictionaryStatsView.as_view(), name='dictionary-stats'),
]