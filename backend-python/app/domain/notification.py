from dataclasses import dataclass
from datetime import datetime


class InvalidNotificationError(ValueError):
    pass


@dataclass(frozen=True)
class NewNotification:
    lawyer_id: str
    deadline_id: str
    message: str


@dataclass(frozen=True)
class Notification:
    id: str
    lawyer_id: str
    deadline_id: str
    message: str
    sent_at: datetime | None
    read_at: datetime | None
    created_at: datetime

    @staticmethod
    def create(lawyer_id: str | None, deadline_id: str | None, message: str | None) -> NewNotification:
        """REQ-009: a Notification always names a recipient Lawyer and the Deadline it's about."""
        if not lawyer_id:
            raise InvalidNotificationError("A Notification must have a recipient Lawyer.")
        if not deadline_id:
            raise InvalidNotificationError("A Notification must reference a Deadline.")
        trimmed = (message or "").strip()
        if not trimmed:
            raise InvalidNotificationError("A Notification message is required.")
        return NewNotification(lawyer_id, deadline_id, trimmed)
