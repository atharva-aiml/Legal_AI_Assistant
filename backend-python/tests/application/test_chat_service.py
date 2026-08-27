from dataclasses import replace

import pytest

import app.application.chat_service as chat_service_module
from app.application.chat_service import (
    AssistantUnavailableError,
    ChatMessageNotFoundError,
    ChatService,
    InvalidEditTargetError,
    NoReadyDocumentsError,
)
from app.domain.chat import ChatMessage, Citation, DocumentMetadata, NOT_FOUND_RESPONSE, OUT_OF_SCOPE_RESPONSE


class FakeChunk:
    def __init__(self, id, document_id, file_name, page_number, content, section=None, chunk_type="prose", element_number=None):
        self.id = id
        self.document_id = document_id
        self.file_name = file_name
        self.page_number = page_number
        self.content = content
        self.section = section
        self.chunk_type = chunk_type
        self.element_number = element_number


class InMemoryChatRetrievalRepository:
    def __init__(self):
        self.ready_documents: dict[str, int] = {}
        self.chunks: dict[str, FakeChunk] = {}
        self.vector_order: dict[str, list[str]] = {}
        self.keyword_order: dict[str, list[str]] = {}
        self.metadata: dict[str, list[DocumentMetadata]] = {}
        self.all_chunks_by_matter: dict[str, list[FakeChunk]] = {}
        self.exact_match_by_matter: dict[str, dict[tuple[str, int], list[FakeChunk]]] = {}
        self.fail = False
        self.vector_search_called = False
        self.keyword_search_called = False
        self.exact_match_refs_seen: list[tuple[str, int]] | None = None

    def ready_document_count(self, matter_id):
        return self.ready_documents.get(matter_id, 0)

    def vector_search(self, matter_id, query_embedding, top_k):
        self.vector_search_called = True
        if self.fail:
            raise RuntimeError("db unreachable")
        return [self.chunks[i] for i in self.vector_order.get(matter_id, [])[:top_k]]

    def keyword_search(self, matter_id, query, top_k):
        self.keyword_search_called = True
        if self.fail:
            raise RuntimeError("db unreachable")
        return [self.chunks[i] for i in self.keyword_order.get(matter_id, [])[:top_k]]

    def document_metadata(self, matter_id):
        if self.fail:
            raise RuntimeError("db unreachable")
        return self.metadata.get(matter_id, [])

    def all_ready_chunks(self, matter_id):
        if self.fail:
            raise RuntimeError("db unreachable")
        return self.all_chunks_by_matter.get(matter_id, [])

    def exact_match_chunks(self, matter_id, refs):
        self.exact_match_refs_seen = refs
        if self.fail:
            raise RuntimeError("db unreachable")
        by_ref = self.exact_match_by_matter.get(matter_id, {})
        seen_ids = set()
        result = []
        for ref in refs:
            for c in by_ref.get(ref, []):
                if c.id not in seen_ids:
                    seen_ids.add(c.id)
                    result.append(c)
        return result


