"""A deterministic client that replays a scripted conversation, for tests (OPS-01, OPS-05)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pantheon.llm.client import LLMReply, LLMUnavailable


class MockClient:
    """Each script item is a reply, or None for an outage. Records what it was sent."""

    def __init__(self, script: Iterable[LLMReply | None]) -> None:
        self.script = list(script)
        self.calls: list[dict[str, Any]] = []

    def complete(
        self, system: list[dict[str, Any]], messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None
    ) -> LLMReply:
        self.calls.append({"system": system, "messages": list(messages), "tools": tools})
        if not self.script:
            raise LLMUnavailable("the script has ended")
        reply = self.script.pop(0)
        if reply is None:
            raise LLMUnavailable("scripted outage")
        return reply
