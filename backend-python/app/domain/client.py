from dataclasses import dataclass
from datetime import datetime


class InvalidClientError(ValueError):
    pass


def _blank_to_none(value: str | None) -> str | None:
    return None if value is None or not value.strip() else value


@dataclass(frozen=True)
class NewClient:
    firm_id: str
    name: str
    contact_email: str | None
    contact_phone: str | None
    notes: str | None


@dataclass(frozen=True)
class UpdatedClientFields:
    name: str
    contact_email: str | None
    contact_phone: str | None
    notes: str | None


@dataclass(frozen=True)
class Client:
    id: str
    firm_id: str
    name: str
    contact_email: str | None
    contact_phone: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def create(firm_id: str | None, name: str | None, contact_email: str | None, contact_phone: str | None, notes: str | None) -> NewClient:
        """BR-008: every tenant-owned row carries firm_id — enforced here as "firm_id is required"."""
        trimmed = (name or "").strip()
        if not trimmed:
            raise InvalidClientError("Name is required")
        if not firm_id:
            raise InvalidClientError("A Client must belong to a Firm (BR-008).")
        return NewClient(firm_id, trimmed, _blank_to_none(contact_email), _blank_to_none(contact_phone), _blank_to_none(notes))

    @staticmethod
    def update(name: str | None, contact_email: str | None, contact_phone: str | None, notes: str | None) -> UpdatedClientFields:
        """I-17: same "name is required" invariant as create() — editing can't leave a Client nameless either."""
        trimmed = (name or "").strip()
        if not trimmed:
            raise InvalidClientError("Name is required")
        return UpdatedClientFields(trimmed, _blank_to_none(contact_email), _blank_to_none(contact_phone), _blank_to_none(notes))
