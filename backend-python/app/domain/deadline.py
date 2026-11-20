from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum

from app.domain.clock import utc_today


class InvalidDeadlineError(ValueError):
    pass


class DeadlineStatus(StrEnum):
    """Values match Postgres's native `deadline_status` enum labels byte-for-byte."""

    open = "open"
    complete = "complete"


class DeadlinePriority(StrEnum):
    """I-40. Values match Postgres's native `deadline_priority` enum labels."""

    standard = "standard"
    critical = "critical"


# REQ-009: "default: 3 days before + day-of."
DEFAULT_NOTIFICATION_LEAD_DAYS = 3
# I-40: every Deadline not explicitly marked otherwise is Standard priority.
DEFAULT_PRIORITY = DeadlinePriority.standard


@dataclass(frozen=True)
class NewDeadline:
    matter_id: str
    title: str
    due_date: date
    priority: DeadlinePriority
    notification_lead_days: int


@dataclass(frozen=True)
class Deadline:
    id: str
    matter_id: str
    title: str
    due_date: date
    status: DeadlineStatus
    priority: DeadlinePriority
    notification_lead_days: int
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def create(
        matter_id: str | None,
        title: str | None,
        due_date: date | None,
        priority: DeadlinePriority | None,
        notification_lead_days: int | None,
    ) -> NewDeadline:
        """BR-004: "A Deadline always has a due date and a linked Matter — it
        cannot exist standalone." A new Deadline always starts "open"."""
        if not matter_id:
            raise InvalidDeadlineError("A Deadline must belong to a Matter (BR-004).")
        trimmed = (title or "").strip()
        if not trimmed:
            raise InvalidDeadlineError("A Deadline title is required.")
        Deadline.validate_due_date(due_date)
        lead_days = notification_lead_days if notification_lead_days is not None else DEFAULT_NOTIFICATION_LEAD_DAYS
        if lead_days < 0:
            raise InvalidDeadlineError("Notification lead time can't be negative.")
        return NewDeadline(matter_id, trimmed, due_date, Deadline.resolve_priority(priority), lead_days)

    @staticmethod
    def resolve_priority(priority: DeadlinePriority | None) -> DeadlinePriority:
        """No validation beyond "default to Standard when unspecified"."""
        return priority if priority is not None else DEFAULT_PRIORITY

    @staticmethod
    def validate_title(title: str | None) -> str:
        trimmed = (title or "").strip()
        if not trimmed:
            raise InvalidDeadlineError("A Deadline title is required.")
        return trimmed

    @staticmethod
    def validate_due_date(due_date: date | None) -> date:
        """BR-009: "A Deadline's due date cannot be in the past — enforced at
        creation and at edit, not just at initial entry." Shared by create()
        and DeadlineService.update() whenever a caller supplies a new due date."""
        if due_date is None:
            raise InvalidDeadlineError("A Deadline must have a due date (BR-004).")
        if due_date < utc_today():
            raise InvalidDeadlineError("The due date can't be in the past (BR-009).")
        return due_date

    @staticmethod
    def validate_lead_days(lead_days: int) -> int:
        if lead_days < 0:
            raise InvalidDeadlineError("Notification lead time can't be negative.")
        return lead_days

    def is_notification_due_on(self, today: date) -> bool:
        """REQ-009: reminder days are lead-days-before and day-of. Pure — whether
        one was already sent today is a separate idempotency check."""
        return today == self.due_date - timedelta(days=self.notification_lead_days) or today == self.due_date

    @staticmethod
    def open_ones(deadlines: list["Deadline"]) -> list["Deadline"]:
        """BR-003: "A Matter cannot be marked Closed while it has one or more
        open (incomplete) Deadlines." Decides which already-fetched ones block."""
        return [d for d in deadlines if d.status == DeadlineStatus.open]
