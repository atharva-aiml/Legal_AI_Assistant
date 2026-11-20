import uuid
from datetime import date

from sqlalchemy import text

from app.domain.clock import utc_now
from app.domain.notification import NewNotification, Notification
from app.infrastructure.persistence.connection import connection
from app.infrastructure.persistence.mappers import to_notification, utc


class SqlNotificationRepository:
    def list_by_lawyer(self, lawyer_id: str) -> list[Notification]:
        with connection() as conn:
            rows = conn.execute(
                text("SELECT * FROM notifications WHERE lawyer_id = :lawyer_id ORDER BY created_at DESC"), {"lawyer_id": lawyer_id}
            ).mappings().all()
        return [to_notification(r) for r in rows]

    def mark_read(self, lawyer_id: str, notification_id: str) -> Notification | None:
        with connection() as conn:
            row = conn.execute(
                text("UPDATE notifications SET read_at = :now WHERE id = :id AND lawyer_id = :lawyer_id RETURNING *"),
                {"id": notification_id, "lawyer_id": lawyer_id, "now": utc_now()},
            ).mappings().first()
        return to_notification(row) if row else None

    def mark_all_read(self, lawyer_id: str) -> int:
        """I-44: one bulk UPDATE, only ever touching this Lawyer's still-unread rows."""
        with connection() as conn:
            result = conn.execute(
                text("UPDATE notifications SET read_at = :now WHERE lawyer_id = :lawyer_id AND read_at IS NULL"),
                {"lawyer_id": lawyer_id, "now": utc_now()},
            )
        return result.rowcount

    def create(self, record: NewNotification) -> Notification:
        now = utc_now()
        with connection() as conn:
            row = conn.execute(
                text(
                    "INSERT INTO notifications (id, lawyer_id, deadline_id, message, sent_at, created_at) "
                    "VALUES (:id, :lawyer_id, :deadline_id, :message, :now, :now) RETURNING *"
                ),
                # In-app only for now (Build Plan V0.5 scope note) — "sent" the moment it's created.
                {"id": str(uuid.uuid4()), "lawyer_id": record.lawyer_id, "deadline_id": record.deadline_id, "message": record.message, "now": now},
            ).mappings().one()
        return to_notification(row)

    def exists_for_deadline_and_lawyer_on_day(self, deadline_id: str, lawyer_id: str, day: date) -> bool:
        # The "same day" check is done here in Python against UTC, deliberately
        # not a DB-side ::date CAST — that depends on the Postgres session
        # TimeZone, a documented source of bugs on this machine (CLAUDE.md §4).
        # The result set is tiny (a handful of rows per pair at most).
        with connection() as conn:
            rows = conn.execute(
                text("SELECT created_at FROM notifications WHERE deadline_id = :deadline_id AND lawyer_id = :lawyer_id"),
                {"deadline_id": deadline_id, "lawyer_id": lawyer_id},
            ).all()
        return any(utc(r[0]).date() == day for r in rows)
