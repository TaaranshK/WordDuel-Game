import random
from .models import Dictionary


def get_random_word(exclude_words: list[str] = []) -> dict | None:
    """
    Fetch a random active word from the dictionary.
    Excludes already-used words in the current match.
    Returns { 'word': str, 'word_length': int } or None.
    """
    queryset = Dictionary.objects.filter(is_active=True)

    if exclude_words:
        queryset = queryset.exclude(word__in=exclude_words)

    words = list(queryset.values_list('word', 'word_length'))

    if not words:
        return None

    word, word_length = random.choice(words)
    return {'word': word, 'word_length': word_length}


def get_random_word_by_difficulty(
    difficulty: str,
    exclude_words: list[str] = []
) -> dict | None:
    """
    Fetch a random word filtered by difficulty.
    Falls back to any difficulty if none found.
    """
    queryset = Dictionary.objects.filter(
        is_active=True,
        difficulty=difficulty
    )

    if exclude_words:
        queryset = queryset.exclude(word__in=exclude_words)

    words = list(queryset.values_list('word', 'word_length'))

    if not words:
        # fallback — try any difficulty
        return get_random_word(exclude_words=exclude_words)

    word, word_length = random.choice(words)
    return {'word': word, 'word_length': word_length}


def get_word_count() -> int:
    """Total number of active words in dictionary."""
    return Dictionary.objects.filter(is_active=True).count()


def word_exists(word: str) -> bool:
    """Check if a word exists in the dictionary (active or not)."""
    return Dictionary.objects.filter(word=word.upper().strip()).exists()


def activate_word(word_id: int) -> bool:
    """Activate a word by ID. Returns True if successful."""
    updated = Dictionary.objects.filter(id=word_id).update(is_active=True)
    return updated > 0


def deactivate_word(word_id: int) -> bool:
    """Deactivate a word by ID. Returns True if successful."""
    updated = Dictionary.objects.filter(id=word_id).update(is_active=False)
    return updated > 0