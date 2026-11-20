from types import SimpleNamespace

import pytest

from app.application.client_service import ClientService
from app.application.document_service import DocumentService
from app.application.matter_service import MatterHasOpenDeadlinesError, MatterService
from app.domain.client import InvalidClientError
from app.domain.deadline import DeadlineStatus
from app.domain.matter import InvalidMatterError, MatterStatus
from tests.application.crud_fakes import (
    FakeUnitOfWork,
    InMemoryChatMessageRepository,
    InMemoryClientRepository,
    InMemoryDeadlineRepository,
    InMemoryDocumentRepository,
    InMemoryMatterRepository,
    InMemoryMatterViewRepository,
    InMemoryStorage,
    RecordingIngestionTrigger,
)

FIRM, OTHER_FIRM = "firm-a", "firm-b"


@pytest.fixture
def env():
    matters = InMemoryMatterRepository()
    deadlines = InMemoryDeadlineRepository(matters)
    documents = InMemoryDocumentRepository(matters)
    storage = InMemoryStorage()
    chat = InMemoryChatMessageRepository()
    views = InMemoryMatterViewRepository()
    clients = InMemoryClientRepository()
    uow = FakeUnitOfWork()
    document_service = DocumentService(documents, storage, RecordingIngestionTrigger())
    matter_service = MatterService(matters, deadlines, document_service, chat, views, uow)
    client_service = ClientService(clients, matters, matter_service, uow)
    return SimpleNamespace(
        matters=matters, deadlines=deadlines, documents=documents, storage=storage, chat=chat, views=views, clients=clients,
        uow=uow, document_service=document_service, matter_service=matter_service, client_service=client_service,
    )


def _upload(env, matter_id):
    return env.document_service.upload(matter_id, "lawyer", "lease.pdf", "application/pdf", b"%PDF")


def _populated_matter(env, client_id, firm=FIRM):
    """A Matter with one of every child row the cascade must clean up."""
    matter = env.matter_service.create(firm, client_id, "Lease review")
    doc = _upload(env, matter.id)
    env.deadlines.add(matter.id)
    env.chat.matter_ids_with_chat.add(matter.id)
    env.views.record_view("lawyer", matter.id)
    return matter, doc


# ---------------------------------------------------------------- MatterService


def test_creates_a_matter_and_persists_it(env):
    m = env.matter_service.create(FIRM, "client", "  Lease review ")
    assert env.matter_service.get(FIRM, m.id) == m
    assert m.title == "Lease review" and m.status == MatterStatus.open


def test_rejects_an_invalid_matter_before_ever_touching_the_repository(env):
    with pytest.raises(InvalidMatterError):
        env.matter_service.create(FIRM, None, "Lease review")
    assert env.matters.matters == {}


def test_a_matter_outside_the_callers_firm_is_none_not_an_error_br008(env):
    m = env.matter_service.create(FIRM, "client", "Lease")
    assert env.matter_service.get(OTHER_FIRM, m.id) is None


def test_lists_only_matters_for_a_given_client_within_a_firm(env):
    mine = env.matter_service.create(FIRM, "c1", "A")
    env.matter_service.create(FIRM, "c2", "B")
    env.matter_service.create(OTHER_FIRM, "c1", "C")
    assert env.matter_service.list(FIRM, "c1", None) == [mine]


def test_filters_by_status_and_combines_with_client(env):
    open_one = env.matter_service.create(FIRM, "c1", "A")
    closed = env.matter_service.create(FIRM, "c1", "B")
    env.matter_service.close(FIRM, closed.id)
    env.matter_service.create(FIRM, "c2", "C")
    assert [m.id for m in env.matter_service.list(FIRM, None, MatterStatus.closed)] == [closed.id]
    assert [m.id for m in env.matter_service.list(FIRM, "c1", MatterStatus.open)] == [open_one.id]
    assert len(env.matter_service.list(FIRM, None, None)) == 3


def test_renames_a_matter_and_rejects_an_empty_title(env):
    m = env.matter_service.create(FIRM, "c", "Old")
    assert env.matter_service.rename(FIRM, m.id, " New ").title == "New"
    with pytest.raises(InvalidMatterError):
        env.matter_service.rename(FIRM, m.id, "  ")


def test_renaming_a_matter_outside_the_callers_firm_returns_none(env):
    m = env.matter_service.create(FIRM, "c", "Old")
    assert env.matter_service.rename(OTHER_FIRM, m.id, "New") is None
    assert env.matter_service.get(FIRM, m.id).title == "Old"


def test_closes_a_matter_with_no_deadlines_at_all(env):
    m = env.matter_service.create(FIRM, "c", "A")
    closed = env.matter_service.close(FIRM, m.id)
    assert closed.status == MatterStatus.closed and closed.closed_at is not None