class InMemoryChatMessageRepository:
    """Mirrors SqlAlchemyChatRepository's contract, including the branching
    methods added for edit-a-previous-message — same in-memory-fake-against-
    Protocol style as this codebase's other application-layer tests
    (CLAUDE.md §2), not a Mockito-style mock."""

    def __init__(self):
        self.messages: list[ChatMessage] = []
        self.citations: list[Citation] = []
        self.active_root: dict[str, str] = {}  # matter_id -> message_id, mirrors matters.active_root_message_id
        self._n = 0

    def _next_id(self):
        self._n += 1
        return f"id-{self._n}"

    def _replace(self, message_id, **changes):
        for i, m in enumerate(self.messages):
            if m.id == message_id:
                self.messages[i] = replace(m, **changes)
                return self.messages[i]
        return None

    def save_user_message(self, matter_id, lawyer_id, content, parent_id=None):
        msg = ChatMessage(id=self._next_id(), matter_id=matter_id, lawyer_id=lawyer_id, role="user", content=content, parent_id=parent_id)
        self.messages.append(msg)
        return msg

    def save_assistant_message(self, matter_id, content, citations, parent_id=None):
        msg = ChatMessage(id=self._next_id(), matter_id=matter_id, lawyer_id=None, role="assistant", content=content, parent_id=parent_id)
        self.messages.append(msg)
        created = []
        for document_id, page_number, excerpt, file_name, section in citations:
            c = Citation(
                id=self._next_id(),
                chat_message_id=msg.id,
                document_id=document_id,
                page_number=page_number,
                excerpt=excerpt,
                file_name=file_name,
                section=section,
            )
            self.citations.append(c)
            created.append(c)
        return msg, created

    def list_messages(self, matter_id):
        return [(m, [c for c in self.citations if c.chat_message_id == m.id]) for m in self.messages if m.matter_id == matter_id]

    def toggle_pin(self, matter_id, message_id, pinned):
        for m in self.messages:
            if m.id == message_id and m.matter_id == matter_id and m.role == "assistant":
                return self._replace(message_id, pinned=pinned)
        return None

    def list_pinned(self, matter_id):
        return [(m, [c for c in self.citations if c.chat_message_id == m.id]) for m in self.messages if m.matter_id == matter_id and m.pinned]

    def citations_for(self, message_id):
        return [c for c in self.citations if c.chat_message_id == message_id]

    # --- Edit-a-previous-message branching ---

    def get_by_id(self, message_id):
        return next((m for m in self.messages if m.id == message_id), None)

    def siblings(self, matter_id, parent_id):
        return [m for m in self.messages if m.matter_id == matter_id and m.parent_id == parent_id]

    def set_active_child(self, message_id, child_id):
        self._replace(message_id, active_child_id=child_id)

    def get_matter_active_root(self, matter_id):
        return self.active_root.get(matter_id)

    def set_matter_active_root(self, matter_id, message_id):
        self.active_root[matter_id] = message_id

    def active_path(self, matter_id):
        root_id = self.get_matter_active_root(matter_id)
        if root_id is None:
            return []
        path = []
        current = self.get_by_id(root_id)
        while current is not None:
            path.append(current)
            current = self.get_by_id(current.active_child_id) if current.active_child_id else None
        return path

    def history_before(self, message_id, limit):
        chain = []
        current = self.get_by_id(message_id)
        while current is not None and current.parent_id is not None and len(chain) < limit:
            parent = self.get_by_id(current.parent_id)
            if parent is None:
                break
            chain.append(parent)
            current = parent
        return list(reversed(chain))


class FakeEmbedder:
    def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


class ScriptedLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[str] = []

    def generate(self, system_prompt, user_prompt):
        self.calls.append(user_prompt)
        if not self.responses:
            raise AssertionError("LLM called more times than the test scripted")
        return self.responses.pop(0)


class FailingLLM:
    def generate(self, system_prompt, user_prompt):
        raise RuntimeError("LLM API down")


MATTER = "matter-1"
LAWYER = "lawyer-1"


def make_service(retrieval=None, messages=None, llm=None):
    return ChatService(
        retrieval=retrieval or InMemoryChatRetrievalRepository(),
        messages=messages or InMemoryChatMessageRepository(),
        embedder=FakeEmbedder(),
        llm=llm or ScriptedLLM([]),
    )


def force_large_corpus(monkeypatch, retrieval, matter_id):
    """Real matters always have >=1 chunk once ready_document_count>0 (a
    Document only reaches 'ready' after producing at least one chunk — see
    ingestion_service.py). These tests exercise the ranked-retrieval
    fallback path specifically, which only activates once a Matter's real
    corpus exceeds FULL_CONTEXT_CHAR_CAP — force that here rather than
    building a 150K-character fixture."""
    monkeypatch.setattr(chat_service_module, "FULL_CONTEXT_CHAR_CAP", 0)
    retrieval.all_chunks_by_matter[matter_id] = [FakeChunk("placeholder", "doc-x", "x.pdf", 1, "x")]


def test_no_ready_documents_raises_before_any_retrieval_or_message_is_saved():
    retrieval = InMemoryChatRetrievalRepository()  # ready_documents empty -> count 0
    messages = InMemoryChatMessageRepository()
    service = make_service(retrieval=retrieval, messages=messages)

    with pytest.raises(NoReadyDocumentsError):
        service.ask(MATTER, LAWYER, "What is the rent?")

    assert messages.messages == [], "nothing was ready to ground an answer in — the question should never be persisted"


# --- Full-context path (default for any Matter whose corpus fits the cap) ---


def test_full_context_path_includes_every_ready_chunk_with_no_ranking_or_search_calls():
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    retrieval.all_chunks_by_matter[MATTER] = [
        FakeChunk("c1", "doc-1", "matter.pdf", 1, "Page one content."),
        FakeChunk("c2", "doc-1", "matter.pdf", 2, "Page two content."),
    ]
    llm = ScriptedLLM(["Page one says X [1], and page two says Y [2]."])
    service = make_service(retrieval=retrieval, llm=llm)

    result = service.ask(MATTER, LAWYER, "Summarize both pages.")

    assert len(result.citations) == 2
    assert retrieval.vector_search_called is False
    assert retrieval.keyword_search_called is False
    assert "[1] (Page 1) Page one content." in llm.calls[0]
    assert "[2] (Page 2) Page two content." in llm.calls[0]


