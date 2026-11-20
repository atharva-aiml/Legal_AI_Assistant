from datetime import datetime, timedelta, timezone

import pytest

from app.application.activity_service import ActivityService
from app.application.deadline_service import DeadlineService
from app.application.document_service import DocumentService
from app.application.matter_chat_service import AssistantUnavailableError, MatterChatService
from app.application.matter_view_service import MatterViewService
from app.application.search_service import RecentSearchService, SearchService
from app.application.template_service import TemplateService
from app.domain.client import NewClient
from app.domain.deadline import DeadlineStatus
from app.domain.matter import MatterStatus, NewMatter
from app.domain.search import InvalidSearchError
from tests.application.crud_fakes import (
    InMemoryChatGateway,
    InMemoryClientRepository,
    InMemoryDeadlineRepository,
    InMemoryDocumentRepository,
    InMemoryMatterRepository,
    InMemoryMatterViewRepository,
    InMemoryRecentSearchRepository,
    InMemorySearchRepository,
    InMemoryStorage,
    InMemoryTemplateRepository,
    RecordingIngestionTrigger,
)

FIRM, OTHER_FIRM = "firm-a", "firm-b"


# ---------------------------------------------------------------- SearchService (SD-009, REQ-011, BR-007/008)


@pytest.fixture
def search():
    clients, matters = InMemoryClientRepository(), InMemoryMatterRepository()
    repo = InMemorySearchRepository(clients, matters)
    return clients, matters, repo, SearchService(repo)


def test_combines_query_and_status_and_never_hides_closed_matters_by_default(search):
    clients, matters, _, service = search
    open_lease = matters.create(NewMatter(FIRM, "c", "Lease dispute", MatterStatus.open))
    closed_lease = matters.create(NewMatter(FIRM, "c", "Old lease", MatterStatus.open))
    matters.close(FIRM, closed_lease.id)
    matters.create(NewMatter(OTHER_FIRM, "c", "Lease elsewhere", MatterStatus.open))
    clients.create(NewClient(FIRM, "Lease Co", None, None, None))

    everything = service.search(FIRM, "lease", None, None, None)
    assert {m.id for m in everything.matters} == {open_lease.id, closed_lease.id}  # BR-007 + BR-008
    assert [c.name for c in everything.clients] == ["Lease Co"]
    assert [m.id for m in service.search(FIRM, "lease", "open", None, None).matters] == [open_lease.id]


def test_rejects_a_search_with_no_criteria_before_touching_the_repository(search):
    _, _, repo, service = search
    with pytest.raises(InvalidSearchError):
        service.search(FIRM, " ", None, None, None)
    assert repo.calls == 0


def test_rejects_an_unknown_status(search):
    with pytest.raises(InvalidSearchError, match="Unknown status"):
        search[3].search(FIRM, None, "archived", None, None)


# ---------------------------------------------------------------- RecentSearchService (I-48) / MatterViewService (I-07)


def test_recent_searches_are_newest_first_deduplicated_capped_and_per_lawyer():
    service = RecentSearchService(InMemoryRecentSearchRepository())
    for q in ["one", "two", "three", "four", "five", "six"]:
        service.record("ada", q)
    service.record("ada", " three ")
    service.record("bob", "bobs")
    assert [s.query for s in service.list_recent("ada")] == ["three", "six", "five", "four", "two"]
    assert [s.query for s in service.list_recent("bob")] == ["bobs"]


def test_rejects_a_blank_recent_search_before_touching_the_repository():
    repo = InMemoryRecentSearchRepository()
    with pytest.raises(InvalidSearchError):
        RecentSearchService(repo).record("ada", "  ")
    assert repo.searches == {}


def test_recent_matters_are_newest_first_deduplicated_capped_and_per_lawyer():
    service = MatterViewService(InMemoryMatterViewRepository())
    for m in ["m1", "m2", "m3", "m4", "m5", "m6"]:
        service.record_view("ada", m)
    service.record_view("ada", "m2")
    service.record_view("bob", "m9")
    assert [v.matter_id for v in service.list_recently_viewed("ada")] == ["m2", "m6", "m5", "m4", "m3"]
    assert [v.matter_id for v in service.list_recently_viewed("bob")] == ["m9"]


