# AI Player Matchmaking Timeout - Implementation Summary

## ✅ Changes Implemented

### 1. Backend Services (`Backend/apps/game/services.py`)

**Changes Made:**

- ✅ Added `import time` for timestamp tracking
- ✅ Updated `add_to_lobby()` to track `'added_at': time.time()` for each player
- ✅ Completely refactored `try_match_players()` with timeout logic:
  - If 2+ players: Pair two humans immediately
  - If 1 player & timeout NOT exceeded: Return None (wait for more)
  - If 1 player & timeout exceeded: Pair with AI opponent

**Key Code Changes:**

```python
# Before:
_lobby_queue.append({
    'player_id': player_id,
    'session_token': session_token,
    'channel_name': channel_name,
})

# After:
_lobby_queue.append({
    'player_id': player_id,
    'session_token': session_token,
    'channel_name': channel_name,
    'added_at': time.time(),  # NEW
})
```

---

### 2. Settings Configuration (`Backend/config/settings/base.py`)

**Changes Made:**

- ✅ Added game settings block at end of file:
  ```python
  # Game Settings
  WORDDUEL_MAX_ROUNDS = env('WORDDUEL_MAX_ROUNDS', default=5, cast=int)
  WORDDUEL_TICK_DURATION_MS = env('WORDDUEL_TICK_DURATION_MS', default=5000, cast=int)
  MATCHMAKING_TIMEOUT_SECONDS = env('MATCHMAKING_TIMEOUT_SECONDS', default=10, cast=int)
  ```

**Environment Variable:**

- Default: `MATCHMAKING_TIMEOUT_SECONDS=10` (10 seconds)
- Configurable via `.env` file

---

### 3. Lobby Consumer (`Backend/apps/game/consumers/lobby.py`)

**Changes Made:**

- ✅ Updated `handle_join_lobby()` to send AI pairing notification after match found
- ✅ Updated `_notify_match_found()` to skip sending to AI player's channel (None)
- ✅ Added AI pairing check with message to user

**Key Code Changes:**

```python
# After match found, check if AI player was paired
if result:
    match, p1_info, p2_info = result
    await self._notify_match_found(match, p1_info, p2_info)

    # Check if AI player was matched
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

**Channel Fix:**

```python
# Only send to player 2 if not AI
if p2_info['channel_name'] is not None:
    await self.channel_layer.send(p2_info['channel_name'], {...})
```

---

### 4. Frontend Socket Handler (`frontend/src/components/game/WordDuel.tsx`)

**Changes Made:**

- ✅ Added `useSocketEvent` listener for `aiPairingNotification`
- ✅ Displays user-friendly warning message
- ✅ Logs AI pairing event for debugging

**Code Added:**

```tsx
useSocketEvent<{ message: string; is_ai_match: boolean }>(
  "aiPairingNotification",
  (p) => {
    setErrorMessage(p.message);
    setErrorVariant("warn");
    console.log("AI Pairing:", p.message);
  },
);
```

---

## 📊 How It Works (Step-by-Step)

### Scenario 1: Two Players (Human vs Human)

1. **Player A** joins lobby → Added to queue with timestamp
2. **Player B** joins lobby → Added to queue with timestamp
3. `try_match_players()` called:
   - Detects 2+ players in queue
   - Pops P1 and P2 immediately
   - Creates human vs human match ✅
   - Returns match to both players
4. **Result:** Both players matched instantly

### Scenario 2: Single Player (Human vs AI after timeout)

1. **Player A** joins lobby → Added with `'added_at': time.time()`
2. `try_match_players()` called:
   - Detects 1 player in queue
   - Checks if timeout exceeded: `(current_time - p1_info['added_at']) >= 10`
   - **NO**: Not yet 10 seconds → Returns None (wait)
   - Player sees "Waiting for opponent..."
3. **10+ seconds pass**, no Player B joins
4. **Next event** (e.g., Player C joins):
   - `try_match_players()` called again
   - Detects Player A has timed out (>= 10 seconds)
   - Creates match with AI_Opponent ✅
   - Sends `aiPairingNotification` to Player A
   - Player sees: "No opponent found. Matched with AI opponent."

---

## 🧪 Testing Checklist

### ✅ Test 1: Human vs Human (No Timeout)

- [ ] Open Browser 1 → Player A joins
- [ ] Open Browser 2 → Player B joins (within 10 seconds)
- [ ] Both should see "Match found" message
- [ ] Check DB: `Match` table has 2 human players
- [ ] `AI_Opponent` was NOT used

### ✅ Test 2: Human vs AI (Timeout Triggered)

- [ ] Open Browser 1 → Player A joins
- [ ] Wait >= 10 seconds (no Player B)
- [ ] Any activity on server (e.g., Player C joins) triggers check
- [ ] Player A should see "Matched with AI opponent"
- [ ] Check DB: `Match` table has Player A + AI_Opponent
- [ ] `is_computer = true` on AI_Opponent row

### ✅ Test 3: Configuration Change

- [ ] Set env: `MATCHMAKING_TIMEOUT_SECONDS=5`
- [ ] Restart Django server
- [ ] Player A joins
- [ ] Wait 5+ seconds
- [ ] Player A gets matched with AI (faster timeout)
- [ ] ✅ Confirms config works

### ✅ Test 4: Race Condition

- [ ] Player A joins (0 seconds)
- [ ] Wait 8 seconds
- [ ] Player B joins (at 8 seconds)
- [ ] Both should match before 10-second timeout
- [ ] ✅ No AI pairing should occur

---

## 📋 Environment Variables

Add to `.env` file in `Backend/` directory:

```bash
# Game Settings
MATCHMAKING_TIMEOUT_SECONDS=10       # Wait 10 seconds before AI pairing
WORDDUEL_MAX_ROUNDS=5                # Matches are best-of-5
WORDDUEL_TICK_DURATION_MS=5000       # Each tick is 5 seconds
```

---

## 🔍 Database Verification

### Check AI Player Exists

```sql
SELECT * FROM player WHERE is_computer = true;
```

**Expected Output:**

```
id | username     | total_wins | total_matches | is_computer | created_at
1  | AI_Opponent  | 0          | 0             | true        | 2026-04-27...
```

### Check Match Types

```sql
-- Human vs Human matches
SELECT m.id, p1.username, p2.username, m.status
FROM match m
JOIN player p1 ON m.player1_id = p1.id
JOIN player p2 ON m.player2_id = p2.id
WHERE p1.is_computer = false AND p2.is_computer = false;

