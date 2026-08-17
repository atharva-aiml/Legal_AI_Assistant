import pytest

import app.application.chat_service as chat_service_module
from app.application.chat_service import AssistantUnavailableError, ChatMessageNotFoundError, ChatService, NoReadyDocumentsError
from app.domain.chat import ChatMessage, Citation, DocumentMetadata, NOT_FOUND_RESPONSE, OUT_OF_SCOPE_RESPONSE


class FakeChunk:
    def __init__(self, id, document_id, file_name, page_number, content):
        self.id = id
        self.document_id = document_id
        self.file_name = file_name
        self.page_number = page_number
        self.content = content


class InMemoryChatRetrievalRepository:
    def __init__(self):
        self.ready_documents: dict[str, int] = {}
        self.chunks: dict[str, FakeChunk] = {}
        self.vector_order: dict[str, list[str]] = {}
        self.keyword_order: dict[str, list[str]] = {}
        self.metadata: dict[str, list[DocumentMetadata]] = {}
        self.all_chunks_by_matter: dict[str, list[FakeChunk]] = {}
        self.fail = False
        self.vector_search_called = False
        self.keyword_search_called = False

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


class InMemoryChatMessageRepository:
    def __init__(self):
        self.messages: list[ChatMessage] = []
        self.citations: list[Citation] = []
        self._n = 0

    def _next_id(self):
        self._n += 1
        return f"id-{self._n}"

    def save_user_message(self, matter_id, lawyer_id, content):
        msg = ChatMessage(id=self._next_id(), matter_id=matter_id, lawyer_id=lawyer_id, role="user", content=content)
        self.messages.append(msg)
        return msg

    def save_assistant_message(self, matter_id, content, citations):
        msg = ChatMessage(id=self._next_id(), matter_id=matter_id, lawyer_id=None, role="assistant", content=content)
        self.messages.append(msg)
        created = []
        for document_id, page_number, excerpt, file_name in citations:
            c = Citation(
                id=self._next_id(),
                chat_message_id=msg.id,
                document_id=document_id,
                page_number=page_number,
                excerpt=excerpt,
                file_name=file_name,
            )
            self.citations.append(c)
            created.append(c)
        return msg, created

    def recent_messages(self, matter_id, limit):
        return [m for m in self.messages if m.matter_id == matter_id][-limit:]

    def list_messages(self, matter_id):
        return [(m, [c for c in self.citations if c.chat_message_id == m.id]) for m in self.messages if m.matter_id == matter_id]

    def toggle_pin(self, matter_id, message_id, pinned):
        for i, m in enumerate(self.messages):
            if m.id == message_id and m.matter_id == matter_id and m.role == "assistant":
                updated = ChatMessage(id=m.id, matter_id=m.matter_id, lawyer_id=m.lawyer_id, role=m.role, content=m.content, created_at=m.created_at, pinned=pinned)
                self.messages[i] = updated
                return updated
        return None

    def list_pinned(self, matter_id):
        return [(m, [c for c in self.citations if c.chat_message_id == m.id]) for m in self.messages if m.matter_id == matter_id and m.pinned]


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
    assert "[1] Page one content." in llm.calls[0]
    assert "[2] Page two content." in llm.calls[0]


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
    assert "[1] Test Page 1 of 10" in llm.calls[0]
    assert "[2] matter.pdf has 11 pages." in llm.calls[0]


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
    assert "[1] Test Page 1 of 10" in llm.calls[0]
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
    messages = InMemoryChatMessageRepository()
    messages.save_user_message(MATTER, LAWYER, "What is the rent?")
    messages.save_assistant_message(MATTER, "Rs. 85,000 [1].", [("doc-1", 2, "the rent is...", "lease.pdf")])
    service = make_service(messages=messages)

    history = service.history(MATTER)

    assert len(history) == 2
    user_msg, user_citations = history[0]
    assert user_msg.role == "user" and user_citations == []
    assistant_msg, assistant_citations = history[1]
    assert assistant_msg.role == "assistant"
    assert len(assistant_citations) == 1


# --- I-34: pinning ---


def test_pinning_an_assistant_message_marks_it_pinned():
    messages = InMemoryChatMessageRepository()
    assistant_msg, _ = messages.save_assistant_message(MATTER, "Rs. 85,000 [1].", [("doc-1", 2, "the rent is...", "lease.pdf")])
    service = make_service(messages=messages)

    updated = service.toggle_pin(MATTER, assistant_msg.id, True)

    assert updated.pinned is True
    assert service.history(MATTER)[0][0].pinned is True, "the pin must be visible through the same read path as normal history"


def test_unpinning_clears_the_flag():
    messages = InMemoryChatMessageRepository()
    assistant_msg, _ = messages.save_assistant_message(MATTER, "Rs. 85,000 [1].", [("doc-1", 2, "the rent is...", "lease.pdf")])
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
    first, _ = messages.save_assistant_message(MATTER, "First answer [1].", [("doc-1", 1, "a", "f.pdf")])
    messages.save_assistant_message(MATTER, "Second answer, never pinned [1].", [("doc-1", 1, "a", "f.pdf")])
    third, _ = messages.save_assistant_message(MATTER, "Third answer [1].", [("doc-1", 1, "a", "f.pdf")])
    service = make_service(messages=messages)
    service.toggle_pin(MATTER, first.id, True)
    service.toggle_pin(MATTER, third.id, True)

    pinned = service.pinned(MATTER)

    assert [m.content for m, _ in pinned] == ["First answer [1].", "Third answer [1]."]
    assert all(len(c) == 1 for _, c in pinned), "pinned messages must still carry their citations"
