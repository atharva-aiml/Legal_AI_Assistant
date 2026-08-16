from dataclasses import dataclass

from app.application.ports import ChatLLM, ChatMessageRepository, ChatRetrievalRepository, Embedder
from app.domain.chat import ChatMessage, Citation, DocumentMetadata, NOT_FOUND_RESPONSE, OUT_OF_SCOPE_RESPONSE, metadata_excerpt, validate_assistant_message
from app.domain.citation_verification import verify_citations
from app.domain.retrieval import reciprocal_rank_fusion, top_n_by_score

# AI Architecture §2: top 6-8 fused chunks passed to the LLM (only reached
# once a Matter's corpus exceeds FULL_CONTEXT_CHAR_CAP below); 20 candidates
# per retrieval method before fusion; last 4 turns for conversation context.
CONTEXT_SIZE = 8
CANDIDATE_POOL_SIZE = 20
RECENT_TURNS = 4

# Real bug (2026-08-16): a ranked top-8 selection structurally cannot answer
# broad questions ("create a complete chronology", "identify all important
# dates") against a Matter with real content spread across dozens of pages —
# confirmed against a real 50-chunk/60-page test document where the answer
# to "how many pages" needed one chunk, but "chronology" legitimately needed
# most of the document. Below this character budget (~37K tokens, well
# inside gpt-4o-mini's context window even after system prompt/history/
# output), every Ready chunk is included directly instead of relying on
# RRF-ranked selection — retrieval only still gates/ranks once a Matter's
# real corpus grows past what comfortably fits in one call.
FULL_CONTEXT_CHAR_CAP = 150_000

# Spiked against real retrieved chunks, not decided on paper (Technology
# Decision Log) — RRF fused-score floor below which nothing is considered
# relevant enough to even call the LLM (Grounding Rule 2), only used once a
# Matter's corpus exceeds FULL_CONTEXT_CHAR_CAP. This is a sum of
# 1/(k+rank) terms (k=60), not a raw cosine similarity, so the scale is
# small by construction.
RELEVANCE_THRESHOLD = 0.01
CONFIDENT_THRESHOLD = 0.02

SYSTEM_PROMPT = (
    "You are a legal document assistant helping a lawyer review a single Matter's "
    "uploaded documents. Answer using ONLY the numbered context items provided "
    "below — never use outside knowledge.\n\n"
    "For broad requests (e.g. \"explain this document\" or \"summarize the matter\"), "
    "organizing and restating what the context actually says into a clear, structured "
    "answer is expected and encouraged — that is NOT the same as unsupported synthesis. "
    "Unsupported synthesis specifically means: stating a legal conclusion, opinion, "
    "prediction, or inferred fact that no context item explicitly says (e.g. deciding "
    "who is liable, or predicting an outcome) — never do that. Restating, organizing, "
    "or summarizing facts the context does state is always allowed, no matter how many "
    "items or how broad the question.\n\n"
    "Be precise about which specific item a fact comes from — never generalize a fact "
    "stated about one specific topic (e.g. a gap noted for one particular ledger or "
    "claim) to a different, related topic it wasn't actually stated about (e.g. a "
    "different ledger or claim), even if both appear in the same answer. When a "
    "question asks for a comprehensive result (a complete chronology, all dates, every "
    "instance of something), include every one the context actually supports — do not "
    "silently select a subset.\n\n"
    "Two common request types get a structured, labeled format, in addition to full "
    "cited detail — do not shorten the substance to fit the labels, and every factual "
    "sentence inside these sections STILL needs its own citation marker, exactly like "
    "anywhere else in your answer — a clean, formatted structure is never a reason to "
    "drop citations:\n"
    "- A matter overview (\"what is this matter about\", \"explain this document\"): lead "
    "with Client / Opposing Party / Forum (each on its own line, cited), then the fuller "
    "narrative below (cited).\n"
    "- A complete matter assessment: use these section headers, in order: Matter, "
    "Client, Matter Type, Current Stage, Summary, Key Issues, Strong Evidence — with "
    "every factual sentence under Summary, Key Issues, and Strong Evidence individually "
    "cited, the same as a normal paragraph answer.\n\n"
    "Some numbered items are labeled \"Document metadata\" — these are real system "
    "facts about the files themselves (page counts, file names), not retrieved document "
    "content. For questions about page counts, file names, or how many documents exist "
    "in this Matter, prefer the metadata items over anything a document's own text says "
    "about itself, since a document's self-description can be wrong (e.g. a mislabeled "
    "page header).\n\n"
    "Every sentence that states a fact must end with a citation marker like [1] "
    "pointing at the specific numbered item it came from; a sentence with no marker is "
    "treated as unsupported and will be discarded. Only use the fixed response "
    f'"{NOT_FOUND_RESPONSE}" — exactly that, and nothing else — when the provided '
    "context genuinely does not address the question's topic at all. A broad question, "
    "or one that draws on several items, is not by itself a reason to use it.\n\n"
    "Some questions ask for a strategic or adversarial judgment rather than for the "
    "context to be organized or restated — e.g. \"which side has the stronger case\", "
    "\"should we settle\", \"what are the strongest documents for [a party]\" (this asks "
    "you to weigh evidence FOR one side against the other, not to report what a "
    "document says). Even if the context contains plenty on the topic, that is not "
    "something you can answer — respond with exactly: "
    f'"{OUT_OF_SCOPE_RESPONSE}" and nothing else. This is different from '
    f'"{NOT_FOUND_RESPONSE}": use that one when the topic simply isn\'t addressed in the '
    "context; use this one when the topic IS addressed, but the question asks you to "
    "make the kind of legal-strategy judgment only the lawyer can make."
)