def test_full_context_path_offers_metadata_numbered_after_all_content_chunks():
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    retrieval.all_chunks_by_matter[MATTER] = [FakeChunk("c1", "doc-1", "matter.pdf", 1, "Test Page 1 of 10")]
    retrieval.metadata[MATTER] = [DocumentMetadata(document_id="doc-1", file_name="matter.pdf", page_count=11)]
    llm = ScriptedLLM(["The document actually has 11 pages [2]."])
    service = make_service(retrieval=retrieval, llm=llm)

    result = service.ask(MATTER, LAWYER, "How many pages does the document have?")

    assert "11 pages" in result.message.content
    assert result.citations[0].page_number is None
    assert "[1] (Page 1) Test Page 1 of 10" in llm.calls[0]
    assert "[2] matter.pdf has 11 pages." in llm.calls[0]


def test_full_context_path_reports_full_context_true():
    # RAG-Pipeline-Development-History.md gap #7: the lawyer needs a signal
    # that this answer had a genuine completeness guarantee (every Ready
    # chunk was considered), not just a best-effort ranked subset.
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    retrieval.all_chunks_by_matter[MATTER] = [FakeChunk("c1", "doc-1", "matter.pdf", 1, "Some content.")]
    llm = ScriptedLLM(["Some content is stated [1]."])
    service = make_service(retrieval=retrieval, llm=llm)

    result = service.ask(MATTER, LAWYER, "What does it say?")

    assert result.full_context is True


def test_full_context_path_low_confidence_is_always_false():
    # There's no partial-retrieval uncertainty concept once the LLM has the
    # entire corpus — confidence is left entirely to citation verification.
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    retrieval.all_chunks_by_matter[MATTER] = [FakeChunk("c1", "doc-1", "matter.pdf", 1, "Some content.")]
    llm = ScriptedLLM(["Some content is stated [1]."])
    service = make_service(retrieval=retrieval, llm=llm)

    result = service.ask(MATTER, LAWYER, "What does it say?")

    assert result.low_confidence is False


def test_full_context_path_still_says_not_found_when_the_llm_cannot_answer():
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    retrieval.all_chunks_by_matter[MATTER] = [FakeChunk("c1", "doc-1", "matter.pdf", 1, "Unrelated content.")]
    llm = ScriptedLLM([NOT_FOUND_RESPONSE])
    service = make_service(retrieval=retrieval, llm=llm)

    result = service.ask(MATTER, LAWYER, "What is the maximum penalty under the SEBI Act?")

    assert result.message.content == NOT_FOUND_RESPONSE
    assert result.citations == []


def test_full_context_path_returns_out_of_scope_for_a_legal_strategy_question():
    # Real bug repro: "what are the strongest documents for the developer"
    # still returned NOT_FOUND_RESPONSE even with the entire document
    # available — the documents address the topic, but answering it means
    # weighing evidence for one side, which is a legal-strategy judgment
    # (Requirements §4 Non-Goals), not organizing what's stated. Distinct
    # fixed response so the lawyer isn't told "not found" when it's really
    # "not something I can judge".
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    retrieval.all_chunks_by_matter[MATTER] = [FakeChunk("c1", "doc-1", "matter.pdf", 1, "Evidence matrix content.")]
    llm = ScriptedLLM([OUT_OF_SCOPE_RESPONSE])
    service = make_service(retrieval=retrieval, llm=llm)

    result = service.ask(MATTER, LAWYER, "What are the strongest documents for the developer?")

    assert result.message.content == OUT_OF_SCOPE_RESPONSE
    assert result.message.content != NOT_FOUND_RESPONSE
    assert result.citations == []


# --- Context labeling (2026-08-20 fix): real location identifiers must reach the
# LLM's prompt, not just the citation it builds after the fact — otherwise the
# model has no way to answer "what's on page/section/table/image N" except by
# coincidentally matching a citation index sharing digits with the question. ---


def test_a_docx_chunk_with_no_page_number_gets_no_page_label():
    # DOCX chunks always have page_number=None — must never fabricate a label.
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    retrieval.all_chunks_by_matter[MATTER] = [FakeChunk("c1", "doc-1", "matter.docx", None, "Some DOCX content.")]
    llm = ScriptedLLM(["Some DOCX content is stated [1]."])
    service = make_service(retrieval=retrieval, llm=llm)

    service.ask(MATTER, LAWYER, "What does it say?")

    assert "[1] Some DOCX content." in llm.calls[0]
    assert "(Page" not in llm.calls[0]


