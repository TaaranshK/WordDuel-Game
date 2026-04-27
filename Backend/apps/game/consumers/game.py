
# LOGIC 
"""
Client A & B connect → ws/game/<match_id>/
         ↓
    sendJoinGame { session_token }
         ↓
   both joined → _start_round()
         ↓
   tick loop starts → tickStart broadcast
         ↓
   client sends submitGuess
         ↓
   correct? → cancel tick → roundEnd → 4s pause → next round or matchEnd
   wrong?   → tick continues
   timeout? → revealTile → next tick
         ↓
   disconnect → grace timer 10s
         ↓
   reconnect within 10s → game resumes
   no reconnect → opponent wins round → match continues
   """


import asyncio
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

from apps.game.services import (
    get_session_by_token,
    close_session,
    create_round,
    end_round,
    get_round_state,
    run_tick_loop,
    validate_and_save_guess,
    check_draw,
    get_match_scores,
    check_match_over,
    finalize_match,
    _active_matches,
)


class GameConsumer(AsyncJsonWebsocketConsumer):
    """
    Handles real-time game WebSocket for a specific match.
    URL: ws/game/<match_id>/

    Flow:
      connect → validate session → join room → start round
      → tick loop → submitGuess → roundEnd → matchEnd
    """

    GRACE_PERIOD = 10  # seconds before forfeit on disconnect


    # -----------------------------------------------------------------------
    # Connection
    # -----------------------------------------------------------------------

    async def connect(self):
        self.match_id    = self.scope['url_route']['kwargs']['match_id']
        self.room_group  = f'match_{self.match_id}'
        self.player      = None
        self.match       = None
        self.session_token = None
        self.tick_task   = None
        self.grace_task  = None

        await self.accept()


    async def disconnect(self, close_code):
        if not self.player or not self.match:
            return

        # close session in DB
        if self.session_token:
            await database_sync_to_async(close_session)(self.session_token)

        # cancel tick loop if running
        if self.tick_task and not self.tick_task.done():
            self.tick_task.cancel()

        # notify opponent
        await self.channel_layer.group_send(self.room_group, {
            'type':            'game.opponent_disconnected',
            'grace_period_ms': self.GRACE_PERIOD * 1000,
            'player_id':       self.player.id,
        })

        # start grace timer — wait for reconnect
        self.grace_task = asyncio.create_task(
            self._grace_timer()
        )

        # leave room
        await self.channel_layer.group_discard(
            self.room_group,
            self.channel_name,
        )


    # -----------------------------------------------------------------------
    # Receive
    # -----------------------------------------------------------------------

    async def send_json(self, content, close=False):
        if isinstance(content, dict):
            if 'event' not in content and 'type' in content:
                content = {'event': content['type'], **content}
            elif 'type' not in content and 'event' in content:
                content = {'type': content['event'], **content}
        await super().send_json(content, close=close)

    async def receive_json(self, content):
        event_type = content.get('type') or content.get('event')
        payload = content.get('payload') if isinstance(content.get('payload'), dict) else content

        handlers = {
            'joinGame':    self.handle_join_game,
            'submitGuess': self.handle_submit_guess,
            'leaveMatch':  self.handle_leave_match,
            'ping':        self.handle_ping,
        }

        handler = handlers.get(event_type)

        if handler:
            await handler(payload)
        else:
            await self.send_json({
                'type':    'error',
                'code':    'UNKNOWN_EVENT',
                'message': f"Unknown event: {event_type}"
            })


    # -----------------------------------------------------------------------
    # Event Handlers
    # -----------------------------------------------------------------------

    async def handle_join_game(self, content):
        """
        Payload: { "type": "joinGame", "session_token": "abc123" }
        1. Validate session token
        2. Join match room
        3. If both players joined → start round 1
        """
        session_token = content.get('session_token')

        if not session_token:
            await self.send_json({
                'type':    'error',
                'code':    'MISSING_SESSION_TOKEN',
                'message': 'session_token is required.'
            })
            return

        # validate session
        session = await database_sync_to_async(get_session_by_token)(session_token)

        if not session:
            await self.send_json({
                'type':    'error',
                'code':    'INVALID_SESSION',
                'message': 'Invalid or expired session token.'
            })
            return

        self.player        = session.player
        self.session_token = session_token
        self.match         = await database_sync_to_async(
            lambda: __import__('game.models', fromlist=['Match']).Match.objects.select_related(
                'player1', 'player2'
            ).get(id=self.match_id)
        )()

        # cancel grace timer if reconnecting
        if self.grace_task and not self.grace_task.done():
            self.grace_task.cancel()
            await self.channel_layer.group_send(self.room_group, {
                'type':      'game.opponent_reconnected',
                'player_id': self.player.id,
            })

        # join match room
        await self.channel_layer.group_add(
            self.room_group,
            self.channel_name,
        )

        # track player joined in memory
        state = _active_matches.get(self.match.id, {})
        joined = state.setdefault('joined', set())
        joined.add(self.player.id)

        await self.send_json({
            'type':     'game_joined',
            'match_id': self.match.id,
            'player_id': self.player.id,
            'message':  'Joined match room. Waiting for opponent...'
        })

        # start round only when both players have joined
        if len(joined) == 2:
            await self._start_round()


    async def handle_submit_guess(self, content):
        """
        Payload: { "type": "submitGuess", "round_id": 1, "guess_text": "apple", "client_sent_at": 123456 }
        """
        round_id       = content.get('round_id')
        guess_text     = content.get('guess_text', '').strip()
        client_sent_at = content.get('client_sent_at', None)

        if not round_id or not guess_text:
            await self.send_json({
                'type':    'error',
                'code':    'INVALID_PAYLOAD',
                'message': 'round_id and guess_text are required.'
            })
            return

        # fetch current round
        game_round = await self._get_round(round_id)

        if not game_round:
            await self.send_json({
                'type':    'error',
                'code':    'INVALID_ROUND',
                'message': 'Round not found.'
            })
            return

        # validate and save guess
        result = await database_sync_to_async(validate_and_save_guess)(
            game_round=game_round,
            player=self.player,
            guess_text=guess_text,
            client_sent_at=client_sent_at,
        )

        # handle errors
        if result['status'] == 'error':
            await self.send_json({
                'type':    'error',
                'code':    result['code'],
                'message': result['code'].replace('_', ' ').title()
            })
            return

        # notify opponent that this player guessed (not the guess text)
        await self.channel_layer.group_send(self.room_group, {
            'type':        'game.opponent_guessed',
            'tick_number': game_round.tick_number,
            'player_id':   self.player.id,
        })

        # handle correct guess
        if result['status'] == 'correct':
            await self._handle_correct_guess(game_round)


    async def handle_leave_match(self, content):
        """Player voluntarily forfeits the match."""
        if not self.match or not self.player:
            return

        # opponent wins
        opponent = await self._get_opponent()

        await self.channel_layer.group_send(self.room_group, {
            'type':      'game.match_end',
            'winner_id': opponent.id if opponent else None,
            'is_draw':   False,
            'reason':    'OPPONENT_LEFT',
            'scores':    get_match_scores(self.match),
        })

        await database_sync_to_async(finalize_match)(
            match=self.match,
            winner=opponent,
            is_draw=False,
        )

        await self.close()


    async def handle_ping(self, content):
        """Heartbeat — respond with pong + server time."""
        await self.send_json({
            'type':        'pong',
            'timestamp':   content.get('timestamp'),
            'server_time': timezone.now().timestamp() * 1000,
        })


    
    # Game Logic
  
    async def _start_round(self):
        """Create a new round and start the tick loop."""
        game_round = await database_sync_to_async(create_round)(self.match)

        await self.channel_layer.group_send(self.room_group, {
            'type':         'game.start_round',
            'round_id':     game_round.id,
            'round_number': game_round.round_number,
            'word_length':  game_round.word_length,
            'scores':       get_match_scores(self.match),
        })

        # start async tick loop
        self.tick_task = asyncio.create_task(
            run_tick_loop(
                match=self.match,
                game_round=game_round,
                channel_layer=self.channel_layer,
                room_group=self.room_group,
            )
        )


    async def _handle_correct_guess(self, game_round):
        """Handle a correct guess — check draw or declare winner."""
        # cancel tick loop immediately
        if self.tick_task and not self.tick_task.done():
            self.tick_task.cancel()

        # re-fetch round and match
        game_round = await self._get_round(game_round.id)
        await database_sync_to_async(self.match.refresh_from_db)()

        # check if both players guessed correctly same tick (draw)
        is_draw = await database_sync_to_async(check_draw)(self.match)
        winner  = None if is_draw else self.player

        # end round in DB
        await database_sync_to_async(end_round)(
            game_round=game_round,
            winner=winner,
            is_draw=is_draw,
        )

        # refresh match scores
        await database_sync_to_async(self.match.refresh_from_db)()

        # broadcast roundEnd
        await self.channel_layer.group_send(self.room_group, {
            'type':          'game.round_end',
            'winner_id':     winner.id if winner else None,
            'is_draw':       is_draw,
            'revealed_word': game_round.word,
            'scores':        get_match_scores(self.match),
        })

        # wait 4 seconds then check match over
        await asyncio.sleep(4)
        await self._check_and_finalize_match()


    async def _check_and_finalize_match(self):
        """Check if match is over — if not, start next round."""
        await database_sync_to_async(self.match.refresh_from_db)()

        is_over, winner, is_draw = await database_sync_to_async(
            check_match_over
        )(self.match)

        if is_over:
            await self.channel_layer.group_send(self.room_group, {
                'type':         'game.match_end',
                'winner_id':    winner.id if winner else None,
                'is_draw':      is_draw,
                'final_scores': get_match_scores(self.match),
                'total_rounds': self.match.rounds.count(),
            })

            await database_sync_to_async(finalize_match)(
                match=self.match,
                winner=winner,
                is_draw=is_draw,
            )
        else:
            # start next round
            await self._start_round()


    async def _grace_timer(self):
        """
        Wait GRACE_PERIOD seconds for reconnect.
        If no reconnect → remaining player wins the round.
        """
        await asyncio.sleep(self.GRACE_PERIOD)

        # player did not reconnect — opponent wins
        opponent = await self._get_opponent()

        # get active round
        game_round = await database_sync_to_async(
            lambda: self.match.rounds.filter(
                status='active'
            ).first()
        )()

        if game_round:
            await database_sync_to_async(end_round)(
                game_round=game_round,
                winner=opponent,
                is_draw=False,
            )

        await self.channel_layer.group_send(self.room_group, {
            'type':      'game.round_end',
            'winner_id': opponent.id if opponent else None,
            'is_draw':   False,
            'reason':    'OPPONENT_DISCONNECTED',
            'scores':    get_match_scores(self.match),
        })

        await asyncio.sleep(4)
        await self._check_and_finalize_match()


    
    # Channel Layer Event Handlers (group_send → WebSocket)
    # -----------------------------------------------------------------------

    async def game_start_round(self, event):
        await self.send_json({
            'type':         'startRound',
            'round_id':     event['round_id'],
            'round_number': event['round_number'],
            'word_length':  event['word_length'],
            'scores':       event['scores'],
        })

    async def game_tick_start(self, event):
        await self.send_json({
            'type':           'tickStart',
            'tick_number':    event['tick_number'],
            'deadline':       event['deadline'],
            'revealed_state': event['revealed_state'],
        })

    async def game_reveal_tile(self, event):
        await self.send_json({
            'type':           'revealTile',
            'index':          event['index'],
            'letter':         event['letter'],
            'revealed_state': event['revealed_state'],
        })

    async def game_round_end(self, event):
        await self.send_json({
            'type':          'roundEnd',
            'winner_id':     event.get('winner_id'),
            'is_draw':       event.get('is_draw'),
            'revealed_word': event.get('revealed_word'),
            'scores':        event.get('scores'),
            'reason':        event.get('reason', None),
        })

    async def game_match_end(self, event):
        await self.send_json({
            'type':         'matchEnd',
            'winner_id':    event.get('winner_id'),
            'is_draw':      event.get('is_draw'),
            'final_scores': event.get('final_scores'),
            'total_rounds': event.get('total_rounds'),
            'reason':       event.get('reason', None),
        })

    async def game_opponent_guessed(self, event):
        # only send to the OTHER player
        if event['player_id'] != self.player.id:
            await self.send_json({
                'type':        'opponentGuessed',
                'tick_number': event['tick_number'],
            })

    async def game_opponent_disconnected(self, event):
        if event['player_id'] != self.player.id:
            await self.send_json({
                'type':            'opponentDisconnected',
                'grace_period_ms': event['grace_period_ms'],
            })

    async def game_opponent_reconnected(self, event):
        if event['player_id'] != self.player.id:
            await self.send_json({
                'type':    'opponentReconnected',
                'message': 'Opponent reconnected. Game resuming.'
            })


    
    # DB Helpers

    async def _get_round(self, round_id):
        try:
            return await database_sync_to_async(
                lambda: __import__('game.models', fromlist=['Round']).Round.objects.get(
                    id=round_id
                )
            )()
        except Exception:
            return None

    async def _get_opponent(self):
        try:
            if self.match.player1_id == self.player.id:
                return self.match.player2
            return self.match.player1
        except Exception:
            return None