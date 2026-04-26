from rest_framework import serializers

from apps.accounts.models import Player

from .models import Match, Round


class PlayerBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ["id", "username"]


class RoundSerializer(serializers.ModelSerializer):
    winner = PlayerBriefSerializer(read_only=True)

    class Meta:
        model = Round
        fields = [
            "id",
            "match",
            "round_number",
            "word",
            "word_length",
            "revealed_tiles",
            "revealed_letters",
            "tick_number",
            "winner",
            "is_draw",
            "status",
            "created_at",
            "ended_at",
        ]
        read_only_fields = fields


class MatchSerializer(serializers.ModelSerializer):
    player1 = PlayerBriefSerializer(read_only=True)
    player2 = PlayerBriefSerializer(read_only=True)
    winner = PlayerBriefSerializer(read_only=True)

    class Meta:
        model = Match
        fields = [
            "id",
            "player1",
            "player2",
            "score1",
            "score2",
            "status",
            "winner",
            "max_rounds",
            "tick_duration_ms",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class MatchHistorySerializer(MatchSerializer):
    pass
