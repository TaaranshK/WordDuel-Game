# Postman AI Bot Prompt - WisFlux Application API Testing

## Base URL

```
http://localhost:8000/api/
```

## Testing Flow & Payloads

### STEP 1: Account Management - Join/Create Player

**1.1 Join as Player 1**

- **Method:** POST
- **URL:** `http://localhost:8000/api/accounts/join/`
- **Headers:**
  - `Content-Type: application/json`
- **Body (JSON):**

```json
{
  "username": "Alice"
}
```

- **Expected Response (200):**

```json
{
  "player": {
    "id": 1,
    "username": "Alice",
    "total_wins": 0,
    "total_matches": 0,
    "created_at": "2026-04-27T10:30:00Z"
  },
  "session_token": "token_alice_xyz"
}
```

**1.2 Join as Player 2**

- **Method:** POST
- **URL:** `http://localhost:8000/api/accounts/join/`
- **Headers:**
  - `Content-Type: application/json`
- **Body (JSON):**

```json
{
  "username": "Bob"
}
```

- **Expected Response (200):**

```json
{
  "player": {
    "id": 2,
    "username": "Bob",
    "total_wins": 0,
    "total_matches": 0,
    "created_at": "2026-04-27T10:31:00Z"
  },
  "session_token": "token_bob_xyz"
}
```

---

### STEP 2: Dictionary Management

**2.1 Get Available Words**

- **Method:** GET
- **URL:** `http://localhost:8000/api/dictionary/words/`
- **Optional Query Params:**
  - `difficulty=easy` (or `medium`, `hard`)
  - `length=5`
- **Example:** `http://localhost:8000/api/dictionary/words/?difficulty=easy&length=5`
- **Expected Response (200):**

```json
[
  {
    "id": 1,
    "word": "APPLE",
    "word_length": 5,
    "difficulty": "easy",
    "is_active": true
  },
  {
    "id": 2,
    "word": "OCEAN",
    "word_length": 5,
    "difficulty": "easy",
    "is_active": true
  }
]
```

**2.2 Add New Word to Dictionary**

- **Method:** POST
- **URL:** `http://localhost:8000/api/dictionary/words/add/`
- **Headers:**
  - `Content-Type: application/json`
- **Body (JSON):**

```json
{
  "word": "PROGRAMMER"
}
```

- **Expected Response (201):**

```json
{
  "id": 10,
  "word": "PROGRAMMER",
  "word_length": 10,
  "difficulty": "hard",
  "is_active": true
}
```

**2.3 Get Dictionary Stats**

- **Method:** GET
- **URL:** `http://localhost:8000/api/dictionary/stats/`
- **Expected Response (200):**

```json
{
  "total_active": 50,
  "easy": 15,
  "medium": 20,
  "hard": 15
}
```

**2.4 Toggle Word Active Status**

- **Method:** PATCH
- **URL:** `http://localhost:8000/api/dictionary/words/<word_id>/toggle/`
- **Example:** `http://localhost:8000/api/dictionary/words/1/toggle/`
- **Expected Response (200):**

```json
{
  "id": 1,
  "word": "APPLE",
  "word_length": 5,
  "difficulty": "easy",
  "is_active": false
}
```

---

### STEP 3: Player Information

**3.1 Get Player Details**

- **Method:** GET
- **URL:** `http://localhost:8000/api/accounts/player/<player_id>/`
- **Example:** `http://localhost:8000/api/accounts/player/1/`
- **Expected Response (200):**

```json
{
  "id": 1,
  "username": "Alice",
  "total_wins": 3,
  "total_matches": 5,
  "created_at": "2026-04-27T10:30:00Z"
}
```

**3.2 Get Leaderboard (Top 10 Players)**

- **Method:** GET
- **URL:** `http://localhost:8000/api/accounts/leaderboard/`
- **Expected Response (200):**

```json
[
  {
    "id": 5,
    "username": "Champion",
    "total_wins": 50,
    "total_matches": 60
  },
  {
    "id": 3,
    "username": "Pro",
    "total_wins": 40,
    "total_matches": 55
  },
  {
    "id": 1,
    "username": "Alice",
    "total_wins": 3,
    "total_matches": 5
  }
]
```

---

### STEP 4: Game Information

**4.1 Get Match Details**

- **Method:** GET
- **URL:** `http://localhost:8000/api/game/match/<match_id>/`
- **Example:** `http://localhost:8000/api/game/match/1/`
- **Expected Response (200):**

```json
{
  "id": 1,
  "player1_id": 1,
  "player1_username": "Alice",
  "player2_id": 2,
  "player2_username": "Bob",
  "player1_score": 2,
  "player2_score": 1,
  "status": "in_progress",
  "winner_id": null,
  "created_at": "2026-04-27T10:35:00Z"
}
```

**4.2 Get Match Rounds**

