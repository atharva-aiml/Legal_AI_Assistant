from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class InvalidLawyerError(ValueError):
    pass


class LawyerRole(StrEnum):
    """Values match Postgres's native `lawyer_role` enum labels byte-for-byte."""

    owner = "owner"
    member = "member"


@dataclass(frozen=True)
class Firm:
    id: str
    name: str
    created_at: datetime


@dataclass(frozen=True)
class Lawyer:
    """Never carries password_hash — that stays inside the auth infrastructure layer."""

    id: str
    firm_id: str
    name: str
    email: str
    role: LawyerRole
    created_at: datetime

    @staticmethod
    def validate_name(name: str | None) -> str:
        """I-51: same "name is required" invariant as registration — editing can't leave a Lawyer nameless either."""
        trimmed = (name or "").strip()
        if not trimmed:
            raise InvalidLawyerError("Name is required.")
        return trimmed

    @staticmethod
    def validate_new_password(new_password: str | None) -> str:
        """I-51: same 8+ character minimum AuthService.register enforces for a new account's password."""
        if new_password is None or len(new_password) < 8:
            raise InvalidLawyerError("A new password must be at least 8 characters.")
        return new_password


@dataclass(frozen=True)
class LawyerPreferences:
    """I-52: a per-Lawyer notification preference. Deadline reminders are the
    only notification type that exists today (SD-006), so a single boolean is
    the honest shape — a multi-type preferences map would be speculative until
    a second notification type actually exists."""

    lawyer_id: str
    deadline_reminders_enabled: bool

    @staticmethod
    def default_for(lawyer_id: str | None) -> "LawyerPreferences":
        """Before I-52, every Lawyer in a Firm received every Deadline reminder
        with no way to opt out — a Lawyer who has never touched this setting must
        keep getting reminders exactly as before, so "no preference row yet"
        defaults to enabled, not disabled."""
        if not lawyer_id:
            raise InvalidLawyerError("Preferences must belong to a real Lawyer.")
        return LawyerPreferences(lawyer_id=lawyer_id, deadline_reminders_enabled=True)
