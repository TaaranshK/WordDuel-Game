# Testing AI Fallback Implementation

## Scenario 1: Immediate Human Match

1. Open frontend in two browser windows
2. Player 1 enters username "Alice" → joins lobby (queue size = 1, waiting)
3. Player 2 enters username "Bob" → joins lobby → **immediate match**
4. Both see matchFound with opponent username
5. Game proceeds normally

## Scenario 2: AI Fallback After Timeout

1. Set `MATCHMAKING_TIMEOUT_SECONDS=5` in Django settings (.env)
2. Player 1 enters username "Alice" → joins lobby (queue size = 1)
3. Wait 5 seconds
4. Player 1 receives matchFound with opponent="AI_Opponent" and `isAiMatch=true`
5. Frontend displays: "Matched with AI opponent: AI_Opponent"
6. Game proceeds against AI

## Expected Backend Flow

### In `WordDuelConsumer._handle_join_lobby()`:

```
Join Lobby Message Received
  ↓
Add player to _LOBBY_QUEUE
  ↓
  ├─ If 2+ players in queue:
  │  ├─ Pop two entries (p1, p2)
  │  ├─ Create Match in DB
  │  ├─ Send matchFound to both players
  │  ├─ Start game loop
  │  └─ Return
  │
  └─ If 1 player in queue:
     ├─ Start background task: _run_timeout_matchmaking()
     └─ Return immediately
```

### In `_run_timeout_matchmaking()` (Background Task):

```
Loop every 1 second for up to MATCHMAKING_TIMEOUT_SECONDS:
  ├─ Check if player still in queue
  ├─ Check if timeout reached
  │  ├─ If yes → Call _match_with_ai()
  │  └─ If no → Continue looping
  └─ If player removed (matched elsewhere) → Exit task
```

### In `_match_with_ai()`:

```
Create AI Player (or fetch existing)
  ↓
Create Match in DB (human vs AI)
  ↓
Create MatchState in memory
  ↓
Add human player to group
  ↓
Send matchFound to human player (with isAiMatch=true)
  ↓
Start game loop (_run_match)
```

## Frontend Behavior

### matchFound Handler:

- If `isAiMatch=true`:
  - Display warning: `"Matched with AI opponent: AI_Opponent"`
  - Show in error message panel
- Either way, transition to "matchFound" phase

### During Game:

- Game proceeds normally
- AI opponent is a regular Player in DB with `is_computer=True`
- All game mechanics (scoring, rounds, etc.) work as normal

## Configuration

### Django Setting (in `config/settings/base.py` or `.env`):

```
MATCHMAKING_TIMEOUT_SECONDS=10  # Default value
```

To test quickly, override in `.env`:

```
MATCHMAKING_TIMEOUT_SECONDS=5
```

## Cleanup

The implementation includes proper task cancellation:

- When a player disconnects, `_remove_from_lobby()` cancels the background task
- This prevents orphaned tasks from trying to create AI matches

## Debug Output

Expected logs in Django console:

```
[MATCHMAKING] 1 player in queue - waiting 0.5s / 10s timeout
[MATCHMAKING] 1 player in queue - waiting 1.5s / 10s timeout
...
[MATCHMAKING] 1 player in queue - waiting 10.0s / 10s timeout
[MATCHMAKING] TIMEOUT! Pairing with AI
[MATCHMAKING] AI match created: 123 - Alice vs AI_Opponent
```
