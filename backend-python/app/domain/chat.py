from dataclasses import dataclass
from datetime import datetime

# REQ-007 / AI Architecture §5 Failure Modes: the fixed response when fused
# retrieval never clears the relevance threshold. Never LLM-generated text —
# always exactly this string, so the frontend/tests can key off it.
NOT_FOUND_RESPONSE = "I couldn't find that in this Matter's documents."

# Requirements §4 Non-Goals: "Case designing or legal strategy formulation";
# "Legal advice or legal decisions of any kind — the system retrieves and
# organizes; the lawyer decides." Distinct from NOT_FOUND_RESPONSE — the
# documents may say plenty on the topic, but the question itself asks for a
# strategic/adversarial judgment (e.g. "which side has stronger evidence",
# "should we settle") rather than for the content to be organized or
# restated. Confirmed as a real, separate case (2026-08-16): "what are the
# strongest documents for the developer" still wasn't answered even once
# the Assistant had the entire document — not a retrieval gap.
OUT_OF_SCOPE_RESPONSE = (
    "That's outside what I can help with. I can retrieve and organize information from "
    "this Matter's documents, but I don't offer legal strategy, opinions, or an assessment "
    "of which side has the stronger case — that judgment is yours to make."
)


class InvalidChatMessageException(Exception):
    pass


@dataclass(frozen=True)
class Citation:
    id: str
    chat_message_id: str
    document_id: str | None
    page_number: int | None
    excerpt: str | None
    file_name: str | None = None  # AI Architecture §4: "so the lawyer knows which uploaded file to check" — joined in, not a citations-table column
    section: str | None = None  # DOCX-adaptive chunking's analog of page_number — a real citations-table column, same permanence rule
    created_at: datetime | None = None


@dataclass(frozen=True)
class DocumentMetadata:
    """Real, system-computed facts about one Ready Document in a Matter —
    distinct from retrieved chunk *content*. Used to answer structural
    questions (page count, file name) that a document's own text can be
    wrong about (e.g. a mis-labeled 'Page N of 10' header on an 11-page
    file) — see the real bug this fixed in the Build Plan."""

    document_id: str
    file_name: str
    page_count: int | None  # None when not determinable (DOCX has no real page concept)


def metadata_excerpt(metadata: DocumentMetadata) -> str:
    """The excerpt text for a metadata-sourced citation — computed directly
    from real data, never LLM-authored, so it's provably accurate the same
    way a content citation's excerpt is the actual retrieved chunk text."""
    if metadata.page_count is None:
        return f"{metadata.file_name} — page count not available."
    return f"{metadata.file_name} has {metadata.page_count} page{'s' if metadata.page_count != 1 else ''}."


@dataclass(frozen=True)
class ChatMessage:
    id: str
    matter_id: str
    lawyer_id: str | None
    role: str  # 'user' | 'assistant'
    content: str
    created_at: datetime | None = None
    pinned: bool = False  # I-34: assistant answers only — enforced where it's set, not here
    # Edit-a-previous-message branching: a tree via two self-referencing
    # pointers (see SqlAlchemyChatRepository / ChatService for the walk).
    # Both None for a message with no parent/children yet.
    parent_id: str | None = None
    active_child_id: str | None = None


def validate_assistant_message(content: str, citations: list[Citation]) -> None:
    """BR-006: 'every AI Assistant answer carries at least one citation, or
    explicitly states the information wasn't found — no uncited factual
    claims.' Enforced here as a real invariant, not just a prompt
    instruction — an assistant message that claims something without
    citing it can never be constructed through this codebase."""
    if content not in (NOT_FOUND_RESPONSE, OUT_OF_SCOPE_RESPONSE) and not citations:
        raise InvalidChatMessageException(
            "BR-006: an assistant answer must carry at least one citation, "
            "unless it's the fixed not-found or out-of-scope response."
        )
