"""Public /api surface against the real database (Postgres must be running,
same as tests/infrastructure). CLAUDE.md §2: every endpoint gets a happy
path and a BR-008 isolation check — a cross-Firm request is a 404, never a
403 and never a leak. Ingestion is swapped for a recorder so no model or
LLM is ever loaded; chat is exercised only on paths that never reach the LLM."""

import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.domain.clock import utc_today
from app.infrastructure.db import engine
from app.main import app
from app.web.api import container
from tests.application.crud_fakes import RecordingIngestionTrigger

TODAY = utc_today()


@pytest.fixture
def trigger(monkeypatch):
    recorder = RecordingIngestionTrigger()
    monkeypatch.setattr(container.document_service, "ingestion_trigger", recorder)
    monkeypatch.setattr(container.draft_generation_service, "ingestion_trigger", recorder)
    return recorder


def _register(name: str) -> TestClient:
    client = TestClient(app)  # no `with`: the hourly scheduler isn't started
    res = client.post("/api/auth/register", json={"name": name, "email": f"{name.lower()}.{uuid.uuid4().hex[:8]}@test.example", "password": "password1"})
    assert res.status_code == 201, res.text
    return client


@pytest.fixture
def a():
    return _register("Ada")


@pytest.fixture
def b():
    return _register("Bob")


@pytest.fixture
def matter(a):
    client = a.post("/api/clients", json={"name": "Acme"}).json()
    return a.post("/api/matters", json={"client_id": client["id"], "title": "Lease"}).json()


def test_auth_round_trip_and_session_revocation():
    anon = TestClient(app)
    assert anon.get("/api/auth/me").status_code == 401
    me = _register("Cy")
    assert me.get("/api/auth/me").json()["lawyer"]["name"] == "Cy"
    token = me.cookies.get("session")
    cleared = me.post("/api/auth/logout").headers["set-cookie"]
    assert cleared.startswith("session=;") and "HttpOnly" in cleared
    # Real revocation, not just a cleared cookie: replaying the old token fails.
    replay = TestClient(app, cookies={"session": token})
    assert replay.get("/api/auth/me").status_code == 401


def test_error_shapes_match_what_the_frontend_was_built_against(a):
    assert a.get("/api/clients/not-a-uuid").json()["error"] == "Bad Request"  # framework-level 400
    assert a.get(f"/api/clients/{uuid.uuid4()}").json() == {"error": {"code": "NOT_FOUND", "message": "Client not found"}}
    assert a.post("/api/clients", content="x", headers={"content-type": "text/plain"}).status_code == 415
    assert TestClient(app).get("/api/clients").json() == {"error": {"code": "UNAUTHENTICATED", "message": "Not signed in"}}


def test_a_foreign_origin_is_refused_and_the_frontend_origin_is_allowed(a):
    assert a.get("/api/clients", headers={"Origin": "http://evil.example"}).status_code == 403
    ok = a.get("/api/clients", headers={"Origin": "http://localhost:3000"})
    assert ok.status_code == 200 and ok.headers["access-control-allow-credentials"] == "true"


def test_clients_happy_path_and_isolation(a, b):
    created = a.post("/api/clients", json={"name": " Acme ", "contact_email": ""}).json()
    assert created["name"] == "Acme" and created["contactEmail"] is None
    assert a.get(f"/api/clients/{created['id']}").json()["client"]["id"] == created["id"]
    assert a.patch(f"/api/clients/{created['id']}", json={"name": "Acme 2"}).json()["name"] == "Acme 2"
    for res in (b.get(f"/api/clients/{created['id']}"), b.patch(f"/api/clients/{created['id']}", json={"name": "x"}), b.delete(f"/api/clients/{created['id']}")):
        assert res.status_code == 404
    assert created["id"] not in [c["id"] for c in b.get("/api/clients").json()["clients"]]
    assert a.delete(f"/api/clients/{created['id']}").status_code == 204