def test_a_chunk_with_a_section_is_labeled_with_its_section_in_the_prompt():
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    retrieval.all_chunks_by_matter[MATTER] = [
        FakeChunk("c1", "doc-1", "matter.docx", None, "Claims are processed via a fund.", section="Claims processing architecture")
    ]
    llm = ScriptedLLM(["Claims are processed via a fund [1]."])
    service = make_service(retrieval=retrieval, llm=llm)

    service.ask(MATTER, LAWYER, "Explain the claims processing architecture section.")

    assert '[1] (Section: "Claims processing architecture") Claims are processed via a fund.' in llm.calls[0]


def test_a_table_chunk_is_labeled_with_its_table_number_not_a_page_number():
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    retrieval.all_chunks_by_matter[MATTER] = [
        FakeChunk("c1", "doc-1", "matter.docx", None, "Row: value", section="Records", chunk_type="table_or_list", element_number=3)
    ]
    llm = ScriptedLLM(["The table shows a value [1]."])
    service = make_service(retrieval=retrieval, llm=llm)

    service.ask(MATTER, LAWYER, "Explain table 3.")

    assert '[1] (Section: "Records", Table 3) Row: value' in llm.calls[0]


def test_an_image_chunk_is_labeled_with_its_image_number():
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    retrieval.all_chunks_by_matter[MATTER] = [
        FakeChunk("c1", "doc-1", "matter.docx", None, "Site plan diagram text.", chunk_type="image", element_number=2)
    ]
    llm = ScriptedLLM(["The site plan shows the layout [1]."])
    service = make_service(retrieval=retrieval, llm=llm)

    service.ask(MATTER, LAWYER, "Describe image 2.")

    assert "[1] (Image 2) Site plan diagram text." in llm.calls[0]


# --- Ranked-retrieval fallback path (only once a Matter's real corpus exceeds the cap) ---


def test_below_relevance_threshold_returns_not_found_without_calling_the_llm_when_no_metadata_exists(monkeypatch):
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    force_large_corpus(monkeypatch, retrieval, MATTER)
    # No candidates in either list at all -> fused_scores is empty -> below threshold.
    # No document metadata either, so there's nothing left to even try.
    llm = ScriptedLLM([])
    service = make_service(retrieval=retrieval, llm=llm)

    result = service.ask(MATTER, LAWYER, "What is the rent?")

    assert result.message.content == NOT_FOUND_RESPONSE
    assert result.citations == []
    assert llm.calls == [], "Grounding Rule 2: no document content is ever shown to the LLM below the relevance threshold"


def test_below_relevance_threshold_with_metadata_still_tries_a_metadata_only_answer(monkeypatch):
    # A purely structural question ("how many documents") won't clear content
    # retrieval at all, but real metadata can still answer it — and no
    # document CONTENT is ever put in front of the LLM for this call, only
    # the metadata block, preserving Grounding Rule 2's spirit for content.
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    force_large_corpus(monkeypatch, retrieval, MATTER)
    retrieval.metadata[MATTER] = [DocumentMetadata(document_id="doc-1", file_name="lease.pdf", page_count=11)]
    llm = ScriptedLLM(["This Matter has one document, lease.pdf, with 11 pages [1]."])
    service = make_service(retrieval=retrieval, llm=llm)

    result = service.ask(MATTER, LAWYER, "How many documents are in this Matter?")

    assert "11 pages" in result.message.content
    assert len(result.citations) == 1
    assert result.citations[0].document_id == "doc-1"
    assert result.citations[0].page_number is None  # metadata citations have no specific page
    assert "Document metadata" in llm.calls[0]
    assert "Context:\n[1]" not in llm.calls[0], "no content chunk should be numbered [1] when there are none"


def test_below_relevance_threshold_with_metadata_that_still_cannot_answer_returns_not_found(monkeypatch):
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    force_large_corpus(monkeypatch, retrieval, MATTER)
    retrieval.metadata[MATTER] = [DocumentMetadata(document_id="doc-1", file_name="lease.pdf", page_count=11)]
    llm = ScriptedLLM([NOT_FOUND_RESPONSE])
    service = make_service(retrieval=retrieval, llm=llm)

    result = service.ask(MATTER, LAWYER, "What is the maximum penalty under the SEBI Act?")

    assert result.message.content == NOT_FOUND_RESPONSE
    assert result.citations == []


