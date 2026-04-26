# WisFlux Assignment (WordDuel)

## Backend (Django)

### Quick start (SQLite — no Postgres required)

```powershell
cd Backend
.\venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

This uses `config.settings.dev` (default in `manage.py`) which is configured for SQLite.

### Postgres (optional)

1. Create `Backend/.env` from `Backend/.env.example` and set your Postgres credentials.
2. Set `USE_SQLITE=false` in `Backend/.env` (keeps dev settings open + Redis-free, but uses Postgres).
3. Run migrations + server:

```powershell
cd Backend
.\venv\Scripts\activate
python manage.py migrate
python manage.py runserver
```

If Postgres is not available, set `USE_SQLITE=true` (or remove it) to run with SQLite again.

### Tests

```powershell
cd Backend
.\venv\Scripts\activate
python manage.py test
```

## Frontend (Vite)

```powershell
cd frontend
npm install
npm run dev
```

Optional env overrides (create `frontend/.env` from `frontend/.env.example`):

- `VITE_BACKEND_HTTP_URL` (default: `http://<your-host>:8000`)
- `VITE_BACKEND_WS_URL` (default: `ws(s)://<your-host>:8000/ws/wordduel/`)

Checks:

```powershell
npm run build
npm run lint
```