def test_matters_happy_path_and_isolation(a, b, matter):
    mid = matter["id"]
    assert a.get(f"/api/matters/{mid}").json()["matter"]["title"] == "Lease"
    assert a.patch(f"/api/matters/{mid}", json={"title": "Lease 2"}).json()["title"] == "Lease 2"
    assert a.post(f"/api/matters/{mid}/view").json() == {}
    assert a.get("/api/matters/recent").json()["matters"][0]["id"] == mid
    assert a.get(f"/api/matters/{mid}/activity").json() == {"entries": []}
    assert a.post(f"/api/matters/{mid}/close").json()["status"] == "closed"
    assert a.post(f"/api/matters/{mid}/reopen").json()["status"] == "open"
    for res in (
        b.get(f"/api/matters/{mid}"), b.patch(f"/api/matters/{mid}", json={"title": "x"}), b.post(f"/api/matters/{mid}/view"),
        b.get(f"/api/matters/{mid}/activity"), b.post(f"/api/matters/{mid}/close"), b.post(f"/api/matters/{mid}/reopen"),
        b.delete(f"/api/matters/{mid}"),
    ):
        assert res.status_code == 404
    assert b.post("/api/matters", json={"client_id": matter["clientId"], "title": "x"}).status_code == 404


def test_deadlines_happy_path_close_blocking_and_isolation(a, b, matter):
    mid = matter["id"]
    d = a.post(f"/api/matters/{mid}/deadlines", json={"title": "File", "dueDate": str(TODAY + timedelta(days=2))}).json()
    assert d["priority"] == "standard" and d["notificationLeadDays"] == 3
    blocked = a.post(f"/api/matters/{mid}/close")
    assert blocked.status_code == 409 and blocked.json()["error"]["openDeadlines"][0]["id"] == d["id"]
    assert a.get("/api/deadlines/upcoming").json()["deadlines"][0]["id"] == d["id"]
    assert a.patch(f"/api/deadlines/{d['id']}", json={"status": "complete"}).json()["status"] == "complete"
    assert a.post(f"/api/matters/{mid}/deadlines", json={"title": "Old", "dueDate": str(TODAY - timedelta(days=1))}).status_code == 400
    for res in (b.get(f"/api/matters/{mid}/deadlines"), b.get(f"/api/deadlines/{d['id']}"), b.patch(f"/api/deadlines/{d['id']}", json={"title": "x"})):
        assert res.status_code == 404
    assert b.get("/api/deadlines/upcoming").json() == {"deadlines": []}


def test_documents_upload_download_delete_and_isolation(a, b, matter, trigger):
    mid = matter["id"]
    up = a.post(f"/api/matters/{mid}/documents", files={"file": ("lease.pdf", b"%PDF-1.4 test", "application/pdf")})
    doc = up.json()["documents"][0]
    assert up.status_code == 201 and doc["status"] == "uploading" and trigger.triggered == [doc["id"]]
    assert a.get(f"/api/documents/{doc['id']}").json()["status"] == "processing"
    dl = a.get(f"/api/documents/{doc['id']}/download")
    assert dl.content == b"%PDF-1.4 test" and dl.headers["content-disposition"] == 'attachment; filename="lease.pdf"'
    assert a.post(f"/api/matters/{mid}/documents", files={"file": ("x.txt", b"hi", "text/plain")}).status_code == 400
    for res in (b.get(f"/api/matters/{mid}/documents"), b.get(f"/api/documents/{doc['id']}"), b.get(f"/api/documents/{doc['id']}/download"), b.delete(f"/api/documents/{doc['id']}")):
        assert res.status_code == 404
    assert a.delete(f"/api/documents/{doc['id']}").status_code == 204
    assert a.get(f"/api/documents/{doc['id']}").status_code == 404


def test_templates_and_draft_generation(a, b, matter, trigger):
    templates = a.get("/api/templates").json()["templates"]
    assert templates, "system templates are seeded by database/seed SQL"
    t = templates[0]
    fields = {p: "value" for p in t["placeholders"]}
    draft = a.post(f"/api/matters/{matter['id']}/documents/generate", json={"template_id": t["id"], "fields": fields})
    assert draft.status_code == 201 and draft.json()["isDraft"] is True and draft.json()["mimeType"] == "text/plain"
    assert a.post(f"/api/matters/{matter['id']}/documents/generate", json={"template_id": t["id"], "fields": {}}).status_code == 400
    assert b.post(f"/api/matters/{matter['id']}/documents/generate", json={"template_id": t["id"], "fields": fields}).status_code == 404


