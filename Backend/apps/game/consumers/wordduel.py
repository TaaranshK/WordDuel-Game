from __future__ import annotations

import asyncio
import json
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as dt_timezone

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from django.conf import settings
from django.utils import timezone

from apps.accounts.services import join_or_create_player, update_player_stats, create_or_get_ai_player
from apps.dictionary.services import get_random_word

from ..models import Guess, Match, Round


@dataclass
class LobbyEntry:
    player_id: int
    username: str
    channel_name: str
    joined_at: float = 0  # Track when player joined queue
    
    def __post_init__(self):
        if self.joined_at == 0:
            self.joined_at = time.time()



@dataclass
class MatchState:
    match_id: int
    group_name: str
    player1_id: int
    player1_username: str
    player1_channel: str
    player2_id: int
    player2_username: str
    player2_channel: str
    max_rounds: int
    tick_duration_ms: int
    score1: int = 0
    score2: int = 0
    used_words: list[str] = None  # filled in __post_init__
    round_number: int = 0
    current_round_id: int | None = None
    current_word: str | None = None
    revealed_state: list[str | None] = None  # filled each round
    reveal_order: list[int] = None  # filled each round
    tick_number: int = 0
    guessed_this_tick: set[int] = None  # filled each tick
    correct_this_tick: set[int] = None  # filled each tick
    match_task: asyncio.Task | None = None
    ended: bool = False
    lock: asyncio.Lock = None  # filled in __post_init__

    def __post_init__(self) -> None:
        if self.used_words is None:
            self.used_words = []
        if self.guessed_this_tick is None:
            self.guessed_this_tick = set()
        if self.correct_this_tick is None:
            self.correct_this_tick = set()
        if self.lock is None:
            self.lock = asyncio.Lock()

    def opponent_of(self, player_id: int) -> tuple[int, str, str]:
        if player_id == self.player1_id:
            return self.player2_id, self.player2_username, self.player2_channel
        return self.player1_id, self.player1_username, self.player1_channel


_LOBBY_LOCK = asyncio.Lock()
_LOBBY_QUEUE: list[LobbyEntry] = []
_MATCHES: dict[int, MatchState] = {}
_MATCHMAKING_TASKS: dict[str, asyncio.Task] = {}  # Track background tasks by channel_name


def _setting_float(name: str, default: float) -> float:
    try:
        return float(getattr(settings, name, default))
    except (TypeError, ValueError):
        return default


@database_sync_to_async
def _db_join_player(username: str) -> tuple[int, str]:
    player, _session_token = join_or_create_player(username=username)
    return player.id, player.username


@database_sync_to_async
def _db_create_match(player1_id: int, player2_id: int) -> Match:
    return Match.objects.create(
        player1_id=player1_id,
        player2_id=player2_id,
        max_rounds=int(getattr(settings, "WORDDUEL_MAX_ROUNDS", 5)),
        tick_duration_ms=int(getattr(settings, "WORDDUEL_TICK_DURATION_MS", 5000)),
    )


@database_sync_to_async
def _db_create_round(match_id: int, *, exclude_words: list[str]) -> Round:
    word_data = get_random_word(exclude_words=exclude_words)
    if word_data is None:
        raise ValueError("No active words available in dictionary.")

    word = word_data["word"]
    length = word_data["word_length"]

    match = Match.objects.get(id=match_id)
    round_number = match.rounds.count() + 1

    return Round.objects.create(
        match=match,
        word=word,
        word_length=length,
        revealed_tiles=[False] * length,
        revealed_letters=[""] * length,
        tick_number=0,
        round_number=round_number,
        status=Round.Status.ACTIVE,
    )


@database_sync_to_async
def _db_save_tick_number(round_id: int, tick_number: int) -> None:
    Round.objects.filter(id=round_id).update(tick_number=tick_number)


@database_sync_to_async
def _db_save_revealed_state(round_id: int, revealed_tiles: list[bool], revealed_letters: list[str]) -> None:
    Round.objects.filter(id=round_id).update(
        revealed_tiles=revealed_tiles,
        revealed_letters=revealed_letters,
    )


