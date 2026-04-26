# API Map (Backend)

## Stack

- Framework: Django 4.2 + Django REST Framework
- Realtime: Django Channels (WebSocket)
- Dev DB: SQLite (see `config/settings/dev.py`)

## Auth

- Dev (`config/settings/dev.py`): APIs are open (`AllowAny`, no auth) for local integration.
- JWT helper exists in `apps/accounts/utils.py` but is not required for the current frontend flow.

## Models (Relationships)

- `accounts.Player`
  - `username` (unique), `total_wins`, `total_matches`, timestamps
- `dictionary.Dictionary`
  - `word` (unique), `word_length`, `difficulty`, `is_active`
- `game.Match`
  - `player1` → `Player`, `player2` → `Player`, scores, status, `winner` → `Player`
- `game.Round`
  - `match` → `Match`, `winner` → `Player` (nullable), reveal state, status
- `game.Guess`
  - `round` → `Round`, `player` → `Player`, `guess_text`, `is_correct`, timestamps
- `game.PlayerSession`
  - `player` → `Player`, optional `match` → `Match`, `session_token`, connection timestamps

## REST APIs

Base prefix is `"/api/"`.

### Accounts

- `POST /api/accounts/join/`
  - Body: `{ "username": "Alice" }`
  - Response `200`: `{ "player": { ... }, "session_token": "..." }`
- `GET /api/accounts/player/<player_id>/`
  - Response `200`: player object
- `GET /api/accounts/leaderboard/`
  - Response `200`: list of top 10 players (ordered by wins, then matches)

### Dictionary

- `GET /api/dictionary/words/`
  - Optional query params:
    - `difficulty=easy|medium|hard`
    - `length=<int>`
  - Response `200`: list of active words
- `POST /api/dictionary/words/add/`
  - Body: `{ "word": "apple" }`
  - Response `201`: created word (stored uppercase, difficulty inferred from length)
- `PATCH /api/dictionary/words/<word_id>/toggle/`
  - Response `200`: word with flipped `is_active`
- `GET /api/dictionary/stats/`
  - Response `200`: `{ total_active, easy, medium, hard }`

### Game

- `GET /api/game/match/<match_id>/`
- `GET /api/game/match/<match_id>/rounds/`
- `GET /api/game/match/history/<player_id>/`
- `GET /api/game/match/active/<player_id>/`

## WebSocket API (Frontend Integration)

- Endpoint: `ws://<backend-host>:8000/ws/wordduel/`
- Transport: plain WebSocket JSON messages
- Message format:
  - Client → Server: `{ "event": "<name>", "payload": { ... } }`
  - Server → Client: `{ "event": "<name>", "payload": { ... } }`

### Client → Server Events

- `joinLobby`
  - Payload: `{ "username": "Alice" }`
- `submitGuess`
  - Payload: `{ "guessText": "APPLE", "clientSentAt": 1710000000000 }`
- `leaveMatch`
  - Payload: `{}` (optional)

### Server → Client Events

- `matchFound`
  - Payload: `{ matchId, opponentUsername, scores: { me, opponent } }`
- `startRound`
  - Payload: `{ roundId, roundNumber, wordLength, scores: { me, opponent } }`
- `tickStart`
  - Payload: `{ tickNumber, deadline, revealedState: Array<string|null> }`
- `revealTile`
  - Payload: `{ index, letter, revealedState }`
- `opponentGuessed`
  - Payload: `{ tickNumber }`
- `roundEnd`
  - Payload: `{ winner: "me"|"opponent"|"draw"|null, revealedWord, scores, isDraw }`
- `matchEnd`
  - Payload: `{ winner: "me"|"opponent"|"draw", finalScores, totalRounds }`
- `error`
  - Payload: `{ code, message }`