- **Method:** GET
- **URL:** `http://localhost:8000/api/game/match/<match_id>/rounds/`
- **Example:** `http://localhost:8000/api/game/match/1/rounds/`
- **Expected Response (200):**

```json
[
  {
    "id": 1,
    "match_id": 1,
    "round_number": 1,
    "word": "APPLE",
    "winner_id": 1,
    "reveal_state": ["A", "P", "P", "L", "E"],
    "status": "completed"
  },
  {
    "id": 2,
    "match_id": 1,
    "round_number": 2,
    "word": "PYTHON",
    "winner_id": null,
    "reveal_state": ["P", null, null, "H", null, "N"],
    "status": "in_progress"
  }
]
```

**4.3 Get Player Match History**

- **Method:** GET
- **URL:** `http://localhost:8000/api/game/match/history/<player_id>/`
- **Example:** `http://localhost:8000/api/game/match/history/1/`
- **Expected Response (200):**

```json
[
  {
    "id": 1,
    "opponent_username": "Bob",
    "player_score": 2,
    "opponent_score": 1,
    "result": "win",
    "completed_at": "2026-04-27T10:40:00Z"
  },
  {
    "id": 2,
    "opponent_username": "Charlie",
    "player_score": 1,
    "opponent_score": 2,
    "result": "loss",
    "completed_at": "2026-04-27T10:50:00Z"
  }
]
```

**4.4 Get Active Match for Player**

- **Method:** GET
- **URL:** `http://localhost:8000/api/game/match/active/<player_id>/`
- **Example:** `http://localhost:8000/api/game/match/active/1/`
- **Expected Response (200):**

```json
{
  "id": 3,
  "player1_id": 1,
  "player1_username": "Alice",
  "player2_id": 4,
  "player2_username": "Diana",
  "player1_score": 0,
  "player2_score": 0,
  "status": "in_progress",
  "current_round": 1
}
```

---

## WebSocket Testing (For Real-Time Game)

### WebSocket Connection

- **URL:** `ws://localhost:8000/ws/wordduel/`

### Client → Server Events & Payloads

**Event 1: Join Lobby**

```json
{
  "event": "joinLobby",
  "payload": {
    "username": "Alice"
  }
}
```

**Event 2: Submit Guess**

```json
{
  "event": "submitGuess",
  "payload": {
    "guessText": "APPLE",
    "clientSentAt": 1714216200000
  }
}
```

**Event 3: Leave Match (Optional)**

```json
{
  "event": "leaveMatch",
  "payload": {}
}
```

### Server → Client Events (Expected Responses)

**Response 1: Match Found**

```json
{
  "event": "matchFound",
  "payload": {
    "matchId": 1,
    "opponentUsername": "Bob",
    "scores": {
      "me": 0,
      "opponent": 0
    }
  }
}
```

**Response 2: Start Round**

```json
{
  "event": "startRound",
  "payload": {
    "roundId": 1,
    "roundNumber": 1,
    "wordLength": 5,
    "scores": {
      "me": 0,
      "opponent": 0
    }
  }
}
```

**Response 3: Tick Start (Timer & Reveal State)**

```json
{
  "event": "tickStart",
  "payload": {
    "tickNumber": 1,
    "deadline": 1714216210000,
    "revealedState": [null, null, null, null, null]
  }
}
```

**Response 4: Reveal Tile (Letter Revealed)**

```json
{
  "event": "revealTile",
  "payload": {
    "index": 0,
    "letter": "A",
    "revealedState": ["A", null, null, null, null]
  }
}
```

**Response 5: Opponent Guessed**

```json
{
  "event": "opponentGuessed",
  "payload": {
    "tickNumber": 2
  }
}
```

**Response 6: Round End**

```json
{
  "event": "roundEnd",
  "payload": {
    "winner": "me",
    "revealedWord": "APPLE",
    "scores": {
      "me": 1,
      "opponent": 0
    },
    "isDraw": false
  }
}
```

**Response 7: Match End**

```json
{
  "event": "matchEnd",
  "payload": {
    "winner": "me",
    "finalScores": {
      "me": 2,
      "opponent": 1
    },
    "totalRounds": 3
  }
}
```

**Response 8: Error (If Any)**

```json
{
  "event": "error",
  "payload": {
    "code": "INVALID_GUESS",
    "message": "Guess text is empty or invalid"
  }
}
```

---

## Testing Sequence Recommendation

1. **Join Players** → Create 2 players (Step 1)
2. **Setup Dictionary** → Add words and verify stats (Step 2)
3. **Get Player Info** → Verify player data and leaderboard (Step 3)
4. **Game Testing** → Use REST to get game info (Step 4)
5. **Real-Time Testing** → Connect via WebSocket and simulate game flow

## Notes

- All timestamps are Unix milliseconds
- Case-insensitive for usernames
- Dictionary words are stored as UPPERCASE
- Difficulty is auto-inferred: easy (2-4 chars), medium (5-7 chars), hard (8+ chars)
- Auth is disabled in dev mode (AllowAny)
