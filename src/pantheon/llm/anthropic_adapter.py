"""Anthropic API adapter; also talks to a local Ollama server through its compatible API (D-020)."""

from __future__ import annotations

from typing import Any

import anthropic

from pantheon.llm.client import LLMReply, LLMUnavailable, ToolCall

MAX_REPLY_TOKENS = 1500
TIMEOUT_SECONDS = 300.0
SDK_RETRIES = 2  # The SDK backs off exponentially with jitter (OPS-03).
CHARS_PER_TOKEN = 4
TRUNCATED_BELOW = 0.5


def estimate_tokens(system: list[dict[str, Any]], messages: list[dict[str, Any]]) -> int:
    return len(str(system) + str(messages)) // CHARS_PER_TOKEN


class AnthropicClient:
    def __init__(self, model: str, base_url: str = "", think: bool = True, client: Any = None) -> None:
        self.model = model
        self.local = bool(base_url)
        self.think = think
        self.client = client or anthropic.Anthropic(
            base_url=base_url or None,
            api_key="ollama" if base_url else None,
            timeout=TIMEOUT_SECONDS,
            max_retries=SDK_RETRIES,
        )

    def complete(
        self, system: list[dict[str, Any]], messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None
    ) -> LLMReply:
        kwargs: dict[str, Any] = {"tools": tools} if tools else {}
        if not self.think:
            kwargs["thinking"] = {"type": "disabled"}
        try:
            reply = self.client.messages.create(
                model=self.model, max_tokens=MAX_REPLY_TOKENS, system=system, messages=messages, **kwargs
            )
        except anthropic.APIError as exc:
            raise LLMUnavailable(str(exc)) from exc
        tokens_in = reply.usage.input_tokens or 0
        tokens_cached = getattr(reply.usage, "cache_read_input_tokens", 0) or 0
        # Ollama cuts an over-long prompt silently, so a short count means the canon was lost (D-027).
        if self.local and tokens_in + tokens_cached < estimate_tokens(system, messages) * TRUNCATED_BELOW:
            raise LLMUnavailable(
                f"the local model read only {tokens_in + tokens_cached} tokens of the prompt; "
                "start Ollama with OLLAMA_CONTEXT_LENGTH=32768 (start.bat does this)"
            )
        text = "".join(b.text for b in reply.content if b.type == "text").strip()
        calls = tuple(ToolCall(b.id, b.name, dict(b.input)) for b in reply.content if b.type == "tool_use")
        return LLMReply(text, calls, tokens_in, tokens_cached, reply.usage.output_tokens or 0)
