import base64

from app.infrastructure.config import OPENAI_CHAT_MODEL
from app.infrastructure.llm import _get_client

# Spiked for real (2026-08-25) against 3 real embedded images from a real
# fixture, using the same OpenAI account/model already in use for chat — no
# new dependency. Confirmed: a real diagram gets its actual step sequence
# reconstructed (OCR alone returns disconnected words); a real near-blank
# filler image correctly returns NO_CONTENT rather than fabricated content.
_NO_CONTENT = "NO_CONTENT"

_CAPTION_SYSTEM_PROMPT = (
    "You are describing an image embedded in a legal case document, for a search "
    "index a lawyer will later query. Describe factually and specifically what the "
    "image shows -- diagram structure, labeled steps/arrows, any text visible in it "
    "(reproduce numbers/dates/amounts exactly as shown), what it appears to "
    "illustrate. Do not speculate about legal conclusions. 2-4 sentences. If the "
    f"image is blank, near-blank, purely decorative, or has no discernible "
    f"meaningful content at all, respond with exactly: {_NO_CONTENT}"
)


class OpenAIImageCaptioner:
    def caption(self, image_bytes: bytes) -> str | None:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        response = _get_client().chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": _CAPTION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this image."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ],
                },
            ],
        )
        text = (response.choices[0].message.content or "").strip()
        return None if not text or text == _NO_CONTENT else text
