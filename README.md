# GET SHIT DONE

> An ADHD-friendly weekly planner with an AI accountability agent.
>
> Plan realistically. Start before you feel ready. Do the next small thing. Adapt without abandoning the goal.

GET SHIT DONE combines the simplicity of a paper planner with a personal execution agent that watches
your schedule, asks *why* you didn't start, and turns vague intentions into concrete next actions —
in the tone you choose (gentle through drill sergeant).

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Docker](#docker)
- [Configuration](#configuration)
- [Using the App](#using-the-app)
- [The Agent](#the-agent)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Data, Privacy, and Export](#data-privacy-and-export)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)
- [License](#license)

---

## Features

### Planning
- **Weekly goals** — title, target outcome, priority, week anchor.
- **Agent-driven decomposition** — say *"break down goal 3 into: write spec, build prototype, review"*
  and get a parent task with nested subtasks, each with estimates.
- **Greedy scheduler** that respects daily availability, fixed commitments, working hours, and
  deadlines. Flags conflicts instead of silently overloading.
- **Two-level task tree** — parents roll up subtask progress (`2/4`). Auto-completes the parent
  when all children are done (Option B).

### Execution
- **Today view** — scheduled tasks *and* unscheduled tasks are both actionable. Every card has
  **Start**, **Done** (round checkbox), **Not done**, **Edit**, **Delete**.
- **Focus mode** with configurable session lengths (5/10/25/50 min), in-tab countdown timer,
  browser notification on completion, and reflection prompt.
- **Reopen** — click the ✓ on a completed task to revert to `planned`. Reopening a subtask also
  reopens its auto-completed parent.
- **Blocker taxonomy** — six categories (*avoidance, too big, unclear, low energy, health, external*)
  plus free-form detail. Each category triggers a different agent response.

### Accountability
- **Six coaching styles** — Gentle, Supportive but firm, Strict, Drill sergeant, Analytical, Custom —
  switchable at any time from Settings or the agent chat.
- **Proactive check-ins** — a background scheduler scans every 10 minutes for overdue tasks,
  repeatedly-postponed tasks, and stale active tasks. When one is found, the agent fires a
  tone-matched check-in: *"You haven't touched 'write spec'. What got in the way?"*
- **The "why" loop** — every check-in asks one question. The reply classifies the blocker, records
  it, and offers ONE concrete next action. Different action per category (2-min start, split into
  smaller pieces, postpone to morning, rest, reschedule).
- **Persistent memory** — `remember` / `recall_memory` tools store preferences across sessions.

### Tracking
- **Mood & energy** — 1–5 sliders, multiple check-ins per day, editable and deletable, 30-day view.
- **Food diary** — meal type, description, notes, timestamps. Full CRUD.
- **Hydration** — quick-add buttons (250/500/750 ml), configurable daily goal, progress bar.
- **Ideas inbox** — one-shot capture, convert to task, archive, edit, delete.
- **Focus sessions** — persisted start/end times and completions.

### Progress
- **Dashboard** — today's counts, next scheduled task, overdue / blocked, water, focus minutes,
  per-goal progress bars, recent mood.
- **Weekly summary** — completion rate, postponements, estimate-vs-actual ratio, cautious
  pattern notes. No shaming, no arbitrary productivity scores.

### Everything else
- **Themes** — six presets (three light, three dark), custom accent color, background image
  (URL or client-resized upload) with opacity control.
- **PWA** — installable, app-shell service worker. Reads cache; writes require connectivity.
- **Export & delete** — full JSON snapshot of all user data at `/api/settings/export`; account
  deletion cascades cleanly.
- **SAST-native** — all scheduling, overdue marking, and day boundaries computed in
  `Africa/Johannesburg` (configurable). No 2-hour drift.
- **Dark mode** everywhere.

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| **Frontend** | React 18 + TypeScript + Vite | Fast HMR, type safety, no build-server coupling |
| **Styling** | Tailwind CSS 3 with CSS variables | Runtime theme switching without CSS-in-JS |
| **Backend** | Python 3.13 + FastAPI | Typed, quick iteration, auto-generated OpenAPI |
| **ORM** | SQLAlchemy 2 | Explicit, testable, swappable to Postgres via one env var |
| **DB** | SQLite (dev) | Zero-config, single-file; production path is Postgres |
| **Scheduler** | APScheduler (in-process) | Survives browser tab closes; runs server-side |
| **Auth** | JWT (HS256) + PBKDF2-SHA256 hashes | Simple, no external dependency |
| **AI** | OpenAI Chat Completions with function calling | Best-in-class tool calling; provider abstracted |
| **AI (offline)** | MockProvider | Deterministic keyword dispatch that still calls real tools |

---

## Quick Start

### Prerequisites
- **Python 3.12 or 3.13** — 3.14 does **not** work with the pinned `pydantic-core`. Use 3.13.
- **Node 18+**
- Optional: **OpenAI API key** (the app runs fully on the mock provider without one)

### 1. Backend

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

Health check: <http://localhost:8000/api/health> → `{"ok":true,"provider":"mock"}`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. **Register** (email + password ≥ 6 characters). You're on the Today page.

### 3. Turn on the real LLM (optional)

Edit `backend/.env`:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Restart uvicorn **fully** (`Ctrl+C`, not just reload — env vars are read at process start). Then:

```bash
curl.exe http://localhost:8000/api/health
# → {"ok":true,"provider":"openai"}
```

Send `hi` to the agent. If you get a natural reply, the switch worked.

---

## Docker

```bash
cp backend/.env.example .env        # optional, uses safe defaults
docker compose up --build
```

- Frontend: <http://localhost:8080>
- Backend: <http://localhost:8000>
- Data persists in the `gsd-data` volume

Wipe everything: `docker compose down -v`

---

## Configuration

All settings live in `backend/.env`. Full reference:

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./gsd.db` | Change to `postgresql://...` for production |
| `SECRET_KEY` | `change-me` | **Change this.** Used for JWT signing |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` (7 days) | |
| `LLM_PROVIDER` | `mock` | `mock` or `openai` |
| `OPENAI_API_KEY` | *(empty)* | Only required if `LLM_PROVIDER=openai` |
| `OPENAI_MODEL` | `gpt-4o-mini` | Any tool-calling-capable model |
| `AGENT_MAX_ITERATIONS` | `6` | Max tool rounds per chat turn |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated |
| `ENABLE_SCHEDULER` | `true` | Turn off in test environments |
| `APP_TIMEZONE` | `Africa/Johannesburg` | All day-boundaries use this |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` | *(empty)* | Optional Web Push |

**The mock provider is fully functional** — it calls the same tools, persists the same records,
produces deterministic responses. Use it for local development without paying for tokens.

---

## Using the App

### First run — 60-second walkthrough

1. **Register** (email + any password ≥ 6 chars).
2. **Goals** tab → add a goal, e.g. `"Ship MVP"`. Note its `#id`.
3. **Agent** (bottom-right) → send: `break down goal 1 into: write spec, build prototype, review`.
   The agent creates a parent task + 3 subtasks.
4. **Planner** → **Auto-schedule** → subtasks get placed in this week's slots.
5. **Today** → click the round ○ on any task to complete it. Badge updates: `subtasks 1/3`.
6. **Focus** → select a task, choose 5 minutes → work. On completion, mark done.
7. **Body** → log mood, water, food. Edit or delete any entry from the same page.
8. **Ideas** → capture a thought, convert to task later.

### Quick reference

| Page | What you can do |
|---|---|
| **Today** | Quick-add, complete, reopen, edit, delete tasks; watch the dashboard counters update |
| **Planner** | Quick-add, auto-schedule, drag-and-drop, delete; see goals + "decompose in agent" button |
| **Goals** | Create, edit, delete. Deleting keeps its tasks (they become unassigned) |
| **Focus** | Start work session with countdown, mark done or not done, add reflection |
| **Ideas** | Capture, edit, archive, convert to task, delete |
| **Body** | Log + edit + delete mood/energy, water, food. See 30-day check-in history |
| **Progress** | Goal progress bars, weekly summary, recent mood/energy |
| **Settings** | Coaching style, work hours, quiet hours, hydration goal, theme, background, autonomy |

---

## The Agent

### How it works

The agent is a **tool-calling LLM** with read and write access to your data. Every response goes
through a registry of 20 tools, each with a Pydantic-validated schema, scoped by `user.id`.

**Read tools** (7): `get_today_context`, `get_tracking_summary`, `list_tasks`, `list_goals`,
`get_ideas`, `recall_memory`, `get_status`

**Write tools** (13): `create_task`, `decompose_goal`, `update_task`, `mark_task_started`,
`complete_task`, `postpone_task`, `suggest_and_apply_schedule`, `set_reminder`, `remember`,
`idea_to_task`, `record_blocker`, `log_mood`, `log_water`, `log_food`, `log_focus`

If a tool fails, the result string starts with `ERROR:` and the model sees it. **The agent cannot
claim to have done something the tool didn't do** — the trace is preserved in `agent_messages`.

### Coaching styles

| Style | When to use |
|---|---|
| **Gentle** | Warm, patient, no shame. Best on rough days |
| **Supportive but firm** | Kind but direct. Reminds you of your commitments |
| **Strict accountability** | Blunt, concise. Presents a decision: start, reschedule, or state the blocker |
| **Drill sergeant** | High-energy, commanding. Short commands |
| **Analytical coach** | Diagnoses bottlenecks with evidence-based questions |
| **Custom** | Free-form instructions in Settings |

Switch styles at any time. The prompt layer only changes tone; behavior logic is identical.

### The check-in loop

Every 10 minutes, the scheduler runs a stall detector:

1. **Overdue** task (`scheduled_end` < now − 10 min) →
   *"Task #3 'write spec' has been overdue for 12 min."*
2. **Postponed ≥ 2×** and still incomplete →
   *"Task #3 has been postponed 3 times."*
3. **Active but stale** (`updated_at` < now − 45 min) →
   *"Task #3 marked active but hasn't been updated in 45+ min."*

If any condition matches, `run_agent_turn()` is called with the trigger `checkin`. The agent
calls `get_today_context`, then asks ONE question in your coaching tone. **It does not lecture in
the check-in** — it asks, then waits for your reply to classify the blocker and act.

Throttle: at most one check-in per user per 30 min. Won't interrupt if you've messaged the agent
in the last 15 min. Won't fire during quiet hours.

### Safety guarantees

- **No silent success.** Every tool returns `OK: …` or `ERROR: …`.
- **No false claims.** The agent sees tool results, not intentions.
- **Message-array sanitization.** Every turn passes through `_sanitize()`, which strips orphan tool
  messages and half-paired `tool_calls` blocks before the request hits OpenAI. A single failed
  turn can't poison subsequent requests.
- **Failed turns don't corrupt state.** Every exception rolls back before returning.
- **Autonomy is per-user.** Set in Settings → `read` (report only), `confirm` (default), or
  `autonomous` (routine actions without asking).

---

## Architecture

### Request flow — chat turn

```
Browser → POST /api/agent/chat
        → FastAPI auth (JWT → user.id)
        → service.run_agent_turn()
            → _sanitize(messages)  ←  repair prior tool-call blocks
            → provider.complete()  ←  OpenAI or Mock
            → tool_calls? → for each:
                → tools.execute_tool()  ←  Pydantic validated, user-scoped
                → append {role: "tool", tool_call_id, content}
            → loop up to AGENT_MAX_ITERATIONS
            → persist all messages to agent_messages
        → ChatOut{reply, tool_calls}
```

### Scheduler loop

Runs in a `BackgroundScheduler` attached to the FastAPI lifespan. Every 30 s:

1. `dispatch_due()` — send reminders whose time has come (respecting quiet hours)
2. `_mark_overdue()` — flip `planned`/`active` → `overdue` for tasks past `scheduled_end`
3. `_schedule_pending_task_reminders()` — pre-create 5-min-before reminders for tasks starting soon
4. Every 20th tick: `_run_monitor()` → `maybe_checkin()` per user → agent turn if stall detected

The scheduler is **server-side** — closing your browser tab doesn't stop overdue detection or
reminder creation. Browser notifications still require the tab open; the DB state is always correct.

### Data model

```
User ──1:1──► UserPreferences
  │
  ├──1:N──► Goal ──1:N──► Task ──self──► Task (subtasks)
  │                        │
  │                        └──1:N──► FocusSession
  │
  ├──1:N──► AgentMessage, AgentMemory, Reminder
  │
  ├──1:N──► DailyAvailability, FixedCommitment
  │
  └──1:N──► MoodEnergyLog, FoodEntry, WaterEntry, Idea
```

All timestamps are **naive SAST** (Africa/Johannesburg wall clock). No tzinfo in the DB.
`timeutils.now_local()` / `today_local()` provide all "now" and "today" computations.

### Provider abstraction

`agent/provider.py` defines an abstract `LLMProvider`. Two implementations:

- **`MockProvider`** — deterministic. Matches phrases, dispatches to real tools. Every workflow
  (create, decompose, complete, block, schedule) works end-to-end without network access.
- **`OpenAIProvider`** — real Chat Completions. Sends the tool registry, parses `tool_calls` from
  the response, and includes the actual error body in exceptions.

Adding a third provider (Anthropic, local Ollama, etc.) is one subclass + one branch in
`get_provider()`. No other code changes.

---

## Project Structure

```
get-shit-done/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, lifespan, CORS, routers
│   │   ├── config.py               # Pydantic Settings — env-driven
│   │   ├── database.py             # SQLAlchemy engine + session
│   │   ├── models.py               # 15 ORM tables
│   │   ├── schemas.py              # Pydantic request/response models
│   │   ├── security.py             # JWT + PBKDF2
│   │   ├── deps.py                 # current_user, user_prefs
│   │   ├── scheduler.py            # APScheduler + monitor loop
│   │   ├── notifications.py        # Reminder dispatch + Web Push
│   │   ├── timeutils.py            # now_local() / today_local() in SAST
│   │   ├── routers/                # 10 routers, ~60 endpoints
│   │   ├── services/
│   │   │   ├── schedule_service.py # Greedy scheduler + conflict detection
│   │   │   ├── tracking_service.py # Hydration, mood series, correlation notes
│   │   │   └── progress_service.py # Weekly summary + goal progress
│   │   └── agent/
│   │       ├── provider.py         # LLMProvider ABC
│   │       ├── openai_provider.py  # Real LLM
│   │       ├── mock_provider.py    # Deterministic
│   │       ├── prompts.py          # System prompt + coaching tones
│   │       ├── tools.py            # 20 tools + schema registry
│   │       ├── service.py          # Tool loop + message sanitization
│   │       └── monitor.py          # Stall detection → check-in
│   ├── tests/                      # pytest: scheduling, agent, API
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # Router + providers
│   │   ├── api.ts                  # Typed fetch wrapper
│   │   ├── types.ts                # Shared types
│   │   ├── auth.tsx                # Auth context
│   │   ├── lib/
│   │   │   ├── theme.tsx           # 6 themes + CSS variable runtime
│   │   │   ├── agentBus.tsx        # Shared agent chat state
│   │   │   ├── tree.ts             # Flat tasks → tree
│   │   │   ├── image.ts            # Client-side image resize
│   │   │   └── sast.ts             # Timezone helpers
│   │   ├── components/             # Layout, TaskCard, AgentChat, BlockerModal
│   │   └── pages/                  # Today, Planner, Goals, Focus, Ideas,
│   │                               # Tracking, Progress, Settings, Login
│   ├── public/
│   │   ├── manifest.webmanifest
│   │   └── sw.js                   # App-shell cache, API passthrough
│   ├── package.json
│   └── vite.config.ts              # Proxies /api → :8000
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
└── README.md
```

---

## Testing

```bash
cd backend
pytest -q
```

Three test files cover:

- **`test_scheduling.py`** — slot construction respects commitments; greedy scheduler flags
  capacity overflows.
- **`test_agent.py`** — decompose creates parent + N subtasks; tool errors surface truthfully.
- **`test_api_flow.py`** — full flow: create goal → create task → suggest schedule → apply →
  complete → dashboard reflects → idea converts.

Type-check the frontend:

```bash
cd frontend
npx tsc --noEmit
```

---

## Data, Privacy, and Export

- **Everything stays local.** SQLite file at `backend/gsd.db`. Nothing is transmitted to OpenAI
  except: the system prompt, your recent agent messages (last 20), and the tool results for that
  turn. Task titles, notes, mood entries, food descriptions, and water amounts are **not** sent
  unless a tool is invoked that returns them (e.g. `get_today_context`).
- **Export** — `GET /api/settings/export` returns a JSON snapshot: tasks, goals, prefs, mood,
  food, water, ideas, memory.
- **Delete** — `DELETE /api/settings/account` cascades all user data.
- **Backup** — `cp backend/gsd.db backend/gsd-$(date +%F).db`. For Docker:
  `docker compose cp gsd-backend:/data/gsd.db ./backup.db`.

If you add a third-party provider, review what each tool returns — the current tool set can
surface task titles, mood notes, and food descriptions to the LLM.

---

## Known Limitations

Explicitly **not** implemented, so you're not surprised:

- **Web Push subscriptions are in-memory only.** They reset on backend restart. Reminders are
  still persisted to SQLite and dispatched on the next scheduler tick — the DB side works, only
  background push delivery is incomplete. Enabling `VAPID_*` keys is a prerequisite.
- **No Alembic migrations.** Schema is created at startup via `Base.metadata.create_all`. For
  production, run `alembic init` + `alembic revision --autogenerate` against the existing models.
- **SQLite is single-writer.** Fine for one user; for multiple, set `DATABASE_URL` to Postgres.
- **No password reset flow.** Single-user local app — if you forget the password, delete
  `backend/gsd.db` and re-register.
- **Planner drag-and-drop** persists new times correctly, but the visual "conflict" indicator is a
  one-line text message, not a highlighted drop zone.
- **Weekly review report** — `progress_service.weekly_summary()` returns all data; the
  **Progress** page currently shows dashboard-level numbers and goal progress bars. Rendering the
  full weekly review document is a small follow-up.
- **Reopening a parent does not reopen its children.** Only subtask → parent cascades. If you
  reopen a parent whose subtasks are all complete, the parent will auto-complete again on the
  next child completion.

---

## Roadmap

Short follow-ups, roughly in order of usefulness:

1. **Weekly review page** — render `weekly_summary()` + `_summary_notes()` in a dedicated view.
2. **Persistent Web Push** — add a `push_subscriptions` table and complete the VAPID flow.
3. **Alembic** — replace `create_all` with real migrations for a Postgres deployment story.
4. **Conflict-highlighting** — replace the text conflict message with a visible overlap indicator
   in the Planner grid.
5. **Recurring tasks** — daily/weekly tasks that regenerate on schedule.
6. **Multiple providers** — Anthropic, Ollama, or Groq via `LLMProvider` subclass.
7. **Parent cascade on reopen** — when a parent is reopened, optionally reopen all children.

---

## License

MIT — do whatever you like with it. Attribution appreciated but not required.

---

## Acknowledgements

Built as a single-file-at-a-time iteration between a human and Claude (Anthropic). Every
production bug encountered during development is preserved in the code's history — including
the mapper-ordering issue in `Task.subtasks`, the `bcrypt` / `passlib` incompatibility, the
`BaseModel()` instantiation in `tools.py`, the f-string `{title}` bug in `prompts.py`, and the
OpenAI tool-call pairing requirement. If you hit one of them, the fix is one file away.

The philosophy is from the project brief:

> Plan realistically. Start before you feel ready. Do the next small thing.
> Adapt without abandoning the goal.
```