@database_sync_to_async
def _db_save_guess(
    *,
    round_id: int,
    player_id: int,
    tick_number: int,
    guess_text: str,
    is_correct: bool,
    client_sent_at_ms: int | None,
) -> None:
    client_sent_at = None
    if client_sent_at_ms is not None:
        try:
            client_sent_at = datetime.fromtimestamp(client_sent_at_ms / 1000, tz=dt_timezone.utc)
        except (OverflowError, OSError, ValueError):
            client_sent_at = None

    Guess.objects.create(
        round_id=round_id,
        player_id=player_id,
        tick_number=tick_number,
        guess_text=guess_text,
        is_correct=is_correct,
        client_sent_at=client_sent_at,
    )


@database_sync_to_async
def _db_complete_round_and_update_match(
    *,
    match_id: int,
    round_id: int,
    winner_id: int | None,
    is_draw: bool,
) -> tuple[int, int]:
    match = Match.objects.get(id=match_id)
    game_round = Round.objects.get(id=round_id)

    if is_draw:
        match.score1 += 1
        match.score2 += 1
    elif winner_id is not None:
        if winner_id == match.player1_id:
            match.score1 += 1
        elif winner_id == match.player2_id:
            match.score2 += 1

    match.save(update_fields=["score1", "score2", "updated_at"])

    game_round.status = Round.Status.COMPLETED
    game_round.ended_at = timezone.now()
    game_round.is_draw = is_draw
    game_round.winner_id = None if is_draw else winner_id
    game_round.revealed_tiles = [True] * game_round.word_length
    game_round.revealed_letters = list(game_round.word)
    game_round.save(
        update_fields=[
            "status",
            "ended_at",
            "is_draw",
            "winner",
            "revealed_tiles",
            "revealed_letters",
        ]
    )

    return match.score1, match.score2


@database_sync_to_async
def _db_complete_match_and_update_players(
    *,
    match_id: int,
    winner_id: int | None,
    is_draw: bool,
) -> None:
    match = Match.objects.select_related("player1", "player2").get(id=match_id)
    match.status = Match.Status.COMPLETED
    match.winner_id = None if is_draw else winner_id
    match.save(update_fields=["status", "winner", "updated_at"])

    update_player_stats(match.player1, won=(winner_id == match.player1_id and not is_draw))
    update_player_stats(match.player2, won=(winner_id == match.player2_id and not is_draw))


@database_sync_to_async
def _db_abandon_match_and_update_players(
    *,
    match_id: int,
    winner_id: int | None,
) -> None:
    match = Match.objects.select_related("player1", "player2").get(id=match_id)
    match.status = Match.Status.ABANDONED
    match.winner_id = winner_id
    match.save(update_fields=["status", "winner", "updated_at"])

    update_player_stats(match.player1, won=(winner_id == match.player1_id))
    update_player_stats(match.player2, won=(winner_id == match.player2_id))


def _scores_payload(state: MatchState) -> dict:
    return {
        "player1_id": state.player1_id,
        "score1": state.score1,
        "player2_id": state.player2_id,
        "score2": state.score2,
    }


def _revealed_state_payload(revealed_state: list[str | None]) -> list[str | None]:
    return list(revealed_state)


async def _broadcast_start_round(state: MatchState) -> None:
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        state.group_name,
        {
            "type": "ws.start_round",
            "round_id": str(state.current_round_id),
            "round_number": state.round_number,
            "word_length": len(state.current_word or ""),
            "scores": _scores_payload(state),
        },
    )


async def _broadcast_tick_start(state: MatchState, *, deadline_ms: float) -> None:
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        state.group_name,
        {
            "type": "ws.tick_start",
            "tick_number": state.tick_number,
            "deadline": deadline_ms,
            "revealed_state": _revealed_state_payload(state.revealed_state or []),
        },
    )


async def _broadcast_reveal_tile(state: MatchState, *, index: int, letter: str) -> None:
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        state.group_name,
        {
            "type": "ws.reveal_tile",
            "index": index,
            "letter": letter,
            "revealed_state": _revealed_state_payload(state.revealed_state or []),
        },
    )


