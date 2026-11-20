from dataclasses import dataclass
from datetime import datetime

from app.application.deadline_service import DeadlineService
from app.application.document_service import DocumentService
from app.application.matter_chat_service import AssistantUnavailableError, MatterChatService
from app.domain.deadline import DeadlineStatus

MAX_TITLE_LENGTH = 80


@dataclass(frozen=True)
class ActivityEntry:
    """I-32: not a new business rule — an aggregation of existing timestamped
    facts. `type` is a fixed discriminator ("document" | "deadline" | "chat")
    the UI uses to pick an icon."""

    type: str
    title: str
    timestamp: datetime


class ActivityService:
    """I-32: a read-only merge across Documents, Deadlines and Chat questions.
    Only a Chat *question* (role='user') becomes an entry — an ask-and-answer
    round trip is one activity, not two."""

    def __init__(self, document_service: DocumentService, deadline_service: DeadlineService, chat_service: MatterChatService) -> None:
        self.document_service = document_service
        self.deadline_service = deadline_service
        self.chat_service = chat_service

    def for_matter(self, firm_id: str, matter_id: str) -> list[ActivityEntry]:
        entries: list[ActivityEntry] = []

        for d in self.document_service.list(firm_id, matter_id):
            entries.append(ActivityEntry("document", f"Document uploaded: {d.file_name}", d.created_at))

        for dl in self.deadline_service.list(firm_id, matter_id):
            label = f"Deadline completed: {dl.title}" if dl.status == DeadlineStatus.complete else f"Deadline added: {dl.title}"
            entries.append(ActivityEntry("deadline", label, dl.updated_at))

        # Best-effort: the Assistant failing shouldn't blank out the whole
        # timeline when Documents/Deadlines can render on their own.
        try:
            for m in self.chat_service.history(matter_id).messages:
                if m.role != "user":
                    continue
                entries.append(ActivityEntry("chat", f"Question asked: {_truncate(m.content)}", m.created_at))
        except AssistantUnavailableError:
            pass

        # Stable sort, newest first — ties keep their insertion order.
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries


def _truncate(content: str) -> str:
    trimmed = content.strip()
    return trimmed if len(trimmed) <= MAX_TITLE_LENGTH else trimmed[: MAX_TITLE_LENGTH - 1] + "…"
