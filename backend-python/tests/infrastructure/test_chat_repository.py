import pytest
from sqlalchemy import text

from app.infrastructure.chat_repository import SqlAlchemyChatRepository
from app.infrastructure.db import engine

# RAG-Pipeline-Development-History.md gap #4: plainto_tsquery's AND semantics
# is a real bug *class* in this codebase (Phase 1.1), already fixed here by
# flipping to OR across the same stemmed terms -- but that fix had zero
# automated regression coverage. Application-layer tests only ever exercise
# an in-memory fake, never this real SQL, so a future "simplification" back
# to plain plainto_tsquery would only be caught by another live user
# complaint. This test locks in the exact 2026-08-15 repro case against the
# real database.

_ZERO_VECTOR = "[" + ",".join(["0"] * 384) + "]"


@pytest.fixture
def matter_with_a_differently_worded_chunk():
    with engine.begin() as conn:
        firm_id = conn.execute(text("INSERT INTO firms (name) VALUES ('Test Firm') RETURNING id")).scalar_one()
        lawyer_id = conn.execute(
            text(
                "INSERT INTO lawyers (firm_id, name, email, password_hash) "
                "VALUES (:firm_id, 'Test Lawyer', 'test-gap4@example.com', 'x') RETURNING id"
            ),
            {"firm_id": firm_id},
        ).scalar_one()
        client_id = conn.execute(
            text("INSERT INTO clients (firm_id, name) VALUES (:firm_id, 'Test Client') RETURNING id"), {"firm_id": firm_id}
        ).scalar_one()
        matter_id = conn.execute(
            text("INSERT INTO matters (firm_id, client_id, title) VALUES (:firm_id, :client_id, 'Test Matter') RETURNING id"),
            {"firm_id": firm_id, "client_id": client_id},
        ).scalar_one()
        document_id = conn.execute(
            text(
                "INSERT INTO documents (matter_id, uploaded_by, file_name, storage_key, mime_type, size_bytes, status) "
                "VALUES (:matter_id, :lawyer_id, 'lease.pdf', 'test-key', 'application/pdf', 100, 'ready') RETURNING id"
            ),
            {"matter_id": matter_id, "lawyer_id": lawyer_id},
        ).scalar_one()
        conn.execute(
            text(
                "INSERT INTO document_chunks (document_id, page_number, content, embedding) "
                "VALUES (:document_id, 1, :content, CAST(:embedding AS vector))"
            ),
            {"document_id": document_id, "content": "The term is 36 months.", "embedding": _ZERO_VECTOR},
        )

    yield str(matter_id)

    with engine.begin() as conn:
        # document_chunks cascades from documents (schema.ts: onDelete: "cascade")
        conn.execute(text("DELETE FROM documents WHERE id = :id"), {"id": document_id})
        conn.execute(text("DELETE FROM matters WHERE id = :id"), {"id": matter_id})
        conn.execute(text("DELETE FROM clients WHERE id = :id"), {"id": client_id})
        conn.execute(text("DELETE FROM lawyers WHERE id = :id"), {"id": lawyer_id})
        conn.execute(text("DELETE FROM firms WHERE id = :id"), {"id": firm_id})


def test_a_differently_worded_natural_language_question_still_matches_via_or_flip(matter_with_a_differently_worded_chunk):
    # Real repro (Phase 1.1, 2026-08-15): "how long" shares no literal word
    # with "the term is 36 months" -- plainto_tsquery's AND semantics would
    # match zero rows here, even though "term" alone is a clean, relevant hit.
    repo = SqlAlchemyChatRepository()

    results = repo.keyword_search(matter_with_a_differently_worded_chunk, "how long is the lease term", top_k=5)

    assert any("36 months" in r.content for r in results), (
        "keyword_search matched nothing for a naturally-phrased question against a chunk "
        "that only shares one word ('term') with it -- this is the exact AND-semantics "
        "regression gap #4 warns could silently reappear."
    )
