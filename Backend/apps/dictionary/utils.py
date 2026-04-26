"""
Utility functions for dictionary app.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


MIN_WORD_LENGTH = 4
MAX_WORD_LENGTH = 12


def normalize_word(word: str | None) -> str:
    """Trim and normalise a raw word to uppercase."""
    if word is None:
        return ""
    return word.strip().upper()


def clean_and_validate_word(
    word: str | None,
    *,
    min_length: int = MIN_WORD_LENGTH,
    max_length: int = MAX_WORD_LENGTH,
) -> str | None:
    """
    Normalise and validate a candidate word.

    Returns the cleaned word (uppercase) if valid, otherwise None.
    """
    cleaned = normalize_word(word)

    if not cleaned:
        return None

    if not cleaned.isalpha():
        return None

    if not (min_length <= len(cleaned) <= max_length):
        return None

    return cleaned


def validate_word(
    word: str | None,
    *,
    min_length: int = MIN_WORD_LENGTH,
    max_length: int = MAX_WORD_LENGTH,
) -> bool:
    """Return True if the word is suitable for the game/dictionary."""
    return clean_and_validate_word(word, min_length=min_length, max_length=max_length) is not None


def get_difficulty_level(word_length: int) -> str:
    """Determine difficulty based on word length."""
    if word_length <= 4:
        return "easy"
    if word_length <= 7:
        return "medium"
    return "hard"


def parse_words_from_lines(
    lines: Iterable[str],
    *,
    min_length: int = MIN_WORD_LENGTH,
    max_length: int = MAX_WORD_LENGTH,
    dedupe: bool = True,
) -> tuple[list[str], list[str]]:
    """
    Parse words from an iterable of raw lines.

    Returns: (valid_words, skipped_words)
    - valid_words are cleaned (uppercase) and optionally deduped.
    - skipped_words are cleaned (uppercase) words that failed validation.
    """
    valid_words: list[str] = []
    skipped_words: list[str] = []
    seen: set[str] = set()

    for line in lines:
        cleaned = normalize_word(line)

        if not cleaned:
            continue

        cleaned_valid = clean_and_validate_word(
            cleaned,
            min_length=min_length,
            max_length=max_length,
        )
        if cleaned_valid is None:
            skipped_words.append(cleaned)
            continue

        if dedupe and cleaned_valid in seen:
            continue

        seen.add(cleaned_valid)
        valid_words.append(cleaned_valid)

    return valid_words, skipped_words


def read_words_from_file(
    file_path: str | Path,
    *,
    encoding: str = "utf-8",
    min_length: int = MIN_WORD_LENGTH,
    max_length: int = MAX_WORD_LENGTH,
    dedupe: bool = True,
) -> tuple[list[str], list[str]]:
    """Read a newline-delimited word file and return (valid_words, skipped_words)."""
    path = Path(file_path)
    with path.open("r", encoding=encoding) as f:
        return parse_words_from_lines(
            f,
            min_length=min_length,
            max_length=max_length,
            dedupe=dedupe,
        )