# ---------------------------------------------------------------- TemplateService (SD-007)


def test_lists_system_templates_plus_only_the_callers_own_custom_ones():
    repo = InMemoryTemplateRepository()
    system = repo.add(name="B system")
    mine = repo.add(firm_id=FIRM, name="A mine")
    theirs = repo.add(firm_id=OTHER_FIRM, name="C theirs")
    service = TemplateService(repo)
    assert service.list(FIRM) == [mine, system]
    assert service.get(OTHER_FIRM, system.id) == system
    assert service.get(FIRM, theirs.id) is None


# ---------------------------------------------------------------- MatterChatService (SD-005 relay)


def test_chat_service_forwards_every_call_to_the_gateway_unchanged():
    gateway = InMemoryChatGateway()
    service = MatterChatService(gateway)
    assert service.ask("m", "ada", "What is the rent?").role == "assistant"
    service.history("m")
    assert service.toggle_pin("m", "msg", True).pinned is True
    service.edit_message("m", "msg", "ada", "What is the deposit?")
    service.activate_branch("m", "msg")
    assert gateway.calls == [
        ("ask", "m", "ada", "What is the rent?"),
        ("history", "m"),
        ("toggle_pin", "m", "msg", True),
        ("edit_message", "m", "msg", "ada", "What is the deposit?"),
        ("activate_branch", "m", "msg"),
    ]


# ---------------------------------------------------------------- ActivityService (I-32)


@pytest.fixture
def activity():
    matters = InMemoryMatterRepository()
    matter = matters.create(NewMatter(FIRM, "c", "Lease", MatterStatus.open))
    deadlines = InMemoryDeadlineRepository(matters)
    documents = InMemoryDocumentRepository(matters)
    gateway = InMemoryChatGateway()
    service = ActivityService(
        DocumentService(documents, InMemoryStorage(), RecordingIngestionTrigger()), DeadlineService(deadlines), MatterChatService(gateway)
    )
    return matter, deadlines, documents, gateway, service


def test_combines_document_deadline_and_chat_question_entries_most_recent_first(activity):
    matter, deadlines, documents, gateway, service = activity
    service.document_service.upload(matter.id, "ada", "lease.pdf", "application/pdf", b"x")
    deadlines.add(matter.id, "File reply")
    done = deadlines.add(matter.id, "Serve notice")
    deadlines.update(FIRM, done.id, done.title, done.due_date, DeadlineStatus.complete, done.priority, done.notification_lead_days)
    gateway.history_messages = [gateway.message(matter.id, "user", "  What is the rent? ", created_at=datetime.now(timezone.utc) + timedelta(days=1))]

    entries = service.for_matter(FIRM, matter.id)
    assert [(e.type, e.title) for e in entries] == [
        ("chat", "Question asked: What is the rent?"),
        ("deadline", "Deadline completed: Serve notice"),
        ("deadline", "Deadline added: File reply"),
        ("document", "Document uploaded: lease.pdf"),
    ]


def test_only_user_chat_messages_become_entries_and_long_ones_are_truncated(activity):
    matter, _, _, gateway, service = activity
    gateway.history_messages = [gateway.message(matter.id, "user", "x" * 100), gateway.message(matter.id, "assistant", "answer", None)]
    entries = service.for_matter(FIRM, matter.id)
    assert len(entries) == 1
    assert entries[0].title == "Question asked: " + "x" * 79 + "…"


def test_a_chat_failure_omits_chat_entries_but_keeps_documents_and_deadlines(activity):
    matter, deadlines, _, gateway, service = activity
    deadlines.add(matter.id, "File reply")
    gateway.fail_with = AssistantUnavailableError("down")
    assert [e.type for e in service.for_matter(FIRM, matter.id)] == ["deadline"]


def test_an_empty_matter_returns_an_empty_timeline(activity):
    matter, _, _, _, service = activity
    assert service.for_matter(FIRM, matter.id) == []
