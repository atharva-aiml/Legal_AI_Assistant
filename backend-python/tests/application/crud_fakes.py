"""Hand-written in-memory fakes for the CRUD ports (app/application/crud_ports.py)
— deliberately not mocks, so each fake's behavior stays honest and readable
(CLAUDE.md §2). Ported from the former Java tests' InMemory* repositories."""

import uuid
from contextlib import contextmanager
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

from app.application.crud_ports import DeadlineWithFirm, LawyerWithHash, SearchResult
from app.application.matter_chat_service import ChatHistoryDto, ChatMessageDto, PinToggleDto
from app.domain.client import Client, NewClient
from app.domain.clock import utc_today
from app.domain.deadline import Deadline, DeadlinePriority, DeadlineStatus, NewDeadline
from app.domain.document import Document, DocumentStatus, NewDocument, NewDraftDocument
from app.domain.lawyer import Firm, Lawyer, LawyerPreferences, LawyerRole
from app.domain.matter import Matter, MatterStatus, MatterView, NewMatter
from app.domain.notification import NewNotification, Notification
from app.domain.search import RecentSearch, SearchQuery
from app.domain.template import Template

_tick = [datetime(2026, 1, 1, tzinfo=timezone.utc)]


def now() -> datetime:
    """Strictly increasing timestamps, so "most recent first" ordering is deterministic."""
    _tick[0] += timedelta(milliseconds=1)
    return _tick[0]


def new_id() -> str:
    return str(uuid.uuid4())


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.transactions = 0

    @contextmanager
    def transaction(self):
        self.transactions += 1
        yield


class InMemoryLawyerRepository:
    def __init__(self) -> None:
        self.lawyers: dict[str, LawyerWithHash] = {}
        self.firms: dict[str, Firm] = {}

    def add(self, firm_id: str, name: str = "Lawyer", email: str | None = None, password_hash: str = "hash") -> Lawyer:
        return self.create(firm_id, name, email or f"{new_id()}@example.com", password_hash).lawyer

    def find_by_email_with_hash(self, email):
        return next((l for l in self.lawyers.values() if l.lawyer.email == email), None)

    def find_by_id(self, lawyer_id):
        found = self.lawyers.get(lawyer_id)
        return found.lawyer if found else None

    def find_by_id_with_hash(self, lawyer_id):
        return self.lawyers.get(lawyer_id)

    def list_by_firm(self, firm_id):
        return [l.lawyer for l in self.lawyers.values() if l.lawyer.firm_id == firm_id]

    def create(self, firm_id, name, email, password_hash):
        lawyer = Lawyer(new_id(), firm_id, name, email, LawyerRole.owner, now())
        self.lawyers[lawyer.id] = LawyerWithHash(lawyer, password_hash)
        return self.lawyers[lawyer.id]

    def create_firm(self, name):
        firm = Firm(new_id(), name, now())
        self.firms[firm.id] = firm
        return firm

    def update_name(self, lawyer_id, name):
        found = self.lawyers.get(lawyer_id)
        if found is None:
            return None
        self.lawyers[lawyer_id] = LawyerWithHash(replace(found.lawyer, name=name), found.password_hash)
        return self.lawyers[lawyer_id].lawyer

    def update_password(self, lawyer_id, new_password_hash):
        found = self.lawyers[lawyer_id]
        self.lawyers[lawyer_id] = LawyerWithHash(found.lawyer, new_password_hash)


class InMemorySessionRepository:
    def __init__(self, lawyers: InMemoryLawyerRepository) -> None:
        self.lawyers = lawyers
        self.sessions: dict[str, tuple[str, datetime]] = {}

    def create(self, lawyer_id, token_hash, expires_at):
        self.sessions[token_hash] = (lawyer_id, expires_at)

    def find_lawyer_by_valid_token_hash(self, token_hash):
        found = self.sessions.get(token_hash)
        if found is None or found[1] <= datetime.now(timezone.utc):
            return None
        return self.lawyers.find_by_id(found[0])

    def delete_by_token_hash(self, token_hash):
        self.sessions.pop(token_hash, None)


class PlainTextPasswordHasher:
    """Reversible stand-in for bcrypt — the hashing algorithm isn't what these tests are about."""

    def hash(self, raw_password):
        return "hashed:" + raw_password

    def matches(self, raw_password, password_hash):
        return password_hash == "hashed:" + raw_password


