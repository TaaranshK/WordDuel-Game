# AI Player Matchmaking Timeout - Complete Implementation Guide

## 📋 Current Architecture Analysis

### Current Flow

1. **Lobby Entry** → Player joins WebSocket and enters `_lobby_queue`
2. **Immediate Matching** → If 1+ player in queue, `try_match_players()` is called
3. **AI Pairing** → Currently pairs with AI **immediately** if only 1 player
4. **Problem** → No wait/threshold before AI pairing

### Issues with Current Implementation

- ❌ No timestamp tracking on queue entries
- ❌ Pairing with AI happens immediately (no threshold)
- ❌ Player has no wait time for human opponent
- ❌ No background task checking for timeouts

---

## ✅ Proposed Solution Architecture

### 1. **Queue Entry Structure Enhancement**

```python
# Current (lacks timestamp)
_lobby_queue = [
    {'player_id': 1, 'session_token': 'xyz', 'channel_name': 'ch1'}
]

# Proposed (with timestamp tracking)
_lobby_queue = [
    {
        'player_id': 1,
        'session_token': 'xyz',
        'channel_name': 'ch1',
        'added_at': time.time()  # ← NEW: Track when player joined
    }
]
```

### 2. **Settings Configuration**

Add to `config/settings/base.py`:

```python
# Matchmaking timeout (seconds before AI pairing)
MATCHMAKING_TIMEOUT_SECONDS = env('MATCHMAKING_TIMEOUT_SECONDS', default=10, cast=int)
```

### 3. **Timeout Checking Logic**

Two approaches:

#### Option A: **Polling-Based** (Simpler)

- Call `check_matchmaking_timeouts()` periodically (recommended)
- Called from lobby consumer when player joins
- Pros: Simple, no background tasks needed
- Cons: Small latency variance

#### Option B: **Background Task-Based** (Advanced)

- Uses asyncio tasks to monitor queue
- Automatically triggers every N seconds
- Pros: Precise timing
- Cons: More complex, resource overhead

**Recommendation: Use Option A** (polling) for your project

---

## 🔧 Implementation Steps

### Step 1: Update Services (`apps/game/services.py`)

**Changes:**

```python
import time

# Update add_to_lobby to track timestamp
def add_to_lobby(player_id: int, session_token: str, channel_name: str) -> None:
    """Add player to the matchmaking queue with timestamp."""
    # prevent duplicate entries
    _lobby_queue[:] = [p for p in _lobby_queue if p['player_id'] != player_id]
    _lobby_queue.append({
        'player_id': player_id,
        'session_token': session_token,
        'channel_name': channel_name,
        'added_at': time.time(),  # ← NEW: Timestamp
    })

# NEW FUNCTION: Check for timeout and pair with AI
def check_matchmaking_timeouts(timeout_seconds: int = 10) -> tuple | None:
    """
    Check if first player in queue has exceeded timeout.
    If yes, pair with AI. Otherwise, return None.
    """
    import time
    from django.conf import settings

    if len(_lobby_queue) != 1:
        return None

    p1_info = _lobby_queue[0]
    current_time = time.time()
    time_in_queue = current_time - p1_info['added_at']

    # If timeout exceeded, pair with AI
    if time_in_queue >= timeout_seconds:
        _lobby_queue.pop(0)

        player1 = Player.objects.get(id=p1_info['player_id'])
        ai_player = create_or_get_ai_player()

        match = Match.objects.create(
            player1=player1,
            player2=ai_player,
        )

        _active_matches[match.id] = {
            'player1_id': player1.id,
            'player2_id': ai_player.id,
            'guessed': set(),
            'correct': set(),
            'tick_task': None,
            'used_words': [],
            'round_end_event': None,
            'ai_player_id': ai_player.id,
        }

        p2_info = {
            'player_id': ai_player.id,
            'session_token': 'ai_token',
            'channel_name': None,
        }

        return match, p1_info, p2_info

    return None

# Update try_match_players
def try_match_players() -> tuple | None:
    """
    Attempt to match players:
    1. If 2+ players, match two humans
    2. If 1 player and timeout NOT exceeded, return None (wait for more)
    3. If 1 player and timeout exceeded, pair with AI
    """
    # Match two human players if available
    if len(_lobby_queue) >= 2:
        p1_info = _lobby_queue.pop(0)
        p2_info = _lobby_queue.pop(0)

        player1 = Player.objects.get(id=p1_info['player_id'])
        player2 = Player.objects.get(id=p2_info['player_id'])

        match = Match.objects.create(player1=player1, player2=player2)

        _active_matches[match.id] = {
            'player1_id': player1.id,
            'player2_id': player2.id,
            'guessed': set(),
            'correct': set(),
            'tick_task': None,
            'used_words': [],
            'round_end_event': None,
            'ai_player_id': None,
        }

        return match, p1_info, p2_info

    # Check if single player has timed out
    timeout_seconds = int(getattr(
        __import__('django.conf', fromlist=['settings']).settings,
        'MATCHMAKING_TIMEOUT_SECONDS',
        10
    ))
    return check_matchmaking_timeouts(timeout_seconds)
```

