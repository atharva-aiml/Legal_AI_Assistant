import uuid

from sqlalchemy import text

from app.domain.client import Client, NewClient
from app.domain.clock import utc_now
from app.domain.matter import Matter, MatterStatus, MatterView, NewMatter
from app.infrastructure.persistence.connection import connection
from app.infrastructure.persistence.mappers import to_client, to_matter, utc

# No ORDER BY on the plain list queries — deliberately the same as the former
# Spring Data findByFirmId/findByFirmIdAndClientId, so list order is unchanged.


class SqlClientRepository:
    def create(self, record: NewClient) -> Client:
        now = utc_now()
        with connection() as conn:
            row = conn.execute(
                text(
                    "INSERT INTO clients (id, firm_id, name, contact_email, contact_phone, notes, created_at, updated_at) "
                    "VALUES (:id, :firm_id, :name, :contact_email, :contact_phone, :notes, :now, :now) RETURNING *"
                ),
                {"id": str(uuid.uuid4()), "firm_id": record.firm_id, "name": record.name, "contact_email": record.contact_email,
                 "contact_phone": record.contact_phone, "notes": record.notes, "now": now},
            ).mappings().one()
        return to_client(row)

    def list_by_firm(self, firm_id: str) -> list[Client]:
        with connection() as conn:
            rows = conn.execute(text("SELECT * FROM clients WHERE firm_id = :firm_id"), {"firm_id": firm_id}).mappings().all()
        return [to_client(r) for r in rows]

    def find_by_id(self, firm_id: str, client_id: str) -> Client | None:
        with connection() as conn:
            row = conn.execute(text("SELECT * FROM clients WHERE id = :id AND firm_id = :firm_id"), {"id": client_id, "firm_id": firm_id}).mappings().first()
        return to_client(row) if row else None

    def update(self, firm_id: str, client_id: str, name: str, contact_email: str | None, contact_phone: str | None, notes: str | None) -> Client | None:
        with connection() as conn:
            row = conn.execute(
                text(
                    "UPDATE clients SET name = :name, contact_email = :contact_email, contact_phone = :contact_phone, "
                    "notes = :notes, updated_at = :now WHERE id = :id AND firm_id = :firm_id RETURNING *"
                ),
                {"id": client_id, "firm_id": firm_id, "name": name, "contact_email": contact_email,
                 "contact_phone": contact_phone, "notes": notes, "now": utc_now()},
            ).mappings().first()
        return to_client(row) if row else None

    def delete(self, firm_id: str, client_id: str) -> bool:
        with connection() as conn:
            result = conn.execute(text("DELETE FROM clients WHERE id = :id AND firm_id = :firm_id"), {"id": client_id, "firm_id": firm_id})
        return result.rowcount > 0


