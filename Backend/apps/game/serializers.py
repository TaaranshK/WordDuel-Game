from rest_framework import serializers
from .models import Match, Round, Guess, PlayerSession
from accounts.serializers import PlayerSerializer


class MatchSerializer(serializers.ModelSerializer):
    """Full match details — used in match history & leaderboard responses."""
    player1 = PlayerSerializer(read_only=True)
    player2 = PlayerSerializer(read_only=True)
    winner  = PlayerSerializer(read_only=True)

    class Meta:
        model  = Match
        fields = (
            'id', 'player1', 'player2',
            'score1', 'score2',
            'status', 'winner',
            'max_rounds', 'tick_duration_ms',
            'created_at', 'updated_at'
        )
        read_only_fields = fields


class RoundSerializer(serializers.ModelSerializer):
    """Round details — never exposes the word to clients."""
    winner = PlayerSerializer(read_only=True)

    class Meta:
        model  = Round
        fields = (
            'id', 'match', 'round_number',
            'word_length',
            'revealed_tiles', 'revealed_letters',
            'tick_number', 'status',
            'winner', 'is_draw',
            'created_at', 'ended_at'
        )
        read_only_fields = fields
        # 'word' intentionally excluded — never sent to client


class GuessSerializer(serializers.ModelSerializer):
    """Used for audit/history — not used in real-time WS flow."""
    player = PlayerSerializer(read_only=True)

    class Meta:
        model  = Guess
        fields = (
            'id', 'round', 'player',
            'tick_number', 'guess_text',
            'is_correct', 'received_at'
        )
        read_only_fields = fields
        # 'client_sent_at' excluded — internal analytics only


class PlayerSessionSerializer(serializers.ModelSerializer):
    """Used internally for reconnection validation."""
    class Meta:
        model  = PlayerSession
        fields = (
            'id', 'player', 'session_token',
            'match', 'is_active',
            'connected_at', 'disconnected_at'
        )
        read_only_fields = fields


class MatchHistorySerializer(serializers.ModelSerializer):
    """Lightweight match summary — used in player profile / history list."""
    player1     = PlayerSerializer(read_only=True)
    player2     = PlayerSerializer(read_only=True)
    winner      = PlayerSerializer(read_only=True)
    total_rounds = serializers.SerializerMethodField()

    class Meta:
        model  = Match
        fields = (
            'id', 'player1', 'player2',
            'score1', 'score2',
            'status', 'winner',
            'total_rounds', 'created_at'
        )
        read_only_fields = fields

    def get_total_rounds(self, obj):
        return obj.rounds.count()