def test_metadata_is_offered_alongside_content_chunks_numbered_after_them(monkeypatch):
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    force_large_corpus(monkeypatch, retrieval, MATTER)
    retrieval.chunks["c1"] = FakeChunk("c1", "doc-1", "lease.pdf", 1, "Test Page 1 of 10")
    retrieval.vector_order[MATTER] = ["c1"]
    retrieval.keyword_order[MATTER] = ["c1"]
    retrieval.metadata[MATTER] = [DocumentMetadata(document_id="doc-1", file_name="lease.pdf", page_count=11)]

    llm = ScriptedLLM(["The document actually has 11 pages according to its real metadata [2]."])
    service = make_service(retrieval=retrieval, llm=llm)

    result = service.ask(MATTER, LAWYER, "How many pages does the document have?")

    assert "11 pages" in result.message.content
    assert len(result.citations) == 1
    assert result.citations[0].document_id == "doc-1"
    assert result.citations[0].page_number is None
    assert "[1] (Page 1) Test Page 1 of 10" in llm.calls[0]
    assert "[2] lease.pdf has 11 pages." in llm.calls[0]


def test_a_well_cited_answer_persists_with_real_citations(monkeypatch):
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    force_large_corpus(monkeypatch, retrieval, MATTER)
    retrieval.chunks["c1"] = FakeChunk("c1", "doc-1", "lease.pdf", 2, "The monthly rent is Rs. 85,000.")
    retrieval.vector_order[MATTER] = ["c1"]
    retrieval.keyword_order[MATTER] = ["c1"]

    llm = ScriptedLLM(["The monthly rent is Rs. 85,000 [1]."])
    service = make_service(retrieval=retrieval, llm=llm)

    result = service.ask(MATTER, LAWYER, "What is the monthly rent?")

    assert "85,000" in result.message.content
    assert len(result.citations) == 1
    assert result.citations[0].document_id == "doc-1"
    assert result.citations[0].page_number == 2
    assert result.low_confidence is False  # cited by both retrieval methods -> above the confident band
    assert result.full_context is False  # ranked path -> no completeness guarantee, gap #7


def test_low_confidence_flag_set_when_only_one_retrieval_method_found_it(monkeypatch):
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    force_large_corpus(monkeypatch, retrieval, MATTER)
    retrieval.chunks["c1"] = FakeChunk("c1", "doc-1", "lease.pdf", 1, "Some tangentially related clause.")
    retrieval.vector_order[MATTER] = ["c1"]
    retrieval.keyword_order[MATTER] = []  # only found by one method -> above relevance floor, below confident band

    llm = ScriptedLLM(["This clause is tangentially related [1]."])
    service = make_service(retrieval=retrieval, llm=llm)

    result = service.ask(MATTER, LAWYER, "Is there a related clause?")

    assert result.low_confidence is True


# --- Exact-match identifier retrieval (RAG-Pipeline-Development-History.md gap #1) ---


def test_a_page_asked_by_number_is_included_even_though_ranking_never_found_it(monkeypatch):
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    force_large_corpus(monkeypatch, retrieval, MATTER)
    # Deliberately NOT in vector_order/keyword_order -> ranking alone would never surface it.
    page54 = FakeChunk("c-page54", "doc-1", "matter.pdf", 54, "Content that lives on page 54.")
    retrieval.exact_match_by_matter[MATTER] = {("page", 54): [page54]}

    llm = ScriptedLLM(["Page 54 says the content that lives there [1]."])
    service = make_service(retrieval=retrieval, llm=llm)

    result = service.ask(MATTER, LAWYER, "What is on page 54?")

    assert retrieval.exact_match_refs_seen == [("page", 54)]
    assert "[1] (Page 54) Content that lives on page 54." in llm.calls[0]
    assert result.low_confidence is False
    assert len(result.citations) == 1


def test_exact_match_bypasses_the_not_found_refusal_even_with_no_fused_score_hits(monkeypatch):
    # No vector/keyword hits at all (fused_scores empty) would normally trigger
    # NOT_FOUND_RESPONSE without calling the LLM -- a real, verified exact
    # identifier match must still get through, since it's a provable hit.
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    force_large_corpus(monkeypatch, retrieval, MATTER)
    table3 = FakeChunk("c-table3", "doc-1", "matter.pdf", 17, "Row: settlement amount.", chunk_type="table_or_list", element_number=3)
    retrieval.exact_match_by_matter[MATTER] = {("table", 3): [table3]}

    llm = ScriptedLLM(["Table 3 shows the settlement amount [1]."])
    service = make_service(retrieval=retrieval, llm=llm)

    result = service.ask(MATTER, LAWYER, "What does table 3 say?")

    assert result.message.content != NOT_FOUND_RESPONSE
    assert len(llm.calls) == 1


