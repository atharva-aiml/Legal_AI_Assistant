from dataclasses import dataclass

from app.application.ports import ChatLLM, ChatMessageRepository, ChatRetrievalRepository, Embedder
from app.domain.chat import ChatMessage, Citation, DocumentMetadata, NOT_FOUND_RESPONSE, OUT_OF_SCOPE_RESPONSE, metadata_excerpt, validate_assistant_message
from app.domain.citation_verification import verify_citations
from app.domain.identifier_query import extract_identifier_refs
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
# most of the document. Below this character budget, every Ready chunk is
# included directly instead of relying on RRF-ranked selection — retrieval
# only still gates/ranks once a Matter's real corpus grows past what
# comfortably fits in one call.
#
# RAG-Pipeline-Development-History.md gap #7 (2026-08-25): the original
# 150K figure was picked purely for NFR-001 latency headroom, not because
# of any real technical ceiling — and a real Matter already live in this
# database (378 chunks, 353,336 chars) had already grown past it, silently
# losing its completeness guarantee with no signal to the lawyer. Raised
# after spiking the real ceiling directly against the real API (not
# assumed): a real 712,694-char prompt failed with the API's own error --
# "This model's maximum context length is 128000 tokens... your messages
# resulted in 142,948 tokens" (confirms gpt-4o-mini's real limit and this
# corpus's real ~4.99 chars/token ratio). A real 416,049-char full prompt
# (~400K content chars, the value below) succeeded in 10.6s; a real
# 463,971-char prompt (~450K) succeeded too but took 37.1s in that run —
# real API latency in this range didn't scale cleanly with size (variance
# dominates), so 400K was chosen as a round number with real margin under
# the hard 128K-token ceiling (~34% headroom after system prompt/history/
# output) while comfortably covering the real Matter that motivated this.
FULL_CONTEXT_CHAR_CAP = 400_000

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
    "A context item's section/page/table/image label (see below) tells you WHERE it is "
    "located, never WHAT it says. Never state, imply, or elaborate on a fact just "
    "because it's the kind of thing a section with that name would typically discuss — "
    "e.g. a section titled \"Corporate Governance Lessons\" does NOT license you to say "
    "anything about parent-company accountability, safety standards, or communication "
    "practices unless a context item's own body text actually says so. Every fact in "
    "your answer must trace to a specific item's actual text, never to a theme implied "
    "by its label or heading name.\n\n"
    "Every specific, concrete detail present in a context item you draw from — a "
    "monetary amount, date, percentage, calculation, statute/section number, party "
    "name, company name, or other proper noun — must be reproduced exactly as written "
    "in that item, never paraphrased into something vaguer, rounded, or generalized "
    "away. \"US$470 million\" must appear as \"US$470 million\", not \"a substantial "
    "settlement amount\"; \"the Supreme Court of India\" must be named, not \"the "
    "reviewing court\"; a specific year or date must be given, not \"around that time\". "
    "When answering a question about a specific section/topic, this means every such "
    "concrete detail present in that section's real context item(s) must actually "
    "appear in your answer — never silently drop a specific fact for a vaguer summary "
    "sentence, and never state a specific fact (a number, date, name) that isn't "
    "literally present in a context item, even if it sounds plausible for the topic.\n\n"
    "When asked to \"explain\", \"detail\", or \"brief\" a specific section, page, table, "
    "or image, you must cover EVERY context item that belongs to it — not a selective "
    "subset. Do not decide, on your own judgment, that one item's content is \"too "
    "generic\", \"already covered by another item\", or \"less important\" and leave it "
    "out — if it's a real context item under that section/page/table/image, state its "
    "actual content. A specific fact (a figure, date, or name) is never optional to "
    "include just because a nearby item also has generic commentary — state BOTH, not "
    "instead of each other. This document's own text sometimes repeats the same wording "
    "under several different sections — that repetition is NOT a reason to treat a fact "
    "as too generic, not truly specific to this section, or safe to skip: if it is the "
    "real content of a context item under the section asked about, it must be stated, "
    "with its own citation marker, exactly the same as if it appeared nowhere else.\n\n"
    "Every individual sentence that states a fact needs its OWN citation marker — not "
    "just the last sentence of a paragraph. If you write three sentences from the same "
    "context item, all three get that item's marker (e.g. [7]); do not write several "
    "unmarked sentences and only tag the final one, since every sentence without its "
    "own marker is discarded as unsupported regardless of how the paragraph around it "
    "was cited. This is checked mechanically, sentence by sentence, after you answer — "
    "repeating the same marker on consecutive sentences is correct and expected, never "
    "redundant. For example, if item [7] says \"The 1989 settlement required US$470 "
    "million. The settlement was reviewed by the Supreme Court in 1991.\", write: \"The "
    "1989 settlement required US$470 million [7]. The settlement was reviewed by the "
    "Supreme Court in 1991 [7].\" — NOT: \"The 1989 settlement required US$470 million. "
    "The settlement was reviewed by the Supreme Court in 1991 [7].\", which silently "
    "loses the first, unmarked sentence (and its dollar figure) to verification.\n\n"
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
    "Some numbered items begin with a parenthetical location label, e.g. "
    "\"[7] (Page 12) ...\", \"[7] (Section: \\\"Claims processing architecture\\\") ...\", "
    "\"[7] (Table 3) ...\", or \"[7] (Image 2) ...\" — these labels are the ONLY real, "
    "verified page/section/table/image identifiers in this document. A section label can "
    "be a full breadcrumb through nested headings, e.g. \"Section: \\\"53. Access to "
    "Justice > Mass claims and vulnerable populations\\\"\" — a lawyer asking about EITHER "
    "\"53. Access to Justice\" (the outer/parent heading) OR \"Mass claims and vulnerable "
    "populations\" (the inner/child heading) is referring to a real part of that same "
    "label; match against any part of the breadcrumb, not only the whole string. The "
    "bracketed "
    "number itself (the \"7\" in \"[7]\") is never a real page, section, table, or image "
    "number — it is only that item's position in this list, and must never be treated "
    "as if it matched a number the lawyer mentioned. If a lawyer asks about a specific "
    "page number, section NUMBER (e.g. \"section 54\"), table number, or image number, "
    "find it ONLY by matching their number against a real parenthetical label above — "
    "never by assuming the citation index [N] sharing that digit is the answer, and "
    "never by substituting a different item. If none exists (e.g. this document has no "
    "page numbers at all, or no section/table/image with that exact number), say so "
    "plainly — e.g. \"this document doesn't have page numbers\" — rather than "
    "guessing.\n\n"
    "A section asked about BY NAME is different from a section number, and gets more "
    "latitude: real section names are written by a human and a lawyer's own phrasing "
    "will rarely match one word-for-word. If no section's real name is an exact match, "
    "but one or more sections are clearly the closest real match on the actual topic "
    "asked about, explain the closest matching section(s) instead of refusing — but you "
    "MUST say plainly, in your own words, that this isn't the exact section name they "
    "used and name the real section you're using instead (e.g. \"There's no section "
    "literally titled 'Access to Justice', but the closest matching section is 'Why "
    "ordinary litigation was insufficient', which covers...\"). Never extend this "
    "same latitude to a page, section NUMBER, table, or image number — those are exact "
    "identifiers with no meaningful 'closest' one, and guessing among them is exactly "
    "the mistake the rule above forbids.\n\n"
    "When a question specifically asks to identify or explain what's on a page, or what "
    "a section is/contains, name the real section (from its label) explicitly in your "
    "answer text itself — e.g. \"Page 54 falls under Section 53. Access to Justice "
    "(specifically 'Mass claims and vulnerable populations')\" — don't just cite it "
    "silently and describe the content in generic terms; the section identity itself is "
    "part of what's being asked for.\n\n"
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


