from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from ..config import settings
from ..models import AgentMessage, User, UserPreferences
from .prompts import system_prompt
from .provider import get_provider
from .tools import execute_tool, tool_definitions_for_llm

log = logging.getLogger("gsd.agent")


def _sanitize(messages: list[dict]) -> list[dict]:
    """OpenAI 400s the whole request if a 'tool' message has no parent
    'assistant tool_calls' message, or if tool_calls lack responses. Strip both."""
    out: list[dict] = []
    i = 0
    while i < len(messages):
        m = messages[i]
        if m.get("role") == "tool":
            i += 1
            continue
        if m.get("role") == "assistant" and m.get("tool_calls"):
            ids = {tc["id"] for tc in m["tool_calls"]}
            j = i + 1
            replies: dict[str, dict] = {}
            while j < len(messages) and messages[j].get("role") == "tool":
                tid = messages[j].get("tool_call_id")
                if tid in ids:
                    replies[tid] = messages[j]
                j += 1
            if len(replies) == len(ids):
                out.append(m)
                out.extend(replies[tid] for tid in ids)
            else:
                if m.get("content"):
                    out.append({"role": "assistant", "content": m["content"]})
            i = j
            continue
        out.append(m)
        i += 1
    return out


def run_agent_turn(db: Session, user: User, prefs: UserPreferences,
                   message: str, trigger: str = "user") -> dict:
    try:
        return _run_inner(db, user, prefs, message, trigger)
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        log.exception("agent turn failed")
        return {
            "reply": (
                f"The agent provider is unavailable right now "
                f"({type(e).__name__}: {e}). Nothing was changed."
            ),
            "tool_calls": [],
        }


def _run_inner(db: Session, user: User, prefs: UserPreferences,
               message: str, trigger: str) -> dict:
    if trigger == "user":
        db.add(AgentMessage(user_id=user.id, role="user", content=message))
        db.commit()

    provider = get_provider()
    tools = tool_definitions_for_llm()
    sys_prompt = system_prompt(prefs)

    history = (
        db.query(AgentMessage)
        .filter(
            AgentMessage.user_id == user.id,
            AgentMessage.role.in_(["user", "assistant", "checkin"]),
        )
        .order_by(AgentMessage.created_at.desc())
        .limit(20)
        .all()
    )
    history.reverse()

    messages: list[dict] = []
    for m in history:
        if trigger == "user" and m.role == "user" and m.content == message and m is history[-1]:
            continue
        role = "assistant" if m.role in ("assistant", "checkin") else m.role
        if m.content:
            messages.append({"role": role, "content": m.content})
    messages.append({"role": "user", "content": message})
    messages = _sanitize(messages)

    tool_trace: list[dict] = []
    final_reply = ""

    for _ in range(settings.AGENT_MAX_ITERATIONS):
        try:
            resp = provider.complete(messages, tools, sys_prompt)
        except Exception as e:
            final_reply = (
                f"The agent provider is unavailable right now "
                f"({type(e).__name__}: {e}). Nothing was changed."
            )
            break

        if resp.tool_calls:
            assistant_msg = {
                "role": "assistant",
                "content": resp.content or None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments or {}),
                        },
                    }
                    for tc in resp.tool_calls
                ],
            }

            # Execute every tool FIRST, so the following message block is complete
            results: list[tuple] = []
            for tc in resp.tool_calls:
                try:
                    result = execute_tool(db, user.id, tc.name, tc.arguments)
                except Exception as e:
                    result = f"ERROR: {type(e).__name__}: {e}"
                results.append((tc, result))
                tool_trace.append({"name": tc.name, "args": tc.arguments, "result": result})
                db.add(AgentMessage(
                    user_id=user.id, role="tool", content=result,
                    tool_name=tc.name, tool_input=str(tc.arguments)[:2000],
                ))
            db.commit()

            # Append assistant + ALL its tool responses together — never partial
            messages.append(assistant_msg)
            for tc, result in results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.name,
                    "content": result,
                })
            continue

        final_reply = resp.content or ""
        db.add(AgentMessage(
            user_id=user.id,
            role="checkin" if trigger == "checkin" else "assistant",
            content=final_reply,
        ))
        db.commit()
        break

    if not final_reply:
        final_reply = "Stopped after several tool rounds to avoid looping."
    return {"reply": final_reply, "tool_calls": tool_trace}