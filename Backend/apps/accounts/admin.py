from django.contrib import admin
from .models import Player


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display  = ('id', 'username', 'total_wins', 'total_matches', 'last_seen_at', 'created_at')
    search_fields = ('username',)
    ordering      = ('-total_wins',)
    readonly_fields = ('created_at', 'last_seen_at')