class InMemoryPreferencesRepository:
    def __init__(self) -> None:
        self.rows: dict[str, LawyerPreferences] = {}

    def find_by_lawyer_id(self, lawyer_id):
        return self.rows.get(lawyer_id)

    def upsert(self, lawyer_id, deadline_reminders_enabled):
        self.rows[lawyer_id] = LawyerPreferences(lawyer_id, deadline_reminders_enabled)
        return self.rows[lawyer_id]


class InMemoryClientRepository:
    def __init__(self) -> None:
        self.clients: dict[str, Client] = {}
        self.deleted: list[str] = []

    def create(self, record: NewClient):
        t = now()
        client = Client(new_id(), record.firm_id, record.name, record.contact_email, record.contact_phone, record.notes, t, t)
        self.clients[client.id] = client
        return client

    def list_by_firm(self, firm_id):
        return [c for c in self.clients.values() if c.firm_id == firm_id]

    def find_by_id(self, firm_id, client_id):
        c = self.clients.get(client_id)
        return c if c and c.firm_id == firm_id else None

    def update(self, firm_id, client_id, name, contact_email, contact_phone, notes):
        c = self.find_by_id(firm_id, client_id)
        if c is None:
            return None
        self.clients[client_id] = replace(c, name=name, contact_email=contact_email, contact_phone=contact_phone, notes=notes, updated_at=now())
        return self.clients[client_id]

    def delete(self, firm_id, client_id):
        if self.find_by_id(firm_id, client_id) is None:
            return False
        del self.clients[client_id]
        self.deleted.append(client_id)
        return True


class InMemoryMatterRepository:
    def __init__(self) -> None:
        self.matters: dict[str, Matter] = {}

    def create(self, record: NewMatter):
        t = now()
        matter = Matter(new_id(), record.firm_id, record.client_id, record.title, record.status, None, t, t)
        self.matters[matter.id] = matter
        return matter

    def list_by_firm(self, firm_id):
        return [m for m in self.matters.values() if m.firm_id == firm_id]

    def list_by_client(self, firm_id, client_id):
        return [m for m in self.list_by_firm(firm_id) if m.client_id == client_id]

    def find_by_id(self, firm_id, matter_id):
        m = self.matters.get(matter_id)
        return m if m and m.firm_id == firm_id else None

    def _set(self, firm_id, matter_id, **changes):
        m = self.find_by_id(firm_id, matter_id)
        if m is None:
            return None
        self.matters[matter_id] = replace(m, updated_at=now(), **changes)
        return self.matters[matter_id]

    def update_title(self, firm_id, matter_id, title):
        return self._set(firm_id, matter_id, title=title)

    def close(self, firm_id, matter_id):
        return self._set(firm_id, matter_id, status=MatterStatus.closed, closed_at=now())

    def reopen(self, firm_id, matter_id):
        return self._set(firm_id, matter_id, status=MatterStatus.open, closed_at=None)

    def delete(self, firm_id, matter_id):
        if self.find_by_id(firm_id, matter_id) is None:
            return False
        del self.matters[matter_id]
        return True


class InMemoryDeadlineRepository:
    def __init__(self, matters: InMemoryMatterRepository) -> None:
        self.matters = matters
        self.deadlines: dict[str, Deadline] = {}

    def _in_firm(self, firm_id, d):
        m = self.matters.matters.get(d.matter_id)
        return m is not None and m.firm_id == firm_id

    def add(self, matter_id, title="Deadline", due_date: date | None = None, status=DeadlineStatus.open, lead_days=3, priority=DeadlinePriority.standard):
        t = now()
        d = Deadline(new_id(), matter_id, title, due_date or utc_today() + timedelta(days=10), status, priority, lead_days, t, t)
        self.deadlines[d.id] = d
        return d

    def create(self, record: NewDeadline):
        return self.add(record.matter_id, record.title, record.due_date, DeadlineStatus.open, record.notification_lead_days, record.priority)

    def list_by_matter(self, firm_id, matter_id):
        found = [d for d in self.deadlines.values() if d.matter_id == matter_id and self._in_firm(firm_id, d)]
        return sorted(found, key=lambda d: d.due_date)

    def find_by_id(self, firm_id, deadline_id):
        d = self.deadlines.get(deadline_id)
        return d if d and self._in_firm(firm_id, d) else None

    def update(self, firm_id, deadline_id, title, due_date, status, priority, notification_lead_days):
        d = self.find_by_id(firm_id, deadline_id)
        if d is None:
            return None
        self.deadlines[deadline_id] = replace(
            d, title=title, due_date=due_date, status=status, priority=priority, notification_lead_days=notification_lead_days, updated_at=now()
        )
        return self.deadlines[deadline_id]

    def list_upcoming(self, firm_id, days):
        cutoff = utc_today() + timedelta(days=days)
        found = [d for d in self.deadlines.values() if d.status == DeadlineStatus.open and d.due_date <= cutoff and self._in_firm(firm_id, d)]
        return sorted(found, key=lambda d: d.due_date)

    def list_all_open_with_firm(self):
        return [
            DeadlineWithFirm(d, self.matters.matters[d.matter_id].firm_id)
            for d in self.deadlines.values()
            if d.status == DeadlineStatus.open and d.matter_id in self.matters.matters
        ]

    def delete_by_matter(self, matter_id):
        for deadline_id in [d.id for d in self.deadlines.values() if d.matter_id == matter_id]:
            del self.deadlines[deadline_id]


