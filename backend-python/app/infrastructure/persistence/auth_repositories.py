import uuid
from datetime import datetime

from sqlalchemy import text

from app.application.crud_ports import LawyerWithHash
from app.domain.clock import utc_now
from app.domain.lawyer import Firm, Lawyer, LawyerPreferences, LawyerRole
from app.infrastructure.persistence.connection import connection
from app.infrastructure.persistence.mappers import to_lawyer, utc


def _with_hash(row) -> LawyerWithHash:
    return LawyerWithHash(to_lawyer(row), row["password_hash"])


class SqlLawyerRepository:
    def find_by_email_with_hash(self, email: str) -> LawyerWithHash | None:
        with connection() as conn:
            row = conn.execute(text("SELECT * FROM lawyers WHERE email = :email"), {"email": email}).mappings().first()
        return _with_hash(row) if row else None

    def find_by_id(self, lawyer_id: str) -> Lawyer | None:
        found = self.find_by_id_with_hash(lawyer_id)
        return found.lawyer if found else None

    def find_by_id_with_hash(self, lawyer_id: str) -> LawyerWithHash | None:
        with connection() as conn:
            row = conn.execute(text("SELECT * FROM lawyers WHERE id = :id"), {"id": lawyer_id}).mappings().first()
        return _with_hash(row) if row else None

    def list_by_firm(self, firm_id: str) -> list[Lawyer]:
        with connection() as conn:
            rows = conn.execute(text("SELECT * FROM lawyers WHERE firm_id = :firm_id"), {"firm_id": firm_id}).mappings().all()
        return [to_lawyer(r) for r in rows]

    def create(self, firm_id: str, name: str, email: str, password_hash: str) -> LawyerWithHash:
        with connection() as conn:
            row = conn.execute(
                text(
                    "INSERT INTO lawyers (id, firm_id, name, email, password_hash, role, created_at) "
                    "VALUES (:id, :firm_id, :name, :email, :password_hash, :role, :created_at) RETURNING *"
                ),
                {"id": str(uuid.uuid4()), "firm_id": firm_id, "name": name, "email": email, "password_hash": password_hash,
                 "role": LawyerRole.owner.value, "created_at": utc_now()},
            ).mappings().one()
        return _with_hash(row)

    def create_firm(self, name: str) -> Firm:
        with connection() as conn:
            row = conn.execute(
                text("INSERT INTO firms (id, name, created_at) VALUES (:id, :name, :created_at) RETURNING *"),
                {"id": str(uuid.uuid4()), "name": name, "created_at": utc_now()},
            ).mappings().one()
        return Firm(str(row["id"]), row["name"], utc(row["created_at"]))

    def update_name(self, lawyer_id: str, name: str) -> Lawyer | None:
        with connection() as conn:
            row = conn.execute(text("UPDATE lawyers SET name = :name WHERE id = :id RETURNING *"), {"id": lawyer_id, "name": name}).mappings().first()
        return to_lawyer(row) if row else None

    def update_password(self, lawyer_id: str, new_password_hash: str) -> None:
        with connection() as conn:
            conn.execute(text("UPDATE lawyers SET password_hash = :hash WHERE id = :id"), {"id": lawyer_id, "hash": new_password_hash})


class SqlSessionRepository:
    def create(self, lawyer_id: str, token_hash: str, expires_at: datetime) -> None:
        with connection() as conn:
            conn.execute(
                text(
                    "INSERT INTO sessions (id, lawyer_id, token_hash, expires_at, created_at) "
                    "VALUES (:id, :lawyer_id, :token_hash, :expires_at, :created_at)"
                ),
                {"id": str(uuid.uuid4()), "lawyer_id": lawyer_id, "token_hash": token_hash, "expires_at": expires_at, "created_at": utc_now()},
            )

    def find_lawyer_by_valid_token_hash(self, token_hash: str) -> Lawyer | None:
        with connection() as conn:
            row = conn.execute(
                text(
                    "SELECT l.*, s.expires_at AS session_expires_at FROM sessions s "
                    "JOIN lawyers l ON l.id = s.lawyer_id WHERE s.token_hash = :token_hash"
                ),
                {"token_hash": token_hash},
            ).mappings().first()
        if row is None or row["session_expires_at"] <= utc_now():
            return None
        return to_lawyer(row)

    def delete_by_token_hash(self, token_hash: str) -> None:
        with connection() as conn:
            conn.execute(text("DELETE FROM sessions WHERE token_hash = :token_hash"), {"token_hash": token_hash})


class SqlLawyerPreferencesRepository:
    def find_by_lawyer_id(self, lawyer_id: str) -> LawyerPreferences | None:
        with connection() as conn:
            row = conn.execute(
                text("SELECT lawyer_id, deadline_reminders_enabled FROM lawyer_preferences WHERE lawyer_id = :lawyer_id"),
                {"lawyer_id": lawyer_id},
            ).mappings().first()
        return LawyerPreferences(str(row["lawyer_id"]), row["deadline_reminders_enabled"]) if row else None

    def upsert(self, lawyer_id: str, deadline_reminders_enabled: bool) -> LawyerPreferences:
        """One row per lawyer_id (I-52's unique index) — atomic upsert, same shape as matter_views/recent_searches."""
        with connection() as conn:
            row = conn.execute(
                text(
                    "INSERT INTO lawyer_preferences (lawyer_id, deadline_reminders_enabled, updated_at) "
                    "VALUES (:lawyer_id, :enabled, now()) "
                    "ON CONFLICT (lawyer_id) DO UPDATE SET deadline_reminders_enabled = :enabled, updated_at = now() "
                    "RETURNING lawyer_id, deadline_reminders_enabled"
                ),
                {"lawyer_id": lawyer_id, "enabled": deadline_reminders_enabled},
            ).mappings().one()
        return LawyerPreferences(str(row["lawyer_id"]), row["deadline_reminders_enabled"])
