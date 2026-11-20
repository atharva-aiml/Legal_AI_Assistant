import uuid
from datetime import date, timedelta

from sqlalchemy import text

from app.application.crud_ports import DeadlineWithFirm
from app.domain.clock import utc_now, utc_today
from app.domain.deadline import Deadline, DeadlinePriority, DeadlineStatus, NewDeadline
from app.domain.document import Document, DocumentStatus, NewDocument, NewDraftDocument
from app.infrastructure.persistence.connection import connection
from app.infrastructure.persistence.mappers import to_deadline, to_document

# Deadline and Document carry no firm_id of their own (only matter_id) —
# BR-008 isolation is enforced with a subquery join to matters, same invariant
# as everywhere else, just expressed at the SQL level.
_IN_FIRM = "matter_id IN (SELECT m.id FROM matters m WHERE m.firm_id = :firm_id)"


class SqlDeadlineRepository:
    def create(self, record: NewDeadline) -> Deadline:
        now = utc_now()
        with connection() as conn:
            row = conn.execute(
                text(
                    "INSERT INTO deadlines (id, matter_id, title, due_date, status, priority, notification_lead_days, created_at, updated_at) "
                    "VALUES (:id, :matter_id, :title, :due_date, :status, :priority, :lead, :now, :now) RETURNING *"
                ),
                {"id": str(uuid.uuid4()), "matter_id": record.matter_id, "title": record.title, "due_date": record.due_date,
                 "status": DeadlineStatus.open.value, "priority": record.priority.value, "lead": record.notification_lead_days, "now": now},
            ).mappings().one()
        return to_deadline(row)

    def list_by_matter(self, firm_id: str, matter_id: str) -> list[Deadline]:
        with connection() as conn:
            rows = conn.execute(
                text(f"SELECT * FROM deadlines WHERE matter_id = :matter_id AND {_IN_FIRM} ORDER BY due_date ASC"),
                {"matter_id": matter_id, "firm_id": firm_id},
            ).mappings().all()
        return [to_deadline(r) for r in rows]

    def find_by_id(self, firm_id: str, deadline_id: str) -> Deadline | None:
        with connection() as conn:
            row = conn.execute(text(f"SELECT * FROM deadlines WHERE id = :id AND {_IN_FIRM}"), {"id": deadline_id, "firm_id": firm_id}).mappings().first()
        return to_deadline(row) if row else None

    def update(self, firm_id: str, deadline_id: str, title: str, due_date: date, status: DeadlineStatus, priority: DeadlinePriority, notification_lead_days: int) -> Deadline | None:
        with connection() as conn:
            row = conn.execute(
                text(
                    "UPDATE deadlines SET title = :title, due_date = :due_date, status = :status, priority = :priority, "
                    f"notification_lead_days = :lead, updated_at = :now WHERE id = :id AND {_IN_FIRM} RETURNING *"
                ),
                {"id": deadline_id, "firm_id": firm_id, "title": title, "due_date": due_date, "status": status.value,
                 "priority": priority.value, "lead": notification_lead_days, "now": utc_now()},
            ).mappings().first()
        return to_deadline(row) if row else None

    def list_upcoming(self, firm_id: str, days: int) -> list[Deadline]:
        cutoff = utc_today() + timedelta(days=days)
        with connection() as conn:
            rows = conn.execute(
                text(f"SELECT * FROM deadlines WHERE status = :status AND due_date <= :cutoff AND {_IN_FIRM} ORDER BY due_date ASC"),
                {"status": DeadlineStatus.open.value, "cutoff": cutoff, "firm_id": firm_id},
            ).mappings().all()
        return [to_deadline(r) for r in rows]

    def list_all_open_with_firm(self) -> list[DeadlineWithFirm]:
        with connection() as conn:
            rows = conn.execute(
                text("SELECT d.*, m.firm_id AS matter_firm_id FROM deadlines d JOIN matters m ON m.id = d.matter_id WHERE d.status = :status"),
                {"status": DeadlineStatus.open.value},
            ).mappings().all()
        return [DeadlineWithFirm(to_deadline(r), str(r["matter_firm_id"])) for r in rows]

    def delete_by_matter(self, matter_id: str) -> None:
        with connection() as conn:
            conn.execute(text("DELETE FROM deadlines WHERE matter_id = :matter_id"), {"matter_id": matter_id})


class SqlDocumentRepository:
    def _insert(self, matter_id, uploaded_by, file_name, storage_key, mime_type, size_bytes, is_draft: bool, source_template_id) -> Document:
        with connection() as conn:
            row = conn.execute(
                text(
                    "INSERT INTO documents (id, matter_id, uploaded_by, file_name, storage_key, mime_type, size_bytes, status, is_draft, source_template_id, created_at) "
                    "VALUES (:id, :matter_id, :uploaded_by, :file_name, :storage_key, :mime_type, :size_bytes, :status, :is_draft, :source_template_id, :now) RETURNING *"
                ),
                {"id": str(uuid.uuid4()), "matter_id": matter_id, "uploaded_by": uploaded_by, "file_name": file_name,
                 "storage_key": storage_key, "mime_type": mime_type, "size_bytes": size_bytes, "status": DocumentStatus.uploading.value,
                 "is_draft": is_draft, "source_template_id": source_template_id, "now": utc_now()},
            ).mappings().one()
        return to_document(row)

    def create(self, record: NewDocument) -> Document:
        return self._insert(record.matter_id, record.uploaded_by, record.file_name, record.storage_key, record.mime_type, record.size_bytes, False, None)

    def create_draft(self, record: NewDraftDocument) -> Document:
        return self._insert(record.matter_id, record.uploaded_by, record.file_name, record.storage_key, record.mime_type, record.size_bytes, True, record.source_template_id)

    def list_by_matter(self, firm_id: str, matter_id: str) -> list[Document]:
        with connection() as conn:
            rows = conn.execute(text(f"SELECT * FROM documents WHERE matter_id = :matter_id AND {_IN_FIRM}"), {"matter_id": matter_id, "firm_id": firm_id}).mappings().all()
        return [to_document(r) for r in rows]

    def find_by_id(self, firm_id: str, document_id: str) -> Document | None:
        with connection() as conn:
            row = conn.execute(text(f"SELECT * FROM documents WHERE id = :id AND {_IN_FIRM}"), {"id": document_id, "firm_id": firm_id}).mappings().first()
        return to_document(row) if row else None

    def update_status(self, document_id: str, status: DocumentStatus, error_message: str | None) -> None:
        with connection() as conn:
            conn.execute(text("UPDATE documents SET status = :status, error_message = :msg WHERE id = :id"),
                         {"id": document_id, "status": status.value, "msg": error_message})

    def delete(self, firm_id: str, document_id: str) -> bool:
        with connection() as conn:
            result = conn.execute(text(f"DELETE FROM documents WHERE id = :id AND {_IN_FIRM}"), {"id": document_id, "firm_id": firm_id})
        return result.rowcount > 0