class InMemoryDocumentRepository:
    def __init__(self, matters: InMemoryMatterRepository) -> None:
        self.matters = matters
        self.documents: dict[str, Document] = {}

    def _in_firm(self, firm_id, d):
        m = self.matters.matters.get(d.matter_id)
        return m is not None and m.firm_id == firm_id

    def _insert(self, matter_id, uploaded_by, file_name, storage_key, mime_type, size_bytes, is_draft, source_template_id):
        doc = Document(new_id(), matter_id, uploaded_by, file_name, storage_key, mime_type, size_bytes, DocumentStatus.uploading, is_draft, source_template_id, None, now())
        self.documents[doc.id] = doc
        return doc

    def create(self, record: NewDocument):
        return self._insert(record.matter_id, record.uploaded_by, record.file_name, record.storage_key, record.mime_type, record.size_bytes, False, None)

    def create_draft(self, record: NewDraftDocument):
        return self._insert(record.matter_id, record.uploaded_by, record.file_name, record.storage_key, record.mime_type, record.size_bytes, True, record.source_template_id)

    def list_by_matter(self, firm_id, matter_id):
        return [d for d in self.documents.values() if d.matter_id == matter_id and self._in_firm(firm_id, d)]

    def find_by_id(self, firm_id, document_id):
        d = self.documents.get(document_id)
        return d if d and self._in_firm(firm_id, d) else None

    def update_status(self, document_id, status, error_message):
        if document_id in self.documents:
            self.documents[document_id] = replace(self.documents[document_id], status=status, error_message=error_message)

    def delete(self, firm_id, document_id):
        if self.find_by_id(firm_id, document_id) is None:
            return False
        del self.documents[document_id]
        return True


class InMemoryStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def store(self, original_file_name, content):
        key = new_id()
        self.files[key] = content
        return key

    def retrieve(self, storage_key):
        try:
            return self.files[storage_key]
        except KeyError:
            raise FileNotFoundError(storage_key) from None

    def delete(self, storage_key):
        self.files.pop(storage_key, None)


class RecordingIngestionTrigger:
    def __init__(self) -> None:
        self.triggered: list[str] = []

    def trigger_ingestion(self, document_id):
        self.triggered.append(document_id)


class InMemoryChatMessageRepository:
    def __init__(self) -> None:
        self.matter_ids_with_chat: set[str] = set()

    def delete_by_matter(self, matter_id):
        self.matter_ids_with_chat.discard(matter_id)


class InMemoryMatterViewRepository:
    def __init__(self) -> None:
        self.views: dict[tuple[str, str], datetime] = {}

    def record_view(self, lawyer_id, matter_id):
        self.views[(lawyer_id, matter_id)] = now()

    def list_recently_viewed(self, lawyer_id, limit):
        mine = [MatterView(l, m, t) for (l, m), t in self.views.items() if l == lawyer_id]
        return sorted(mine, key=lambda v: v.viewed_at, reverse=True)[:limit]

    def delete_by_matter(self, matter_id):
        for key in [k for k in self.views if k[1] == matter_id]:
            del self.views[key]


