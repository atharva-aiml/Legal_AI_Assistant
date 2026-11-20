"""Row -> domain mappers shared by the SQL repositories. Every timestamp is
normalized to UTC here, whatever the Postgres session TimeZone was."""

from datetime import datetime, timezone

from app.domain.client import Client
from app.domain.deadline import Deadline, DeadlinePriority, DeadlineStatus
from app.domain.document import Document, DocumentStatus
from app.domain.lawyer import Lawyer, LawyerRole
from app.domain.matter import Matter, MatterStatus
from app.domain.notification import Notification
from app.domain.template import Template


def utc(value: datetime | None) -> datetime | None:
    return value.astimezone(timezone.utc) if value is not None else None


def _id(value) -> str | None:
    return str(value) if value is not None else None


def to_lawyer(row) -> Lawyer:
    return Lawyer(str(row["id"]), str(row["firm_id"]), row["name"], row["email"], LawyerRole(row["role"]), utc(row["created_at"]))


def to_client(row) -> Client:
    return Client(
        str(row["id"]), str(row["firm_id"]), row["name"], row["contact_email"], row["contact_phone"], row["notes"],
        utc(row["created_at"]), utc(row["updated_at"]),
    )


def to_matter(row) -> Matter:
    return Matter(
        str(row["id"]), str(row["firm_id"]), str(row["client_id"]), row["title"], MatterStatus(row["status"]),
        utc(row["closed_at"]), utc(row["created_at"]), utc(row["updated_at"]),
    )


def to_deadline(row) -> Deadline:
    return Deadline(
        str(row["id"]), str(row["matter_id"]), row["title"], row["due_date"], DeadlineStatus(row["status"]),
        DeadlinePriority(row["priority"]), row["notification_lead_days"], utc(row["created_at"]), utc(row["updated_at"]),
    )


def to_document(row) -> Document:
    return Document(
        str(row["id"]), str(row["matter_id"]), str(row["uploaded_by"]), row["file_name"], row["storage_key"],
        row["mime_type"], row["size_bytes"], DocumentStatus(row["status"]), row["is_draft"],
        _id(row["source_template_id"]), row["error_message"], utc(row["created_at"]),
    )


def to_notification(row) -> Notification:
    return Notification(
        str(row["id"]), str(row["lawyer_id"]), str(row["deadline_id"]), row["message"],
        utc(row["sent_at"]), utc(row["read_at"]), utc(row["created_at"]),
    )


def to_template(row) -> Template:
    return Template(str(row["id"]), _id(row["firm_id"]), row["name"], row["description"], row["body"], utc(row["created_at"]))