async def _broadcast_round_end(
    state: MatchState,
    *,
    winner_id: int | None,
    is_draw: bool,
    revealed_word: str,
) -> None:
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        state.group_name,
        {
            "type": "ws.round_end",
            "winner_id": winner_id,
            "is_draw": is_draw,
            "revealed_word": revealed_word,
            "scores": _scores_payload(state),
        },
    )


async def _broadcast_match_end(state: MatchState, *, winner_id: int | None, is_draw: bool) -> None:
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        state.group_name,
        {
            "type": "ws.match_end",
            "winner_id": winner_id,
            "is_draw": is_draw,
            "scores": _scores_payload(state),
            "total_rounds": state.max_rounds,
        },
    )


async def _broadcast_error(state: MatchState, *, code: str, message: str) -> None:
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        state.group_name,
        {
            "type": "ws.error",
            "code": code,
            "message": message,
        },
    )


async def _simulate_ai_guess(state: MatchState, tick_number: int) -> None:
    """
    AI player attempts to guess during a tick.
    AI guesses with varying probability based on revealed letters.
    """
    async with state.lock:
        # Check if AI already guessed this tick
        if state.player2_id in state.guessed_this_tick:
            return
        
        # Determine if AI attempts a guess this tick
        # AI guesses if at least 40% of letters are revealed
        if not state.revealed_state or not state.current_word:
            return
        
        revealed_count = sum(1 for c in state.revealed_state if c is not None)
        total_count = len(state.revealed_state)
        revealed_percentage = revealed_count / total_count if total_count > 0 else 0
        
        # AI guesses if 40%+ revealed and passes random chance check
        if revealed_percentage < 0.4 or random.random() > 0.65:
            return
        
        # AI attempts the guess
        state.guessed_this_tick.add(state.player2_id)
        is_correct = True  # AI always guesses correctly when attempting
        state.correct_this_tick.add(state.player2_id)
        
        # Save guess to database
        if state.current_round_id:
            await _db_save_guess(
                round_id=state.current_round_id,
                player_id=state.player2_id,
                tick_number=tick_number,
                guess_text=state.current_word,
                is_correct=is_correct,
                client_sent_at_ms=None,
            )