def test_exact_matches_are_never_truncated_by_context_size(monkeypatch):
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    force_large_corpus(monkeypatch, retrieval, MATTER)
    # More exact matches than CONTEXT_SIZE (8) -- all of them belong to the
    # same asked-about section and must all still reach the prompt.
    section_chunks = [
        FakeChunk(f"c-sec-{i}", "doc-1", "matter.pdf", i, f"Section content {i}.", section="53. Access to Justice")
        for i in range(10)
    ]
    retrieval.exact_match_by_matter[MATTER] = {("section", 53): section_chunks}

    llm = ScriptedLLM(["Section 53 covers ten points " + " ".join(f"[{i+1}]" for i in range(10)) + "."])
    service = make_service(retrieval=retrieval, llm=llm)

    service.ask(MATTER, LAWYER, "Explain section 53 in full.")

    for i in range(10):
        assert f"[{i + 1}] (Page {i}, Section: \"53. Access to Justice\") Section content {i}." in llm.calls[0]


def test_a_question_with_no_identifier_never_calls_exact_match(monkeypatch):
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    force_large_corpus(monkeypatch, retrieval, MATTER)
    retrieval.chunks["c1"] = FakeChunk("c1", "doc-1", "lease.pdf", 1, "The monthly rent is Rs. 85,000.")
    retrieval.vector_order[MATTER] = ["c1"]
    retrieval.keyword_order[MATTER] = ["c1"]

    llm = ScriptedLLM(["The monthly rent is Rs. 85,000 [1]."])
    service = make_service(retrieval=retrieval, llm=llm)

    service.ask(MATTER, LAWYER, "What is the monthly rent?")

    assert retrieval.exact_match_refs_seen is None, "no identifier in the question -> exact_match_chunks should never be called"


def test_an_uncited_answer_triggers_one_corrective_regeneration(monkeypatch):
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    force_large_corpus(monkeypatch, retrieval, MATTER)
    retrieval.chunks["c1"] = FakeChunk("c1", "doc-1", "lease.pdf", 1, "The term is 36 months.")
    retrieval.vector_order[MATTER] = ["c1"]
    retrieval.keyword_order[MATTER] = ["c1"]

    llm = ScriptedLLM(
        [
            "The term is 36 months.",  # first attempt: no citation marker at all
            "The term is 36 months [1].",  # corrective attempt: properly cited
        ]
    )
    service = make_service(retrieval=retrieval, llm=llm)

    result = service.ask(MATTER, LAWYER, "What is the term?")

    assert len(llm.calls) == 2, "an uncited answer must trigger exactly one corrective regeneration"
    assert result.message.content == "The term is 36 months [1]."
    assert len(result.citations) == 1


def test_a_still_uncited_answer_after_regeneration_is_stripped_not_kept_as_if_verified(monkeypatch):
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    force_large_corpus(monkeypatch, retrieval, MATTER)
    retrieval.chunks["c1"] = FakeChunk("c1", "doc-1", "lease.pdf", 1, "The term is 36 months.")
    retrieval.vector_order[MATTER] = ["c1"]
    retrieval.keyword_order[MATTER] = ["c1"]

    llm = ScriptedLLM(["The term is 36 months.", "The term is still 36 months."])  # both uncited
    service = make_service(retrieval=retrieval, llm=llm)

    result = service.ask(MATTER, LAWYER, "What is the term?")

    assert result.message.content == NOT_FOUND_RESPONSE
    assert result.citations == []


def test_retrieval_failure_raises_assistant_unavailable_not_a_fabricated_answer():
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    retrieval.fail = True
    service = make_service(retrieval=retrieval)

    with pytest.raises(AssistantUnavailableError):
        service.ask(MATTER, LAWYER, "What is the rent?")


def test_generation_failure_raises_assistant_unavailable_not_a_fabricated_answer():
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    retrieval.all_chunks_by_matter[MATTER] = [FakeChunk("c1", "doc-1", "lease.pdf", 1, "Some content.")]
    service = make_service(retrieval=retrieval, llm=FailingLLM())

    with pytest.raises(AssistantUnavailableError):
        service.ask(MATTER, LAWYER, "What does it say?")


def test_history_returns_messages_with_their_citations():
    # history() now walks the Matter's active path (branching), not "every row
    # by matter_id" -- build the tree by hand the way ask() would.
    messages = InMemoryChatMessageRepository()
    user_msg = messages.save_user_message(MATTER, LAWYER, "What is the rent?")
    messages.set_matter_active_root(MATTER, user_msg.id)
    assistant_msg, _ = messages.save_assistant_message(
        MATTER, "Rs. 85,000 [1].", [("doc-1", 2, "the rent is...", "lease.pdf", None)], parent_id=user_msg.id
    )
    messages.set_active_child(user_msg.id, assistant_msg.id)
    service = make_service(messages=messages)

    history = service.history(MATTER)

    assert len(history) == 2
    user_result, user_citations = history[0]
    assert user_result.role == "user" and user_citations == []
    assistant_result, assistant_citations = history[1]
    assert assistant_result.role == "assistant"
    assert len(assistant_citations) == 1


