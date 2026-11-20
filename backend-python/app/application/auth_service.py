import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

from app.application.crud_ports import LawyerRepository, PasswordHasher, SessionRepository
from app.domain.clock import utc_now
from app.domain.lawyer import Lawyer

SESSION_COOKIE_NAME = "session"
SESSION_DURATION = timedelta(days=7)


class SessionToken:
    """A 256-bit random raw token that only ever lives in the browser's
    cookie, and a SHA-256 hash of it that's the only thing ever persisted
    (System Architecture §5). Byte-for-byte the same scheme the Node and Java
    implementations used, so existing sessions survive every backend swap.
    SHA-256 (not bcrypt) is deliberate — see CLAUDE.md §4."""

    @staticmethod
    def generate_raw_token() -> str:
        return secrets.token_hex(32)

    @staticmethod
    def hash(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class ValidationError(Exception):
    pass


class EmailTakenError(Exception):
    pass


class InvalidCredentialsError(Exception):
    def __init__(self) -> None:
        super().__init__("Incorrect email or password.")


class IncorrectPasswordError(Exception):
    def __init__(self) -> None:
        super().__init__("Current password is incorrect.")


@dataclass(frozen=True)
class AuthResult:
    lawyer: Lawyer
    raw_session_token: str


def _normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


class AuthService:
    def __init__(self, lawyers: LawyerRepository, sessions: SessionRepository, password_hasher: PasswordHasher) -> None:
        self.lawyers = lawyers
        self.sessions = sessions
        self.password_hasher = password_hasher

    def register(self, name: str | None, email: str | None, password: str | None) -> AuthResult:
        """Creates a new Firm + Lawyer (role=owner) in one flow."""
        trimmed_name = (name or "").strip()
        normalized_email = _normalize_email(email)

        if not trimmed_name or not normalized_email or password is None or len(password) < 8:
            raise ValidationError("Name, email, and an 8+ character password are required.")

        if self.lawyers.find_by_email_with_hash(normalized_email) is not None:
            raise EmailTakenError("An account with this email already exists.")

        password_hash = self.password_hasher.hash(password)
        firm = self.lawyers.create_firm(f"{trimmed_name}'s Firm")
        created = self.lawyers.create(firm.id, trimmed_name, normalized_email, password_hash)
        return AuthResult(created.lawyer, self._issue_session(created.lawyer.id))

    def is_email_available(self, email: str | None) -> bool:
        """I-06: reuses register's uniqueness check, read-only, for a live pre-submit hint."""
        normalized_email = _normalize_email(email)
        if not normalized_email:
            return False
        return self.lawyers.find_by_email_with_hash(normalized_email) is None

    def login(self, email: str | None, password: str | None) -> AuthResult:
        """Identical error for "no such email" and "wrong password"."""
        normalized_email = _normalize_email(email)
        found = self.lawyers.find_by_email_with_hash(normalized_email) if normalized_email else None

        if found is None or password is None or not self.password_hasher.matches(password, found.password_hash):
            raise InvalidCredentialsError()

        return AuthResult(found.lawyer, self._issue_session(found.lawyer.id))

    def logout(self, raw_session_token: str | None) -> None:
        """Deletes the Session row — real revocation, not just a cleared cookie."""
        if not raw_session_token:
            return
        self.sessions.delete_by_token_hash(SessionToken.hash(raw_session_token))

    def resolve_session(self, raw_session_token: str | None) -> Lawyer | None:
        """The real per-request authorization check — System Architecture §5, steps 6-8."""
        if not raw_session_token:
            return None
        return self.sessions.find_lawyer_by_valid_token_hash(SessionToken.hash(raw_session_token))

    def list_firm_members(self, firm_id: str) -> list[Lawyer]:
        """SCR-15: read-only Firm/team roster."""
        return self.lawyers.list_by_firm(firm_id)

    def update_name(self, lawyer_id: str, name: str | None) -> Lawyer:
        """I-51: PATCH /api/auth/me."""
        validated = Lawyer.validate_name(name)
        updated = self.lawyers.update_name(lawyer_id, validated)
        if updated is None:
            raise RuntimeError(f"Lawyer {lawyer_id} not found for an already-authenticated session.")
        return updated

    def change_password(self, lawyer_id: str, current_password: str | None, new_password: str | None) -> None:
        """I-51: re-verifies the current password before a new one is ever hashed and stored."""
        found = self.lawyers.find_by_id_with_hash(lawyer_id)
        if found is None:
            raise RuntimeError(f"Lawyer {lawyer_id} not found for an already-authenticated session.")

        if current_password is None or not self.password_hasher.matches(current_password, found.password_hash):
            raise IncorrectPasswordError()

        validated = Lawyer.validate_new_password(new_password)
        self.lawyers.update_password(lawyer_id, self.password_hasher.hash(validated))

    def _issue_session(self, lawyer_id: str) -> str:
        raw = SessionToken.generate_raw_token()
        self.sessions.create(lawyer_id, SessionToken.hash(raw), utc_now() + SESSION_DURATION)
        return raw
