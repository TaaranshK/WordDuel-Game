import secrets
from django.utils import timezone
from .models import Player


def join_or_create_player(username: str) -> tuple[Player, str]:
    """
    Get existing player by username or create a new one.
    Always generates a fresh session token on join.
    Returns (player, session_token).
    """
    player, created = Player.objects.get_or_create(
        username=username,
    )

    # update last seen on every join
    player.last_seen_at = timezone.now()
    player.save(update_fields=['last_seen_at'])

    # generate a secure session token
    session_token = secrets.token_hex(32)

    return player, session_token


def get_player_by_id(player_id: int) -> Player | None:
    """Fetch player by PK. Returns None if not found."""
    try:
        return Player.objects.get(id=player_id)
    except Player.DoesNotExist:
        return None


def create_or_get_ai_player() -> Player:
    """Create or return the built-in AI opponent."""
    ai_player, created = Player.objects.get_or_create(
        username='AI_Opponent',
        defaults={'is_computer': True}
    )
    return ai_player


def update_player_stats(player: Player, won: bool) -> None:
    """
    Increment total_matches always.
    Increment total_wins only if player won.
    Uses update_fields for efficiency.
    """
    player.total_matches += 1
    if won:
        player.total_wins += 1
        player.save(update_fields=['total_matches', 'total_wins'])
    else:
        player.save(update_fields=['total_matches'])