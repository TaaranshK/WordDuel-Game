from rest_framework import serializers

from .models import Player


class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = [
            "id",
            "username",
            "total_wins",
            "total_matches",
            "last_seen_at",
            "created_at",
        ]
        read_only_fields = fields


class PlayerJoinSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50)

    def validate_username(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Username is required.")
        return cleaned


class PlayerJoinResponseSerializer(serializers.Serializer):
    player = PlayerSerializer()
    session_token = serializers.CharField()
