import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import (
    agent, auth, dashboard, focus, goals, ideas, schedule, settings as settings_r,
    tasks, tracking,
)
from .scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)


def _ensure_prefs_columns() -> None:
    """Add theme/bg columns to user_preferences for databases created earlier."""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "user_preferences" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("user_preferences")}
    needed = {
        "theme": "VARCHAR(32) DEFAULT 'paper'",
        "accent_color": "VARCHAR(16) DEFAULT ''",
        "bg_image": "TEXT DEFAULT ''",
        "bg_opacity": "INTEGER DEFAULT 60",
    }
    missing = [(n, ddl) for n, ddl in needed.items() if n not in cols]
    if not missing:
        return
    with engine.begin() as conn:
        for name, ddl in missing:
            conn.execute(text(f"ALTER TABLE user_preferences ADD COLUMN {name} {ddl}"))
    logging.getLogger("gsd").info("migrated user_preferences: added %s", [n for n, _ in missing])


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_prefs_columns()
    start_scheduler()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth, goals, tasks, schedule, agent, tracking, ideas, focus, settings_r, dashboard):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    return {"ok": True, "provider": settings.LLM_PROVIDER}