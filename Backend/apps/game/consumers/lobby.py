import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer


class LobbyConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for game lobby.
    Handles: joinLobby, matchmaking, matchFound
    """
    
    async def connect(self):
        self.player_id = self.scope['user'].id if self.scope['user'].is_authenticated else None
        self.room_group_name = 'lobby'
        
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

        if message_type == 'join_lobby':
            await self.join_lobby(data)
        elif message_type == 'leave_lobby':
            await self.leave_lobby(data)

    async def join_lobby(self, data):
        """Handle player joining the lobby."""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'lobby_update',
                'player_id': self.player_id,
                'action': 'joined'
            }
        )

    async def leave_lobby(self, data):
        """Handle player leaving the lobby."""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'lobby_update',
                'player_id': self.player_id,
                'action': 'left'
            }
        )

    async def lobby_update(self, event):
        """Send lobby update to WebSocket."""
        await self.send(text_data=json.dumps(event))

    async def match_found(self, event):
        """Send match found notification to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'match_found',
            'match_id': event['match_id'],
            'opponent_id': event['opponent_id']
        }))
