from __future__ import annotations

from app.application.crud_ports import (
    ChatMessageRepository,
    DeadlineRepository,
    MatterRepository,
    MatterViewRepository,
    UnitOfWork,
)
from app.application.document_service import DocumentService
from app.domain.deadline import Deadline
from app.domain.matter import Matter, MatterStatus


class MatterHasOpenDeadlinesError(Exception):
    """Carries the specific blocking Deadlines so the API/UI can name them, not just say "blocked"."""

    def __init__(self, open_deadlines: list[Deadline]) -> None:
        super().__init__("Matter cannot be closed while it has open Deadlines (BR-003).")
        self.open_deadlines = open_deadlines


class MatterService:
    """Depends on DeadlineRepository too — BR-003 is inherently cross-entity:
    deciding whether a close is allowed requires the Matter's Deadlines. Also
    owns the single-Matter cascade delete that ClientService reuses."""

    def __init__(
        self,
        repository: MatterRepository,
        deadline_repository: DeadlineRepository,
        document_service: DocumentService,
        chat_message_repository: ChatMessageRepository,
        matter_view_repository: MatterViewRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self.repository = repository
        self.deadline_repository = deadline_repository
        self.document_service = document_service
        self.chat_message_repository = chat_message_repository
        self.matter_view_repository = matter_view_repository
        self.unit_of_work = unit_of_work

    def create(self, firm_id: str, client_id: str | None, title: str | None) -> Matter:
        """Validated by the domain layer before the repository is ever touched."""
        return self.repository.create(Matter.create(firm_id, client_id, title))

    def list(self, firm_id: str, client_id: str | None, status: MatterStatus | None) -> list[Matter]:
        """I-23: status is filtered here, in-memory — the Firm's Matter volume never justifies a new query."""
        matters = self.repository.list_by_client(firm_id, client_id) if client_id else self.repository.list_by_firm(firm_id)
        return matters if status is None else [m for m in matters if m.status == status]

    def get(self, firm_id: str, matter_id: str) -> Matter | None:
        """BR-008: a Matter outside the caller's Firm resolves to None, not an error."""
        return self.repository.find_by_id(firm_id, matter_id)

    def rename(self, firm_id: str, matter_id: str, title: str | None) -> Matter | None:
        validated = Matter.rename_title(title)
        return self.repository.update_title(firm_id, matter_id, validated)

    def close(self, firm_id: str, matter_id: str) -> Matter | None:
        """REQ-010/BR-003: closes the Matter unless it has open Deadlines — then
        raises, naming exactly which ones. None means not found (BR-008)."""
        if self.repository.find_by_id(firm_id, matter_id) is None:
            return None
        open_deadlines = Deadline.open_ones(self.deadline_repository.list_by_matter(firm_id, matter_id))
        if open_deadlines:
            raise MatterHasOpenDeadlinesError(open_deadlines)
        return self.repository.close(firm_id, matter_id)

    def reopen(self, firm_id: str, matter_id: str) -> Matter | None:
        """I-35: BR-008 first, then the domain "must actually be Closed" check."""
        existing = self.repository.find_by_id(firm_id, matter_id)
        if existing is None:
            return None
        Matter.validate_reopen(existing.status)
        return self.repository.reopen(firm_id, matter_id)

    def delete_cascade(self, firm_id: str, matter_id: str) -> bool:
        """Cascade-deletes one Matter: its Documents (through DocumentService, so
        stored files are cleaned up too, never orphaned), then Deadlines, then
        chat_messages, then matter_views, then the Matter row — in one
        transaction, because no FK-level ON DELETE CASCADE exists from matters
        to any of those (CLAUDE.md §4). document_chunks, citations and
        notifications cascade automatically at the DB level.

        BR-008: returns False (nothing deleted) for an unknown/other-Firm Matter."""
        with self.unit_of_work.transaction():
            if self.repository.find_by_id(firm_id, matter_id) is None:
                return False

            for document in self.document_service.list(firm_id, matter_id):
                self.document_service.delete(firm_id, document.id)
            self.deadline_repository.delete_by_matter(matter_id)
            self.chat_message_repository.delete_by_matter(matter_id)
            self.matter_view_repository.delete_by_matter(matter_id)
            return self.repository.delete(firm_id, matter_id)