### Step 2: Update Settings (`config/settings/base.py`)

Add at end of file:

```python
# Game Settings
WORDDUEL_MAX_ROUNDS = env('WORDDUEL_MAX_ROUNDS', default=5, cast=int)
WORDDUEL_TICK_DURATION_MS = env('WORDDUEL_TICK_DURATION_MS', default=5000, cast=int)
MATCHMAKING_TIMEOUT_SECONDS = env('MATCHMAKING_TIMEOUT_SECONDS', default=10, cast=int)
```

### Step 3: Update Lobby Consumer (`apps/game/consumers/lobby.py`)

Replace the matchmaking call:

```python
# OLD CODE (in handle_join_lobby):
result = try_match_players()
if result:
    match, p1_info, p2_info = result
    await self._notify_match_found(match, p1_info, p2_info)

# NEW CODE:
result = try_match_players()
if result:
    match, p1_info, p2_info = result
    await self._notify_match_found(match, p1_info, p2_info)
    if _active_matches[match.id].get('ai_player_id'):
        await self._notify_ai_pairing(match, p1_info)

# NEW HELPER METHOD:
async def _notify_ai_pairing(self, match, p1_info):
    """Notify player that they're matched with AI due to timeout."""
    await self.channel_layer.send(p1_info['channel_name'], {
        'type': 'lobby.ai_pairing_notification',
        'message': 'No human opponent found. Matched with AI opponent.',
        'is_ai_match': True,
    })

async def lobby_ai_pairing_notification(self, event):
    """Send AI pairing notification to client."""
    await self.send_json({
        'type': 'aiPairingNotification',
        'message': event['message'],
        'is_ai_match': True,
    })
```

### Step 4: Update Frontend (Optional - User Feedback)

In `src/components/game/LobbyScreen.tsx` or game component:

```tsx
// Listen for AI pairing notification
socket.on("aiPairingNotification", (payload) => {
  console.log("Matched with AI:", payload.message);
  // Show toast or modal: "No opponent found, playing vs AI..."
});
```

---

## ⚙️ Configuration Options

### Environment Variables (`.env`)

```bash
# Matchmaking timeout before AI pairing (default: 10 seconds)
MATCHMAKING_TIMEOUT_SECONDS=10

# Other game settings
WORDDUEL_MAX_ROUNDS=5
WORDDUEL_TICK_DURATION_MS=5000
```

### Timeout Values by Use Case

- **10 seconds** - Balanced (recommended for production)
- **5 seconds** - Aggressive (quick AI pairing, less waiting)
- **20-30 seconds** - Patient (more wait time for human opponent)

---

## 🧪 Testing the Feature

### Test Case 1: Human vs Human Match

1. Open 2 browser tabs
2. Player A enters lobby
3. Wait < 10 seconds
4. Player B enters lobby
5. ✅ Both should match with each other

### Test Case 2: Human vs AI Match (Timeout)

1. Open 1 browser tab
2. Player A enters lobby
3. Wait ≥ 10 seconds (no Player B)
4. ✅ Player A should be matched with "AI_Opponent"
5. Check frontend for AI pairing notification

### Test Case 3: Race Condition

1. Open 2 browser tabs
2. Player A enters lobby (queue: 1)
3. Wait 9 seconds
4. Player B enters lobby (queue: 2)
5. ✅ Both should match before timeout triggers
6. No AI pairing should occur

