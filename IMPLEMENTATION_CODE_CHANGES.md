# AI Player Timeout - Complete Code Changes Reference

## Overview

This document shows all exact code changes made to implement AI player matchmaking timeout.

---

## 1️⃣ Backend/apps/game/services.py

### Change 1.1: Import Time Module

**Location:** Top of file (line 1-6)

```python
# BEFORE:
import asyncio
import random
from datetime import timedelta
from django.utils import timezone
from django.db import DatabaseError

# AFTER:
import asyncio
import random
import time  # ← NEW
from datetime import timedelta
from django.utils import timezone
from django.db import DatabaseError
```

---

### Change 1.2: Update add_to_lobby() Function

**Location:** Line ~52

```python
# BEFORE:
def add_to_lobby(player_id: int, session_token: str, channel_name: str) -> None:
    """Add player to the matchmaking queue."""
    # prevent duplicate entries
    _lobby_queue[:] = [p for p in _lobby_queue if p['player_id'] != player_id]
    _lobby_queue.append({
        'player_id':    player_id,
        'session_token': session_token,
        'channel_name': channel_name,
    })

# AFTER:
def add_to_lobby(player_id: int, session_token: str, channel_name: str) -> None:
    """Add player to the matchmaking queue with timestamp tracking."""
    # prevent duplicate entries
    _lobby_queue[:] = [p for p in _lobby_queue if p['player_id'] != player_id]
    _lobby_queue.append({
        'player_id':    player_id,
        'session_token': session_token,
        'channel_name': channel_name,
        'added_at': time.time(),  # Track when player joined queue ← NEW
    })
```

---

### Change 1.3: Refactor try_match_players() Function

**Location:** Line ~65-125

```python
# BEFORE:
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

# AFTER:
def try_match_players() -> tuple | None:
    """
    Attempt to match players:
    1. If 2+ players, match two humans
    2. If 1 player and timeout NOT exceeded, return None (wait for more)
    3. If 1 player and timeout exceeded, pair with AI

    Returns (match, p1_info, p2_info) or None.
    """
    from django.conf import settings  # ← NEW

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

    # ← NEW: Single player in queue? Check if timeout exceeded
    if len(_lobby_queue) == 1:
        timeout_seconds = int(getattr(
            settings,
            'MATCHMAKING_TIMEOUT_SECONDS',
            10
        ))

        p1_info = _lobby_queue[0]
        current_time = time.time()
        time_in_queue = current_time - p1_info['added_at']

        # ← NEW: If timeout NOT exceeded, wait for more players
        if time_in_queue < timeout_seconds:
            return None

        # ← NEW: Timeout exceeded! Pair with AI
        from apps.accounts.services import create_or_get_ai_player

        _lobby_queue.pop(0)
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
```

---

## 2️⃣ Backend/config/settings/base.py

### Change 2.1: Add Game Settings

**Location:** End of file (after JWT Configuration)

```python
# BEFORE: (ends with JWT Configuration)
JWT_SECRET = env('JWT_SECRET', default='your-jwt-secret-key')
JWT_ALGORITHM = env('JWT_ALGORITHM', default='HS256')
JWT_EXPIRATION_HOURS = env('JWT_EXPIRATION_HOURS', default=24, cast=int)

# AFTER: (added game settings)
JWT_SECRET = env('JWT_SECRET', default='your-jwt-secret-key')
JWT_ALGORITHM = env('JWT_ALGORITHM', default='HS256')
JWT_EXPIRATION_HOURS = env('JWT_EXPIRATION_HOURS', default=24, cast=int)

# Game Settings ← NEW SECTION
WORDDUEL_MAX_ROUNDS = env('WORDDUEL_MAX_ROUNDS', default=5, cast=int)
WORDDUEL_TICK_DURATION_MS = env('WORDDUEL_TICK_DURATION_MS', default=5000, cast=int)
MATCHMAKING_TIMEOUT_SECONDS = env('MATCHMAKING_TIMEOUT_SECONDS', default=10, cast=int)
```

---

## 3️⃣ Backend/apps/game/consumers/lobby.py

### Change 3.1: Add AI Pairing Notification to handle_join_lobby()

**Location:** Inside `handle_join_lobby()` method, after `_notify_match_found()` call (around line 125)

```python
# BEFORE:
        # --- try to pair players ---
        result = try_match_players()

        if result:
            match, p1_info, p2_info = result
            await self._notify_match_found(match, p1_info, p2_info)

# AFTER:
        # --- try to pair players ---
        result = try_match_players()

        if result:
            match, p1_info, p2_info = result
            await self._notify_match_found(match, p1_info, p2_info)

            # ← NEW: Check if AI player was matched
            from game.services import _active_matches
            match_state = _active_matches.get(match.id, {})
            if match_state.get('ai_player_id'):
                await self.send_json({
                    'type': 'aiPairingNotification',
                    'message': 'No opponent found. Matched with AI opponent.',
                    'opponent_username': 'AI_Opponent',
                    'is_ai_match': True,
                })
```