class NoReadyDocumentsError(Exception):
    """422: the Matter has no Document with status='ready' yet — nothing to ground an answer in."""


class AssistantUnavailableError(Exception):
    """502: the retrieval query or the LLM call itself failed — a system fault, not a content gap."""


@dataclass(frozen=True)
class AskResult:
    message: ChatMessage
    citations: list[Citation]
    low_confidence: bool


def _format_context(chunks: list, metadata: list[DocumentMetadata]) -> str:
    parts = [f"[{i}] {c.content}" for i, c in enumerate(chunks, start=1)]
    if metadata:
        offset = len(chunks)
        parts.append(
            "Document metadata (real system facts about the files themselves, not "
            "retrieved content — use these for questions about page counts, file "
            "names, or how many documents exist in this Matter):"
        )
        parts.extend(f"[{offset + i}] {metadata_excerpt(m)}" for i, m in enumerate(metadata, start=1))
    return "\n\n".join(parts)


def _format_history(recent: list[ChatMessage]) -> str:
    if not recent:
        return ""
    lines = [f"{m.role}: {m.content}" for m in recent]
    return "Recent conversation:\n" + "\n".join(lines) + "\n\n"


class ChatService:
    """SD-005: full-context-or-hybrid-retrieval -> (threshold gate, large
    corpora only) -> grounded generation -> citation verification (AI
    Architecture §1). BR-005 is enforced one layer down, at the SQL level
    in the retrieval repository — this class never sees another Matter's
    chunks to begin with."""

    def __init__(self, retrieval: ChatRetrievalRepository, messages: ChatMessageRepository, embedder: Embedder, llm: ChatLLM):
        self.retrieval = retrieval
        self.messages = messages
        self.embedder = embedder
        self.llm = llm

    def ask(self, matter_id: str, lawyer_id: str, question: str) -> AskResult:
        if self.retrieval.ready_document_count(matter_id) == 0:
            raise NoReadyDocumentsError()

        self.messages.save_user_message(matter_id, lawyer_id, question)

        try:
            metadata = self.retrieval.document_metadata(matter_id)
            all_chunks = self.retrieval.all_ready_chunks(matter_id)
        except Exception as e:
            raise AssistantUnavailableError("retrieval failed") from e

        total_chars = sum(len(c.content) for c in all_chunks)
        if total_chars <= FULL_CONTEXT_CHAR_CAP:
            # Small enough to just include everything — no ranking, no
            # threshold gate, no risk of a broad question missing content
            # that simply wasn't in a relevance-ranked top-K.
            return self._generate_and_persist(matter_id, question, chunks=all_chunks, metadata=metadata, low_confidence=False)

        try:
            query_embedding = self.embedder.embed([question])[0]
            vector_hits = self.retrieval.vector_search(matter_id, query_embedding, top_k=CANDIDATE_POOL_SIZE)
            keyword_hits = self.retrieval.keyword_search(matter_id, question, top_k=CANDIDATE_POOL_SIZE)
        except Exception as e:
            raise AssistantUnavailableError("retrieval failed") from e

        by_id = {c.id: c for c in [*vector_hits, *keyword_hits]}
        fused_scores = reciprocal_rank_fusion([c.id for c in vector_hits], [c.id for c in keyword_hits])

        if not fused_scores or max(fused_scores.values()) < RELEVANCE_THRESHOLD:
            # Grounding Rule 2 still holds for document CONTENT: no chunk
            # content is ever shown to the LLM when nothing content-relevant
            # was found. Real system metadata (page counts, file names) is a
            # much narrower, non-hallucinatable surface, though — it's
            # provably real data, not retrieved/generatable text — so a
            # purely structural question ("how many documents are here")
            # can still be tried against metadata alone, with zero document
            # content ever entering the prompt.
            if metadata:
                return self._generate_and_persist(matter_id, question, chunks=[], metadata=metadata, low_confidence=False)
            return self._persist_answer(matter_id, NOT_FOUND_RESPONSE, [], low_confidence=False)

        top_ids = top_n_by_score(fused_scores, CONTEXT_SIZE)
        chunks = [by_id[chunk_id] for chunk_id in top_ids]
        low_confidence = max(fused_scores.values()) < CONFIDENT_THRESHOLD

        return self._generate_and_persist(matter_id, question, chunks=chunks, metadata=metadata, low_confidence=low_confidence)

    def _generate_and_persist(
        self, matter_id: str, question: str, chunks: list, metadata: list[DocumentMetadata], low_confidence: bool
    ) -> AskResult:
        recent = self.messages.recent_messages(matter_id, limit=RECENT_TURNS)
        context = _format_context(chunks, metadata)
        user_prompt = _format_history(recent) + f"Context:\n{context}\n\nQuestion: {question}"
        num_sources = len(chunks) + len(metadata)

        try:
            raw_answer = self.llm.generate(SYSTEM_PROMPT, user_prompt)
        except Exception as e:
            raise AssistantUnavailableError("generation failed") from e

        verified = verify_citations(raw_answer, num_chunks=num_sources)

        # verify_citations collapses to NOT_FOUND_RESPONSE in two different
        # cases: the LLM legitimately said so (all_valid=True, nothing to
        # regenerate), or every sentence got stripped for lacking a citation
        # (all_valid=False — the original answer had content, just none of
        # it grounded). Only all_valid distinguishes them; text alone can't.
        if not verified.all_valid:
            # Grounding Rule 5: one corrective regeneration attempt before
            # falling back to the stripped version — never left in as if verified.
            corrective_prompt = (
                f"{user_prompt}\n\nYour previous answer included a claim that wasn't clearly "
                f"grounded in the numbered context above. Answer again, citing ONLY items "
                f"1..{num_sources}, and only state what those items directly support."
            )
            try:
                retry_answer = self.llm.generate(SYSTEM_PROMPT, corrective_prompt)
                retry_verified = verify_citations(retry_answer, num_chunks=num_sources)
                if retry_verified.all_valid:
                    verified = retry_verified
            except Exception:
                pass  # keep the first (already-stripped) attempt rather than fail the whole request

        citation_data = [self._citation_for(n, chunks, metadata) for n in verified.cited_chunk_numbers]
        return self._persist_answer(matter_id, verified.text, citation_data, low_confidence=low_confidence)

    @staticmethod
    def _citation_for(n: int, chunks: list, metadata: list[DocumentMetadata]) -> tuple[str, int | None, str, str]:
        if n <= len(chunks):
            c = chunks[n - 1]
            return c.document_id, c.page_number, c.content[:300], c.file_name
        m = metadata[n - len(chunks) - 1]
        return m.document_id, None, metadata_excerpt(m), m.file_name

    def _persist_answer(
        self, matter_id: str, content: str, citation_data: list[tuple[str, int | None, str, str]], low_confidence: bool
    ) -> AskResult:
        # BR-006, enforced as a real gate on the write path — not just documented.
        pending = [
            Citation(id="", chat_message_id="", document_id=d, page_number=p, excerpt=e, file_name=f)
            for d, p, e, f in citation_data
        ]
        validate_assistant_message(content, pending)

        message, citations = self.messages.save_assistant_message(matter_id, content, citation_data)
        return AskResult(message, citations, low_confidence=low_confidence)

    def history(self, matter_id: str) -> list[tuple[ChatMessage, list[Citation]]]:
        return self.messages.list_messages(matter_id)
