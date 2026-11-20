"""The Matter-scoped Chat facade the public /api layer talks to (the former
Java ChatService). Thin by design: the web layer owns auth and Matter
ownership (BR-008); the AI Chat module (chat_service.py, SD-005) owns the
entire chat domain — retrieval, generation, grounding rules, persistence.
This only relays, through the ChatGateway port, so the web layer never
depends on the AI module directly."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class CitationDto:
    id: str
    document_id: str | None
    file_name: str | None
    page_number: int | None
    section: str | None
    excerpt: str | None


@dataclass(frozen=True)
class ChatMessageDto:
    id: str
    matter_id: str
    lawyer_id: str | None
    role: str
    content: str
    created_at: datetime | None
    citations: list[CitationDto]
    # Ephemeral, computed only for the question that produced them — None on history.
    low_confidence: bool | None
    full_context: bool | None
    pinned: bool | None
    # Edit-a-previous-message branching: None for a root-level message.
    parent_id: str | None
    # Ordered ids of every message sharing this parent, itself included.
    sibling_ids: list[str] | None


@dataclass(frozen=True)
class ChatHistoryDto:
    messages: list[ChatMessageDto]


@dataclass(frozen=True)
class PinToggleDto:
    id: str
    pinned: bool


class NoReadyDocumentsError(Exception):
    """422: the Matter has no ready Document yet — nothing to ground an answer in."""


class ChatMessageNotFoundError(Exception):
    """404: no message with that id in this Matter."""


class InvalidEditTargetError(Exception):
    """400: the message exists but isn't a 'user' message."""


class AssistantUnavailableError(Exception):
    """502: retrieval or the LLM call itself failed — a system fault, not a content gap."""


class ChatGateway(Protocol):
    def ask(self, matter_id: str, lawyer_id: str, question: str) -> ChatMessageDto: ...
    def history(self, matter_id: str) -> ChatHistoryDto: ...
    def toggle_pin(self, matter_id: str, message_id: str, pinned: bool) -> PinToggleDto: ...
    def edit_message(self, matter_id: str, message_id: str, lawyer_id: str, question: str) -> ChatHistoryDto: ...
    def activate_branch(self, matter_id: str, message_id: str) -> ChatHistoryDto: ...


class MatterChatService:
    def __init__(self, gateway: ChatGateway) -> None:
        self.gateway = gateway

    def ask(self, matter_id: str, lawyer_id: str, question: str) -> ChatMessageDto:
        return self.gateway.ask(matter_id, lawyer_id, question)

    def history(self, matter_id: str) -> ChatHistoryDto:
        return self.gateway.history(matter_id)

    def toggle_pin(self, matter_id: str, message_id: str, pinned: bool) -> PinToggleDto:
        return self.gateway.toggle_pin(matter_id, message_id, pinned)

    def edit_message(self, matter_id: str, message_id: str, lawyer_id: str, question: str) -> ChatHistoryDto:
        """ChatGPT-style edit: creates a new sibling branch, never deletes/overwrites the original."""
        return self.gateway.edit_message(matter_id, message_id, lawyer_id, question)

    def activate_branch(self, matter_id: str, message_id: str) -> ChatHistoryDto:
        """Repoints which sibling branch is active. Generates nothing new."""
        return self.gateway.activate_branch(matter_id, message_id)
