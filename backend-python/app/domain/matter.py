from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class InvalidMatterError(ValueError):
    pass


class MatterStatus(StrEnum):
    """Values match Postgres's native `matter_status` enum labels byte-for-byte."""

    open = "open"
    closed = "closed"


@dataclass(frozen=True)
class NewMatter:
    firm_id: str
    client_id: str
    title: str
    status: MatterStatus


@dataclass(frozen=True)
class Matter:
    id: str
    firm_id: str
    client_id: str
    title: str
    status: MatterStatus
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def create(firm_id: str | None, client_id: str | None, title: str | None) -> NewMatter:
        """BR-001: a Matter must belong to exactly one Client. Enforced here as
        "client_id is required" — the domain-layer half of the invariant; the
        real repository's FK constraint is the storage-layer half. A new Matter
        always starts "open"."""
        trimmed = (title or "").strip()
        if not trimmed:
            raise InvalidMatterError("Matter title is required.")
        if not client_id:
            raise InvalidMatterError("A Matter must belong to a Client (BR-001).")
        if not firm_id:
            raise InvalidMatterError("A Matter must belong to a Firm (BR-008).")
        return NewMatter(firm_id, client_id, trimmed, MatterStatus.open)

    @staticmethod
    def rename_title(title: str | None) -> str:
        """Renaming keeps the same "non-empty title" invariant as creation."""
        trimmed = (title or "").strip()
        if not trimmed:
            raise InvalidMatterError("Matter title is required.")
        return trimmed

    @staticmethod
    def validate_reopen(current_status: MatterStatus) -> None:
        """I-35: the counterpart to closing — only meaningful from Closed."""
        if current_status != MatterStatus.closed:
            raise InvalidMatterError("Only a Closed Matter can be reopened.")


@dataclass(frozen=True)
class MatterView:
    """I-07: a lightweight fact — "this Lawyer had this Matter open at this
    time" — not an invariant-bearing entity, so no factory/validation. The one
    behavior worth testing (re-viewing moves it to the top without duplicating)
    is a repository/ordering concern, covered at the application layer."""

    lawyer_id: str
    matter_id: str
    viewed_at: datetime