# --- I-34: pinning ---


def test_pinning_an_assistant_message_marks_it_pinned():
    messages = InMemoryChatMessageRepository()
    assistant_msg, _ = messages.save_assistant_message(MATTER, "Rs. 85,000 [1].", [("doc-1", 2, "the rent is...", "lease.pdf", None)])
    messages.set_matter_active_root(MATTER, assistant_msg.id)  # history() now walks the active path, not every row
    service = make_service(messages=messages)

    updated = service.toggle_pin(MATTER, assistant_msg.id, True)

    assert updated.pinned is True
    assert service.history(MATTER)[0][0].pinned is True, "the pin must be visible through the same read path as normal history"


def test_unpinning_clears_the_flag():
    messages = InMemoryChatMessageRepository()
    assistant_msg, _ = messages.save_assistant_message(MATTER, "Rs. 85,000 [1].", [("doc-1", 2, "the rent is...", "lease.pdf", None)])
    service = make_service(messages=messages)
    service.toggle_pin(MATTER, assistant_msg.id, True)

    updated = service.toggle_pin(MATTER, assistant_msg.id, False)

    assert updated.pinned is False


def test_pinning_a_user_message_is_not_found_not_silently_allowed():
    messages = InMemoryChatMessageRepository()
    user_msg = messages.save_user_message(MATTER, LAWYER, "What is the rent?")
    service = make_service(messages=messages)

    with pytest.raises(ChatMessageNotFoundError):
        service.toggle_pin(MATTER, user_msg.id, True)


def test_pinning_a_message_from_a_different_matter_is_not_found():
    messages = InMemoryChatMessageRepository()
    assistant_msg, _ = messages.save_assistant_message(MATTER, "Rs. 85,000 [1].", [])
    service = make_service(messages=messages)

    with pytest.raises(ChatMessageNotFoundError):
        service.toggle_pin("a-different-matter", assistant_msg.id, True)


def test_pinned_lists_only_pinned_messages_most_pin_order_preserved():
    messages = InMemoryChatMessageRepository()
    first, _ = messages.save_assistant_message(MATTER, "First answer [1].", [("doc-1", 1, "a", "f.pdf", None)])
    messages.save_assistant_message(MATTER, "Second answer, never pinned [1].", [("doc-1", 1, "a", "f.pdf", None)])
    third, _ = messages.save_assistant_message(MATTER, "Third answer [1].", [("doc-1", 1, "a", "f.pdf", None)])
    service = make_service(messages=messages)
    service.toggle_pin(MATTER, first.id, True)
    service.toggle_pin(MATTER, third.id, True)

    pinned = service.pinned(MATTER)

    assert [m.content for m, _ in pinned] == ["First answer [1].", "Third answer [1]."]
    assert all(len(c) == 1 for _, c in pinned), "pinned messages must still carry their citations"


# --- Edit-a-previous-message branching (ChatGPT-style edit-message arrows) ---


def make_branching_service(llm_responses):
    """A full-context Matter (small corpus) with a scripted LLM, real
    InMemoryChatMessageRepository so the tree-walking methods (active_path,
    history_before, siblings) are exercised the same way the real SQL
    repository would be, not stubbed out."""
    retrieval = InMemoryChatRetrievalRepository()
    retrieval.ready_documents[MATTER] = 1
    retrieval.all_chunks_by_matter[MATTER] = [FakeChunk("c1", "doc-1", "matter.pdf", 1, "The rent is Rs. 85,000.")]
    messages = InMemoryChatMessageRepository()
    llm = ScriptedLLM(llm_responses)
    service = make_service(retrieval=retrieval, messages=messages, llm=llm)
    return service, messages, llm


def test_editing_a_message_creates_a_sibling_never_deleting_the_original():
    service, messages, llm = make_branching_service(
        ["The rent is Rs. 85,000 [1].", "The updated rent is Rs. 90,000 [1]."]
    )
    service.ask(MATTER, LAWYER, "What is the rent?")
    original_user_id = next(m.id for m in messages.messages if m.content == "What is the rent?")

    edited_path = service.edit(MATTER, original_user_id, LAWYER, "What is the updated rent?")

    # Nothing was deleted/overwritten -- the original question row still exists as-is.
    original = messages.get_by_id(original_user_id)
    assert original is not None
    assert original.content == "What is the rent?"

    # It's now a sibling of the new question (same parent -- both root-level here).
    siblings = messages.siblings(MATTER, original.parent_id)
    assert {s.content for s in siblings} == {"What is the rent?", "What is the updated rent?"}

    # The edit's own returned active path is the new branch, in full.
    assert [m.content for m, _ in edited_path] == ["What is the updated rent?", "The updated rent is Rs. 90,000 [1]."]


