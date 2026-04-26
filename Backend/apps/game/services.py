import asyncio
import random
from datetime import timedelta
from django.utils import timezone
from django.db import DatabaseError

from apps.accounts.models import Player
from apps.dictionary.services import get_random_word
from .models import Match, Round, Guess, PlayerSession


# In Memory Jo chize Rahengi
# { match_id: { 'player1_id': int, 'player2_id': int, 'guessed': set() } }
_active_matches: dict = {}

# Matchmaking queue: [ { 'player_id': int, 'session_token': str, 'channel_name': str } ]
_lobby_queue: list = []


# basically The Sessiom 
def create_session(player: Player, session_token: str, match=None) -> PlayerSession:
    """Create a new active session for a player."""
    # deactivate any existing active sessions
    PlayerSession.objects.filter(player=player, is_active=True).update(is_active=False)

    return PlayerSession.objects.create(
        player=player,
        session_token=session_token,
        match=match,
        is_active=True,
    )

# Get the Token of the Session 
def get_session_by_token(session_token: str) -> PlayerSession | None:
    """Fetch active session by token — used for reconnection."""
    try:
        return PlayerSession.objects.select_related('player', 'match').get(
            session_token=session_token,
            is_active=True,
        )
    except PlayerSession.DoesNotExist:
        return None


def close_session(session_token: str) -> None:
    """Mark session as inactive on disconnect."""
    PlayerSession.objects.filter(session_token=session_token).update(
        is_active=False,
        disconnected_at=timezone.now(),
    )


# matchmaking Service 
def add_to_lobby(player_id: int, session_token: str, channel_name: str) -> None:
    """Add player to the matchmaking queue."""
    # prevent duplicate entries
    _lobby_queue[:] = [p for p in _lobby_queue if p['player_id'] != player_id]
    _lobby_queue.append({
        'player_id':    player_id,
        'session_token': session_token,
        'channel_name': channel_name,
    })


def remove_from_lobby(player_id: int) -> None:
    """Remove player from queue on disconnect."""
    _lobby_queue[:] = [p for p in _lobby_queue if p['player_id'] != player_id]


def try_match_players() -> tuple | None:
    """
    If 2+ players in queue, pop first two and create a match.
    If only 1 player in queue for 10+ seconds, pair with AI.
    Returns (match, p1_info, p2_info) or None.
    """
    # Pair two human players if available
    if len(_lobby_queue) >= 2:
        p1_info = _lobby_queue.pop(0)
        p2_info = _lobby_queue.pop(0)

        player1 = Player.objects.get(id=p1_info['player_id'])
        player2 = Player.objects.get(id=p2_info['player_id'])

        match = Match.objects.create(
            player1=player1,
            player2=player2,
        )
        # initialise in-memory match state
        _active_matches[match.id] = {
            'player1_id': player1.id,
            'player2_id': player2.id,
            'guessed':    set(),
            'correct':    set(),
            'tick_task':  None,
            'used_words': [],
            'round_end_event': None,
            'ai_player_id': None,
        }

        return match, p1_info, p2_info

    # Single player? Pair with AI after short delay
    if len(_lobby_queue) == 1:
        from apps.accounts.services import create_or_get_ai_player
        
        p1_info = _lobby_queue.pop(0)
        player1 = Player.objects.get(id=p1_info['player_id'])
        ai_player = create_or_get_ai_player()

        match = Match.objects.create(
            player1=player1,
            player2=ai_player,
        )
        # initialise in-memory match state with AI flag
        _active_matches[match.id] = {
            'player1_id': player1.id,
            'player2_id': ai_player.id,
            'guessed':    set(),
            'correct':    set(),
            'tick_task':  None,
            'used_words': [],
            'round_end_event': None,
            'ai_player_id': ai_player.id,  # Mark as AI match
        }

        # Create dummy info for AI player (no real channel)
        p2_info = {
            'player_id': ai_player.id,
            'session_token': 'ai_token',
            'channel_name': None,  # No WebSocket channel for AI
        }

        return match, p1_info, p2_info

    return None