---

## 📊 Database Checks

### Verify AI Player Created

```sql
SELECT * FROM player WHERE is_computer = true;
-- Should return: AI_Opponent
```

### Check Match Types

```sql
-- Human vs Human matches
SELECT m.id, p1.username AS player1, p2.username AS player2
FROM match m
JOIN player p1 ON m.player1_id = p1.id
JOIN player p2 ON m.player2_id = p2.id
WHERE p1.is_computer = false AND p2.is_computer = false;

-- Human vs AI matches
SELECT m.id, p1.username AS player1, p2.username AS player2
FROM match m
JOIN player p1 ON m.player1_id = p1.id
JOIN player p2 ON m.player2_id = p2.id
WHERE p1.is_computer = true OR p2.is_computer = true;
```

---

## 🚀 Advanced Features (Optional Future)

### 1. Progressive Wait Time

```python
# Notify player of wait time
WAIT_NOTIFICATIONS = {
    5: "Still searching for opponent...",
    8: "Searching for 2 more seconds...",
    10: "Pairing with AI opponent...",
}
```

### 2. Player Preferences

```python
# Allow players to opt-out of AI
# Add to Player model: prefer_humans_only (BooleanField)
if player.prefer_humans_only and time_in_queue < 30:
    continue_waiting()  # Wait longer
else:
    pair_with_ai()
```

### 3. Skill-Based AI Selection

```python
# Match AI difficulty to player skill
if player.total_wins > 50:
    ai_player = create_hard_ai()
elif player.total_wins > 20:
    ai_player = create_medium_ai()
else:
    ai_player = create_easy_ai()
```

### 4. Dynamic Timeout

```python
# Adjust timeout based on player count
if Player.objects.filter(last_seen_at__gte=timezone.now()-timedelta(minutes=5)).count() > 100:
    MATCHMAKING_TIMEOUT_SECONDS = 5  # More players = faster timeout
else:
    MATCHMAKING_TIMEOUT_SECONDS = 15  # Fewer players = wait longer
```

---

## 📝 File Summary

### Files to Modify

1. ✏️ `Backend/apps/game/services.py` - Add timeout checking logic
2. ✏️ `Backend/config/settings/base.py` - Add timeout configuration
3. ✏️ `Backend/apps/game/consumers/lobby.py` - Update notification flow
4. ✏️ `frontend/src/game/socket.tsx` - Add AI notification listener (optional)

### Files Already Prepared

- ✅ `Backend/apps/accounts/models.py` - Has `is_computer` flag
- ✅ `Backend/apps/accounts/services.py` - Has `create_or_get_ai_player()`
- ✅ `Backend/apps/game/models.py` - Match model ready

---

## 🔍 Debugging Tips

### Check Queue State

```python
# In Django shell or logger
from apps.game.services import _lobby_queue
print(f"Queue size: {len(_lobby_queue)}")
for entry in _lobby_queue:
    import time
    print(f"Player {entry['player_id']}, Wait time: {time.time() - entry['added_at']:.1f}s")
```

### Monitor AI Matches

```python
# Check if AI player is being used
from apps.accounts.models import Player
ai = Player.objects.get(username='AI_Opponent')
print(f"AI matches: {ai.matches_as_player1.count() + ai.matches_as_player2.count()}")
```

### Test Timestamp Logic

```python
import time

# Simulate 11-second queue time
entry = {
    'added_at': time.time() - 11,
    'player_id': 1,
}
current_time = time.time()
print(f"Time in queue: {current_time - entry['added_at']:.1f}s")
print(f"Timed out: {(current_time - entry['added_at']) >= 10}")
```

---

## Summary

**Key Changes:**

- ⏱️ Track when player joins queue using `time.time()`
- ⏱️ Check timeout in `try_match_players()` before AI pairing
- ⚙️ Add `MATCHMAKING_TIMEOUT_SECONDS` to settings
- 📢 Notify players about AI pairing via WebSocket
- 🎯 Fallback to AI only after timeout threshold

**Benefits:**

- ✅ Players wait for human opponent (better UX)
- ✅ Configurable timeout (production ready)
- ✅ No background tasks (simpler deployment)
- ✅ Backward compatible with existing code
