from django.contrib import admin
from .models import Match, Round, Guess, PlayerSession


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display  = ('id', 'player1', 'player2', 'score1', 'score2', 'status', 'winner', 'created_at')
    list_filter   = ('status',)
    search_fields = ('player1__username', 'player2__username')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display  = ('id', 'match', 'round_number', 'word', 'tick_number', 'status', 'winner', 'is_draw')
    list_filter   = ('status', 'is_draw')
    search_fields = ('match__id',)
    readonly_fields = ('created_at', 'ended_at')


@admin.register(Guess)
class GuessAdmin(admin.ModelAdmin):
    list_display  = ('id', 'player', 'round', 'tick_number', 'guess_text', 'is_correct', 'received_at')
    list_filter   = ('is_correct',)
    search_fields = ('player__username', 'guess_text')
    readonly_fields = ('received_at',)


@admin.register(PlayerSession)
class PlayerSessionAdmin(admin.ModelAdmin):
    list_display  = ('id', 'player', 'match', 'is_active', 'connected_at', 'disconnected_at')
    list_filter   = ('is_active',)
    search_fields = ('player__username', 'session_token')
    readonly_fields = ('connected_at',)