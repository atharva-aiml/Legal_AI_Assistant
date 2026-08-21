from dataclasses import dataclass

from sqlalchemy import text

from app.domain.chat import ChatMessage, Citation, DocumentMetadata
from app.infrastructure.db import engine


@dataclass
class ChunkResult:
    id: str
    document_id: str
    file_name: str
    page_number: int | None
    content: str
    section: str | None = None
    chunk_type: str = "prose"
    element_number: int | None = None


class SqlAlchemyChatRepository:
    """SD-005 (Python owns chat_messages/citations, System Architecture §2).
    Raw SQL with an explicit ::vector cast, mirroring
    SqlAlchemyIngestionRepository's posture — no ORM fighting pgvector's
    custom type. Every retrieval query is hard-filtered to one Matter's
    Ready Documents at the SQL level (Grounding Rule 1) — BR-005 can't be
    bypassed by anything above this layer because the row is simply never
    fetched."""

    def ready_document_count(self, matter_id: str) -> int:
        with engine.connect() as conn:
            return conn.execute(
                text("SELECT count(*) FROM documents WHERE matter_id = :matter_id AND status = 'ready'"),
                {"matter_id": matter_id},
            ).scalar_one()

    def document_metadata(self, matter_id: str) -> list[DocumentMetadata]:
        """Real, system-computed facts (not retrieved chunk content) — the
        highest real page_number stored for a Document approximates its
        true page count for PDF/images (chunking is per-page, System
        Architecture §3); NULL for DOCX, which has no page concept at all."""
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT d.id AS document_id, d.file_name, max(dc.page_number) AS page_count "
                    "FROM documents d LEFT JOIN document_chunks dc ON dc.document_id = d.id "
                    "WHERE d.matter_id = :matter_id AND d.status = 'ready' "
                    "GROUP BY d.id, d.file_name ORDER BY d.created_at"
                ),
                {"matter_id": matter_id},
            ).mappings().all()
            return [DocumentMetadata(document_id=str(r["document_id"]), file_name=r["file_name"], page_count=r["page_count"]) for r in rows]

    def all_ready_chunks(self, matter_id: str) -> list[ChunkResult]:
        """Every chunk for the Matter's Ready Documents, in document/page
        reading order (not relevance rank) — used for the full-context path
        (AI Architecture §2) when the corpus is small enough to just include
        entirely rather than rely on RRF-ranked top-K selection."""
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT dc.id, dc.document_id, d.file_name, dc.page_number, dc.section, dc.chunk_type, dc.element_number, dc.content "
                    "FROM document_chunks dc JOIN documents d ON d.id = dc.document_id "
                    "WHERE d.matter_id = :matter_id AND d.status = 'ready' "
                    "ORDER BY d.created_at, dc.page_number, dc.created_at"
                ),
                {"matter_id": matter_id},
            ).mappings().all()
            return [ChunkResult(**dict(r)) for r in rows]

    def vector_search(self, matter_id: str, query_embedding: list[float], top_k: int) -> list[ChunkResult]:
        vector_literal = "[" + ",".join(str(x) for x in query_embedding) + "]"
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT dc.id, dc.document_id, d.file_name, dc.page_number, dc.section, dc.chunk_type, dc.element_number, dc.content "
                    "FROM document_chunks dc JOIN documents d ON d.id = dc.document_id "
                    "WHERE d.matter_id = :matter_id AND d.status = 'ready' "
                    "ORDER BY dc.embedding <=> CAST(:query_embedding AS vector) "
                    "LIMIT :top_k"
                ),
                {"matter_id": matter_id, "query_embedding": vector_literal, "top_k": top_k},
            ).mappings().all()
            return [ChunkResult(**dict(r)) for r in rows]

    def keyword_search(self, matter_id: str, query: str, top_k: int) -> list[ChunkResult]:
        # plainto_tsquery ANDs every significant word together — a natural-
        # language question phrased even slightly differently from the
        # source text (e.g. asking "how long" when the document says "the
        # term is 36 months", with no literal word "long" anywhere) then
        # matches nothing at all, even though several other words hit
        # cleanly. Reuse plainto_tsquery's stemming/stopword handling (don't
        # reimplement tokenization here) but flip its AND (&) to OR (|), so
        # any one matching word is enough — ts_rank still scores chunks
        # matching more words higher than chunks matching only one.
        or_query = "to_tsquery('english', replace(plainto_tsquery('english', :query)::text, ' & ', ' | '))"
        # 2026-08-20: section is folded into the searchable text, not just
        # dc.content — a section HEADING's own words (e.g. "Access to
        # Justice") never appear in its body prose (extraction strips
        # heading paragraphs out of chunk content, keeping them only as
        # metadata), so without this a section-name question could never
        # match via keyword search once a Matter outgrows the full-context
        # path, no matter how relevant the section actually is.
        searchable_text = "to_tsvector('english', coalesce(dc.section, '') || ' ' || dc.content)"
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT dc.id, dc.document_id, d.file_name, dc.page_number, dc.section, dc.chunk_type, dc.element_number, dc.content "
                    "FROM document_chunks dc JOIN documents d ON d.id = dc.document_id "
                    "WHERE d.matter_id = :matter_id AND d.status = 'ready' "
                    f"AND {searchable_text} @@ {or_query} "
                    f"ORDER BY ts_rank({searchable_text}, {or_query}) DESC "
                    "LIMIT :top_k"
                ),
                {"matter_id": matter_id, "query": query, "top_k": top_k},
            ).mappings().all()
            return [ChunkResult(**dict(r)) for r in rows]

    def save_user_message(self, matter_id: str, lawyer_id: str, content: str) -> ChatMessage:
        with engine.begin() as conn:
            row = conn.execute(
                text(
                    "INSERT INTO chat_messages (id, matter_id, lawyer_id, role, content, created_at) "
                    "VALUES (gen_random_uuid(), :matter_id, :lawyer_id, 'user', :content, now()) "
                    "RETURNING id, matter_id, lawyer_id, role, content, created_at, pinned"
                ),
                {"matter_id": matter_id, "lawyer_id": lawyer_id, "content": content},
            ).mappings().first()
            return _to_message(row)

    def save_assistant_message(
        self, matter_id: str, content: str, citations: list[tuple[str | None, int | None, str | None, str | None, str | None]]
    ) -> tuple[ChatMessage, list[Citation]]:
        with engine.begin() as conn:
            message_row = conn.execute(
                text(
                    "INSERT INTO chat_messages (id, matter_id, lawyer_id, role, content, created_at) "
                    "VALUES (gen_random_uuid(), :matter_id, NULL, 'assistant', :content, now()) "
                    "RETURNING id, matter_id, lawyer_id, role, content, created_at, pinned"
                ),
                {"matter_id": matter_id, "content": content},
            ).mappings().first()
            message = _to_message(message_row)

            created_citations = []
            for document_id, page_number, excerpt, file_name, section in citations:
                citation_row = conn.execute(
                    text(
                        "INSERT INTO citations (id, chat_message_id, document_id, page_number, section, excerpt, created_at) "
                        "VALUES (gen_random_uuid(), :chat_message_id, :document_id, :page_number, :section, :excerpt, now()) "
                        "RETURNING id, chat_message_id, document_id, page_number, section, excerpt, created_at"
                    ),
                    {
                        "chat_message_id": message.id,
                        "document_id": document_id,
                        "page_number": page_number,
                        "section": section,
                        "excerpt": excerpt,
                    },
                ).mappings().first()
                # file_name isn't a citations-table column (it's the source Document's, joined
                # at read time elsewhere) — passed straight through from what retrieval already had.
                created_citations.append(_to_citation({**dict(citation_row), "file_name": file_name}))

            return message, created_citations

    def recent_messages(self, matter_id: str, limit: int) -> list[ChatMessage]:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id, matter_id, lawyer_id, role, content, created_at, pinned FROM chat_messages "
                    "WHERE matter_id = :matter_id ORDER BY created_at DESC LIMIT :limit"
                ),
                {"matter_id": matter_id, "limit": limit},
            ).mappings().all()
            return [_to_message(r) for r in reversed(rows)]

    def list_messages(self, matter_id: str) -> list[tuple[ChatMessage, list[Citation]]]:
        with engine.connect() as conn:
            message_rows = conn.execute(
                text(
                    "SELECT id, matter_id, lawyer_id, role, content, created_at, pinned FROM chat_messages "
                    "WHERE matter_id = :matter_id ORDER BY created_at ASC"
                ),
                {"matter_id": matter_id},
            ).mappings().all()
            messages = [_to_message(r) for r in message_rows]
            if not messages:
                return []

            citations_by_message = self._citations_by_message(conn, matter_id)
            return [(m, citations_by_message.get(m.id, [])) for m in messages]

    def toggle_pin(self, matter_id: str, message_id: str, pinned: bool) -> ChatMessage | None:
        """I-34: pinnable state only ever applies to assistant answers — scoping the
        UPDATE to role='assistant' AND matter_id=:matter_id makes that the one place
        this is enforced, rather than trusting every caller to check it first."""
        with engine.begin() as conn:
            row = conn.execute(
                text(
                    "UPDATE chat_messages SET pinned = :pinned "
                    "WHERE id = :message_id AND matter_id = :matter_id AND role = 'assistant' "
                    "RETURNING id, matter_id, lawyer_id, role, content, created_at, pinned"
                ),
                {"pinned": pinned, "message_id": message_id, "matter_id": matter_id},
            ).mappings().first()
            return _to_message(row) if row else None

    def list_pinned(self, matter_id: str) -> list[tuple[ChatMessage, list[Citation]]]:
        with engine.connect() as conn:
            message_rows = conn.execute(
                text(
                    "SELECT id, matter_id, lawyer_id, role, content, created_at, pinned FROM chat_messages "
                    "WHERE matter_id = :matter_id AND pinned = true ORDER BY created_at ASC"
                ),
                {"matter_id": matter_id},
            ).mappings().all()
            messages = [_to_message(r) for r in message_rows]
            if not messages:
                return []

            citations_by_message = self._citations_by_message(conn, matter_id)
            return [(m, citations_by_message.get(m.id, [])) for m in messages]

    @staticmethod
    def _citations_by_message(conn, matter_id: str) -> dict[str, list[Citation]]:
        citation_rows = conn.execute(
            text(
                "SELECT c.id, c.chat_message_id, c.document_id, d.file_name, c.page_number, c.section, c.excerpt, c.created_at "
                "FROM citations c JOIN chat_messages m ON m.id = c.chat_message_id "
                # LEFT JOIN, not JOIN: REQ-027 lets a Document be deleted unconditionally,
                # and a Citation must survive that (AI Architecture §4, "persisted permanently").
                "LEFT JOIN documents d ON d.id = c.document_id "
                "WHERE m.matter_id = :matter_id ORDER BY c.created_at ASC"
            ),
            {"matter_id": matter_id},
        ).mappings().all()
        citations_by_message: dict[str, list[Citation]] = {}
        for r in citation_rows:
            citation = _to_citation(r)
            citations_by_message.setdefault(citation.chat_message_id, []).append(citation)
        return citations_by_message


def _to_message(row) -> ChatMessage:
    return ChatMessage(
        id=str(row["id"]),
        matter_id=str(row["matter_id"]),
        lawyer_id=str(row["lawyer_id"]) if row["lawyer_id"] else None,
        role=row["role"],
        content=row["content"],
        created_at=row["created_at"],
        pinned=bool(row["pinned"]),
    )


def _to_citation(row) -> Citation:
    return Citation(
        id=str(row["id"]),
        chat_message_id=str(row["chat_message_id"]),
        document_id=str(row["document_id"]) if row["document_id"] else None,
        page_number=row["page_number"],
        excerpt=row["excerpt"],
        file_name=row.get("file_name"),
        section=row.get("section"),
        created_at=row["created_at"],
    )