class ChatMessageNotFoundError(Exception):
    """404: no assistant message with that id in this Matter — covers a bad id, a
    different Matter's message, and a user message alike, same as the rest of this
    codebase collapsing an out-of-scope id to "not found" rather than a distinct error."""


@dataclass(frozen=True)
class AskResult:
    message: ChatMessage
    citations: list[Citation]
    low_confidence: bool
    # RAG-Pipeline-Development-History.md gap #7: True means every Ready
    # chunk was considered (a genuine completeness guarantee); False means
    # ranked retrieval was used instead (best-effort — a broad "summarize
    # everything" question is not guaranteed to have seen every chunk).
    # Ephemeral like low_confidence — computed per-request, not persisted,
    # so it's only present on the response to the question that produced it.
    full_context: bool


def _label_for(c) -> str:
    """The real, verified location identifiers for one chunk — page_number/
    section/element_number were previously computed and stored (for
    citations) but never actually shown to the model, so it had no way to
    answer "what's on page N" / "explain section X" / "describe table N"
    except by coincidence (see the 2026-08-20 bug: the model latched onto a
    citation index sharing digits with a number the lawyer asked about).
    This is the fix — put the real identifiers directly in the prompt."""
    parts = []
    if c.page_number is not None:
        parts.append(f"Page {c.page_number}")
    if getattr(c, "section", None):
        parts.append(f'Section: "{c.section}"')
    element_number = getattr(c, "element_number", None)
    chunk_type = getattr(c, "chunk_type", "prose")
    if element_number is not None and chunk_type == "table_or_list":
        parts.append(f"Table {element_number}")
    elif element_number is not None and chunk_type == "image":
        parts.append(f"Image {element_number}")
    return f"({', '.join(parts)}) " if parts else ""


