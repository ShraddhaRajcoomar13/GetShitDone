# GET SHIT DONE

An ADHD-friendly weekly planner with an AI accountability agent.
Plan realistically. Start before you feel ready. Do the next small thing.

---

## What's actually implemented

- **Auth**: email/password (bcrypt + JWT). User-level data isolation on every query.
- **Weekly goals + task decomposition** via the agent's `decompose_goal` / `create_task` tools.
- **Greedy scheduler** (`services/schedule_service.py`): respects daily availability + fixed commitments, sorts by deadline → priority → size, flags conflicts, never silently overfills a day.
- **Persisted schedule** — drags/edits update tasks in SQLite and survive restarts.
- **Focus mode** with a countdown, browser notification on session end, and a completion path that increments actual minutes.
- **Unfinished-task handling**: `postpone_task` increments `postpone_count`, sets status, does **not** duplicate the row.
- **Agent** with a provider abstraction:
  - `MockProvider` (default): deterministic, keyword-driven, but still calls **real tools**.
  - `OpenAIProvider`: real Chat Completions with function calling. Enable via `LLM_PROVIDER=openai` + `OPENAI_API_KEY`.
- **Tool registry** (`agent/tools.py`) with Pydantic validation per tool, user-scoped, and errors that surface truthfully (the agent cannot claim a tool succeeded when it returned `ERROR`).
- **Coaching styles** (6): gentle, supportive but firm, strict, drill sergeant, analytical, custom — wired into the system prompt.
- **Scheduler** (APScheduler, runs in-process, `ENABLE_SCHEDULER=true`) that:
  - marks overdue tasks,
  - pre-creates 5-minute reminders for upcoming starts,
  - dispatches due reminders, respecting quiet hours.
- **Web Push (optional)**: `pywebpush` with VAPID keys. If keys are absent, push is skipped; in-app data still flows.
- **Tracking**: mood, energy, water, food — all editable/deletable via the export endpoint.
- **Ideas inbox** with one-shot capture, convert-to-task.
- **Dashboard** + weekly summary (with cautious, non-causal notes).
- **Data export** (`GET /api/settings/export`) and **account delete** (`DELETE /api/settings/account`).
- **PWA**: manifest + service worker (app-shell cache; API passthrough).
- **Tests**: scheduling, agent tool-calls, full API flow.

## What's deliberately out of scope

- **Real Web Push** requires VAPID key management + a persistent subscription table (currently the subscription store is in-memory and resets on backend restart). Browser notifications only fire when the app tab is open. **Server-side APScheduler reminders still persist** in SQLite and will be dispatched the next time the user has the app open.
- **True offline writes**. Reads are cached by the SW; writes need connectivity.
- **Alembic migrations**. Schema is auto-created on startup via `Base.metadata.create_all`. For production, generate migrations with `alembic init` and autogenerate against the existing models.
- **Multi-tenant Postgres hardening**. It runs on Postgres by changing `DATABASE_URL`; row-level security is *not* configured — user isolation is enforced in application code.
- **Drag-and-drop conflict UI**. Dragging in the planner currently reorders visually; **persisting a new time slot** is available via `PATCH /api/tasks/{id}` and `GET /api/tasks/{id}/conflicts`. The planner wires the drop handler to this in code but the visual "dropped into unavailable slot" warning is minimal.
- **Full weekly review report**. `services/progress_service.weekly_summary()` returns the data; the Progress page shows top-line metrics but does not yet render a formal weekly review document.

---

## Local setup (no Docker, no paid infra)

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # defaults: mock LLM, SQLite, scheduler on
uvicorn app.main:app --reload --port 8000
```

Health check: <http://localhost:8000/api/health> → `{"ok":true,"provider":"mock"}`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Register a user. You can immediately plan, focus, track, and chat with the mock agent without any API key.

### 3. Run the tests

```bash
cd backend
pytest -q
```

Tests use `LLM_PROVIDER=mock`, `ENABLE_SCHEDULER=false`, and their own SQLite DB.

---

## Docker setup

```bash
cp backend/.env.example .env   # optional
docker compose up --build
```

- Frontend: <http://localhost:8080>
- Backend: <http://localhost:8000>
- Data volume: `gsd-data` (persists SQLite)

---

## Configuring the LLM provider

**Default (mock, offline).** No keys. Deterministic keyword dispatch to real tools. Best for local dev and for verifying workflows.

**OpenAI.** In `backend/.env`:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Restart the backend. The `agent/provider.py` factory will pick up `OpenAIProvider`. If the API call fails, the agent replies with a truthful "unavailable, nothing was changed" message — no state is mutated.

**Adding a provider.** Subclass `LLMProvider` in `backend/app/agent/provider.py`, add a branch to `get_provider()`. No other code needs to change.

---

## Notification permissions

- **In-app**: reminders appear in the database (queryable via `/api/schedule/...` and rendered by the dashboard).
- **Browser notifications** (foreground): Focus Mode requests permission via the Notification API. If denied, focus still works; only the end-of-session popup is skipped.
- **Web Push** (background): set `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_CLAIM_EMAIL`. Generate keys with:

  ```bash
  python -c "from pywebpush import webpush; import json; print(json.dumps({'private': '...', 'public': '...'}))"
  ```

  Or use the official `web-push` CLI. Then wire `navigator.serviceWorker.ready.then(r => r.pushManager.subscribe(...))` on the client and POST the subscription to the backend (extend `scheduler.set_push_subscriptions` to persist to a new `push_subscriptions` table). This is intentionally left as the next integration step; without it, push degrades gracefully to in-app.

---

## Architecture decisions

- **FastAPI + SQLAlchemy** for typed, quick iteration. `DATABASE_URL` swaps SQLite → Postgres in one line.
- **APScheduler** as an in-process loop is correct for a single-instance deployment (local laptop, small VPS). For multi-worker deployments, move reminders to a shared store and run the scheduler on a single dedicated worker, or use Celery beat. This is documented, not pretended.
- **Agent ≠ chat bot.** The agent's job is to call tools. The MockProvider proves the tool pipeline works end-to-end without external dependencies.
- **Coaching tone is a prompt concern**, not a code concern. Interventions are generated, not hardcoded.
- **No silent success.** Every tool returns `OK: …` or `ERROR: …` and the trace is preserved in `agent_messages`. If a tool fails, the model sees the failure.
- **User isolation** is enforced via `current_user.id` in every query. A future hardening step is Postgres row-level security.

## Data ownership

- Export: `GET /api/settings/export` returns a JSON snapshot of tasks, prefs, tracking, ideas, memory.
- Delete: `DELETE /api/settings/account` cascades all user data.
- Backups: `cp backend/gsd.db backend/gsd-$(date +%F).db` (or `docker compose cp gsd-backend:/data/gsd.db ./backup.db`).

## Known limitations

1. Browser push subscriptions aren't persisted (in-memory only). Reminders still write to DB and dispatch on next app open.
2. Planner drag-and-drop updates the UI but does not yet **persist** the new slot when dropped onto a different day — use the task `PATCH` endpoint or reschedule via the agent for now.
3. `weekly_summary()` returns the review data but the Progress page currently shows the dashboard-level numbers. Extending the UI to render the full weekly review is a short follow-up.
4. SQLite is single-writer; for heavier use, set `DATABASE_URL` to Postgres.
5. No CSRF tokens on the JSON API — the frontend uses bearer tokens, which are not sent by the browser automatically on cross-origin requests, so classic CSRF does not apply. If you switch to cookie auth, add CSRF.