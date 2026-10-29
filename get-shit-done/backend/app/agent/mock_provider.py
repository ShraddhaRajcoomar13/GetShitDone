"""Deterministic provider. Still calls real tools — nothing is mocked at the data layer."""
import re
import uuid

from .provider import LLMProvider, LLMResponse, ToolCall


class MockProvider(LLMProvider):
    def complete(self, messages, tools, system):
        user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        lower = user_msg.lower()

        last_tool = next((m["content"] for m in reversed(messages) if m["role"] == "tool"), None)
        if last_tool:
            return LLMResponse(content=f"Done. {last_tool[:500]}")

        # Check-in trigger (from scheduler)
        if user_msg.startswith("[SYSTEM CHECK-IN]"):
            return LLMResponse(content="", tool_calls=[
                ToolCall(str(uuid.uuid4()), "get_today_context", {}),
            ])

        # Reads
        if any(k in lower for k in ("how am i", "how's my day", "status", "what's today", "whats today")):
            return LLMResponse(content="", tool_calls=[
                ToolCall(str(uuid.uuid4()), "get_today_context", {}),
            ])
        if any(k in lower for k in ("food", "eat", "meal", "mood", "energy", "water", "hydration", "tracking")):
            return LLMResponse(content="", tool_calls=[
                ToolCall(str(uuid.uuid4()), "get_tracking_summary", {"days": 7}),
            ])
        if any(k in lower for k in ("ideas", "inbox")):
            return LLMResponse(content="", tool_calls=[ToolCall(str(uuid.uuid4()), "get_ideas", {})])
        if "goal" in lower and "break" not in lower and "decompose" not in lower:
            return LLMResponse(content="", tool_calls=[ToolCall(str(uuid.uuid4()), "list_goals", {})])
        if any(k in lower for k in ("remember", "what did i tell you", "preferences")):
            return LLMResponse(content="", tool_calls=[ToolCall(str(uuid.uuid4()), "recall_memory", {})])
        if "tasks" in lower or "list" in lower:
            return LLMResponse(content="", tool_calls=[
                ToolCall(str(uuid.uuid4()), "list_tasks", {"include_completed": False}),
            ])

        # Writes / tracking
        m = re.search(r"drank\s+(\d+)\s*ml|water\s+(\d+)\s*ml", lower)
        if m:
            amt = int(m.group(1) or m.group(2))
            return LLMResponse(content="", tool_calls=[
                ToolCall(str(uuid.uuid4()), "log_water", {"amount_ml": amt}),
            ])
        if lower.startswith("ate ") or "i ate" in lower:
            desc = user_msg.replace("I ate", "").replace("i ate", "").strip() or user_msg
            return LLMResponse(content="", tool_calls=[
                ToolCall(str(uuid.uuid4()), "log_food", {"meal_type": "snack", "description": desc}),
            ])

        # Decompose
        if any(k in lower for k in ("break down", "decompose", "subtask", "split")):
            gm = re.search(r"goal\s+(\d+)", lower)
            goal_id = int(gm.group(1)) if gm else None
            if goal_id is None:
                return LLMResponse(content="Which goal? e.g. 'break down goal 3 into: …'.")
            return LLMResponse(content="", tool_calls=[ToolCall(
                str(uuid.uuid4()), "decompose_goal",
                {"goal_id": goal_id, "tasks": self._decompose_from_message(user_msg), "create_parent": True},
            )])

        # Task actions
        tid = self._first_task_id(user_msg)
        if tid and any(k in lower for k in ("start", "begin")):
            return LLMResponse(content="", tool_calls=[
                ToolCall(str(uuid.uuid4()), "mark_task_started", {"task_id": tid}),
            ])
        if tid and any(k in lower for k in ("done", "complete", "finish")):
            return LLMResponse(content="", tool_calls=[
                ToolCall(str(uuid.uuid4()), "complete_task", {"task_id": tid}),
            ])
        if tid and any(k in lower for k in ("postpone", "reschedule")):
            return LLMResponse(content="", tool_calls=[
                ToolCall(str(uuid.uuid4()), "postpone_task", {"task_id": tid, "reason": "user_request"}),
            ])

        if any(k in lower for k in ("schedule", "plan my week")):
            return LLMResponse(content="", tool_calls=[
                ToolCall(str(uuid.uuid4()), "suggest_and_apply_schedule", {}),
            ])
                # User answering "why didn't you do it?"
        if any(k in lower for k in (
            "didn't do", "didnt do", "didn't finish", "didnt finish",
            "not done", "haven't started", "havent started", "didn't start", "didnt start",
        )):
            tid = self._first_task_id(user_msg)
            if tid:
                category = "other"
                if any(k in lower for k in ("avoid", "scared", "don't want", "dont want", "hate", "procrastinat")):
                    category = "avoidance"
                elif any(k in lower for k in ("too big", "too much", "huge", "overwhelm", "massive")):
                    category = "too_big"
                elif any(k in lower for k in ("confus", "unclear", "don't know", "dont know", "not sure", "where to start")):
                    category = "unclear"
                elif any(k in lower for k in ("tired", "exhaust", "low energy", "sleepy", "burnt out", "burned out")):
                    category = "low_energy"
                elif any(k in lower for k in ("sick", "ill", "unwell", "pain", "migraine", "fever")):
                    category = "health"
                elif any(k in lower for k in ("busy", "interrupt", "something came up", "distract", "meeting ran")):
                    category = "external"

                next_step = {
                    "avoidance": "Just open it for 2 minutes. Don't aim to finish — aim to start.",
                    "too_big": "Let's split it. Say 'break it down' and I'll generate the pieces.",
                    "unclear": "Tell me what's ambiguous and I'll help pin down the first step.",
                    "low_energy": "Let me postpone this to tomorrow morning when you have energy.",
                    "health": "Rest first. I'll push this to a better day.",
                    "external": "Not your fault. Let me find you a better slot.",
                    "other": "Tell me a bit more — what specifically got in the way?",
                }[category]

        return LLMResponse(content="", tool_calls=[ToolCall(
                    str(uuid.uuid4()), "record_blocker",
                    {
                        "task_id": tid,
                        "reason": user_msg,
                        "category": category,
                        "next_action": next_step,
                    },
                )])

        return LLMResponse(content=(
            "I've got you. What's the smallest next physical action? "
            "If you want a snapshot, say 'how am I doing?'."
        ))

    @staticmethod
    def _first_task_id(msg: str) -> int | None:
        m = re.search(r"task\s+(\d+)", msg.lower()) or re.search(r"#(\d+)", msg)
        return int(m.group(1)) if m else None

    @staticmethod
    def _decompose_from_message(msg: str) -> list[dict]:
        tail = msg.split("into", 1)[1] if "into" in msg else msg
        parts = [p.strip(" .") for p in re.split(r",|\band\b|\n", tail) if p.strip(" .")]
        if not parts:
            parts = ["Define the outcome", "Do the first small step", "Review and finish"]
        return [
            {"title": p[:140], "estimated_minutes": 30, "priority": 3,
             "smallest_first_action": f"Open your workspace and start: {p[:60]}",
             "outcome": f"Complete: {p[:80]}"}
            for p in parts[:6]
        ]