def _format_context(chunks: list, metadata: list[DocumentMetadata]) -> str:
    parts = [f"[{i}] {_label_for(c)}{c.content}" for i, c in enumerate(chunks, start=1)]
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
            return self._generate_and_persist(matter_id, question, chunks=all_chunks, metadata=metadata, low_confidence=False, full_context=True)

        identifier_refs = extract_identifier_refs(question)
        try:
            # RAG-Pipeline-Development-History.md gap #1: a page/section/table/image
            # number named in the question is a real, verifiable identifier, not a
            # fuzzy-relevance guess — fetched directly so it can never be left out
            # by an unlucky RRF ranking, on top of (not instead of) normal hybrid search.
            exact_chunks = self.retrieval.exact_match_chunks(matter_id, identifier_refs) if identifier_refs else []
            query_embedding = self.embedder.embed([question])[0]
            vector_hits = self.retrieval.vector_search(matter_id, query_embedding, top_k=CANDIDATE_POOL_SIZE)
            keyword_hits = self.retrieval.keyword_search(matter_id, question, top_k=CANDIDATE_POOL_SIZE)
        except Exception as e:
            raise AssistantUnavailableError("retrieval failed") from e

        by_id = {c.id: c for c in [*exact_chunks, *vector_hits, *keyword_hits]}
        fused_scores = reciprocal_rank_fusion([c.id for c in vector_hits], [c.id for c in keyword_hits])

        if not exact_chunks and (not fused_scores or max(fused_scores.values()) < RELEVANCE_THRESHOLD):
            # Grounding Rule 2 still holds for document CONTENT: no chunk
            # content is ever shown to the LLM when nothing content-relevant
            # was found. Real system metadata (page counts, file names) is a
            # much narrower, non-hallucinatable surface, though — it's
            # provably real data, not retrieved/generatable text — so a
            # purely structural question ("how many documents are here")
            # can still be tried against metadata alone, with zero document
            # content ever entering the prompt.
            if metadata:
                return self._generate_and_persist(matter_id, question, chunks=[], metadata=metadata, low_confidence=False, full_context=False)
            return self._persist_answer(matter_id, NOT_FOUND_RESPONSE, [], low_confidence=False, full_context=False)

        # Exact-identifier chunks are never capped at CONTEXT_SIZE — a page or
        # table's own chunk count is naturally small and bounded, so truncating
        # it would just reintroduce the incompleteness this fix exists to solve.
        # Ranking only fills whatever budget is left over, for surrounding context.
        exact_ids = {c.id for c in exact_chunks}
        remaining_slots = max(CONTEXT_SIZE - len(exact_chunks), 0)
        ranked_ids = [cid for cid in top_n_by_score(fused_scores, len(fused_scores)) if cid not in exact_ids][:remaining_slots]
        chunks = exact_chunks + [by_id[chunk_id] for chunk_id in ranked_ids]
        # A guaranteed exact match is a certain, structural hit, not a fuzzy
        # score — it's never "low confidence" the way an ambiguous ranked
        # match can be, even if fused_scores itself is thin or empty.
        low_confidence = False if exact_chunks else max(fused_scores.values()) < CONFIDENT_THRESHOLD

        return self._generate_and_persist(matter_id, question, chunks=chunks, metadata=metadata, low_confidence=low_confidence, full_context=False)

    def _generate_and_persist(
        self, matter_id: str, question: str, chunks: list, metadata: list[DocumentMetadata], low_confidence: bool, full_context: bool
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
        return self._persist_answer(matter_id, verified.text, citation_data, low_confidence=low_confidence, full_context=full_context)

    @staticmethod
    def _citation_for(n: int, chunks: list, metadata: list[DocumentMetadata]) -> tuple[str, int | None, str, str, str | None]:
        if n <= len(chunks):
            c = chunks[n - 1]
            return c.document_id, c.page_number, c.content[:300], c.file_name, c.section
        m = metadata[n - len(chunks) - 1]
        return m.document_id, None, metadata_excerpt(m), m.file_name, None

    def _persist_answer(
        self,
        matter_id: str,
        content: str,
        citation_data: list[tuple[str, int | None, str, str, str | None]],
        low_confidence: bool,
        full_context: bool,
    ) -> AskResult:
        # BR-006, enforced as a real gate on the write path — not just documented.
        pending = [
            Citation(id="", chat_message_id="", document_id=d, page_number=p, excerpt=e, file_name=f, section=s)
            for d, p, e, f, s in citation_data
        ]
        validate_assistant_message(content, pending)

        message, citations = self.messages.save_assistant_message(matter_id, content, citation_data)
        return AskResult(message, citations, low_confidence=low_confidence, full_context=full_context)

    def history(self, matter_id: str) -> list[tuple[ChatMessage, list[Citation]]]:
        return self.messages.list_messages(matter_id)

    def toggle_pin(self, matter_id: str, message_id: str, pinned: bool) -> ChatMessage:
        message = self.messages.toggle_pin(matter_id, message_id, pinned)
        if message is None:
            raise ChatMessageNotFoundError()
        return message

    def pinned(self, matter_id: str) -> list[tuple[ChatMessage, list[Citation]]]:
        return self.messages.list_pinned(matter_id)
