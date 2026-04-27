import secrets
import string
from django.utils import timezone


def generate_session_token(length: int = 64) -> str:
    """
    Generate a cryptographically secure session token.
    Uses secrets module — safe for session identity.
    Returns a hex string of given length.
    """
    return secrets.token_hex(length // 2)


def sanitize_username(username: str) -> str:
    """
    Clean and normalize a raw username input.
    - Strip whitespace
    - Lowercase
    - Remove non-alphanumeric characters
    """
    return ''.join(
        char for char in username.strip().lower()
        if char in string.ascii_lowercase + string.digits
    )


def is_valid_username(username: str) -> tuple[bool, str]:
    """
    Validate a username against game rules.
    Returns (is_valid, error_message).

    Rules:
    - Must not be empty
    - Must be alphanumeric only
    - Must be between 3 and 50 characters
    """
    if not username:
        return False, 'Username cannot be empty.'

    if not username.isalnum():
        return False, 'Username must be alphanumeric only.'

    if len(username) < 3:
        return False, 'Username must be at least 3 characters.'

    if len(username) > 50:
        return False, 'Username cannot exceed 50 characters.'

    return True, ''


def format_player_stats(player) -> dict:
    """
    Returns a clean stats summary dict for a player.
    Used in leaderboard and profile responses.
    """
    win_rate = (
        round((player.total_wins / player.total_matches) * 100, 1)
        if player.total_matches > 0 else 0.0
    )

    return {
        'player_id':     player.id,
        'username':      player.username,
        'total_wins':    player.total_wins,
        'total_matches': player.total_matches,
        'win_rate':      f"{win_rate}%",
        'member_since':  player.created_at.strftime('%Y-%m-%d'),
        'last_seen':     (
            player.last_seen_at.strftime('%Y-%m-%d %H:%M:%S')
            if player.last_seen_at else 'Never'
        ),
    }