from django.contrib import admin
from .models import Match, Round, Guess, PlayerSession

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'player1', 'player2', 'winner', 'status', 'created_at')
    search_fields = ('player1__username', 'player2__username')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ("id", "match", "round_number", "word", "status", "is_draw", "winner", "created_at", "ended_at")
    readonly_fields = ("created_at", "ended_at")

@admin.register(Guess)
class GuessAdmin(admin.ModelAdmin):
    list_display = ("id", "round", "player", "tick_number", "guess_text", "is_correct", "received_at")
    readonly_fields = ("received_at",)

@admin.register(PlayerSession)
class PlayerSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "player", "match", "session_token", "is_active", "connected_at", "disconnected_at")
    search_fields = ("player__username", "session_token")
    readonly_fields = ("connected_at", "disconnected_at")
