from django.db import IntegrityError
from rest_framework import serializers

from .models import Dictionary
from .utils import clean_and_validate_word, get_difficulty_level


class DictionarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Dictionary
        fields = ["id", "word", "word_length", "difficulty", "is_active"]
        read_only_fields = ["id", "word_length", "difficulty"]


class WordCreateSerializer(serializers.Serializer):
    word = serializers.CharField(max_length=12)

    def validate_word(self, value: str) -> str:
        cleaned = clean_and_validate_word(value)
        if cleaned is None:
            raise serializers.ValidationError("Word must be 4–12 alphabetic characters.")
        return cleaned

    def create(self, validated_data):
        word = validated_data["word"]
        word_length = len(word)
        difficulty = get_difficulty_level(word_length)

        try:
            return Dictionary.objects.create(
                word=word,
                word_length=word_length,
                difficulty=difficulty,
                is_active=True,
            )
        except IntegrityError:
            raise serializers.ValidationError({"word": "Word already exists."})
