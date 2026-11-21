from openai import OpenAI, RateLimitError

from app.infrastructure.config import GOOGLE_API_KEY, LLM_BASE_URL, LLM_CHAT_MODELS

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        # Gemini via its OpenAI-compatible endpoint — same `openai` SDK and
        # request shape as the former gpt-4o-mini integration. The timeout
        # bounds a free-tier stall (seen at 200s+ on some models in the spike)
        # so it surfaces as ASSISTANT_UNAVAILABLE instead of hanging the request.
        _client = OpenAI(api_key=GOOGLE_API_KEY, base_url=LLM_BASE_URL, timeout=120)
    return _client


def complete(messages: list[dict]) -> str:
    """One chat completion at temperature 0, trying each configured model in
    order. Only a 429 (per-model free-tier quota) falls through to the next
    model — any other error is a real failure and is raised as-is."""
    last_error: RateLimitError | None = None
    for model in LLM_CHAT_MODELS:
        try:
            response = _get_client().chat.completions.create(model=model, temperature=0, messages=messages)
        except RateLimitError as e:
            last_error = e
            continue
        return response.choices[0].message.content or ""
    assert last_error is not None, "LLM_CHAT_MODELS is empty"
    raise last_error


class GeminiChatLLM:
    """AI Architecture §3, Grounding Rule 7: temperature 0 — this is
    fact-retrieval behavior, not creative generation. Spiked for real against
    real Matters (Technology Decision Log, 2026-11-21) before wiring it in:
    same citations as the stored gpt-4o-mini baseline, correct not-found and
    metadata answers, an 83K-token full-context prompt answered in ~5s."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return complete([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
