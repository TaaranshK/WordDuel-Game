from rest_framework import serializers
from .models import Dictionary


class DictionarySerializer(serializers.ModelSerializer):
    """Full word details — admin use only."""
    class Meta:
        model  = Dictionary
        fields = ('id', 'word', 'word_length', 'difficulty', 'is_active')
        read_only_fields = ('word_length',)  # auto-set in model's save()


class WordCreateSerializer(serializers.ModelSerializer):
    """Used for POST — adding a new word via admin API."""
    class Meta:
        model  = Dictionary
        fields = ('word', 'difficulty')

    def validate_word(self, value):
        value = value.upper().strip()
        if not value.isalpha():
            raise serializers.ValidationError("Word must contain letters only.")
        if len(value) < 4 or len(value) > 12:
            raise serializers.ValidationError("Word must be between 4 and 12 characters.")
        return value


class RandomWordSerializer(serializers.ModelSerializer):
    """Internal use only — passed to game engine, never sent to client."""
    class Meta:
        model  = Dictionary
        fields = ('word', 'word_length')