# Create the Round 
def create_round(match: Match) -> Round:
    """Create a new round with a fresh word."""
    state      = _active_matches.get(match.id, {})
    used_words = state.get('used_words', [])

    word_data = get_random_word(exclude_words=used_words)
    if word_data is None:
        raise ValueError("No active words available in dictionary.")
    word      = word_data['word']
    length    = word_data['word_length']

    round_number = match.rounds.count() + 1

    game_round = Round.objects.create(
        match=match,
        word=word,
        word_length=length,
        revealed_tiles=[False] * length,
        revealed_letters=[''] * length,
        round_number=round_number,
        status=Round.Status.ACTIVE,
    )

    # track used word
    if match.id in _active_matches:
        _active_matches[match.id]['used_words'].append(word)
        _active_matches[match.id]['guessed'] = set()   # reset for new round
        _active_matches[match.id]['correct'] = set()

    return game_round


def end_round(game_round: Round, winner: Player | None, is_draw: bool = False) -> None:
    """Mark round as completed and update match score."""
    game_round.status   = Round.Status.COMPLETED
    game_round.ended_at = timezone.now()
    game_round.is_draw  = is_draw

    if winner and not is_draw:
        game_round.winner = winner

    try:
        game_round.save(update_fields=['status', 'ended_at', 'is_draw', 'winner'])
    except DatabaseError:
        pass  # in-memory state already updated; retry handled in score_service

    # update match scores
    update_match_score(game_round.match, winner, is_draw)


def get_round_state(game_round: Round) -> dict:
    """Returns safe client-facing round state — no word exposed."""
    return {
        'round_id':         game_round.id,
        'round_number':     game_round.round_number,
        'word_length':      game_round.word_length,
        'revealed_tiles':   game_round.revealed_tiles,
        'revealed_letters': game_round.revealed_letters,
        'tick_number':      game_round.tick_number,
        'status':           game_round.status,
    }


# Tick Engine 
async def run_tick_loop(match: Match, game_round: Round, channel_layer, room_group) -> None:
    """
    Core async tick loop.
    Each iteration: broadcast tickStart → wait T seconds → evaluate → reveal or end.
    """
    tick_duration = match.tick_duration_ms / 1000  # convert ms to seconds

    while game_round.status == Round.Status.ACTIVE:

        # reset guess lock for this tick
        if match.id in _active_matches:
            _active_matches[match.id]['guessed'] = set()
            _active_matches[match.id]['correct'] = set()

        round_end_event = None
        if match.id in _active_matches:
            round_end_event = _active_matches[match.id].get('round_end_event')

        # increment tick number
        game_round.tick_number += 1
        game_round.save(update_fields=['tick_number'])

        deadline = (timezone.now() + timedelta(milliseconds=match.tick_duration_ms)).timestamp() * 1000

        # broadcast tickStart to room
        await channel_layer.group_send(room_group, {
            'type':          'game.tick_start',
            'tick_number':   game_round.tick_number,
            'deadline':      deadline,
            'revealed_state': {
                'tiles':   game_round.revealed_tiles,
                'letters': game_round.revealed_letters,
            }
        })

        # wait for tick duration (or until round ends early)
        if round_end_event is not None:
            try:
                await asyncio.wait_for(round_end_event.wait(), timeout=tick_duration)
            except asyncio.TimeoutError:
                pass
        else:
            await asyncio.sleep(tick_duration)

        # re-fetch round from DB to check if already ended by a correct guess
        game_round.refresh_from_db()
        if game_round.status == Round.Status.COMPLETED:
            break

        # reveal a random hidden tile
        hidden_indices = [i for i, revealed in enumerate(game_round.revealed_tiles) if not revealed]

        if not hidden_indices:
            # all tiles revealed — no winner
            await channel_layer.group_send(room_group, {
                'type':         'game.round_end',
                'winner_id':    None,
                'is_draw':      False,
                'revealed_word': game_round.word,
                'scores':       get_match_scores(match),
            })
            end_round(game_round, winner=None, is_draw=False)
            break

        # pick and reveal one random hidden tile
        index  = random.choice(hidden_indices)
        letter = game_round.word[index]

        game_round.revealed_tiles[index]   = True
        game_round.revealed_letters[index] = letter
        game_round.save(update_fields=['revealed_tiles', 'revealed_letters'])

        await channel_layer.group_send(room_group, {
            'type':   'game.reveal_tile',
            'index':  index,
            'letter': letter,
            'revealed_state': {
                'tiles':   game_round.revealed_tiles,
                'letters': game_round.revealed_letters,
            }
        })

