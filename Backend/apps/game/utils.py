from django.utils import timezone



# WebSocket Event Builders

def build_match_found_event(match, opponent_username: str, player_id: int) -> dict:
    """Payload sent to both players when a match is created."""
    return {
        'type':              'matchFound',
        'match_id':          match.id,
        'opponent_username': opponent_username,
        'your_player_id':    player_id,
        'tick_duration_ms':  match.tick_duration_ms,
        'max_rounds':        match.max_rounds,
    }


def build_start_round_event(game_round, scores: dict) -> dict:
    """Payload sent to both players at the start of each round."""
    return {
        'type':         'startRound',
        'round_id':     game_round.id,
        'round_number': game_round.round_number,
        'word_length':  game_round.word_length,
        'scores':       scores,
    }


def build_tick_start_event(tick_number: int, deadline: float, revealed_state: dict) -> dict:
    """Payload sent at the start of each tick."""
    return {
        'type':           'tickStart',
        'tick_number':    tick_number,
        'deadline':       deadline,         # Unix ms timestamp
        'revealed_state': revealed_state,   # { tiles: [...], letters: [...] }
    }


def build_reveal_tile_event(index: int, letter: str, revealed_state: dict) -> dict:
    """Payload sent when a tile is revealed after tick timeout."""
    return {
        'type':           'revealTile',
        'index':          index,
        'letter':         letter,
        'revealed_state': revealed_state,
    }


def build_round_end_event(
    winner_id: int | None,
    is_draw: bool,
    revealed_word: str,
    scores: dict,
    reason: str = None,
) -> dict:
    """Payload sent when a round concludes."""
    return {
        'type':          'roundEnd',
        'winner_id':     winner_id,
        'is_draw':       is_draw,
        'revealed_word': revealed_word,
        'scores':        scores,
        'reason':        reason,            # OPPONENT_DISCONNECTED | None
    }


def build_match_end_event(
    winner_id: int | None,
    is_draw: bool,
    final_scores: dict,
    total_rounds: int,
    reason: str = None,
) -> dict:
    """Payload sent when the full match concludes."""
    return {
        'type':         'matchEnd',
        'winner_id':    winner_id,
        'is_draw':      is_draw,
        'final_scores': final_scores,
        'total_rounds': total_rounds,
        'reason':       reason,             # OPPONENT_LEFT | None
    }


def build_error_event(code: str) -> dict:
    """Standardised error payload for all WS error responses."""
    messages = {
        'ALREADY_GUESSED':       'You have already guessed this tick.',
        'LATE_SUBMISSION':       'Guess submitted after tick expired.',
        'INVALID_ROUND':         'Round ID does not match current round.',
        'INVALID_GUESS':         'Guess must contain letters only.',
        'INVALID_PAYLOAD':       'Missing required fields in payload.',
        'INVALID_SESSION':       'Invalid or expired session token.',
        'MISSING_SESSION_TOKEN': 'session_token is required.',
        'MATCH_IN_PROGRESS':     'You already have an active match.',
        'UNKNOWN_EVENT':         'Unrecognised event type.',
    }

    return {
        'type':    'error',
        'code':    code,
        'message': messages.get(code, 'An unexpected error occurred.'),
    }



# Tick Helpers

def calculate_deadline(tick_duration_ms: int) -> float:
    """
    Returns Unix timestamp in milliseconds for when the current tick expires.
    Sent to clients so they can display accurate countdown.
    """
    return (timezone.now().timestamp() * 1000) + tick_duration_ms


def get_hidden_indices(revealed_tiles: list[bool]) -> list[int]:
    """Returns list of indices that have not yet been revealed."""
    return [i for i, revealed in enumerate(revealed_tiles) if not revealed]


def get_revealed_state(game_round) -> dict:
    """Returns safe revealed state dict for client consumption."""
    return {
        'tiles':   game_round.revealed_tiles,
        'letters': game_round.revealed_letters,
    }



# Score Helpers

def build_scores_dict(match) -> dict:
    """Consistent scores payload used across all events."""
    return {
        'player1_id': match.player1_id,
        'player1':    match.player1.username,
        'score1':     match.score1,
        'player2_id': match.player2_id,
        'player2':    match.player2.username,
        'score2':     match.score2,
    }


def determine_match_winner(match) -> tuple[object | None, bool]:
    """
    Determine match winner from current scores.
    Returns (winner_player | None, is_draw).
    """
    if match.score1 > match.score2:
        return match.player1, False
    elif match.score2 > match.score1:
        return match.player2, False
    else:
        return None, True