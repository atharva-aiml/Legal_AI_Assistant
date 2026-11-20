from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.application.deadline_service import DeadlineService
from app.application.document_service import DocumentService
from app.application.draft_generation_service import DraftGenerationService
from app.domain.clock import utc_today
from app.domain.deadline import DeadlinePriority, DeadlineStatus, InvalidDeadlineError
from app.domain.document import DocumentStatus, InvalidDocumentError
from app.domain.matter import MatterStatus, NewMatter
from app.domain.template import InvalidTemplateError
from tests.application.crud_fakes import (
    InMemoryDeadlineRepository,
    InMemoryDocumentRepository,
    InMemoryMatterRepository,
    InMemoryStorage,
    InMemoryTemplateRepository,
    RecordingIngestionTrigger,
)

FIRM, OTHER_FIRM = "firm-a", "firm-b"
TODAY = utc_today()


@pytest.fixture
def env():
    matters = InMemoryMatterRepository()
    matter = matters.create(NewMatter(FIRM, "client", "Lease", MatterStatus.open))
    deadlines = InMemoryDeadlineRepository(matters)
    documents = InMemoryDocumentRepository(matters)
    storage = InMemoryStorage()
    trigger = RecordingIngestionTrigger()
    templates = InMemoryTemplateRepository()
    return SimpleNamespace(
        matter=matter, matters=matters, deadlines=deadlines, documents=documents, storage=storage, trigger=trigger, templates=templates,
        deadline_service=DeadlineService(deadlines),
        document_service=DocumentService(documents, storage, trigger),
        drafts=DraftGenerationService(templates, documents, storage, trigger),
    )


# ---------------------------------------------------------------- DeadlineService (BR-004, BR-009, I-40)


def test_creates_a_deadline_and_persists_it(env):
    d = env.deadline_service.create(env.matter.id, "File", TODAY + timedelta(days=2), None, None)
    assert env.deadline_service.get(FIRM, d.id) == d
    assert d.status == DeadlineStatus.open and d.priority == DeadlinePriority.standard


def test_rejects_an_invalid_deadline_before_touching_the_repository(env):
    with pytest.raises(InvalidDeadlineError):
        env.deadline_service.create(env.matter.id, "File", TODAY - timedelta(days=1), None, None)
    assert env.deadlines.deadlines == {}


def test_lists_deadlines_for_a_matter_within_the_callers_firm_only(env):
    d = env.deadline_service.create(env.matter.id, "File", TODAY, None, None)
    assert env.deadline_service.list(FIRM, env.matter.id) == [d]
    assert env.deadline_service.list(OTHER_FIRM, env.matter.id) == []
    assert env.deadline_service.get(OTHER_FIRM, d.id) is None


def test_updates_only_the_fields_provided(env):
    d = env.deadline_service.create(env.matter.id, "File", TODAY + timedelta(days=4), None, 2)
    updated = env.deadline_service.update(FIRM, d.id, " Reply ", None, None, None, None)
    assert (updated.title, updated.due_date, updated.notification_lead_days, updated.status) == ("Reply", d.due_date, 2, DeadlineStatus.open)


def test_marks_a_deadline_complete(env):
    d = env.deadline_service.create(env.matter.id, "File", TODAY, None, None)
    assert env.deadline_service.update(FIRM, d.id, None, None, DeadlineStatus.complete, None, None).status == DeadlineStatus.complete


def test_rejects_updating_to_an_empty_title_a_past_date_or_negative_lead(env):
    d = env.deadline_service.create(env.matter.id, "File", TODAY, None, None)
    for kwargs in ({"title": " "}, {"due_date": TODAY - timedelta(days=1)}, {"lead": -1}):
        with pytest.raises(InvalidDeadlineError):
            env.deadline_service.update(FIRM, d.id, kwargs.get("title"), kwargs.get("due_date"), None, None, kwargs.get("lead"))


def test_updating_status_without_touching_due_date_is_allowed_even_if_overdue(env):
    overdue = env.deadlines.add(env.matter.id, due_date=TODAY - timedelta(days=3))
    assert env.deadline_service.update(FIRM, overdue.id, None, None, DeadlineStatus.complete, None, None).status == DeadlineStatus.complete


def test_creates_with_an_explicit_critical_priority_and_updates_just_the_priority(env):
    d = env.deadline_service.create(env.matter.id, "File", TODAY, DeadlinePriority.critical, None)
    assert d.priority == DeadlinePriority.critical
    updated = env.deadline_service.update(FIRM, d.id, None, None, None, DeadlinePriority.standard, None)
    assert updated.priority == DeadlinePriority.standard and updated.title == "File"


def test_priority_survives_marking_as_complete(env):
    d = env.deadline_service.create(env.matter.id, "File", TODAY, DeadlinePriority.critical, None)
    assert env.deadline_service.update(FIRM, d.id, None, None, DeadlineStatus.complete, None, None).priority == DeadlinePriority.critical