def test_chat_relays_to_the_ai_module_in_process_without_an_llm_call(a, b, matter):
    mid = matter["id"]
    assert a.get(f"/api/matters/{mid}/chat").json() == {"messages": []}
    no_docs = a.post(f"/api/matters/{mid}/chat", json={"question": "What is the rent?"})
    assert no_docs.status_code == 422 and no_docs.json()["error"]["code"] == "NO_READY_DOCUMENTS"
    assert a.post(f"/api/matters/{mid}/chat", json={"question": " "}).status_code == 400
    assert a.patch(f"/api/matters/{mid}/chat/{uuid.uuid4()}/pin", json={"pinned": True}).status_code == 404
    assert a.patch(f"/api/matters/{mid}/chat/{uuid.uuid4()}/activate").status_code == 404
    assert b.get(f"/api/matters/{mid}/chat").status_code == 404


def test_search_recent_searches_notifications_preferences_firm(a, b, matter):
    assert [m["id"] for m in a.get("/api/search", params={"q": "lease"}).json()["matters"]] == [matter["id"]]
    assert b.get("/api/search", params={"q": "lease"}).json()["matters"] == []
    assert a.get("/api/search").status_code == 400
    a.post("/api/search/recent", json={"query": "lease"})
    assert a.get("/api/search/recent").json() == {"queries": ["lease"]}
    assert b.get("/api/search/recent").json() == {"queries": []}
    assert a.get("/api/notifications").json() == {"notifications": []}
    assert a.patch("/api/notifications/read-all").json() == {"markedCount": 0}
    assert a.patch("/api/auth/me/preferences", json={"deadlineRemindersEnabled": False}).json() == {"deadlineRemindersEnabled": False}
    assert b.get("/api/auth/me/preferences").json() == {"deadlineRemindersEnabled": True}
    assert len(a.get("/api/firm/lawyers").json()["lawyers"]) == 1


def test_deleting_a_matter_with_branched_chat_history_cascades_regression(a, matter, trigger):
    """The Java backend 500'd here: Hibernate deleted chat rows one at a time,
    hit a child the DB had already cascade-deleted with its parent, and
    rolled the whole delete back. Seeds a real Q/A tree with a citation."""
    mid = matter["id"]
    doc = a.post(f"/api/matters/{mid}/documents", files={"file": ("lease.pdf", b"%PDF-1.4", "application/pdf")}).json()["documents"][0]
    lawyer_id = a.get("/api/auth/me").json()["lawyer"]["id"]
    question, answer = str(uuid.uuid4()), str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO chat_messages (id, matter_id, lawyer_id, role, content) VALUES (:id, :m, :l, 'user', 'Q')"), {"id": question, "m": mid, "l": lawyer_id})
        conn.execute(text("INSERT INTO chat_messages (id, matter_id, role, content, parent_id) VALUES (:id, :m, 'assistant', 'A', :p)"), {"id": answer, "m": mid, "p": question})
        conn.execute(text("UPDATE chat_messages SET active_child_id = :a WHERE id = :q"), {"a": answer, "q": question})
        conn.execute(text("UPDATE matters SET active_root_message_id = :q WHERE id = :m"), {"q": question, "m": mid})
        conn.execute(text("INSERT INTO citations (chat_message_id, document_id, excerpt) VALUES (:a, :d, 'x')"), {"a": answer, "d": doc["id"]})

    assert a.delete(f"/api/matters/{mid}").status_code == 204
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM chat_messages WHERE matter_id = :m"), {"m": mid}).scalar_one() == 0
        assert conn.execute(text("SELECT count(*) FROM citations WHERE chat_message_id = :a"), {"a": answer}).scalar_one() == 0
        assert conn.execute(text("SELECT count(*) FROM documents WHERE matter_id = :m"), {"m": mid}).scalar_one() == 0
    assert a.get(f"/api/matters/{mid}").status_code == 404