class InMemoryNotificationRepository:
    def __init__(self) -> None:
        self.notifications: dict[str, Notification] = {}

    def add(self, lawyer_id, deadline_id="d", message="msg", read=False, created_at: datetime | None = None):
        t = created_at or now()
        n = Notification(new_id(), lawyer_id, deadline_id, message, t, t if read else None, t)
        self.notifications[n.id] = n
        return n

    def list_by_lawyer(self, lawyer_id):
        return sorted((n for n in self.notifications.values() if n.lawyer_id == lawyer_id), key=lambda n: n.created_at, reverse=True)

    def mark_read(self, lawyer_id, notification_id):
        n = self.notifications.get(notification_id)
        if n is None or n.lawyer_id != lawyer_id:
            return None
        self.notifications[notification_id] = replace(n, read_at=now())
        return self.notifications[notification_id]

    def mark_all_read(self, lawyer_id):
        unread = [n for n in self.notifications.values() if n.lawyer_id == lawyer_id and n.read_at is None]
        for n in unread:
            self.notifications[n.id] = replace(n, read_at=now())
        return len(unread)

    def create(self, record: NewNotification):
        return self.add(record.lawyer_id, record.deadline_id, record.message, created_at=datetime.now(timezone.utc))

    def exists_for_deadline_and_lawyer_on_day(self, deadline_id, lawyer_id, day):
        return any(n.deadline_id == deadline_id and n.lawyer_id == lawyer_id and n.created_at.date() == day for n in self.notifications.values())


class InMemoryRecentSearchRepository:
    def __init__(self) -> None:
        self.searches: dict[tuple[str, str], datetime] = {}

    def record(self, lawyer_id, query):
        self.searches[(lawyer_id, query)] = now()

    def list_recent(self, lawyer_id, limit):
        mine = [RecentSearch(l, q, t) for (l, q), t in self.searches.items() if l == lawyer_id]
        return sorted(mine, key=lambda s: s.searched_at, reverse=True)[:limit]


class InMemorySearchRepository:
    """Case-insensitive substring match — the real FTS behavior is covered live, not here."""

    def __init__(self, clients: InMemoryClientRepository, matters: InMemoryMatterRepository) -> None:
        self.clients = clients
        self.matters = matters
        self.calls = 0

    def search(self, firm_id, query: SearchQuery):
        self.calls += 1

        def name_ok(text):
            return query.q is None or query.q.lower() in text.lower()

        def date_ok(ts):
            return (query.from_date is None or ts.date() >= query.from_date) and (query.to_date is None or ts.date() <= query.to_date)

        clients = [c for c in self.clients.list_by_firm(firm_id) if name_ok(c.name) and date_ok(c.created_at)]
        matters = [
            m for m in self.matters.list_by_firm(firm_id)
            if name_ok(m.title) and date_ok(m.created_at) and (query.status is None or m.status == query.status)
        ]
        return SearchResult(clients, matters)


class InMemoryTemplateRepository:
    def __init__(self) -> None:
        self.templates: dict[str, Template] = {}

    def add(self, firm_id=None, name="Template", body="Body {{client_name}}", description=None):
        t = Template(new_id(), firm_id, name, description, body, now())
        self.templates[t.id] = t
        return t

    def list_available(self, firm_id):
        return sorted((t for t in self.templates.values() if t.firm_id is None or t.firm_id == firm_id), key=lambda t: t.name)

    def find_available(self, firm_id, template_id):
        t = self.templates.get(template_id)
        return t if t and (t.firm_id is None or t.firm_id == firm_id) else None


class InMemoryChatGateway:
    """Records what it was asked to do and returns canned results, or raises `fail_with`."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.history_messages: list[ChatMessageDto] = []
        self.fail_with: Exception | None = None

    def _record(self, *call):
        self.calls.append(call)
        if self.fail_with is not None:
            raise self.fail_with

    @staticmethod
    def message(matter_id, role="user", content="question", lawyer_id="lawyer", created_at: datetime | None = None) -> ChatMessageDto:
        return ChatMessageDto(new_id(), matter_id, lawyer_id, role, content, created_at or now(), [], None, None, False, None, [])

    def ask(self, matter_id, lawyer_id, question):
        self._record("ask", matter_id, lawyer_id, question)
        return self.message(matter_id, "assistant", "answer", None)

    def history(self, matter_id):
        self._record("history", matter_id)
        return ChatHistoryDto(list(self.history_messages))

    def toggle_pin(self, matter_id, message_id, pinned):
        self._record("toggle_pin", matter_id, message_id, pinned)
        return PinToggleDto(message_id, pinned)

    def edit_message(self, matter_id, message_id, lawyer_id, question):
        self._record("edit_message", matter_id, message_id, lawyer_id, question)
        return ChatHistoryDto(list(self.history_messages))

    def activate_branch(self, matter_id, message_id):
        self._record("activate_branch", matter_id, message_id)
        return ChatHistoryDto(list(self.history_messages))
