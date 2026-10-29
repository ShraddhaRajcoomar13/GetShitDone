import json
import httpx

from ..config import settings
from .provider import LLMProvider, LLMResponse, ToolCall


class OpenAIProvider(LLMProvider):
    API = "https://api.openai.com/v1/chat/completions"

    def complete(self, messages, tools, system):
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY missing while LLM_PROVIDER=openai")

        payload = {
            "model": settings.OPENAI_MODEL,
            "messages": [{"role": "system", "content": system}, *messages],
            "temperature": 0.4,
        }
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t.get("parameters")
                        or {"type": "object", "properties": {}},
                    },
                }
                for t in tools
            ]
            payload["tool_choice"] = "auto"

        r = httpx.post(
            self.API,
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        if r.status_code >= 400:
            # Surface the real OpenAI message, not just the status code
            raise RuntimeError(f"OpenAI {r.status_code}: {r.text[:800]}")

        data = r.json()
        choice = data["choices"][0]["message"]
        raw_calls = choice.get("tool_calls") or []
        calls = [
            ToolCall(
                id=c["id"],
                name=c["function"]["name"],
                arguments=json.loads(c["function"]["arguments"] or "{}"),
            )
            for c in raw_calls
        ]
        return LLMResponse(content=choice.get("content") or "", tool_calls=calls)