from __future__ import annotations

import random
from typing import TypedDict

from .models import Dictionary
from .utils import normalize_word


class RandomWord(TypedDict):
    word: str
    word_length: int


def get_random_word(exclude_words: list[str] | None = None) -> RandomWord | None:
    """
    Fetch a random active word from the dictionary.
    Excludes already-used words in the current match if provided.
    Returns None if no words available.
    """
    queryset = Dictionary.objects.filter(is_active=True)

    exclude_words_cleaned = [normalize_word(word) for word in (exclude_words or [])]
    exclude_words_cleaned = [word for word in exclude_words_cleaned if word]

    if exclude_words_cleaned:
        queryset = queryset.exclude(word__in=exclude_words_cleaned)

    words = list(queryset.values_list('word', 'word_length'))

    if not words:
        return None

    word, word_length = random.choice(words)
    return {"word": word, "word_length": word_length}


def get_word_count() -> int:
    """Returns total number of active words in dictionary."""
    return Dictionary.objects.filter(is_active=True).count()
