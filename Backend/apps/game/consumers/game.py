import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class GameConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for active game.
    Handles: asyncio tick loop, submitGuess, leaveMatch
    """
    
    async def connect(self):
        self.player_id = self.scope['user'].id if self.scope['user'].is_authenticated else None
        self.match_id = self.scope['url_route']['kwargs']['match_id']
        self.room_group_name = f'game_{self.match_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'submit_guess':
            await self.submit_guess(data)
        elif message_type == 'leave_match':
            await self.leave_match(data)

    async def submit_guess(self, data):
        """Handle player submitting a guess."""
        guess = data.get('guess')
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'guess_submitted',
                'player_id': self.player_id,
                'guess': guess
            }
        )

    async def leave_match(self, data):
        """Handle player leaving the match."""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'player_left',
                'player_id': self.player_id
            }
        )

    async def guess_submitted(self, event):
        """Send guess submission to WebSocket."""
        await self.send(text_data=json.dumps(event))

    async def player_left(self, event):
        """Notify when player leaves."""
        await self.send(text_data=json.dumps({
            'type': 'player_left',
            'player_id': event['player_id']
        }))

    async def game_state_update(self, event):
        """Send game state update to WebSocket."""
        await self.send(text_data=json.dumps(event))

    async def game_ended(self, event):
        """Send game end notification to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'game_ended',
            'winner_id': event['winner_id'],
            'loser_id': event['loser_id']
        }))