class SqlMatterRepository:
    def create(self, record: NewMatter) -> Matter:
        now = utc_now()
        with connection() as conn:
            row = conn.execute(
                text(
                    "INSERT INTO matters (id, firm_id, client_id, title, status, created_at, updated_at) "
                    "VALUES (:id, :firm_id, :client_id, :title, :status, :now, :now) RETURNING *"
                ),
                {"id": str(uuid.uuid4()), "firm_id": record.firm_id, "client_id": record.client_id, "title": record.title,
                 "status": record.status.value, "now": now},
            ).mappings().one()
        return to_matter(row)

    def list_by_firm(self, firm_id: str) -> list[Matter]:
        with connection() as conn:
            rows = conn.execute(text("SELECT * FROM matters WHERE firm_id = :firm_id"), {"firm_id": firm_id}).mappings().all()
        return [to_matter(r) for r in rows]

    def list_by_client(self, firm_id: str, client_id: str) -> list[Matter]:
        with connection() as conn:
            rows = conn.execute(
                text("SELECT * FROM matters WHERE firm_id = :firm_id AND client_id = :client_id"), {"firm_id": firm_id, "client_id": client_id}
            ).mappings().all()
        return [to_matter(r) for r in rows]

    def find_by_id(self, firm_id: str, matter_id: str) -> Matter | None:
        with connection() as conn:
            row = conn.execute(text("SELECT * FROM matters WHERE id = :id AND firm_id = :firm_id"), {"id": matter_id, "firm_id": firm_id}).mappings().first()
        return to_matter(row) if row else None

    def _update(self, firm_id: str, matter_id: str, assignments: str, params: dict) -> Matter | None:
        with connection() as conn:
            row = conn.execute(
                text(f"UPDATE matters SET {assignments} WHERE id = :id AND firm_id = :firm_id RETURNING *"),
                {"id": matter_id, "firm_id": firm_id, **params},
            ).mappings().first()
        return to_matter(row) if row else None

    def update_title(self, firm_id: str, matter_id: str, title: str) -> Matter | None:
        return self._update(firm_id, matter_id, "title = :title, updated_at = :now", {"title": title, "now": utc_now()})

    def close(self, firm_id: str, matter_id: str) -> Matter | None:
        return self._update(firm_id, matter_id, "status = :status, closed_at = :now, updated_at = :now",
                            {"status": MatterStatus.closed.value, "now": utc_now()})

    def reopen(self, firm_id: str, matter_id: str) -> Matter | None:
        return self._update(firm_id, matter_id, "status = :status, closed_at = NULL, updated_at = :now",
                            {"status": MatterStatus.open.value, "now": utc_now()})

    def delete(self, firm_id: str, matter_id: str) -> bool:
        with connection() as conn:
            result = conn.execute(text("DELETE FROM matters WHERE id = :id AND firm_id = :firm_id"), {"id": matter_id, "firm_id": firm_id})
        return result.rowcount > 0


class SqlMatterViewRepository:
    def record_view(self, lawyer_id: str, matter_id: str) -> None:
        """One row per (lawyer_id, matter_id) — I-07's unique index lets Postgres
        insert-or-bump atomically, no read-then-decide round trip."""
        with connection() as conn:
            conn.execute(
                text(
                    "INSERT INTO matter_views (lawyer_id, matter_id, viewed_at) VALUES (:lawyer_id, :matter_id, now()) "
                    "ON CONFLICT (lawyer_id, matter_id) DO UPDATE SET viewed_at = now()"
                ),
                {"lawyer_id": lawyer_id, "matter_id": matter_id},
            )

    def list_recently_viewed(self, lawyer_id: str, limit: int) -> list[MatterView]:
        with connection() as conn:
            rows = conn.execute(
                text("SELECT lawyer_id, matter_id, viewed_at FROM matter_views WHERE lawyer_id = :lawyer_id ORDER BY viewed_at DESC LIMIT :limit"),
                {"lawyer_id": lawyer_id, "limit": limit},
            ).mappings().all()
        return [MatterView(str(r["lawyer_id"]), str(r["matter_id"]), utc(r["viewed_at"])) for r in rows]

    def delete_by_matter(self, matter_id: str) -> None:
        with connection() as conn:
            conn.execute(text("DELETE FROM matter_views WHERE matter_id = :matter_id"), {"matter_id": matter_id})


class SqlChatMessageRepository:
    """Cascade-delete only (see crud_ports.ChatMessageRepository).

    One set-based DELETE, never row-by-row: chat_messages is a tree
    (parent_id ON DELETE CASCADE), so deleting a parent already removes its
    children. The former Java/Hibernate implementation deleted row-by-row,
    hit an already-cascaded child (StaleStateException), and rolled back —
    every Matter/Client delete with chat history failed with a 500. Citations
    cascade off chat_messages, and matters.active_root_message_id is SET NULL,
    both at the DB level."""

    def delete_by_matter(self, matter_id: str) -> None:
        with connection() as conn:
            conn.execute(text("DELETE FROM chat_messages WHERE matter_id = :matter_id"), {"matter_id": matter_id})
