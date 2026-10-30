"""The provider-neutral LLM interface (OPS-01). Messages and tools use the Anthropic shape."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class LLMUnavailable(RuntimeError):
    """The model could not answer after retries; the turn takes the fallback path (NAR-07)."""


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]


@dataclass(frozen=True)
class LLMReply:
    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    tokens_in: int = 0
    tokens_cached: int = 0
    tokens_out: int = 0

    def blocks(self) -> list[dict[str, Any]]:
        """The assistant turn to send back: text and tool calls, without thinking."""
        blocks: list[dict[str, Any]] = [{"type": "text", "text": self.text}] if self.text else []
        blocks += [{"type": "tool_use", "id": c.id, "name": c.name, "input": c.args} for c in self.tool_calls]
        return blocks


class LLMClient(Protocol):
    def complete(
        self,
        system: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        *,
        fast: bool = False,
    ) -> LLMReply: ...