async def _run_match(match_id: int) -> None:
    state = _MATCHES.get(match_id)
    if state is None:
        return

    try:
        await asyncio.sleep(_setting_float("WORDDUEL_FIRST_ROUND_DELAY_S", 3.2))

        while True:
            async with state.lock:
                if state.ended:
                    return
                if state.round_number >= state.max_rounds:
                    break

                try:
                    game_round = await _db_create_round(match_id, exclude_words=state.used_words)
                except ValueError as e:
                    state.ended = True
                    await _broadcast_error(state, code="NO_WORDS", message=str(e))
                    await _db_complete_match_and_update_players(
                        match_id=state.match_id,
                        winner_id=None,
                        is_draw=True,
                    )
                    await _broadcast_match_end(state, winner_id=None, is_draw=True)
                    return
                state.current_round_id = game_round.id
                state.current_word = game_round.word
                state.used_words.append(game_round.word)

                state.round_number = game_round.round_number
                state.tick_number = 0
                state.revealed_state = [None] * game_round.word_length
                state.reveal_order = list(range(game_round.word_length))
                random.shuffle(state.reveal_order)
                state.guessed_this_tick = set()
                state.correct_this_tick = set()

            await _broadcast_start_round(state)
            await asyncio.sleep(_setting_float("WORDDUEL_AFTER_START_ROUND_GAP_S", 0.6))

            # Tick loop
            while True:
                async with state.lock:
                    if state.ended:
                        return

                    state.tick_number += 1
                    state.guessed_this_tick = set()
                    state.correct_this_tick = set()

                    tick_number = state.tick_number
                    deadline = (timezone.now() + timedelta(milliseconds=state.tick_duration_ms)).timestamp() * 1000
                    round_id = state.current_round_id

                if round_id is not None:
                    await _db_save_tick_number(round_id, tick_number)

                await _broadcast_tick_start(state, deadline_ms=deadline)

                # Simulate AI guess if AI player is in match
                if state.player2_channel is None:  # AI player has no channel
                    await _simulate_ai_guess(state, tick_number)

                # wait for tick duration
                await asyncio.sleep(state.tick_duration_ms / 1000)

                async with state.lock:
                    if state.ended:
                        return

                    if state.correct_this_tick:
                        # resolve round at tick end
                        revealed_word = state.current_word or ""
                        is_draw = (
                            state.player1_id in state.correct_this_tick and
                            state.player2_id in state.correct_this_tick
                        )
                        if is_draw:
                            winner_id = None
                        else:
                            winner_id = next(iter(state.correct_this_tick))

                        score1, score2 = await _db_complete_round_and_update_match(
                            match_id=state.match_id,
                            round_id=state.current_round_id,
                            winner_id=winner_id,
                            is_draw=is_draw,
                        )
                        state.score1, state.score2 = score1, score2
                        await _broadcast_round_end(
                            state,
                            winner_id=winner_id,
                            is_draw=is_draw,
                            revealed_word=revealed_word,
                        )
                        state.current_round_id = None
                        state.current_word = None
                        break

                    # reveal next letter
                    if not state.reveal_order:
                        # should be impossible (round would have ended on the last reveal)
                        break

                    index = state.reveal_order.pop(0)
                    assert state.current_word is not None
                    letter = state.current_word[index]
                    if state.revealed_state is None:
                        state.revealed_state = []
                    state.revealed_state[index] = letter

                    all_revealed = all(c is not None for c in state.revealed_state)
                    revealed_tiles = [c is not None for c in state.revealed_state]
                    revealed_letters = [c or "" for c in state.revealed_state]
                    round_id = state.current_round_id

                if round_id is not None:
                    await _db_save_revealed_state(round_id, revealed_tiles, revealed_letters)

                await _broadcast_reveal_tile(state, index=index, letter=letter)

                if all_revealed:
                    score1, score2 = await _db_complete_round_and_update_match(
                        match_id=state.match_id,
                        round_id=state.current_round_id,
                        winner_id=None,
                        is_draw=False,
                    )
                    revealed_word = state.current_word or ""
                    async with state.lock:
                        state.score1, state.score2 = score1, score2
                        state.current_round_id = None
                        state.current_word = None
                    await _broadcast_round_end(state, winner_id=None, is_draw=False, revealed_word=revealed_word)
                    break

                await asyncio.sleep(_setting_float("WORDDUEL_BETWEEN_TICKS_GAP_S", 0.35))

            # between rounds
            await asyncio.sleep(_setting_float("WORDDUEL_ROUND_END_DELAY_S", 4.0))

        # match end
        async with state.lock:
            if state.ended:
                return
            state.ended = True

            if state.score1 > state.score2:
                winner_id = state.player1_id
                is_draw = False
            elif state.score2 > state.score1:
                winner_id = state.player2_id
                is_draw = False
            else:
                winner_id = None
                is_draw = True

        await _db_complete_match_and_update_players(match_id=state.match_id, winner_id=winner_id, is_draw=is_draw)
        await _broadcast_match_end(state, winner_id=winner_id, is_draw=is_draw)

    except asyncio.CancelledError:
        # Match cancelled (player left/disconnected)
        raise
    finally:
        _MATCHES.pop(match_id, None)