---

### Change 3.2: Update \_notify_match_found() to Handle AI Player

**Location:** `_notify_match_found()` method (around line 138)

```python
# BEFORE:
    async def _notify_match_found(self, match, p1_info, p2_info):
        """Send matchFound event to both players via their channel names."""
        from accounts.models import Player

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

        # notify player 2
        await self.channel_layer.send(p2_info['channel_name'], {
            'type':              'lobby.match_found',
            'match_id':          match.id,
            'opponent_username': player1.username,
            'your_player_id':    player2.id,
            'session_token':     p2_info['session_token'],
        })

# AFTER:
    async def _notify_match_found(self, match, p1_info, p2_info):
        """Send matchFound event to both players via their channel names."""
        from accounts.models import Player

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

        # ← NEW: notify player 2 (skip if AI player - no channel)
        if p2_info['channel_name'] is not None:
            await self.channel_layer.send(p2_info['channel_name'], {
                'type':              'lobby.match_found',
                'match_id':          match.id,
                'opponent_username': player1.username,
                'your_player_id':    player2.id,
                'session_token':     p2_info['session_token'],
            })
```

---

## 4️⃣ frontend/src/components/game/WordDuel.tsx

### Change 4.1: Add AI Pairing Notification Handler

**Location:** In `WordDuel()` component, after the `matchFound` event handler (around line 85-92)

```typescript
// BEFORE:
useSocketEvent<{
  opponentUsername: string;
  scores: { me: number; opponent: number };
}>("matchFound", (p) => {
  setOpponentUsername(p.opponentUsername);
  setScores(p.scores);
  setRoundNumber(0);
  setMatchEnd(null);
  setPhase("matchFound");
});

useSocketEvent<{
  roundNumber: number;
  wordLength: number;
  scores: { me: number; opponent: number };
}>("startRound", (p) => {
  // ...
});

// AFTER:
useSocketEvent<{
  opponentUsername: string;
  scores: { me: number; opponent: number };
}>("matchFound", (p) => {
  setOpponentUsername(p.opponentUsername);
  setScores(p.scores);
  setRoundNumber(0);
  setMatchEnd(null);
  setPhase("matchFound");
});

// ← NEW: Handle AI pairing notification
useSocketEvent<{ message: string; is_ai_match: boolean }>(
  "aiPairingNotification",
  (p) => {
    setErrorMessage(p.message);
    setErrorVariant("warn");
    console.log("AI Pairing:", p.message);
  },
);

useSocketEvent<{
  roundNumber: number;
  wordLength: number;
  scores: { me: number; opponent: number };
}>("startRound", (p) => {
  // ...
});
```

---

## 📋 Summary of Changes

| File                                        | Changes   | Purpose                               |
| ------------------------------------------- | --------- | ------------------------------------- |
| `Backend/apps/game/services.py`             | 3 changes | Timestamp tracking & timeout logic    |
| `Backend/config/settings/base.py`           | 1 change  | Configuration for timeout duration    |
| `Backend/apps/game/consumers/lobby.py`      | 2 changes | AI notification & handle None channel |
| `frontend/src/components/game/WordDuel.tsx` | 1 change  | Display AI pairing notification       |

---

## ✅ Verification Checklist

- [ ] All 4 files modified correctly
- [ ] No syntax errors in Python files
- [ ] No TypeScript errors in frontend
- [ ] `time` module imported in services.py
- [ ] `django.conf.settings` imported where needed
- [ ] AI pairing notification sent to client
- [ ] None channel handled in lobby consumer
- [ ] Frontend displays warning message

---

## 🚀 Deployment Steps

1. **Update Backend Code:**

   ```bash
   cd Backend
   git add apps/game/services.py config/settings/base.py apps/game/consumers/lobby.py
   git commit -m "feat: add AI player matchmaking timeout"
   ```

2. **Update Frontend Code:**

   ```bash
   cd frontend
   git add src/components/game/WordDuel.tsx
   git commit -m "feat: handle AI pairing notification"
   ```

3. **Restart Django:**

   ```bash
   python manage.py runserver
   ```

4. **Test Locally:**
   - Follow testing scenarios in `AI_TIMEOUT_IMPLEMENTATION_SUMMARY.md`

---

## 💡 Key Points

1. **Timestamp tracking** happens in `add_to_lobby()` - no DB changes needed
2. **Timeout check** only runs in `try_match_players()` - efficient
3. **Configuration** via environment variable - easily tunable
4. **AI channel is None** - prevents errors when sending WebSocket messages
5. **User feedback** via `aiPairingNotification` event - good UX