# guess Sevice 
def validate_and_save_guess(
    game_round: Round,
    player: Player,
    guess_text: str,
    client_sent_at=None,
) -> dict:
    """
    Validate guess and save to DB.
    Returns { 'status': 'correct'|'incorrect'|'error', 'code': str }
    """
    state = _active_matches.get(game_round.match_id)
    if not state:
        return {'status': 'error', 'code': 'NO_ACTIVE_MATCH'}

    # check round is still active
    if game_round.status != Round.Status.ACTIVE:
        return {'status': 'error', 'code': 'LATE_SUBMISSION'}

    # check one guess per player per tick
    if player.id in state.get('guessed', set()):
        return {'status': 'error', 'code': 'ALREADY_GUESSED'}

    # normalise
    guess_text = guess_text.upper().strip()

    # validate not empty or non-alpha
    if not guess_text.isalpha():
        return {'status': 'error', 'code': 'INVALID_GUESS'}

    # lock this player's guess for this tick
    state['guessed'].add(player.id)

    is_correct = guess_text == game_round.word
    if is_correct:
        state.setdefault('correct', set()).add(player.id)

    # save guess to DB
    try:
        Guess.objects.create(
            round=game_round,
            player=player,
            tick_number=game_round.tick_number,
            guess_text=guess_text,
            is_correct=is_correct,
            client_sent_at=client_sent_at,
        )
    except DatabaseError:
        pass  # guess lock already in memory; DB failure non-critical here

    return {
        'status': 'correct' if is_correct else 'incorrect',
        'code':   'CORRECT' if is_correct else 'INCORRECT',
    }


def check_draw(match: Match) -> bool:
    """
    Returns True if both players guessed correctly in the same tick.
    Called after both players have submitted correct guesses.
    """
    state = _active_matches.get(match.id, {})
    return (
        state.get('player1_id') in state.get('correct', set()) and
        state.get('player2_id') in state.get('correct', set())
    )


# Score Service 

def update_match_score(match: Match, winner: Player | None, is_draw: bool) -> None:
    """Increment match score for the round winner."""
    if is_draw:
        try:
            match.score1 += 1
            match.score2 += 1
            match.save(update_fields=['score1', 'score2', 'updated_at'])
        except DatabaseError:
            pass
        return

    if winner is None:
        return

    try:
        if winner.id == match.player1_id:
            match.score1 += 1
        else:
            match.score2 += 1
        match.save(update_fields=['score1', 'score2', 'updated_at'])
    except DatabaseError:
        pass  # in-memory scores remain; log discrepancy


def get_match_scores(match: Match) -> dict:
    """Returns current scores as a dict."""
    return {
        'player1_id': match.player1_id,
        'score1':     match.score1,
        'player2_id': match.player2_id,
        'score2':     match.score2,
    }


def check_match_over(match: Match) -> tuple[bool, Player | None, bool]:
    """
    Check if match termination condition is met.
    Returns (is_over, winner, is_draw).
    Best of 5: first to 3 wins.
    Max 5 rounds: most wins after 5 rounds.
    """
    rounds_played = match.rounds.filter(status=Round.Status.COMPLETED).count()
    score1, score2 = match.score1, match.score2

    # first to 3 wins
    if score1 >= 3 and score2 >= 3:
        return True, None, True
    if score1 >= 3:
        return True, match.player1, False
    if score2 >= 3:
        return True, match.player2, False

    # all 5 rounds played
    if rounds_played >= match.max_rounds:
        if score1 > score2:
            return True, match.player1, False
        elif score2 > score1:
            return True, match.player2, False
        else:
            return True, None, True  # draw

    return False, None, False


def finalize_match(match: Match, winner: Player | None, is_draw: bool) -> None:
    """Close match and update player lifetime stats."""
    match.status = Match.Status.COMPLETED
    match.winner = winner if not is_draw else None

    try:
        match.save(update_fields=['status', 'winner', 'updated_at'])
    except DatabaseError:
        pass

    # update player stats
    from apps.accounts.services import update_player_stats
    update_player_stats(match.player1, won=(winner == match.player1))
    update_player_stats(match.player2, won=(winner == match.player2))

    # cleanup in-memory state
    _active_matches.pop(match.id, None)
