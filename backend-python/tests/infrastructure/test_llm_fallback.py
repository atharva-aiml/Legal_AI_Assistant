"""The free-tier quota is per model, so a 429 on one model must fall through
to the next configured model — but any other failure must surface as-is
(ChatService turns it into ASSISTANT_UNAVAILABLE), never be retried silently."""
from types import SimpleNamespace

import httpx
import pytest
from openai import APIConnectionError, RateLimitError

from app.infrastructure import llm


def _rate_limit() -> RateLimitError:
    request = httpx.Request("POST", "https://example.invalid")
    return RateLimitError("quota", response=httpx.Response(429, request=request), body=None)


class _FakeClient:
    def __init__(self, outcomes: dict):
        self.outcomes = outcomes
        self.called: list[str] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, model, temperature, messages):
        self.called.append(model)
        outcome = self.outcomes[model]
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=outcome))])


@pytest.fixture
def fake(monkeypatch):
    def install(outcomes: dict):
        client = _FakeClient(outcomes)
        monkeypatch.setattr(llm, "LLM_CHAT_MODELS", list(outcomes))
        monkeypatch.setattr(llm, "_get_client", lambda: client)
        return client

    return install


def test_first_model_answers_without_touching_the_fallback(fake):
    client = fake({"primary": "answer [1]", "backup": "unused"})
    assert llm.GeminiChatLLM().generate("sys", "user") == "answer [1]"
    assert client.called == ["primary"]


def test_rate_limited_model_falls_through_to_next(fake):
    client = fake({"primary": _rate_limit(), "backup": "answer [1]"})
    assert llm.GeminiChatLLM().generate("sys", "user") == "answer [1]"
    assert client.called == ["primary", "backup"]


def test_every_model_rate_limited_raises(fake):
    fake({"primary": _rate_limit(), "backup": _rate_limit()})
    with pytest.raises(RateLimitError):
        llm.GeminiChatLLM().generate("sys", "user")


def test_non_quota_error_is_not_retried_on_another_model(fake):
    error = APIConnectionError(request=httpx.Request("POST", "https://example.invalid"))
    client = fake({"primary": error, "backup": "should not be used"})
    with pytest.raises(APIConnectionError):
        llm.GeminiChatLLM().generate("sys", "user")
    assert client.called == ["primary"]
