import asyncio
import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

from apps.accounts.services import join_or_create_player
from apps.game.services import (
    add_to_lobby,
    remove_from_lobby,
    try_match_players,
    create_session,
    close_session,
    get_session_by_token,
)


class LobbyConsumer(AsyncJsonWebsocketConsumer):
    """
    Handles WebSocket connections in the lobby.
    Flow:
      connect → joinLobby → matchmaking → matchFound → disconnect to game room
    """

    LOBBY_GROUP = 'lobby'

    async def connect(self):
        self.player      = None
        self.session_token = None
        self.matchmaking_task = None  # Track background task

        await self.accept()

        await self.send_json({
            'type':    'connection_established',
            'message': 'Connected to lobby. Send joinLobby to begin.'
        })


    async def disconnect(self, close_code):
        # Cancel matchmaking task if running
        if self.matchmaking_task:
            self.matchmaking_task.cancel()
            try:
                await self.matchmaking_task
            except asyncio.CancelledError:
                pass

        if self.player:
            # remove from matchmaking queue
            remove_from_lobby(self.player.id)

            # mark session inactive
            if self.session_token:
                close_session(self.session_token)

            await self.send_safe({
                'type':    'lobby_left',
                'message': 'Disconnected from lobby.'
            })


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

        if event_type == 'joinLobby':
            await self.handle_join_lobby(payload)
        else:
            await self.send_json({
                'type':    'error',
                'code':    'UNKNOWN_EVENT',
                'message': f"Unknown event type: {event_type}"
            })


    
    # Event Handlers
    

    async def handle_join_lobby(self, content):
        """
        Payload: { "type": "joinLobby", "username": "taaransh", "session_token": "..." }
        1. Validate username
        2. Check for existing session (reconnect case)
        3. Add to matchmaking queue
        4. Try to pair with another player
        """
        username      = content.get('username', '').strip().lower()
        session_token = content.get('session_token', None)

        # --- validate username ---
        if not username or not username.isalnum():
            await self.send_json({
                'type':    'error',
                'code':    'INVALID_USERNAME',
                'message': 'Username must be alphanumeric and non-empty.'
            })
            return

        # --- handle reconnect via session token ---
        if session_token:
            session = get_session_by_token(session_token)
            if session:
                self.player        = session.player
                self.session_token = session_token

                # if player already has an active match, redirect them
                if session.match and session.match.status == 'ongoing':
                    await self.send_json({
                        'type':     'rejoin_match',
                        'match_id': session.match.id,
                        'message':  'You have an active match. Reconnecting...'
                    })
                    return

        # --- get or create player ---
        from apps.accounts.services import join_or_create_player
        self.player, self.session_token = await self._get_or_create_player(username)

        # --- save session to DB ---
        await self._create_session(self.player, self.session_token)

        await self.send_json({
            'type':          'lobby_joined',
            'player_id':     self.player.id,
            'username':      self.player.username,
            'session_token': self.session_token,
            'message':       'Waiting for opponent...'
        })

        # --- add to matchmaking queue ---
        add_to_lobby(
            player_id=self.player.id,
            session_token=self.session_token,
            channel_name=self.channel_name,
        )

        # --- try to pair players ---
        result = try_match_players()

        if result:
            match, p1_info, p2_info = result
            await self._notify_match_found(match, p1_info, p2_info)
            
            # Check if AI player was matched
            from apps.game.services import _active_matches
            match_state = _active_matches.get(match.id, {})
            if match_state.get('ai_player_id'):
                await self.send_json({
                    'type': 'aiPairingNotification',
                    'message': 'No opponent found. Matched with AI opponent.',
                    'opponent_username': 'AI_Opponent',
                    'is_ai_match': True,
                })
        else:
            # No match yet, start background task to check for timeout
            if not self.matchmaking_task:
                self.matchmaking_task = asyncio.create_task(
                    self._run_periodic_matchmaking_check(self.player.id)
                )


    async def _run_periodic_matchmaking_check(self, player_id):
        """
        Periodically check if the queued player should be matched with AI.
        Runs every 1 second until match is found or task is cancelled.
        """
        from channels.db import database_sync_to_async
        
        try:
            while True:
                await asyncio.sleep(1)  # Check every 1 second
                
                # Try to match again (wrap sync function)
                result = await database_sync_to_async(try_match_players)()
                
                if result:
                    match, matched_p1_info, matched_p2_info = result
                    
                    # Only process if this is OUR player
                    if matched_p1_info['player_id'] == player_id:
                        await self._notify_match_found(match, matched_p1_info, matched_p2_info)
                        
                        # Check if AI player was matched
                        from apps.game.services import _active_matches
                        match_state = _active_matches.get(match.id, {})
                        if match_state.get('ai_player_id'):
                            await self.send_json({
                                'type': 'aiPairingNotification',
                                'message': 'No opponent found. Matched with AI opponent.',
                                'opponent_username': 'AI_Opponent',
                                'is_ai_match': True,
                            })
                        break  # Match found, exit loop
                        
        except asyncio.CancelledError:
            pass  # Task was cancelled (player disconnected)
        except Exception as e:
            print(f"[MATCHMAKING ERROR] {e}")  # Log any errors
            pass


    
    # Match Found — notify both players
    
    async def _notify_match_found(self, match, p1_info, p2_info):
        """Send matchFound event to both players via their channel names."""
        from apps.accounts.models import Player

        player1 = await self._get_player(p1_info['player_id'])
        player2 = await self._get_player(p2_info['player_id'])

        # notify player 1
        await self.channel_layer.send(p1_info['channel_name'], {
            'type':              'lobby.match_found',
            'match_id':          match.id,
            'opponent_username': player2.username,
            'your_player_id':    player1.id,
            'session_token':     p1_info['session_token'],
        })

        # notify player 2 (skip if AI player - no channel)
        if p2_info['channel_name'] is not None:
            await self.channel_layer.send(p2_info['channel_name'], {
                'type':              'lobby.match_found',
                'match_id':          match.id,
                'opponent_username': player1.username,
                'your_player_id':    player2.id,
                'session_token':     p2_info['session_token'],
            })


    async def lobby_match_found(self, event):
        """Forward matchFound to WebSocket client."""
        await self.send_json({
            'type':              'matchFound',
            'match_id':          event['match_id'],
            'opponent_username': event['opponent_username'],
            'your_player_id':    event['your_player_id'],
            'session_token':     event['session_token'],
            'message':           'Match found! Connecting to game...'
        })


   

    async def _get_or_create_player(self, username):
        from channels.db import database_sync_to_async
        return await database_sync_to_async(join_or_create_player)(username)

    async def _create_session(self, player, session_token):
        from channels.db import database_sync_to_async
        await database_sync_to_async(create_session)(
            player=player,
            session_token=session_token,
        )

    async def _get_player(self, player_id):
        from channels.db import database_sync_to_async
        from apps.accounts.models import Player
        return await database_sync_to_async(Player.objects.get)(id=player_id)


    

    async def send_safe(self, data):
        """Send JSON without raising if connection already closed."""
        try:
            await self.send_json(data)
        except Exception:
            pass