def test_close_is_blocked_by_open_deadlines_naming_them_br003(env):
    m = env.matter_service.create(FIRM, "c", "A")
    blocking = env.deadlines.add(m.id, "File reply")
    env.deadlines.add(m.id, "Done already", status=DeadlineStatus.complete)
    with pytest.raises(MatterHasOpenDeadlinesError) as e:
        env.matter_service.close(FIRM, m.id)
    assert [d.id for d in e.value.open_deadlines] == [blocking.id]
    assert env.matter_service.get(FIRM, m.id).status == MatterStatus.open


def test_closing_another_firms_matter_returns_none(env):
    m = env.matter_service.create(FIRM, "c", "A")
    assert env.matter_service.close(OTHER_FIRM, m.id) is None


def test_reopens_a_closed_matter_and_rejects_an_already_open_one(env):
    m = env.matter_service.create(FIRM, "c", "A")
    with pytest.raises(InvalidMatterError):
        env.matter_service.reopen(FIRM, m.id)
    env.matter_service.close(FIRM, m.id)
    reopened = env.matter_service.reopen(FIRM, m.id)
    assert reopened.status == MatterStatus.open and reopened.closed_at is None


def test_delete_cascade_removes_the_matter_and_every_child_row(env):
    matter, doc = _populated_matter(env, "client")
    assert env.matter_service.delete_cascade(FIRM, matter.id) is True
    assert env.matters.find_by_id(FIRM, matter.id) is None
    assert env.documents.documents == {}
    assert env.deadlines.deadlines == {}
    assert matter.id not in env.chat.matter_ids_with_chat
    assert env.views.views == {}
    assert env.uow.transactions >= 1


def test_delete_cascade_deletes_documents_through_document_service_so_stored_files_go_too(env):
    matter, doc = _populated_matter(env, "client")
    assert doc.storage_key in env.storage.files
    env.matter_service.delete_cascade(FIRM, matter.id)
    assert env.storage.files == {}


def test_delete_cascade_returns_false_for_an_unknown_or_other_firm_matter(env):
    matter, _ = _populated_matter(env, "client")
    assert env.matter_service.delete_cascade(OTHER_FIRM, matter.id) is False
    assert env.matter_service.delete_cascade(FIRM, "nope") is False
    assert env.matters.find_by_id(FIRM, matter.id) is not None
    assert len(env.documents.documents) == 1


# ---------------------------------------------------------------- ClientService


def test_updates_a_clients_fields_and_persists_them(env):
    c = env.client_service.create(FIRM, "Acme", None, None, None)
    updated = env.client_service.update(FIRM, c.id, " Acme Two ", "ops@acme.test", " ", "notes")
    assert (updated.name, updated.contact_email, updated.contact_phone) == ("Acme Two", "ops@acme.test", None)
    assert env.client_service.get(FIRM, c.id) == updated


def test_rejects_updating_to_an_empty_name_before_touching_the_repository(env):
    c = env.client_service.create(FIRM, "Acme", None, None, None)
    with pytest.raises(InvalidClientError):
        env.client_service.update(FIRM, c.id, "  ", None, None, None)
    assert env.client_service.get(FIRM, c.id).name == "Acme"


def test_updating_another_firms_client_returns_none(env):
    c = env.client_service.create(FIRM, "Acme", None, None, None)
    assert env.client_service.update(OTHER_FIRM, c.id, "Hijack", None, None, None) is None


def test_delete_cascade_removes_a_client_with_no_matters(env):
    c = env.client_service.create(FIRM, "Acme", None, None, None)
    assert env.client_service.delete_cascade(FIRM, c.id) is True
    assert env.client_service.get(FIRM, c.id) is None


def test_delete_cascade_removes_every_matter_and_its_children_under_the_client(env):
    c = env.client_service.create(FIRM, "Acme", None, None, None)
    other = env.client_service.create(FIRM, "Keep me", None, None, None)
    m1, _ = _populated_matter(env, c.id)
    m2, _ = _populated_matter(env, c.id)
    kept, kept_doc = _populated_matter(env, other.id)

    assert env.client_service.delete_cascade(FIRM, c.id) is True

    assert env.matters.find_by_id(FIRM, m1.id) is None and env.matters.find_by_id(FIRM, m2.id) is None
    assert list(env.documents.documents) == [kept_doc.id]
    assert {d.matter_id for d in env.deadlines.deadlines.values()} == {kept.id}
    assert env.chat.matter_ids_with_chat == {kept.id}
    assert {k[1] for k in env.views.views} == {kept.id}
    assert list(env.storage.files) == [kept_doc.storage_key]


def test_delete_cascade_returns_false_for_an_unknown_or_other_firm_client(env):
    c = env.client_service.create(FIRM, "Acme", None, None, None)
    assert env.client_service.delete_cascade(OTHER_FIRM, c.id) is False
    assert env.client_service.get(FIRM, c.id) is not None