def test_the_old_branch_stays_fully_fetchable_via_activate_branch_after_an_edit():
    service, messages, llm = make_branching_service(
        ["The rent is Rs. 85,000 [1].", "The updated rent is Rs. 90,000 [1]."]
    )
    service.ask(MATTER, LAWYER, "What is the rent?")
    original_user_id = next(m.id for m in messages.messages if m.content == "What is the rent?")
    service.edit(MATTER, original_user_id, LAWYER, "What is the updated rent?")

    # After the edit, GET history (active_path) returns only the NEW branch.
    assert [m.content for m, _ in service.history(MATTER)] == ["What is the updated rent?", "The updated rent is Rs. 90,000 [1]."]

    # Switching back to the old sibling brings its full original conversation back intact.
    reactivated = service.activate_branch(MATTER, original_user_id)

    assert [m.content for m, _ in reactivated] == ["What is the rent?", "The rent is Rs. 85,000 [1]."]
    assert [m.content for m, _ in service.history(MATTER)] == ["What is the rent?", "The rent is Rs. 85,000 [1]."]


def test_editing_a_non_first_message_repoints_its_parents_active_child_not_the_matter_root():
    service, messages, llm = make_branching_service(
        ["Answer 1 [1].", "Answer 2 [1].", "Answer 2 edited [1]."]
    )
    service.ask(MATTER, LAWYER, "Question 1?")
    service.ask(MATTER, LAWYER, "Question 2?")
    question1_id = next(m.id for m in messages.messages if m.content == "Question 1?")
    question2_id = next(m.id for m in messages.messages if m.content == "Question 2?")

    edited_path = service.edit(MATTER, question2_id, LAWYER, "Question 2 edited?")

    assert [m.content for m, _ in edited_path] == ["Question 1?", "Answer 1 [1].", "Question 2 edited?", "Answer 2 edited [1]."]
    # The Matter's root pointer is untouched -- editing Q2 only repoints Q1's active_child.
    assert messages.get_matter_active_root(MATTER) == question1_id


def test_history_before_never_pulls_in_a_sibling_branchs_messages():
    service, messages, llm = make_branching_service(
        ["First branch answer [1].", "Second branch answer [1]."]
    )
    service.ask(MATTER, LAWYER, "First question?")
    first_user_id = next(m.id for m in messages.messages if m.content == "First question?")
    service.edit(MATTER, first_user_id, LAWYER, "Edited question?")
    edited_assistant_id = next(m.id for m in messages.messages if m.content == "Second branch answer [1].")

    # A naive "last N rows by matter_id" would include "First question?" (it's
    # an earlier row in the same Matter) -- history_before must not, since it
    # only exists on the sibling branch, not on the edited branch's own chain.
    history = messages.history_before(edited_assistant_id, limit=10)

    assert [m.content for m in history] == ["Edited question?"]
    assert "First question?" not in [m.content for m in history]


def test_editing_a_non_user_message_is_rejected():
    service, messages, llm = make_branching_service(["The rent is Rs. 85,000 [1]."])
    service.ask(MATTER, LAWYER, "What is the rent?")
    assistant_id = next(m.id for m in messages.messages if m.role == "assistant")

    with pytest.raises(InvalidEditTargetError):
        service.edit(MATTER, assistant_id, LAWYER, "New question")


def test_editing_a_nonexistent_message_is_not_found():
    service, messages, llm = make_branching_service([])
    with pytest.raises(ChatMessageNotFoundError):
        service.edit(MATTER, "no-such-id", LAWYER, "anything")


def test_activating_a_nonexistent_branch_is_not_found():
    service, messages, llm = make_branching_service([])
    with pytest.raises(ChatMessageNotFoundError):
        service.activate_branch(MATTER, "no-such-id")


def test_sibling_ids_includes_the_message_itself_and_every_sibling():
    service, messages, llm = make_branching_service(["Answer 1 [1].", "Answer 1 edited [1]."])
    service.ask(MATTER, LAWYER, "Question?")
    original_id = next(m.id for m in messages.messages if m.content == "Question?")
    service.edit(MATTER, original_id, LAWYER, "Question edited?")
    edited_id = next(m.id for m in messages.messages if m.content == "Question edited?")

    original = messages.get_by_id(original_id)
    ids = service.sibling_ids(original)

    assert set(ids) == {original_id, edited_id}