class WordDuelConsumer(AsyncWebsocketConsumer):
    player_id: int | None = None
    username: str | None = None
    match_id: int | None = None
    match_group: str | None = None

    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        await self._leave_match()
        if self.player_id is not None:
            await self._remove_from_lobby()

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self._send_error("BAD_JSON", "Invalid JSON.")
            return

        event = data.get("event") or data.get("type")
        payload = data.get("payload") if "payload" in data else data.get("data")

        if event == "joinLobby":
            await self._handle_join_lobby(payload or {})
        elif event == "submitGuess":
            await self._handle_submit_guess(payload or {})
        elif event == "leaveMatch":
            await self._leave_match()
            await self._remove_from_lobby()
        else:
            await self._send_error("UNKNOWN_EVENT", f"Unknown event: {event}")

    async def ws_match_found(self, message):
        self.match_id = message["match_id"]
        self.match_group = message["group_name"]

        if self.match_group:
            await self.channel_layer.group_add(self.match_group, self.channel_name)

        # Send matchFound to client
        event_payload = {
            "matchId": str(message["match_id"]),
            "opponentUsername": message["opponent_username"],
            "scores": message["scores"],
        }
        
        # Include AI flag if present
        if message.get("is_ai_match"):
            event_payload["isAiMatch"] = True
        
        await self._send_event(
            "matchFound",
            event_payload,
        )

    async def ws_opponent_guessed(self, message):
        await self._send_event("opponentGuessed", {"tickNumber": message.get("tick_number")})

    async def ws_start_round(self, message):
        scores = self._map_scores(message["scores"])
        await self._send_event(
            "startRound",
            {
                "roundId": message["round_id"],
                "roundNumber": message["round_number"],
                "wordLength": message["word_length"],
                "scores": scores,
            },
        )

    async def ws_tick_start(self, message):
        await self._send_event(
            "tickStart",
            {
                "tickNumber": message["tick_number"],
                "deadline": message["deadline"],
                "revealedState": message["revealed_state"],
            },
        )

    async def ws_reveal_tile(self, message):
        await self._send_event(
            "revealTile",
            {
                "index": message["index"],
                "letter": message["letter"],
                "revealedState": message["revealed_state"],
            },
        )

    async def ws_round_end(self, message):
        scores = self._map_scores(message["scores"])
        winner = self._map_winner(message.get("winner_id"), bool(message.get("is_draw")))
        await self._send_event(
            "roundEnd",
            {
                "winner": winner,
                "revealedWord": message.get("revealed_word"),
                "scores": scores,
                "isDraw": bool(message.get("is_draw")),
            },
        )

    async def ws_match_end(self, message):
        scores = self._map_scores(message["scores"])
        winner = self._map_winner(message.get("winner_id"), bool(message.get("is_draw")))
        if winner is None:
            winner = "draw"
        await self._send_event(
            "matchEnd",
            {
                "winner": winner,
                "finalScores": scores,
                "totalRounds": message.get("total_rounds"),
            },
        )

    async def ws_error(self, message):
        await self._send_event("error", {"code": message.get("code"), "message": message.get("message")})

    def _map_scores(self, scores: dict) -> dict:
        if self.player_id is None:
            return {"me": 0, "opponent": 0}

        if self.player_id == scores["player1_id"]:
            return {"me": scores["score1"], "opponent": scores["score2"]}
        return {"me": scores["score2"], "opponent": scores["score1"]}

    def _map_winner(self, winner_id: int | None, is_draw: bool) -> str | None:
        if is_draw:
            return "draw"
        if winner_id is None or self.player_id is None:
            return None
        return "me" if winner_id == self.player_id else "opponent"

    async def _send_event(self, event: str, payload: dict) -> None:
        await self.send(text_data=json.dumps({"event": event, "payload": payload}))

    async def _send_error(self, code: str, message: str) -> None:
        await self._send_event("error", {"code": code, "message": message})

    async def _handle_join_lobby(self, payload: dict) -> None:
        username = (payload.get("username") or "").strip()
        if not username:
            await self._send_error("INVALID_USERNAME", "Username is required.")
            return
        if len(username) > 50:
            await self._send_error("INVALID_USERNAME", "Username must be 50 characters or fewer.")
            return

        # reset state for this socket
        await self._leave_match()
        await self._remove_from_lobby()

        self.player_id, self.username = await _db_join_player(username)

        async with _LOBBY_LOCK:
            # remove duplicates
            _LOBBY_QUEUE[:] = [
                entry
                for entry in _LOBBY_QUEUE
                if entry.player_id != self.player_id and entry.channel_name != self.channel_name
            ]
            _LOBBY_QUEUE.append(
                LobbyEntry(
                    player_id=self.player_id,
                    username=self.username,
                    channel_name=self.channel_name,
                )
            )

            if len(_LOBBY_QUEUE) < 2:
                # Single player in queue - start background task for AI timeout matching
                if self.channel_name not in _MATCHMAKING_TASKS or _MATCHMAKING_TASKS[self.channel_name].done():
                    task = asyncio.create_task(
                        self._run_timeout_matchmaking(self.player_id, self.channel_name, self.username)
                    )
                    _MATCHMAKING_TASKS[self.channel_name] = task
                return

            p1 = _LOBBY_QUEUE.pop(0)
            p2 = _LOBBY_QUEUE.pop(0)

        match = await _db_create_match(p1.player_id, p2.player_id)
        group_name = f"wordduel_{match.id}"

        state = MatchState(
            match_id=match.id,
            group_name=group_name,
            player1_id=p1.player_id,
            player1_username=p1.username,
            player1_channel=p1.channel_name,
            player2_id=p2.player_id,
            player2_username=p2.username,
            player2_channel=p2.channel_name,
            max_rounds=match.max_rounds,
            tick_duration_ms=match.tick_duration_ms,
            score1=match.score1,
            score2=match.score2,
        )
        _MATCHES[match.id] = state

        # Add both channels to the match group immediately so no broadcasts are missed.
        await self.channel_layer.group_add(group_name, p1.channel_name)
        await self.channel_layer.group_add(group_name, p2.channel_name)

        await self.channel_layer.send(
            p1.channel_name,
            {
                "type": "ws.match_found",
                "match_id": match.id,
                "group_name": group_name,
                "opponent_username": p2.username,
                "scores": {"me": 0, "opponent": 0},
            },
        )
        await self.channel_layer.send(
            p2.channel_name,
            {
                "type": "ws.match_found",
                "match_id": match.id,
                "group_name": group_name,
                "opponent_username": p1.username,
                "scores": {"me": 0, "opponent": 0},
            },
        )

        # start match loop once
        state.match_task = asyncio.create_task(_run_match(match.id))

    async def _handle_submit_guess(self, payload: dict) -> None:
        if self.player_id is None:
            await self._send_error("NO_PLAYER", "Join the lobby first.")
            return
        if self.match_id is None:
            await self._send_error("NO_MATCH", "No active match.")
            return

        state = _MATCHES.get(self.match_id)
        if state is None:
            await self._send_error("NO_MATCH", "No active match.")
            return

        guess_text = (payload.get("guessText") or "").strip().upper()
        client_sent_at = payload.get("clientSentAt")
        if client_sent_at is not None:
            try:
                client_sent_at = int(client_sent_at)
            except (TypeError, ValueError):
                client_sent_at = None

        async with state.lock:
            if state.ended or state.current_round_id is None or state.current_word is None:
                await self._send_error("LATE_SUBMISSION", "Round already ended.")
                return

            if self.player_id in state.guessed_this_tick:
                await self._send_error("ALREADY_GUESSED", "Already submitted this tick.")
                return

            if not guess_text or not guess_text.isalpha():
                await self._send_error("INVALID_GUESS", "Guess must be alphabetic.")
                return
            if len(guess_text) > 12:
                await self._send_error("INVALID_GUESS", "Guess is too long.")
                return

            state.guessed_this_tick.add(self.player_id)

            is_correct = guess_text == state.current_word
            if is_correct:
                state.correct_this_tick.add(self.player_id)
            tick_number = state.tick_number
            round_id = state.current_round_id

            opponent_id, _opponent_username, opponent_channel = state.opponent_of(self.player_id)

            # animation-only hint for the other player
            await self.channel_layer.send(
                opponent_channel,
                {"type": "ws.opponent_guessed", "tick_number": tick_number},
            )

        # Save guess outside the lock (DB)
        await _db_save_guess(
            round_id=round_id,
            player_id=self.player_id,
            tick_number=tick_number,
            guess_text=guess_text,
            is_correct=is_correct,
            client_sent_at_ms=client_sent_at,
        )

        if not is_correct:
            return
        return

    async def _remove_from_lobby(self) -> None:
        _LOBBY_QUEUE[:] = [e for e in _LOBBY_QUEUE if e.channel_name != self.channel_name]
        
        # Cancel any pending AI matchmaking task for this player
        if self.channel_name in _MATCHMAKING_TASKS:
            task = _MATCHMAKING_TASKS.pop(self.channel_name)
            if not task.done():
                task.cancel()

    async def _run_timeout_matchmaking(self, player_id: int, channel_name: str, username: str) -> None:
        """
        Background task that waits for MATCHMAKING_TIMEOUT_SECONDS.
        If another player joins, immediate matching occurs.
        If timeout is reached, match with AI player.
        """
        timeout_seconds = int(getattr(
            settings, 
            'MATCHMAKING_TIMEOUT_SECONDS', 
            10
        ))
        start_time = time.time()
        
        try:
            while True:
                await asyncio.sleep(1)  # Check every 1 second
                current_time = time.time()
                time_in_queue = current_time - start_time
                
                # Check if another player has been matched meanwhile
                async with _LOBBY_LOCK:
                    # If queue is empty, we were already matched
                    if not any(e.player_id == player_id for e in _LOBBY_QUEUE):
                        return
                    
                    # If timeout exceeded, match with AI
                    if time_in_queue >= timeout_seconds:
                        entry = next((e for e in _LOBBY_QUEUE if e.player_id == player_id), None)
                        if entry:
                            _LOBBY_QUEUE.remove(entry)
                        else:
                            return
                
                    # Recheck - if 2+ players now, normal match will handle it
                    if len(_LOBBY_QUEUE) >= 2:
                        return
                
                # If we reach here at timeout, match with AI
                if time_in_queue >= timeout_seconds:
                    await self._match_with_ai(player_id, username, channel_name)
                    return
        
        except asyncio.CancelledError:
            pass  # Task was cancelled (player disconnected)
        except Exception as e:
            print(f"[MATCHMAKING ERROR] {e}")
            pass
    
    async def _match_with_ai(self, player_id: int, username: str, channel_name: str) -> None:
        """Create a match between the queued player and an AI opponent."""
        try:
            # Create the AI match in the database
            ai_player = await database_sync_to_async(create_or_get_ai_player)()
            match = await _db_create_match(player_id, ai_player.id)
            group_name = f"wordduel_{match.id}"
            
            # Create match state
            state = MatchState(
                match_id=match.id,
                group_name=group_name,
                player1_id=player_id,
                player1_username=username,
                player1_channel=channel_name,
                player2_id=ai_player.id,
                player2_username=ai_player.username,
                player2_channel=None,  # AI has no channel
                max_rounds=match.max_rounds,
                tick_duration_ms=match.tick_duration_ms,
                score1=0,
                score2=0,
            )
            _MATCHES[match.id] = state
            
            # Add human player to the group
            await self.channel_layer.group_add(group_name, channel_name)
            
            # Send matchFound to human player
            await self.channel_layer.send(
                channel_name,
                {
                    "type": "ws.match_found",
                    "match_id": match.id,
                    "group_name": group_name,
                    "opponent_username": ai_player.username,
                    "scores": {"me": 0, "opponent": 0},
                    "is_ai_match": True,
                },
            )
            
            print(f"[MATCHMAKING] AI match created: {match.id} - {username} vs {ai_player.username}")
            
            # Start match loop
            state.match_task = asyncio.create_task(_run_match(match.id))
            
        except Exception as e:
            print(f"[MATCHMAKING] AI match creation failed: {e}")
            pass

    async def _leave_match(self) -> None:
        if self.match_group:
            await self.channel_layer.group_discard(self.match_group, self.channel_name)

        if self.match_id is None or self.player_id is None:
            self.match_id = None
            self.match_group = None
            return

        state = _MATCHES.get(self.match_id)
        if state is None:
            self.match_id = None
            self.match_group = None
            return

        async with state.lock:
            if state.ended:
                self.match_id = None
                self.match_group = None
                return

            state.ended = True
            opponent_id, _opponent_username, _opponent_channel = state.opponent_of(self.player_id)
            winner_id = opponent_id

            if state.match_task is not None:
                state.match_task.cancel()

        await _db_abandon_match_and_update_players(match_id=state.match_id, winner_id=winner_id)
        await _broadcast_match_end(state, winner_id=winner_id, is_draw=False)

        self.match_id = None
        self.match_group = None