-- Human vs AI matches
SELECT m.id, p1.username, p2.username, m.status
FROM match m
JOIN player p1 ON m.player1_id = p1.id
JOIN player p2 ON m.player2_id = p2.id
WHERE p1.is_computer = true OR p2.is_computer = true;
```

---

## 🐛 Debugging

### Check Queue State (in Django shell)

```python
from apps.game.services import _lobby_queue
import time

for entry in _lobby_queue:
    wait_time = time.time() - entry['added_at']
    print(f"Player {entry['player_id']}: waiting {wait_time:.1f}s")
```

### Enable Logging

```python
# In services.py try_match_players()
print(f"[MATCHMAKING] {len(_lobby_queue)} players in queue")
print(f"[MATCHMAKING] Player {p1_info['player_id']} waited {time_in_queue:.1f}s (timeout: {timeout_seconds}s)")
```

### Test Manual Timeout

```python
# Simulate old queue entry (100 seconds old)
from apps.game.services import _lobby_queue
import time

_lobby_queue.append({
    'player_id': 999,
    'session_token': 'test',
    'channel_name': 'test',
    'added_at': time.time() - 100,  # 100 seconds old
})

# Now call try_match_players() - should pair with AI immediately
```

---

## 📁 Files Modified

1. ✅ `Backend/apps/game/services.py`
   - Added timestamp tracking
   - Implemented timeout checking
   - Refactored `try_match_players()`

2. ✅ `Backend/config/settings/base.py`
   - Added `MATCHMAKING_TIMEOUT_SECONDS` config

3. ✅ `Backend/apps/game/consumers/lobby.py`
   - Updated `handle_join_lobby()`
   - Updated `_notify_match_found()`
   - Added AI pairing notification

4. ✅ `frontend/src/components/game/WordDuel.tsx`
   - Added AI pairing notification listener

---

## 🚀 Deployment Checklist

- [ ] Code reviewed and tested locally
- [ ] All 4 test scenarios passed
- [ ] Database migration (if any) applied
- [ ] Environment variables set in production
- [ ] Monitored first 24 hours for AI pairing events
- [ ] Confirmed no AI player sessions created until after 10 seconds

---

## 📈 Future Enhancements

1. **Progressive Notifications**
   - Notify player at 5s: "Still searching..."
   - Notify player at 8s: "Searching for 2 more seconds..."
   - Pair at 10s: "Matching with AI..."

2. **Skill-Based AI**
   - Match AI difficulty to player skill level
   - Easy AI for new players
   - Hard AI for experienced players

3. **Player Preferences**
   - Option to "Prefer human opponents"
   - Longer wait time if selected

4. **Dynamic Timeout**
   - Reduce timeout if many players online
   - Increase timeout if few players online

5. **Analytics**
   - Track AI vs human match ratio
   - Measure average wait time
   - Identify peak hours

---

## 📞 Support

**Issues?**

1. Check implementation guide: `AI_TIMEOUT_IMPLEMENTATION_GUIDE.md`
2. Review test cases above
3. Check database state
4. Verify environment variables set correctly
5. Check server logs for timestamp tracking messages
