from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, messages: list[dict], tools: list[dict], system: str) -> LLMResponse:
        ...


def get_provider() -> LLMProvider:
    from ..config import settings
    if settings.LLM_PROVIDER == "openai":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider()
    from .mock_provider import MockProvider
    return MockProvider()