def test_updating_another_firms_deadline_returns_none(env):
    d = env.deadline_service.create(env.matter.id, "File", TODAY, None, None)
    assert env.deadline_service.update(OTHER_FIRM, d.id, "x", None, None, None, None) is None


def test_upcoming_returns_open_deadlines_within_the_window_including_overdue(env):
    soon = env.deadlines.add(env.matter.id, due_date=TODAY + timedelta(days=2))
    overdue = env.deadlines.add(env.matter.id, due_date=TODAY - timedelta(days=2))
    env.deadlines.add(env.matter.id, due_date=TODAY + timedelta(days=30))
    env.deadlines.add(env.matter.id, due_date=TODAY + timedelta(days=1), status=DeadlineStatus.complete)
    assert env.deadline_service.upcoming(FIRM, 7) == [overdue, soon]
    assert env.deadline_service.upcoming(OTHER_FIRM, 7) == []


# ---------------------------------------------------------------- DocumentService (REQ-003/004/027)


def test_upload_stores_the_file_creates_the_document_and_triggers_ingestion(env):
    doc = env.document_service.upload(env.matter.id, "lawyer", "lease.pdf", "application/pdf", b"%PDF-1.4")
    assert env.storage.files[doc.storage_key] == b"%PDF-1.4"
    assert doc.status == DocumentStatus.uploading  # the response reflects the row as created
    assert env.documents.documents[doc.id].status == DocumentStatus.processing
    assert env.trigger.triggered == [doc.id]
    assert doc.size_bytes == 8


def test_upload_rejects_an_unsupported_type_before_any_storage_io(env):
    with pytest.raises(InvalidDocumentError, match="REQ-003"):
        env.document_service.upload(env.matter.id, "lawyer", "notes.txt", "text/plain", b"hi")
    assert env.storage.files == {} and env.trigger.triggered == []


def test_lists_documents_for_a_matter_and_get_is_none_for_unknown(env):
    doc = env.document_service.upload(env.matter.id, "lawyer", "a.pdf", "application/pdf", b"x")
    assert [d.id for d in env.document_service.list(FIRM, env.matter.id)] == [doc.id]
    assert env.document_service.get(FIRM, "nope") is None
    assert env.document_service.get(OTHER_FIRM, doc.id) is None


def test_download_returns_the_exact_stored_bytes(env):
    doc = env.document_service.upload(env.matter.id, "lawyer", "a.pdf", "application/pdf", b"\x00\x01bytes")
    assert env.document_service.download(FIRM, doc.id) == b"\x00\x01bytes"
    assert env.document_service.download(OTHER_FIRM, doc.id) is None


def test_delete_removes_file_and_row_and_is_false_for_unknown(env):
    doc = env.document_service.upload(env.matter.id, "lawyer", "a.pdf", "application/pdf", b"x")
    assert env.document_service.delete(OTHER_FIRM, doc.id) is False
    assert env.document_service.delete(FIRM, doc.id) is True
    assert env.storage.files == {} and env.documents.documents == {}
    assert env.document_service.delete(FIRM, doc.id) is False


def test_delete_is_unrestricted_by_matter_status_explicit_user_decision(env):
    doc = env.document_service.upload(env.matter.id, "lawyer", "a.pdf", "application/pdf", b"x")
    env.matters.close(FIRM, env.matter.id)
    assert env.document_service.delete(FIRM, doc.id) is True


# ---------------------------------------------------------------- DraftGenerationService (SD-007, REQ-015)


def test_generates_a_draft_document_and_triggers_ingestion(env):
    t = env.templates.add(name="NDA", body="Between {{client_name}} and {{counterparty}}.")
    draft = env.drafts.generate(FIRM, env.matter.id, "lawyer", t.id, {"client_name": "Acme", "counterparty": "Globex"})
    assert draft.file_name == "NDA.txt" and draft.mime_type == "text/plain"
    assert draft.is_draft and draft.source_template_id == t.id
    assert env.storage.files[draft.storage_key] == b"Between Acme and Globex."
    assert env.documents.documents[draft.id].status == DocumentStatus.processing
    assert env.trigger.triggered == [draft.id]


def test_rejects_generation_when_the_template_is_not_found_or_another_firms(env):
    other = env.templates.add(firm_id=OTHER_FIRM)
    for template_id in ("nope", other.id):
        with pytest.raises(InvalidTemplateError, match="Template not found."):
            env.drafts.generate(FIRM, env.matter.id, "lawyer", template_id, {"client_name": "Acme"})


def test_rejects_a_missing_placeholder_value_before_any_storage_io(env):
    t = env.templates.add(body="{{client_name}}")
    with pytest.raises(InvalidTemplateError, match="client_name"):
        env.drafts.generate(FIRM, env.matter.id, "lawyer", t.id, {})
    assert env.storage.files == {} and env.documents.documents == {}
