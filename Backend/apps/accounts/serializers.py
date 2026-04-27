from rest_framework import serializers
from .models import Player


class PlayerJoinSerializer(serializers.Serializer):
    """Used for POST /api/accounts/join — takes username, returns player + session token."""
    username = serializers.CharField(max_length=50, trim_whitespace=True)

    def validate_username(self, value):
        if not value.isalnum():
            raise serializers.ValidationError("Username must be alphanumeric only.")
        return value.lower()


class PlayerSerializer(serializers.ModelSerializer):
    """Read-only — used in responses after join and in leaderboard."""
    class Meta:
        model  = Player
        fields = ('id', 'username', 'total_wins', 'total_matches', 'created_at')
        read_only_fields = fields


class PlayerJoinResponseSerializer(serializers.Serializer):
    """Shape of the response after a successful join."""
    player        = PlayerSerializer()
    session_token = serializers.CharField()