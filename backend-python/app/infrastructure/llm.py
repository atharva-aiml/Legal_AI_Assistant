from openai import OpenAI

from app.infrastructure.config import OPENAI_API_KEY, OPENAI_CHAT_MODEL

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


class OpenAIChatLLM:
    """AI Architecture §3, Grounding Rule 7: temperature 0 — this is
    fact-retrieval behavior, not creative generation. Spiked for real
    against gpt-4o-mini (Technology Decision Log) before wiring it in here."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = _get_client().chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""
