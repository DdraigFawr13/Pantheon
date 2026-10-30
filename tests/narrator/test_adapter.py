"""OPS-01 and OPS-02: the Anthropic adapter, with a fake SDK client. No network."""

from types import SimpleNamespace
from typing import Any

import anthropic
import pytest

from pantheon.llm.anthropic_adapter import AnthropicClient
from pantheon.llm.client import LLMReply, LLMUnavailable, ToolCall
from pantheon.llm.mock import MockClient

SYSTEM = [{"type": "text", "text": "x" * 4000}]
MESSAGES = [{"role": "user", "content": "go"}]


class FakeMessages:
    def __init__(self, reply: Any) -> None:
        self.reply = reply
        self.kwargs: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def sdk_reply(tokens_in: int = 1000, cached: int | None = 0) -> SimpleNamespace:
    return SimpleNamespace(
        usage=SimpleNamespace(input_tokens=tokens_in, cache_read_input_tokens=cached, output_tokens=7),
        content=[
            SimpleNamespace(type="thinking", thinking="hidden"),
            SimpleNamespace(type="text", text=" You climb. "),
            SimpleNamespace(type="tool_use", id="t1", name="grant_xp", input={"kind": "minor"}),
        ],
    )


def client(reply: Any, base_url: str = "", think: bool = True) -> tuple[AnthropicClient, FakeMessages]:
    fake = FakeMessages(reply)
    return AnthropicClient("a-model", base_url, think, client=SimpleNamespace(messages=fake)), fake


def test_reply_is_translated_and_thinking_is_dropped() -> None:
    adapter, fake = client(sdk_reply())
    reply = adapter.complete(SYSTEM, MESSAGES, [{"name": "grant_xp"}])
    assert reply == LLMReply("You climb.", (ToolCall("t1", "grant_xp", {"kind": "minor"}),), 1000, 0, 7)
    assert fake.kwargs["model"] == "a-model"
    assert fake.kwargs["tools"] == [{"name": "grant_xp"}]
    assert "thinking" not in fake.kwargs
    assert {b["type"] for b in reply.blocks()} == {"text", "tool_use"}


def test_think_false_and_no_tools_are_passed_through() -> None:
    adapter, fake = client(sdk_reply(), think=False)
    adapter.complete(SYSTEM, MESSAGES, None)
    assert fake.kwargs["thinking"] == {"type": "disabled"}
    assert "tools" not in fake.kwargs


def test_d031_a_fast_call_skips_thinking() -> None:
    adapter, fake = client(sdk_reply())
    adapter.complete(SYSTEM, MESSAGES, None, fast=True)
    assert fake.kwargs["thinking"] == {"type": "disabled"}


def test_d027_a_truncated_local_prompt_fails_the_call() -> None:
    adapter, _ = client(sdk_reply(tokens_in=100), base_url="http://localhost")
    with pytest.raises(LLMUnavailable, match="OLLAMA_CONTEXT_LENGTH"):
        adapter.complete(SYSTEM, MESSAGES, None)


def test_d027_cached_tokens_count_as_read() -> None:
    adapter, _ = client(sdk_reply(tokens_in=100, cached=900), base_url="http://localhost")
    assert adapter.complete(SYSTEM, MESSAGES, None).tokens_cached == 900


def test_nar07_api_errors_become_llm_unavailable() -> None:
    adapter, _ = client(anthropic.APIConnectionError(request=SimpleNamespace()))  # type: ignore[arg-type]
    with pytest.raises(LLMUnavailable):
        adapter.complete(SYSTEM, MESSAGES, None)


def test_real_sdk_client_builds_for_a_local_server() -> None:
    assert AnthropicClient("a-model", "http://127.0.0.1:1").local is True


def test_mock_records_calls_and_ends_with_an_outage() -> None:
    mock = MockClient([LLMReply(text="hi")])
    assert mock.complete(SYSTEM, MESSAGES, None).text == "hi"
    assert mock.calls[0]["messages"] == MESSAGES
    with pytest.raises(LLMUnavailable):
        mock.complete(SYSTEM, MESSAGES, None)
