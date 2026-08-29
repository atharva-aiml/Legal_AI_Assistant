# LEGAL AI ASSISTANT
## LinkedIn 3‑Part Technical Content & Media Strategy

*Master production document. Everything below is derived from the actual source tree — `backend-python/app/**`, `backend-java/src/**`, `database/schema/schema.ts`, `frontend/**` — and the project's own design docs (`05-System-Architecture.md`, `06-AI-Architecture.md`, `RAG-Pipeline-Development-History.md`, `03-UX-Product-Design.md`, `08-Technology-Decision-Log.md`). Where something could not be confirmed from artifacts it is marked* **Not verified from the available project artifacts.**

*Generated 2026‑08‑29. Diagrams referenced live in `/diagrams/` (PNG + editable SVG + `gen_diagrams.py`).*

---

### Executive Summary

The Legal AI Assistant is a case‑workspace web app for small law firms. A lawyer files clients and matters, uploads the documents for a matter (contracts, pleadings, correspondence, scanned exhibits), and then asks questions about *that matter's* documents in a chat panel. Every factual sentence in an answer comes back with a citation that links to the exact source file and — where the format allows — the page and the section heading, plus the quoted passage it rests on. If the documents don't address the question, the system says so in a fixed sentence rather than guessing. If the question asks for a legal judgment ("which side is stronger", "should we settle"), it declines, by design.

It is built as **three services with one hard boundary**: a Next.js frontend that holds no business logic and never touches the database; a Java/Spring Boot backend that owns authentication and all CRUD; and a Python/FastAPI backend that owns everything AI — document ingestion and the retrieval‑augmented chat pipeline. All three share one PostgreSQL database (with the `pgvector` extension) whose schema is authored by a standalone Drizzle migration tool, not by either backend's ORM.

What makes it more than "chat with PDF": the ingestion pipeline is **structure‑aware** — it detects headings, tables and embedded diagrams in PDF and DOCX and preserves that structure as queryable metadata, so a lawyer can ask "what's on page 54" or "explain Table 3" and get the *right* chunk, not a lexical coincidence. Retrieval is **hybrid** (exact‑identifier match + vector similarity + Postgres full‑text, merged with Reciprocal Rank Fusion). Grounding is **structural, not a polite prompt** — matter isolation is a SQL predicate; below a relevance threshold the LLM is never called; after generation, every citation marker is mechanically checked against the chunks that were actually retrieved, and unsupported sentences are stripped. And the system is honest about its own regime: for a large matter it tells the lawyer "this answer used the most relevant sections, not the whole document."

---

# PART 0 — PROJECT UNDERSTANDING

## 0.1 What it is, who it's for, what it solves

**What it is.** A multi‑tenant SaaS workspace where the unit of work is a *Matter* (a case) belonging to a *Client* belonging to a *Firm*. Around each Matter sit its Documents, its Deadlines, and an AI chat thread. The AI only ever answers from the documents of the one Matter you're looking at.

**Who it's for.** Solo practitioners and small firms — the architecture is explicitly tuned (Charter §5, System Architecture §3) for "≥ 50 concurrent Matters × 500 Documents", not thousands of tenants. It is a solo, self‑funded project with no deadline pressure, which is why the technology choices lean consistently toward *fewer moving parts and no per‑call cost* (local embedding model, local OCR, no message queue yet, filesystem storage in dev).

**What it solves.** A lawyer reviewing a case has tens to hundreds of pages across many files. The questions that matter — *"give me the complete correspondence chronology", "what does the indemnity clause actually say", "which page covers access to justice", "are there contradictions about payment"* — require reading widely and citing precisely. A general chatbot will answer fluently and sometimes wrongly, with no way to check it. This system is built so that (a) an answer is grounded in retrieved text or it isn't given, (b) every claim is traceable to a specific location a lawyer can open in seconds, and (c) the boundary between "organising what the documents say" and "making a legal call" is enforced, not blurred.

**What makes it different from a basic chatbot.**

| A basic "chat with PDF" | This system |
|---|---|
| One flat text blob, fixed‑size character chunks | Structure‑aware extraction: heading hierarchy, tables (row → `column: value`), embedded diagrams OCR'd **and** vision‑captioned; chunk boundaries never cross a page, heading, table, or image |
| Vector search, top‑K, hope | Exact‑identifier SQL match + vector + keyword, fused with RRF; a named "page 54 / Table 3 / §15" is fetched directly, never left to ranking |
| "Answer from context" in the prompt | Matter isolation is a SQL `WHERE` clause; below‑threshold questions never reach the LLM; post‑generation per‑sentence citation verification strips unsupported claims |
| Citations are page guesses | `Citation` rows persisted permanently with `document_id`, `page_number`, `section` breadcrumb, and the actual `excerpt`; survive deletion of the source file |
| Same behaviour at any size | Full‑context below 400 K chars (genuine completeness); hybrid+ranked above it — **and the answer tells the lawyer which regime produced it** |
| "I can't find that" == error | Fixed `NOT_FOUND` string (not an error) *and* a separate fixed `OUT_OF_SCOPE` string for "you're asking me to make a legal judgment" |

## 0.2 Project Capability Matrix

| Capability | Status | Evidence in project | Explanation |
|---|---|---|---|
| Document ingestion | ✅ Implemented | `app/application/ingestion_service.py`, `web/ingest_router.py` | `IngestionService.ingest()`: storage → extract → chunk → embed → persist; always ends in `ready` or `failed`. Triggered by Java's `HttpIngestionTrigger` right after upload. |
| PDF processing | ✅ Implemented | `extraction.py::_extract_pdf_segments` (`pdfplumber` + `pypdf`) | Structure‑aware: per‑character font size/weight → heading levels; `find_tables()` with bbox exclusion; real page numbers from PDF structure; embedded images via content‑stream `Do` check. |
| DOCX processing | ✅ Implemented | `extraction.py::_extract_docx_segments` (`python-docx`) | `iter_block_items()` walk in true document order; heading stack from `paragraph.style`; real `<w:tbl>` tables; page numbers from `<w:br w:type="page"/>` markers when present, honest `None` otherwise. |
| OCR | ✅ Implemented | EasyOCR 1.7.2, `extraction.py::_get_ocr_reader` (CPU, lazy singleton) | Standalone image uploads → one OCR pass (`page_number = 1`). Embedded diagrams in PDF/DOCX → OCR **plus** vision caption. **Scanned (image‑only) PDFs are not handled** — no text layer ⇒ `failed`. |
| Image understanding | ⚠️ Partial (Tier 1) | `app/infrastructure/vision.py::OpenAIImageCaptioner`, `_combine_ocr_and_caption` | `gpt-4o-mini` vision captions **embedded** diagrams at ingestion time; caption + OCR text are concatenated into the chunk. A blank/decorative image returns `NO_CONTENT` and is dropped. **Not built:** persisted image bytes, or a live "what does Image 2 show" call (Tier 2, deliberately deferred). |
| Table extraction | ✅ Implemented | `_rows_to_table_segments`, `chunk_type='table_or_list'`, `element_number` | Header row supplies field names; each data row → `col: value; col: value` segment so it reads in isolation. All rows of one table share an `element_number` ("Table 3"). Tighter 850‑char budget for table chunks. |
| Chunking | ✅ Implemented | `app/domain/chunk.py` (`chunk_pages`, `_pack_typed_segments`) | Adaptive by data *shape*, one fixed output. Sentence‑boundary packing, 1000‑char target / 150 overlap, whole‑sentence overlap. Hard boundary on page / heading / chunk‑type / element‑number change. |
| Metadata | ✅ Implemented | `document_chunks` columns; `DocumentMetadata` | Per chunk: `page_number`, `section` (full heading breadcrumb), `chunk_type`, `element_number`. Per document: `file_name`, computed `page_count` (`max(page_number)`). |
| Embeddings | ✅ Implemented | `app/infrastructure/embedding.py`, `all-MiniLM-L6-v2` (384‑dim) | Runs locally via `sentence-transformers`, no API key, no per‑call cost. Runtime token‑count check warns (does not block) if a text would exceed the model's real 256‑token limit. |
| Vector search | ✅ Implemented | `chat_repository.py::vector_search` | `ORDER BY dc.embedding <=> CAST(:q AS vector) LIMIT 20`, pgvector cosine distance, matter‑scoped. |
| Semantic retrieval | ✅ Implemented | vector_search + RRF | Catches paraphrase ("how long is the lease" ≈ "the term is 36 months"). |
| Exact retrieval | ✅ Implemented | `domain/identifier_query.py`, `chat_repository.py::exact_match_chunks`, `keyword_search` | Regex extracts `page/section/table/image` + number → direct SQL on the real column, **no `LIMIT`, bypasses the relevance gate**. Plus Postgres full‑text (OR‑flipped `tsquery`, section folded into the searchable text). |
| Cross‑reference resolution | ❌ Not implemented | `identifier_query.py` docstring; RAG history Phase 5 "Deliberately out of scope" | "See Section 8.2" inside a chunk is **not** followed. Clause/exhibit/annexure references have no storage column. The prompt *does* do breadcrumb (parent/child heading) matching and disclosed approximate section‑name matching, but there is no follow‑the‑pointer retrieval step. |
| LLM generation | ✅ Implemented | `app/infrastructure/llm.py::OpenAIChatLLM`, `gpt-4o-mini`, `temperature=0` | Single completion, no token streaming. System prompt + user prompt (history + numbered context + question). |
| Validation | ⚠️ Partial | `domain/citation_verification.py::verify_citations`; `domain/chat.py::validate_assistant_message` | Mechanical, per‑sentence: does each factual sentence carry a `[n]` marker resolving to a chunk actually retrieved this call? Unsupported sentences are dropped; one corrective regeneration is attempted. `BR-006` write‑path invariant blocks an uncited assistant row. **There is no independent fact‑checking model and no external truth source.** |
| Citations | ✅ Implemented | `citations` table; `_citation_for`; `chat-panel.tsx` renders links | One row per distinct source location: `document_id`, `page_number`, `section`, `excerpt` (`chunk.content[:300]`), joined `file_name`. `ON DELETE SET NULL` on `document_id` so a citation outlives its source file. |
| Multi‑document analysis | ✅ (within a Matter) | `all_ready_chunks(matter_id)`, `document_metadata(matter_id)` | Retrieval spans every `ready` Document in the Matter. Cross‑Matter is impossible by design (BR‑005, SQL filter). |
| Agent / workflow | ❌ No agent framework | `chat_service.py` (hand‑written); no LangGraph/LangChain in `requirements.txt` | Deterministic pipeline with one data‑driven branch (full‑context vs. ranked) and one bounded corrective‑regeneration loop. The chat *message tree* (edit/branch/regenerate) is conversation state, not an agent. |
| Document generation | ✅ Implemented (V0.8) | `backend-java` `DraftGenerationService`; `frontend/app/matters/[id]/generate-draft-modal.tsx` | Pre‑authored `Template` + Matter/Client data → new `Document` (`is_draft=true`) → ingested like any upload so it's queryable. **Renders as plain `.txt`, not real DOCX/PDF** (flagged scope decision). |
| Memory / state | ✅ (conversation) / ❌ (long‑term) | `chat_messages` tree, `history_before(id, limit=4)`, `RECENT_TURNS=4`, pinned messages | Last 4 turns of the *current branch* go into the prompt. Full thread persisted, branchable (ChatGPT‑style edit). No cross‑session user memory, no embedding of past conversations; retrieval always runs on the **current question only** (prevents topic drift). |

## 0.3 Technology Stack

### Application shape
- **Three services, one database.** Explicit user requirement (System Architecture §1). The frontend has no DB driver and no API routes of its own; every read/write is an HTTP call to Java (today) or Python. This boundary is the point of the split — see `CLAUDE.md §0`.

### Frontend
- **Next.js 15 (App Router), React 19, TypeScript 5 (strict), pnpm.** Renders 16 screens. Server Components call the Java API through `lib/api/java-client.ts::javaFetch()` (which explicitly forwards the session cookie server‑side); client components call `JAVA_API_URL_PUBLIC` with `fetch(..., { credentials: 'include' })`. Used because the UI is genuinely interactive (chat, polling, voice) and TypeScript catches shape drift against the backend DTOs.
- **`middleware.ts`** does a cheap cookie‑presence redirect only — *not* the real auth boundary.

### Backend — CRUD / "the rest of the backend"
- **Java 21 (LTS) + Spring Boot 4.1, Maven Wrapper (`mvnw`).** Owns auth, Firm/Client/Matter/Document/Deadline/Notification/Template/Search. Layered `domain → application (ports) → infrastructure → web`. `ddl-auto=validate` (never generates schema).
- **Spring Data JPA + Hibernate**, native `pgvector` untouched by Java (it never reads `document_chunks` content).
- **`spring-security-crypto` `BCryptPasswordEncoder` (cost 12)** for passwords; **plain SHA‑256** for session‑token hashes (the token is already 256 bits of `SecureRandom`).
- **Jackson 3** (`tools.jackson.*`, Spring Boot 4) for the Java↔Python JSON relay.
- `java.net.http.HttpClient` for both hand‑offs: `HttpIngestionTrigger` (fire‑and‑forget, virtual‑thread executor, marks `failed` if Python is unreachable) and `HttpChatGateway` (blocking, 30 s read timeout for `ask`/`edit`, 5 s connect, relays Python's status/body unchanged).

### Backend — AI
- **Python 3.13 + FastAPI 0.141**, `uvicorn`. Same layering as Java: `app/domain` (pure), `app/application` (`typing.Protocol` ports), `app/infrastructure`, `app/web`. Two internal routers: `/ingest/{document_id}` and `/chat/{matter_id}` (+ edit/activate/pin). Never called by the browser — only by Java, after auth + BR‑008.
- **SQLAlchemy 2.0** + `psycopg2-binary`. Raw SQL via `text()` with an explicit `CAST(:embedding AS vector)` — deliberately *not* the ORM layer, to control the pgvector type.

### LLM
- **OpenAI `gpt-4o-mini`, `temperature = 0`**, via the `openai` Python SDK 3.0. `OPENAI_CHAT_MODEL` env var (default `gpt-4o-mini`); `OPENAI_API_KEY` has **no default** — a missing key fails loudly. Chosen by asking the user directly (paid API on legal data) and spiked with a real 2‑chunk grounded prompt before any pipeline code was written. It is the **only paid external API** in the system.
- **Vision:** the same `gpt-4o-mini` (and the same OpenAI client) captions embedded diagrams at ingestion — no second vendor (`app/infrastructure/vision.py`).

### Embeddings
- **`sentence-transformers` 5.7, model `all-MiniLM-L6-v2`, 384 dimensions.** Fully local, no API key, no per‑call cost (fits the low‑budget constraint). Loaded once per process (lazy singleton). Real `max_seq_length` is **256 tokens**; this corpus's legal text runs ~5.0–5.1 chars/token, which drove `CHUNK_SIZE_CHARS` down to 1000 (see 3.5). `document_chunks.embedding` is fixed at `vector(384)` in the schema.

### Vector database
- **PostgreSQL 16 + `pgvector`.** One database for relational data *and* embeddings — no separate vector store at this scale. `pgvector/pgvector:pg16` Docker image (the vanilla `postgres:16` image doesn't ship the extension). Cosine distance operator `<=>`. No ANN index yet (exact scan; fine at the target scale — **Not verified from the available project artifacts** whether an `ivfflat`/`hnsw` index is planned).

### RAG
- Hand‑built. `reciprocal_rank_fusion` (`k=60`) in `app/domain/retrieval.py`; hybrid SQL in `chat_repository.py`; orchestration in `chat_service.py`. No RAG framework.

### Agent orchestration
- **None.** No LangGraph, no LangChain, no state‑machine library. `ChatService._answer()` is a straight‑line function with one `if total_chars <= FULL_CONTEXT_CHAR_CAP` branch and one `if not verified.all_valid` corrective‑regeneration attempt.

### Document processing
- **`pypdf` 6.16** (PDF object model, embedded images, content‑stream inspection), **`pdfplumber` 0.11** (per‑character font metrics, `find_tables()`, bbox filtering), **`python-docx` 1.2** (DOCX body walk, styles, `<w:tbl>`, page‑break markers, embedded‑image relationships), **`cryptography` 50** (AES‑encrypted PDFs — common in corporate/bank exports, so not optional).

### OCR
- **EasyOCR 1.7.2**, PyTorch‑based, CPU only (`gpu=False`), English. No system binary needed (Tesseract couldn't be installed — no admin rights). ~30 s one‑time model download, ~1.4 s/image after. `PYTHONIOENCODING=utf-8` needed on Windows for the first download (progress‑bar unicode).
- CPU‑only `torch` installed separately (`--index-url https://download.pytorch.org/whl/cpu`) so it doesn't drag CUDA libraries; shared by EasyOCR and `sentence-transformers`.

### Storage
- **Local filesystem `/uploads` at the repo root in dev** — Java writes (`LocalFilesystemStorageService`), Python reads (`LocalFileStorage`), same directory. Behind a `StorageService` interface so a `R2StorageService` (Cloudflare R2, `region: 'auto'`) swaps in for production without a rewrite. No R2 credentials in this environment.

### Infrastructure
- **Docker Compose** for local Postgres. **Railway** is the intended host (always‑on processes in any language, usage‑based pricing) — **not yet deployed; Not verified from the available project artifacts.**
- **No message queue.** BullMQ + Redis is named in the docs as the eventual durable‑retry layer for ingestion and the deadline scanner, but V0.3 deliberately ships a direct HTTP hand‑off instead. Every failure still ends in a visible `Document.status='failed'` with an `error_message`; re‑attempting currently means re‑uploading.

### Development tools
- **Drizzle Kit** (TypeScript) in `/database` — the single schema‑authoring tool across both backend languages (`pnpm db:generate` → review SQL → `pnpm db:migrate`). 16 migrations to date.
- **JUnit 5** (Java: domain tests plain, application tests against hand‑written in‑memory fakes), **pytest** (Python: `tests/domain`, `tests/application`, `tests/infrastructure` — 108 tests as of the last RAG‑history entry), **Playwright** (`/tests/e2e`, the 5 UX journeys, run against all services live).

## 0.4 Complete User Journey

*(Diagram: `diagrams/02_user_journey.png`.)*

1. **Open the app / a Matter.** Login (self‑hosted: BCrypt verify → `Session` row → httpOnly cookie). Land on the Dashboard, open a Client, open a Matter (`SCR-09`). The Chat tab is disabled until at least one Document is `ready` — "Upload a document first."
2. **Upload documents.** `POST /api/matters/:id/documents` (multipart). Java validates the MIME type *before* any storage I/O, stores the file, writes a `Document` row, sets `status = processing`, and calls Python's `POST /ingest/{id}` **without waiting** for it.
3. **Documents are processed** (Python, synchronous within the ingest request): fetch bytes → **extract** (branch on MIME: PDF via `pdfplumber`+`pypdf`, DOCX via `python-docx`, image via EasyOCR) → for embedded diagrams, OCR **+** `gpt-4o-mini` vision caption → **chunk** (`chunk_pages`, adaptive) → **embed** each chunk (`all-MiniLM-L6-v2`) → **persist** `document_chunks` rows via raw SQL with a `::vector` cast → `status = ready`. Any failure (bad file, no text, exception) → `status = failed` with a visible message.
4. **Knowledge is created.** The Matter now has N `document_chunks`, each carrying `content`, a 384‑dim `embedding`, and structural metadata (`page_number`, `section` breadcrumb, `chunk_type`, `element_number`). The frontend polls `/documents` every 3 s and flips "Processing → Ready".
5. **Ask a question.** `POST /api/matters/:id/chat { question }`. Java resolves the session, checks the Matter belongs to the caller's Firm (BR‑008, 404 not 403 on a miss), then proxies to Python's internal `/chat/:matterId` with the resolved `lawyerId`.
6. **Query is processed** (`ChatService._answer`): if the Matter has 0 `ready` Documents → HTTP 422. Otherwise fetch `document_metadata` + `all_ready_chunks`.
7. **Relevant information is retrieved.**
   - **Corpus ≤ 400 000 chars** → *full‑context path*: every chunk is sent, no ranking, no threshold. `full_context = True`.
   - **Otherwise** → *hybrid path*: regex pulls any `page/section/table/image` number → direct SQL (`exact_match_chunks`, uncapped); embed the question → `vector_search` (top 20); `keyword_search` (top 20, OR‑flipped `tsquery`, section folded in); merge with `reciprocal_rank_fusion` (`k=60`). Below `RELEVANCE_THRESHOLD` (0.01) with no exact hit → no LLM call (try metadata‑only, else the fixed `NOT_FOUND` string).
8. **Context is constructed** (`_format_context` / `_format_history`): the last 4 turns of this branch + a numbered list where each item is prefixed with its **real** verified label — `[7] (Page 12) …`, `[10] (Section: "53. Access to Justice > Mass claims …") …`, `[4] (Table 3) …` — followed by "Document metadata" items (page counts, file names).
9. **LLM generates an answer.** `gpt-4o-mini`, `temperature = 0`, with a ~1.8 KB system prompt: answer only from the numbered items; restating/organising is fine, inferring a legal conclusion is not; reproduce every amount/date/name/section‑number verbatim; a label says *where* an item is, never *what* it says; every factual sentence needs its **own** `[n]` marker.
10. **Answer is validated** (`verify_citations`, pure function): split into sentences; drop any sentence with no valid marker; if anything was dropped, run **one** corrective regeneration; if that still doesn't verify clean, keep the stripped answer plus a gap note. If nothing survives → the fixed `NOT_FOUND` string.
11. **Citations are generated.** One `Citation` row per distinct cited source: `document_id`, `page_number`, `section`, `excerpt = chunk.content[:300]`, joined `file_name`. `validate_assistant_message` (BR‑006) refuses to persist an uncited factual answer.
12. **Result is displayed.** Java relays Python's JSON unchanged. The chat panel reveals the answer with a **client‑side** typing animation (the response is a single JSON payload — there is no token stream), then renders each citation as a link to `GET /api/documents/:id/download` showing `file.pdf, p.54, 53. Access to Justice > …` and the excerpt. A `lowConfidence` or `fullContext === false` note appears when applicable.

---

# PART 1 — LINKEDIN POST 1 · PRODUCT / CINEMATIC DEMO

## 1.1 Post Strategy

- **Target audience:** the broad LinkedIn feed — recruiters, engineering managers, founders, other developers, legal‑tech people. Assume 8 seconds of attention and no patience for jargon.
- **Core message:** *"'Chat with your PDF' is a demo. A tool a lawyer would actually trust needs structure‑aware ingestion, hybrid retrieval, and citations you can click. I built that."*
- **Emotional hook:** the quiet dread of a confidently wrong answer in a context where being wrong has consequences.
- **Technical hook:** every sentence carries a citation to a real page/section, and the system refuses rather than guesses — enforced in code, not asked of the model.
- **What the video communicates:** upload → watch it process → ask a broad question → get a structured, cited answer → click a citation → land on the exact page. Then one "gotcha": ask it to pick a side, and it declines.

## 1.2 Hook Options (pick one)

1. **"A lawyer doesn't need an AI that sounds right. They need one that can show its work."**
2. **"'Chat with PDF' falls apart the moment the answer is spread across 40 pages — or the moment someone asks 'says who?'"**
3. **"I spent most of this project on the 5% that isn't the LLM call: structure‑aware ingestion, hybrid retrieval, and citation verification. Here's why."**
4. **"What happens when the honest answer is 'the documents don't say'? Most RAG apps guess. This one is built to say it."**
5. **"Every sentence this assistant writes ends with a citation you can click. If it can't cite it, it deletes it."**

## 1.3 Complete LinkedIn Caption

> **A lawyer doesn't need an AI that sounds right. They need one that can show its work.**
>
> "Chat with your PDF" is a great demo and a bad tool. It works until the answer is spread across 40 pages, or the file is a scanned exhibit, or someone reads the answer and asks the only question that matters in law: *says who?*
>
> **The problem.** Reviewing a case means reading tens to hundreds of pages across many files and being able to cite every claim precisely. A general chatbot will answer any question fluently — including the ones the documents don't actually answer — and give you no way to check it. In a legal context, a confident wrong answer isn't a cute failure. It's the failure.
>
> **Why "just ask an LLM" isn't enough.** A raw model answers from everything it has ever seen, not from *your* file. Fixed‑size text chunks throw away the structure lawyers navigate by — headings, tables, page numbers. Top‑K retrieval quietly misses content that didn't rank. And "answer only from the context" in a prompt is a request, not a guarantee.
>
> **What I built.** The Legal AI Assistant — a case workspace where you file clients and matters, upload the documents for a matter, and ask questions about *that matter only*. What comes back:
>
> • Every factual sentence ends with a citation that links to the exact file, page, and section heading — plus the quoted passage it rests on.
> • Structure‑aware ingestion: it detects headings, extracts tables row‑by‑row, and both OCRs *and* vision‑captions embedded diagrams — so "explain Table 3" and "what's on page 54" hit the right content, not a lexical coincidence.
> • Hybrid retrieval: an exact match for any named "page / section / table / image", plus semantic search, plus keyword search, merged with Reciprocal Rank Fusion.
> • It refuses rather than guesses. If the documents don't address the question, it says so — a fixed sentence, not an error. If you ask it to pick a side ("who has the stronger case?"), it declines — that judgment is the lawyer's.
>
> **The engineering angle.** Grounding here is structural, not a polite prompt. Matter isolation is a SQL predicate. Below a relevance threshold, the model is never called. After generation, every citation marker is mechanically checked against the chunks that were actually retrieved — unsupported sentences are stripped, and one corrective regeneration is attempted before the answer is allowed through.
>
> **In the video:** upload two documents → watch them process → ask for a full chronology → get a structured, fully cited answer → click a citation → land on the page. Then I ask it to take a side, and it politely won't.
>
> 🔗 GitHub: [GITHUB LINK]
>
> **Part 1/3 — Product Demo.** Part 2 breaks down the architecture behind it (three services, one database, one hard rule). Part 3 is a deep dive into the RAG pipeline.

## 1.4 Demo Storyboard (cinematic, ~60–75 s)

| # | Time | On screen | Voiceover / caption | Notes |
|---|---|---|---|---|
| 1 | 0–4 s | Black → the phrase "*says who?*" fades in, then the app's Matter Detail screen | "Legal work runs on citations." | Cold, quiet open. No logo splash. |
| 2 | 4–12 s | Drag two files (a 30‑page PDF + a DOCX) onto the upload panel; per‑file chips go **Uploading → Processing** | "Upload the documents for a matter." | Real files from `~/Downloads/Apex_Meridian_Legal_Matter_*` or the Bhopal fixtures. |
| 3 | 12–20 s | Chips flip to **Ready**; cut to the `document_chunks` count / a quick pgAdmin peek (optional) | "Behind that: structure‑aware extraction — headings, tables, diagrams — then embeddings." | Keep the DB peek < 2 s; it's flavour. |
| 4 | 20–34 s | Type: *"Give me the complete correspondence chronology."* Thinking dots. A structured, dated, cited answer streams in. | "Ask a broad question — the kind top‑K retrieval fumbles." | This is the money shot. Let the citations be visible. |
| 5 | 34–42 s | Click a citation → new tab opens the source document; scroll‑cut to the cited page | "Every claim links to the exact page and section." | If the viewer can't open the doc, screen‑record the download + a highlighted page. |
| 6 | 42–52 s | Type: *"What's on page 54?"* → answer names the real section ("Mass claims and vulnerable populations") with a `p.54` citation | "Name a page, a table, a section — it fetches that, directly." | Uses `exact_match_chunks` / the label mechanism. |
| 7 | 52–62 s | Type: *"Which side has the stronger case?"* → the fixed `OUT_OF_SCOPE` sentence appears | "Ask it to make the legal call, and it won't. By design." | The differentiator beat. Hold on the refusal text. |
| 8 | 62–72 s | Cut to the low‑confidence / large‑matter note on a different answer | "And it tells you when an answer used only the top sections, not the whole file." | Optional if time. |
| 9 | 72–75 s | Card: "Part 1/3 · Product. Part 2 → architecture. GitHub ↓" | — | End card, GitHub link. |

## 1.5 Screen Recording Checklist

- [ ] Seed a Firm with one Client and one Matter **before** recording (use the Playwright `request` API pattern, not UI clicks).
- [ ] Have the two upload files on the desktop, renamed to something neutral and readable.
- [ ] Pre‑warm the Python backend (first request loads EasyOCR + the embedding model, ~30 s + ~6.5 s). **Do not** record the cold start.
- [ ] Run Java with `MAVEN_OPTS="-Xmx384m"` and Next.js with `NODE_OPTIONS="--max-old-space-size=512"` — this machine OOMs if both run at default heap (`CLAUDE.md §4`).
- [ ] Record at 1920×1080 (or 1440×900 scaled), light theme, browser zoom 110–125 % so text is legible in‑feed.
- [ ] Turn off notifications; hide bookmarks bar; use a clean browser profile.
- [ ] Capture the citation click opening the real document (`GET /api/documents/:id/download`).
- [ ] Capture one `OUT_OF_SCOPE` refusal and one `NOT_FOUND` refusal (ask about something genuinely absent).
- [ ] Optional: one voice‑input take (mic button → dictate a question) — it's a real feature (`chat-panel.tsx`, Web Speech API).
- [ ] Keep total raw footage tight; the client‑side reveal animation finishes in ~1.5 s, so don't over‑wait.

## 1.6 Cinematic Video‑Generation Prompt

> *A clean, modern product demo of a legal AI web application, screen‑recording style, light UI with a serif‑headline / sans‑body typographic system and restrained navy‑and‑purple accents. Shot 1: a document‑upload panel; two file chips transition "Uploading → Processing → Ready" with a subtle progress shimmer. Shot 2: a chat panel; a lawyer types a broad question; three animated "thinking" dots; then a structured, well‑formatted answer with small monospace citation links appearing beneath each paragraph. Shot 3: a citation link is clicked and a document viewer opens to a specific highlighted page. Shot 4: a question is typed and the assistant returns a short, calm refusal message instead of an answer. Mood: precise, trustworthy, understated — enterprise software, not consumer flash. No stock‑photo people, no 3D globes, no glowing "AI brain" clichés. Camera is a steady screen capture with occasional slow push‑ins on the text. 60 seconds, 16:9.*

**Honesty note for whoever assembles the video:** the answer reveal in the real app is a **client‑side typing animation over a single response payload**, not live token streaming. Don't caption it as "real‑time streaming."

---

# PART 2 — LINKEDIN POST 2 · COMPLETE PROJECT & SYSTEM ARCHITECTURE

## 2.1 Post 2 Strategy & Hooks

**Objective:** show there is serious, deliberate engineering behind the product — without yet going to the deepest RAG level (that's Part 3).

**Hook options:**

1. **"The chat box is maybe 5% of this system. Here's the other 95%."**
2. **"Three services, one database, one rule that's never bent: the browser never touches the data."**
3. **"I split one backend into two languages on purpose. Java owns the boring, correct stuff. Python owns the AI. Here's why that was the right call."**
4. **"Every architectural decision in this project traces back to one constraint: a wrong answer has consequences, and it's a solo build with no budget for a wrong answer."**
5. **"Before the LLM ever runs, a legal question passes through auth, tenant isolation, structure‑aware retrieval, and a relevance gate. The model is the last step, not the first."**

## 2.2 Complete LinkedIn Caption

> **The chat box is maybe 5% of this system. Here's the other 95%.**
>
> Part 1 showed the Legal AI Assistant answering questions about a case's documents with clickable, page‑level citations. This post is the architecture underneath it.
>
> **Why it needs more than one component.** The requirements pull in different directions: multi‑tenant auth and CRUD that must simply be *correct*; an AI pipeline that needs Python's OCR/embedding/LLM ecosystem; a UI that's genuinely interactive. Rather than compromise, the system is **three services**:
>
> • **Next.js frontend** — UI only. No database driver, no API routes of its own. Every read/write is an HTTP call to a backend. This boundary is enforced, not aspirational.
> • **Java / Spring Boot backend** — authentication (self‑hosted: BCrypt for passwords, SHA‑256 for session tokens, httpOnly cookies, per‑request DB check) and all CRUD: Firm, Client, Matter, Document, Deadline, Notification, Template, Search. Tenant isolation (a firm can never see another firm's data) is a SQL predicate on every query, plus an explicit authorization call at the top of every controller method.
> • **Python / FastAPI backend** — all AI: document ingestion and the retrieval‑augmented chat pipeline. Internal only — the browser never calls it directly; Java verifies auth and matter ownership first, then proxies.
>
> All three share **one PostgreSQL database** (with `pgvector` for embeddings) whose schema is owned by neither backend — a standalone Drizzle migration tool authors it, so a schema change is one tool, not two.
>
> **Document ingestion** is structure‑aware. PDF: per‑character font metrics → heading levels; `find_tables()` with bounding‑box exclusion so table text isn't double‑counted; embedded images verified via the page's content stream, then OCR'd *and* vision‑captioned. DOCX: a true document‑order walk, heading stack from real paragraph styles, tables from real `<w:tbl>` objects, page numbers from real page‑break markers. Everything funnels into one fixed chunk shape whose boundaries never cross a page, a heading, a table, or an image.
>
> **The query pipeline** picks one of two regimes by corpus size: below ~400 K characters it sends the *entire* matter to the model (genuine completeness for "summarise everything"); above it, hybrid retrieval — exact‑identifier SQL match + vector similarity + Postgres full‑text, merged with Reciprocal Rank Fusion, then a relevance‑threshold gate. **And the answer tells the lawyer which regime produced it.**
>
> **Generation and grounding.** The model runs at temperature 0 with a citation‑required prompt. Then a mechanical, per‑sentence verification pass checks every citation marker against the chunks actually retrieved; unsupported sentences are stripped; one corrective regeneration is attempted. A write‑path invariant refuses to persist an uncited factual answer at all.
>
> **The decisions that shaped it** — the two‑language split, full‑context‑before‑ranking, no message queue yet, local embeddings, one paid API — are all downstream of two facts: a wrong answer has consequences, and this is a solo, self‑funded build. Every trade‑off is written down.
>
> 🔗 GitHub: [GITHUB LINK]
>
> **Part 2/3 — Architecture.** Part 3 goes deep on the RAG pipeline: chunking, metadata, retrieval, cross‑references, citations, and the failure modes.

*(Attach the carousel from 2.11, or the four core diagrams: `01_high_level_architecture.png`, `03_document_ingestion_architecture.png`, `04_query_processing_architecture.png`, `07_data_architecture.png`.)*

## 2.3 High‑Level System Architecture

**Diagram:** `diagrams/01_high_level_architecture.png` (1680×1140 @2×; 16:9‑ish, LinkedIn‑ready).

Derived layers (from `05-System-Architecture.md` and the code):

```
Lawyer's browser
      │  HTTPS / JSON
      ▼
Frontend — Next.js 15 (SD-001)      UI only · no DB · no /api routes · renders 16 screens
      │  javaFetch() (SC, forwards cookie)  |  fetch(credentials:'include') (client)
      ▼
Java backend — Spring Boot (SD-002/003)     auth + all CRUD ("rest of the backend")
      │  synchronous proxy, adds auth + BR-008           (chat & upload only)
      ▼
Python backend — FastAPI (SD-004/005)       ingestion  +  AI chat / retrieval / generation
      │
      ├──► PostgreSQL 16 + pgvector          schema owned by /database (Drizzle), validate-only
      ├──► /uploads (filesystem, dev) → Cloudflare R2 (prod), one interface
      ├──► OpenAI gpt-4o-mini                chat generation + embedded-diagram vision captions
      └──► local: EasyOCR, all-MiniLM-L6-v2  no API, zero per-call cost
```

Key properties to call out in the post:
- **The browser → Python edge does not exist.** SD‑003 ("Java is the sole authority on session validity") rules it out; the chat call goes browser → Java (auth + BR‑008) → Python, and Java relays the response verbatim.
- **Ingestion hand‑off is fire‑and‑forget** (Java doesn't block the upload response); **chat hand‑off is blocking** (the browser is waiting).
- **No queue yet** — a deliberate scope decision, with every failure still landing in a visible `Document.status`.

## 2.4 Document Ingestion Architecture

**Diagram:** `diagrams/03_document_ingestion_architecture.png`.

`IngestionService.ingest(document_id, storage_key, mime_type)` — three stages, every path terminal:

1. **Extraction** (`app/infrastructure/extraction.py`, branches on MIME):
   - **PDF** → `pdfplumber` for per‑character font size/name + `pypdf` for the object model. Body font size = character‑weighted mode. A line that is **bold and larger than body** is a heading candidate; distinct candidate sizes bucket into levels 1, 2, 3…. Running headers/footers = a `(position, text)` pair repeated on **> 50 % of real pages**. Tables via `find_tables()`, with table regions **excluded from the prose pass** by bounding box. Real page numbers from the PDF's own structure. Embedded images: `_truly_drawn_xobject_identities()` scans the page content stream for a `Do` operator actually invoking the image (vs. merely reachable via an inherited `/Resources` dict), so an image is attributed to **every** page that truly draws it; OCR + vision caption computed **once per unique image** (SHA‑256 content hash). Wrapped multi‑line headings at the same size are merged.
   - **DOCX** → `python-docx`. `iter_block_items()` walks the body in **true document order** (paragraphs and tables interleaved, which the flat `.paragraphs`/`.tables` lists don't give you). Heading stack from `paragraph.style.name` (`Heading N` / `Title`). Tables from real `<w:tbl>` objects → header row + `col: value` data rows, one `element_number` per table. Page numbers from explicit `<w:br w:type="page"/>` markers **if the document has any** — otherwise honest `None`. Embedded images via `r:embed` blip relationships; caption cached by content hash.
   - **Image upload** → one EasyOCR pass, `page_number = 1`, plain text path.
   - **text/plain** (generated drafts) → UTF‑8 decode.
   - **Embedded diagrams (PDF & DOCX)** → EasyOCR (character‑exact) **plus** `gpt-4o-mini` vision caption (structure/flow); `_combine_ocr_and_caption` concatenates them; a `NO_CONTENT` sentinel drops blank/decorative images.
   - Output: `list[ExtractedPage]`, each with raw `text` **or** a `list[Segment]` (`text`, `heading_path` tuple, `chunk_type ∈ {prose, table_or_list, image}`, `element_number`, `page_number`).

2. **Chunking** (`app/domain/chunk.py`, pure, zero I/O — branches on **data shape**, `page.segments is not None`, not file type):
   - Greedy sentence‑boundary packer. `CHUNK_SIZE_CHARS = 1000`, `CHUNK_OVERLAP_CHARS = 150`, `TABLE_CHUNK_SIZE_CHARS = 850`.
   - **Hard chunk boundaries** — never merged across: a page change, a heading change, a `chunk_type` change, an `element_number` change. ⇒ a chunk never spans two pages, two sections, or two tables.
   - Overlap is carried back as **whole trailing sentences**, never a raw character slice; forward progress is guaranteed even with no usable overlap.
   - Shared abbreviation‑aware sentence splitter (`Pvt.`, `Ltd.`, `Rs.`, month abbreviations, single initials) — used by both the chunker and citation verification.
   - `section` = `" > ".join(heading_path)` — the **full** breadcrumb, not just the leaf.

3. **Embed & persist** (`embedding.py` + `repository.py`):
   - `all-MiniLM-L6-v2`, 384‑dim, local. Before encoding, each text's real token count is checked against the model's 256‑token limit; a warning is logged if it would still truncate (**embedding proceeds anyway** — a degraded embedding beats none — but the failure is visible).
   - `INSERT INTO document_chunks (…, embedding, …) VALUES (…, CAST(:embedding AS vector), now())` — raw SQL, explicit `::vector` cast.
   - Terminal: no extractable text → `mark_failed("No extractable text found in this document.")`; any exception → `mark_failed(str(e)[:500])`; success → `mark_ready()`.

## 2.5 Query Processing Architecture

**Diagram:** `diagrams/04_query_processing_architecture.png`.

`ChatService.ask()` → `_answer()`:

1. `ready_document_count(matter_id) == 0` → **HTTP 422** (`NoReadyDocumentsError`) — "upload a document first", never a fabricated answer.
2. Fetch `all_ready_chunks(matter_id)` + `document_metadata(matter_id)` — both hard‑filtered to `matter_id` and `status='ready'` **in SQL** (BR‑005; a retrieval/DB error here → **HTTP 502** `AssistantUnavailableError`).
3. `total_chars = Σ len(chunk.content)`.
   - **≤ `FULL_CONTEXT_CHAR_CAP` (400 000)** → *full‑context path*: send every chunk, no ranking, no threshold gate. `full_context = True`.
   - **Otherwise** → *hybrid path*:
     - `extract_identifier_refs(question)` → any `(page|section|table|image, N)` pairs → `exact_match_chunks()` (direct SQL, **no `LIMIT`**, bypasses the relevance gate).
     - `embed([question])` → `vector_search(top_k=20)`.
     - `keyword_search(top_k=20)` — Postgres full‑text, OR‑flipped `tsquery`, `section` folded into the searchable text.
     - `reciprocal_rank_fusion(vector_ids, keyword_ids)` (`k=60`).
     - No exact hit **and** `max(fused) < RELEVANCE_THRESHOLD (0.01)` → no LLM call; try a metadata‑only answer if it's a structural question, else the fixed `NOT_FOUND` string.
     - Otherwise: `chunks = exact_chunks + top ranked to fill CONTEXT_SIZE (8)`. `low_confidence = (no exact hit) and (max(fused) < CONFIDENT_THRESHOLD (0.02))`.
4. → **Generation & citation verification** (2.6).

## 2.6 Generation + Validation Architecture

**Diagram:** `diagrams/06_generation_validation.png`.

1. **Prompt assembly** (`_format_context` / `_format_history`): `SYSTEM_PROMPT` (~1.8 KB) + `USER` = last 4 turns of this branch + numbered context (each item prefixed with its real `(Page N)` / `(Section: "…")` / `(Table N)` / `(Image N)` label) + "Document metadata" items + the question.
2. **Model call** (`OpenAIChatLLM.generate`): `gpt-4o-mini`, `temperature = 0`, one completion.
3. **Citation verification** (`verify_citations`, pure function, unit‑tested): split into sentences; for each, `valid = markers where 1 ≤ n ≤ (chunks + metadata items)`; no valid marker → **drop the sentence**; mixed valid/invalid → keep it but flag a gap note. Nothing survives → the fixed `NOT_FOUND` string. Output: kept text + first‑cited‑order `[n]` list + `all_valid`.
4. **One corrective regeneration** if `all_valid == False`: re‑prompt with "cite ONLY items 1..n, state only what they directly support"; use the retry only if it verifies clean, else keep the first (stripped) answer + gap note. **Never** left in as if verified.
5. **Persist**: `validate_assistant_message()` (BR‑006) — an assistant row with content but zero citations **cannot be constructed** unless it's the fixed `NOT_FOUND` / `OUT_OF_SCOPE` string. Then `save_assistant_message` + one `Citation` row per distinct cited source.

## 2.7 Storage / Data Architecture

**Diagram:** `diagrams/07_data_architecture.png`.

One PostgreSQL 16 schema (`database/schema/schema.ts`, Drizzle). Relevant tables:

- **`matters`** — `firm_id` (BR‑008), `client_id` (BR‑001), `status open|closed`, `active_root_message_id → chat_messages` (chat‑branching pointer).
- **`documents`** — `matter_id` (BR‑002), `status uploading|processing|ready|failed`, `is_draft`, `source_template_id`, `error_message`, `storage_key`, `mime_type`.
- **`document_chunks`** — `document_id` (`ON DELETE CASCADE`), `page_number int?`, `section text?` (breadcrumb), `chunk_type text default 'prose'`, `element_number int?`, `content text`, `embedding vector(384)`.
- **`chat_messages`** — `matter_id` (BR‑005), `lawyer_id?` (null for assistant), `role`, `content`, `pinned`, `parent_id → chat_messages` (`ON DELETE CASCADE`), `active_child_id → chat_messages` (`ON DELETE SET NULL`). The tree is reconstructed by walking `active_root_message_id → active_child_id`.
- **`citations`** — `chat_message_id` (`ON DELETE CASCADE`), `document_id` (`ON DELETE SET NULL` — a citation outlives its source file), `page_number?`, `section?`, `excerpt?`.

**Ownership split.** Java writes `firms/lawyers/sessions/clients/matters/deadlines/notifications/templates/matter_views/recent_searches/lawyer_preferences` and `documents.status`. Python writes `document_chunks/chat_messages/citations` and flips `documents.status` to `ready`/`failed`. Most parent→child FKs are **`NO ACTION`** — cascades that do need to happen (deleting a Client) are done in‑transaction in Java (`ClientService.deleteCascade`), because the DB won't do it for you.

Files live **outside** the DB — `/uploads` on disk in dev, Cloudflare R2 in production, behind one `StorageService` interface.

## 2.8 Component‑by‑Component

### Frontend (SD‑001) — Next.js
- **Responsibility:** render 16 screens; own client‑side empty/loading/error states; the chat panel (send, poll for readiness, reveal animation, citations, edit/branch/regenerate/pin, voice input, read‑aloud).
- **Input:** user actions; JSON from the Java API. **Output:** HTTP requests to Java; rendered UI.
- **Why it exists separately:** an explicit user requirement — keep all business logic and data access out of the UI tier.
- **Technology:** Next.js 15 App Router, React 19, TypeScript strict, pnpm.
- **Design decisions:** Server Components by default; `'use client'` only where a browser API is needed. `javaFetch()` forwards the session cookie server‑side (cross‑service calls don't do it automatically). The answer "stream" is a **client‑side reveal** over a single payload.
- **Failure modes:** a failed chat call → "Couldn't reach the Assistant — retry", never a fabricated answer; a failed doc load → per‑tab retry state; `middleware.ts` is only a fast redirect hint, not real protection.
- **Scalability:** stateless; the bottleneck is the backends, not this tier.

### Java backend (SD‑002 / SD‑003) — auth + CRUD
- **Responsibility:** register/login/logout/session verification; CRUD for every non‑AI entity; BR‑008 tenant isolation; the deadline scanner + notifications; template draft rendering; cross‑entity search; proxying AI calls to Python.
- **Input:** HTTP from the frontend (with the session cookie). **Output:** JSON; files (download streams directly in dev); HTTP calls to Python.
- **Why:** "the rest of the backend" — everything that must simply be correct, in a statically‑typed, boring, well‑trodden stack.
- **Technology:** Java 21, Spring Boot 4.1, Spring Data JPA/Hibernate (`ddl-auto=validate`), `spring-security-crypto` BCrypt, Jackson 3.
- **Design decisions:** `CurrentLawyerResolver.resolve(request)` is called explicitly at the top of every controller method — this is the real authorization boundary. A record outside the caller's Firm returns **404, not 403** (don't confirm it exists). Session tokens hashed with SHA‑256 (already 256‑bit random); passwords with BCrypt cost 12. Native Postgres enums map via `@JdbcTypeCode(SqlTypes.NAMED_ENUM)` with lowercase Java constants.
- **Failure modes:** unreachable Python on ingestion → Java marks the Document `failed`; Python 422/5xx on chat → translated to the same code for the browser, never a guess.
- **Scalability:** stateless behind a session‑cookie DB check; horizontal scale is trivial; the deadline scanner is idempotent (checks for an existing `Notification` before creating one).

### Python backend (SD‑004 / SD‑005) — AI
- **Responsibility:** ingestion (extract → chunk → embed → persist) and chat (retrieve → generate → verify → persist), plus chat‑message branching/pinning.
- **Input:** internal HTTP from Java (`/ingest/{id}`, `/chat/{matterId}` + edit/activate/pin). **Output:** `document_chunks` / `chat_messages` / `citations` rows; JSON responses.
- **Why:** Python's OCR/embedding/LLM ecosystem is the reason the backend was split at all.
- **Technology:** FastAPI, SQLAlchemy (raw `text()` + `::vector`), `sentence-transformers`, EasyOCR, `pypdf`/`pdfplumber`/`python-docx`, `openai`.
- **Design decisions:** Protocol‑based ports (not ABCs); domain layer is pure and branch‑on‑shape; raw SQL to control the pgvector type; every retrieval query hard‑scoped to `matter_id` + `status='ready'`.
- **Failure modes:** ingestion always ends `ready` or `failed`; a retrieval/LLM error surfaces as 502; below‑threshold questions never reach the LLM.
- **Scalability:** the embedding model and OCR reader are per‑process singletons (~30 s + ~6.5 s cold start). Ingestion is synchronous within the request — a very large / image‑heavy PDF can take minutes (a real 60‑page file with 3 diagrams took 52 s after the SHA‑256 dedup fix; before it, 5+ minutes). No queue yet is the main scaling caveat.

### PostgreSQL + pgvector
- **Responsibility:** relational data **and** the 384‑dim embeddings, in one place.
- **Design decisions:** schema authored only by Drizzle in `/database`; both backends `validate`‑only. `document_chunks.embedding` fixed at `vector(384)`. Cosine distance `<=>`. No ANN index yet (exact scan, adequate at target scale).
- **Failure modes / caveats:** a swapped Docker image can trigger a collation‑version warning (`ALTER DATABASE … REFRESH COLLATION VERSION`); `plainto_tsquery`'s AND semantics is a known bug class (fixed in the one place it mattered, audited across the repo).

### OpenAI `gpt-4o-mini`
- **Responsibility:** grounded answer generation (temp 0) **and** embedded‑diagram vision captioning.
- **Design decisions:** chosen by asking the user directly (paid API on legal data); spiked before any pipeline code. Real 128 K‑token context ceiling drove the 400 K‑char `FULL_CONTEXT_CHAR_CAP` (~34 % headroom).
- **Failure modes:** an API error → 502, never retried into a lower‑quality guess; the one corrective regeneration is a fresh identical attempt.

## 2.9 Key Engineering Decisions

For each: **Problem → Options → Decision → Why → Trade‑off.**

1. **Split the backend into two languages.**
   *Problem:* one stack can't be equally good at correct CRUD and at OCR/embeddings/LLM tooling. *Options:* all‑Node; all‑Java (weak AI ecosystem); all‑Python (heavier for CRUD/auth); Java + Python. *Decision:* Java (CRUD/auth) + Python (AI), Next.js UI‑only. *Why:* play each language to its strength; keep the AI blast radius contained. *Trade‑off:* a shared schema is now a real coupling point — a change touching both sides' entities needs both codebases updated together; two runtimes to operate.

2. **The frontend gets no database access, ever.**
   *Problem:* Next.js can technically talk to Postgres directly from Server Components. *Options:* allow it for reads; forbid it entirely. *Decision:* forbid — no DB driver, no `/api` routes in `/frontend`. *Why:* the service boundary *is* the architecture; one authorization model, in Java. *Trade‑off:* an extra network hop for "who am I" (`GET /api/auth/me`) that an in‑process call used to avoid.

3. **Schema owned by a standalone tool, not either ORM.**
   *Problem:* two backends, two migration tools = drift. *Options:* Java owns it (Flyway/Liquibase) + Python maps; Python owns it (Alembic) + Java maps; a third tool owns it. *Decision:* Drizzle Kit in `/database`, both backends `validate`‑only. *Why:* exactly one tool authors changes regardless of how many languages read the data. *Trade‑off:* a schema change is a 3‑step ritual (generate → migrate → update both entity layers) and Drizzle needed a `customType` for `vector`.

4. **Full context before ranked retrieval.**
   *Problem:* top‑8 ranked retrieval **structurally cannot** answer "give me the complete chronology" when the relevant facts are spread across dozens of pages with no keywords to match. *Options:* better ranker/reranker; larger K; map‑reduce; send everything when it fits. *Decision:* below `FULL_CONTEXT_CHAR_CAP` send the entire matter, no ranking, no threshold; fall back to hybrid+RRF only above it. *Why:* completeness is the whole point for broad questions; measured against a real 60‑page matter, chronology completeness went from 2/9 to 14/14. *Trade‑off:* whole‑document calls measured **10–15.5 s**, over the 8 s p95 target — accepted with the user's explicit sign‑off; not further optimised.

5. **Raise the cap with a real spike, and tell the lawyer which regime answered.**
   *Problem:* a live matter had already grown to 353 K chars, past the original 150 K cap, silently losing its completeness guarantee. *Options:* guess a bigger number; measure. *Decision:* three real API calls (712 K chars → real token‑limit error; ~416 K → 10.6 s; ~464 K → 37.1 s) → set 400 K with ~34 % headroom; add a `full_context` boolean threaded Python → Java → UI. *Why:* latency here is variance‑dominated, not a smooth curve — pick margin, not a curve fit. *Trade‑off:* still not unbounded; a map‑reduce architecture is deliberately deferred until a real matter needs it.

6. **Exact‑identifier retrieval as a separate, non‑ranked path.**
   *Problem:* "what's on page 54" had no guarantee its chunk was even in the top‑K for a large matter. *Options:* force full‑context for any numbered question (re‑introduces the latency cost); an LLM call to detect the reference (latency/cost/non‑determinism); fold "page 54" into the keyword index (still subject to fusion + threshold). *Decision:* a pure regex → direct SQL on the real column, **uncapped**, **bypassing the relevance gate** (a provable structural hit, not a fuzzy score). *Why:* the same reasoning that made `document_metadata` a separate non‑hallucinatable surface. *Trade‑off:* scoped to `page/section/table/image` only — clause/exhibit/annexure numbers have no storage column and are explicitly out of scope.

7. **Grounding is structural, not prompt‑only.**
   *Problem:* "answer only from the context" is a request the model can ignore. *Options:* trust the prompt; add layers. *Decision:* matter isolation as a SQL predicate; no LLM call below the relevance threshold; post‑generation per‑sentence citation verification; one corrective regeneration; a BR‑006 write‑path invariant. *Why:* in a legal product, a wrong answer that looks right is worse than an honest refusal. *Trade‑off:* the verification pass can strip a *correct* sentence that the model failed to mark, producing a visible gap note — accepted as the safe direction to fail.

8. **No message queue yet.**
   *Problem:* ingestion could fail transiently and should retry. *Options:* BullMQ + Redis now; direct HTTP now, queue later. *Decision:* direct HTTP hand‑off; Java marks `failed` if Python is unreachable, Python marks `failed` for any in‑process failure. *Why:* every failure still ends in a visible state; a durable queue is real infra to add only when failure rates justify it (Charter §5). *Trade‑off:* re‑attempting a failed ingestion currently means re‑uploading; a hung ingestion blocks that request.

9. **Local embeddings + one paid API.**
   *Problem:* embeddings and OCR could be paid APIs. *Options:* paid embeddings/OCR (simpler ops, per‑call cost); local models (heavier install, zero marginal cost). *Decision:* `all-MiniLM-L6-v2` + EasyOCR local; only the chat/vision LLM is paid. *Why:* the solo/low‑budget constraint — no per‑document cost. *Trade‑off:* 384‑dim MiniLM is not a frontier retriever; a ~30 s + ~6.5 s cold start per process; and its real 256‑token limit forced the whole chunk‑sizing rework.

10. **Adaptive extraction, one fixed chunk shape.**
    *Problem:* uploaded documents have no fixed structure (hierarchical, flat, tabular, image‑bearing, any mix). *Options:* one rigid scheme (e.g. Page→Section→Subsection); per‑format pipelines with divergent outputs; adapt the *strategy*, fix the *output*. *Decision:* extraction adapts (DOCX styles, PDF font metrics, OCR); everything funnels through one packer into one `TextChunk` shape. *Why:* downstream (embedding, search, prompt, citations) should never care where a chunk came from. *Trade‑off:* PDF heading detection is heuristic (font‑based) and can't recover logical depth a PDF's visual rendering flattened (e.g. H1 and H2 rendered at the same size).

## 2.10 Engineering Challenges (honest, from the project's own record)

For each: **Challenge → Root cause → Solution → Result → Remaining limitation.**

1. **Page numbers were never real page numbers.**
   *Root cause:* PDF extraction joined all pages into one blob before chunking; chunking sliced by raw character offset; `save_chunks` stored the chunk's *sequential index* into the `page_number` column. *Solution:* `ExtractedPage` per real page; `chunk_pages()` runs per page; `page_number` = the real page. *Result:* verified against a real 11‑page PDF — clean 1→11, no cross‑page mixing, clean word/sentence boundaries. *Remaining:* a true multi‑page **scanned** PDF (image‑in‑PDF, no text layer) is still not ingested — it surfaces as `failed`.

2. **The chunker silently truncated most of the corpus.**
   *Root cause:* `CHUNK_SIZE_CHARS = 2800` assumed ~4 chars/token; the model's real `max_seq_length` is 256 tokens and this corpus runs ~5.0–5.1 chars/token, so 45–100 % of chunks exceeded the limit and `model.encode()` silently dropped their back halves — no error, no log. *Solution:* swept candidate sizes against every real fixture with the real tokenizer → `CHUNK_SIZE_CHARS = 1000` (0/418 chunks over the limit); added a runtime token‑count warning as a backstop; `TABLE_CHUNK_SIZE_CHARS = 850` for denser table text. *Result:* zero truncation across 477 real chunks. *Remaining:* the backstop only *logs* — a rare unbreakable dense segment can still lose its tail and be written anyway.

3. **A named page/section produced confidently wrong, cited‑looking answers.**
   *Root cause:* `section`/`page_number` were stored for citations but **never shown to the model**; heading text is stripped from chunk content; so for "page 54" the model latched onto context item `[54]` (a coincidental index match) and it passed verification. *Solution:* `_label_for()` prefixes every numbered item with its real `(Page N)` / `(Section: "…")` / `(Table N)` / `(Image N)` label; the prompt explains that `[N]` is only a list position; `section` folded into the keyword index; `element_number` added for tables/images; later, exact‑identifier SQL retrieval. *Result:* "brief me page 54" returns real page‑54 content with a `p.54` citation. *Remaining:* approximate section‑name matching is disclosed but still a model judgment; clause/exhibit references aren't resolved at all.

4. **The label fix taught the model to pattern‑complete from headings.**
   *Root cause:* handing the model a rich section label ("Corporate Governance Lessons") gave it a topical cue it then filled in from — stating facts ("parent‑company accountability", "UCIL") that weren't in the retrieved chunks. *Solution:* explicit prompt rule — a label says *where*, never *what*; every fact must trace to an item's body text; plus a per‑sentence‑marker rule with a concrete right‑vs‑wrong example. *Result:* the same question now states only the section's real content, each sentence marked. *Remaining:* this is prompt mitigation of a model behaviour, not a mechanical guarantee — a milder version of cross‑section conflation still appears sometimes and is reported honestly, not claimed solved.

5. **A real PDF upload hung for 5+ minutes.**
   *Root cause:* `pypdf`'s `page.images` reported the same 3 embedded diagrams on all 60 pages (a shared/inherited `/Resources` dict) → 180 OCR passes on 3 real images. *Solution:* SHA‑256 content‑hash dedup before OCR; later, `_truly_drawn_xobject_identities()` (content‑stream `Do` check) to attribute each image to every page that genuinely draws it, OCR'd once. *Result:* 52 s on the same file; correct per‑page attribution (9/4/3 real pages for the 3 images) at no extra OCR cost. *Remaining:* image→page attribution depends on `pypdf` correctly modelling the content stream; exotic PDFs are untested.

6. **Broad questions were wrongly refused; then structured‑template answers came back with zero citations.**
   *Root cause:* the model over‑applied "no unsupported synthesis" to *any* multi‑chunk synthesis; and a clean section‑header template read as a "fill in the values" exercise with the citation requirement stated too far away. *Solution:* the prompt now explicitly separates "restating/organising" (always allowed) from "stating an unstated conclusion" (never); the citation requirement is repeated *at* the template definition. *Result:* matter‑overview and full‑assessment questions return structured, fully‑cited answers. *Remaining:* structured‑output prompting remains brittle to model updates — regression‑tested by hand, not by an eval harness.

7. **Keyword search silently matched nothing for natural phrasing.**
   *Root cause:* `plainto_tsquery` ANDs every significant word; "how **long** is the lease term" against "the term is 36 months" shares no word → zero rows, silently zeroing keyword search's contribution. *Solution:* reuse `plainto_tsquery`'s stemming/stopwords but flip `&` → `|`; `ts_rank` still favours chunks matching more words. *Result:* hybrid retrieval stopped degrading to vector‑only; added a real‑Postgres regression test (spike‑validated against a reverted AND‑only version). *Remaining:* the OR flip trades some precision for recall; deliberately *not* applied to Java's name/title search, where every typed word *should* match.

## 2.11 Post 2 Carousel (10 slides)

| # | Title | Exact on‑slide text | Image | Speaker note |
|---|---|---|---|---|
| 1 | **Inside the Legal AI Assistant** | "The chat box is ~5% of the system. Here's the other 95%. — 3 services · 1 database · 1 rule that's never bent." | `01_high_level_architecture.png` (cropped to top) | Set expectation: this is the architecture post, not the RAG deep dive. |
| 2 | **Three services, one database, one hard rule** | "Frontend (UI only, no DB) → Java (auth + CRUD) → Python (all AI). One Postgres, schema owned by neither backend. The browser never touches the data." | `01_high_level_architecture.png` | Explain *why* the split: right tool per job, contained AI blast radius. |
| 3 | **Document ingestion is structure‑aware** | "PDF: font metrics → headings · `find_tables()` · content‑stream image check. DOCX: real styles, real `<w:tbl>`, real page‑break markers. Diagrams: OCR **+** vision caption." | `03_document_ingestion_architecture.png` | The differentiator vs. "split into 1000‑char chunks". |
| 4 | **One fixed chunk shape** | "Adaptive strategy, fixed output. A chunk never crosses a page, a heading, a table, or an image. So a citation always points at exactly one real location." | `08_chunking_architecture.png` | Bridge into Part 3. |
| 5 | **Query processing: two regimes** | "≤ 400K chars → send the whole matter (real completeness). Otherwise → hybrid retrieval + RRF + threshold gate. And the answer tells the lawyer which one it used." | `04_query_processing_architecture.png` | The full‑context decision + the transparency signal. |
| 6 | **The pipeline, not an agent** | "No LangGraph, no agent loop. A deterministic function: one data‑driven branch, one bounded corrective regeneration. Predictable is the feature." | `04_query_processing_architecture.png` (bottom) | Pre‑empt "where's the agent framework". |
| 7 | **Evidence & citations** | "One `Citation` row per source: file + page + section breadcrumb + the quoted excerpt. `ON DELETE SET NULL` — a citation outlives its source file." | `09_citation_architecture.png` | Provenance as a first‑class table, not a page guess. |
| 8 | **Grounding is structural** | "SQL matter‑scope · no LLM call below threshold · temperature 0 · per‑sentence citation check · one corrective retry · a write‑path invariant. Not 'answer from context' in a prompt." | `06_generation_validation.png` | The core credibility slide. |
| 9 | **Ten decisions, every trade‑off written down** | "Two languages · full‑context‑before‑ranking · no queue yet · local embeddings · one paid API · adaptive extraction. Each one has a Problem → Options → Decision → Trade‑off entry." | plain text slide | Signals engineering maturity to hiring managers. |
| 10 | **Part 3: the RAG deep dive** | "Chunking · metadata · embeddings · retrieval · cross‑references · citations · failure modes. Next post. GitHub ↓" | `05_retrieval_architecture.png` (teaser) | CTA + series continuity. |

---

# PART 3 — LINKEDIN POST 3 · DEEP DIVE INTO THE RAG ARCHITECTURE

## 3.1 Strong Technical Hooks

1. **"Top‑K retrieval can't answer 'give me the complete chronology' when the chronology is spread across 40 pages. So for most matters, this system doesn't rank at all."**
2. **"A lawyer asks 'what's on page 54'. Vector search has no idea what page 54 is. Here's the retrieval path that does."**
3. **"'Answer only from the context' is a prompt. This is what it takes to make it a guarantee: a SQL predicate, a threshold gate, and a per‑sentence verification pass."**
4. **"The bug that mattered most in this project wasn't in the LLM call. It was that 45–100% of chunks were being silently truncated before they were ever embedded."**
5. **"Naive RAG for legal documents throws away the three things lawyers navigate by: headings, tables, and page numbers. Here's how we kept them."**

## 3.2 Why Naive RAG Isn't Enough

**The generic pipeline:**

```
Document → fixed-size chunks → embeddings → vector search → top-K → LLM
```

**Where it breaks for legal documents:**
- **Structure is discarded.** A contract is `Document → Part → Section → Sub‑section → Clause`. A flat character window doesn't know a chunk is inside "§15 Indemnity" or on page 9 — so it can't answer "what does the indemnity clause say" or "what's on page 54", and a citation is a guess.
- **Tables become word soup.** `185,000 | 2024‑03‑11 | INV‑4471` with the column headers three rows up loses all meaning once flattened.
- **Broad questions fall through top‑K.** "Create a complete chronology" has no keywords to match the actual dated entries; ranked top‑8 surfaces 2 of 9. The relevant facts existing in the corpus doesn't help if retrieval never selects them together.
- **Exact tokens get blurred.** Semantic similarity smooths over the difference between "§54" and "§45", between "Apex Meridian" and "Apex Components". Legal text lives on those exact tokens.
- **Citations are an afterthought.** Without a location threaded from ingestion to the answer, "[Document 1, p.4]" is generated text, not verified provenance.
- **"Answer from context" is unenforced.** Nothing stops the model reaching for parametric knowledge when the context is thin.

**What this project implements instead** (distinguish clearly from the generic sketch above):
- Structure‑aware extraction → `section` breadcrumb, `chunk_type`, `element_number`, real `page_number` as **queryable columns**.
- Full‑context for matters that fit (~400 K chars) → no ranking, no top‑K to fall through.
- Hybrid retrieval above the cap → **exact‑identifier SQL match** (uncapped, gate‑bypassing) + vector + keyword, fused with RRF.
- Provenance threaded end‑to‑end → one `Citation` row per source with `page_number`, `section`, `excerpt`.
- Grounding as code → SQL matter‑scope, no‑call‑below‑threshold, per‑sentence citation verification, one corrective regeneration, a write‑path invariant.

## 3.3 Actual Document Processing Pipeline

**Diagram:** `diagrams/03_document_ingestion_architecture.png`.

*(Full detail in 2.4. Summary of the real steps, in order.)*

1. **File handling** — Java stores the upload; Python fetches the bytes from shared storage in the `/ingest/{id}` handler.
2. **MIME branch** — `application/pdf` / DOCX / `image/*` / `text/plain`; anything else → `ValueError` → `failed`.
3. **PDF text extraction** — `pdfplumber.extract_words(extra_attrs=["size","fontname"])`, grouped into visual lines by rounded vertical position.
4. **PDF structure detection** — body font size = character‑weighted mode; heading = bold ∧ size > body, bucketed into levels; running header/footer filter (> 50 % of real pages); consecutive same‑size heading lines merged.
5. **PDF tables** — `page.find_tables()`; table regions removed from the text pass via `page.outside_bbox(bbox)`; rows → `col: value` segments; one `element_number` per table.
6. **PDF images** — `_truly_drawn_xobject_identities()` (content‑stream `Do` operator vs. inherited `/Resources`); per unique image (SHA‑256): EasyOCR text + `gpt-4o-mini` vision caption, `_combine_ocr_and_caption`; attributed to every true drawing page; `NO_CONTENT` → dropped.
7. **DOCX extraction** — `iter_block_items()` true‑order walk; heading stack from `paragraph.style`; `<w:tbl>` → row segments; `<w:br w:type="page"/>` page counter (only if any exist); embedded images via blip relationships, cached by hash.
8. **Paragraph / sentence segmentation** — `_segments_for()`: paragraph split on blank lines where present, else the abbreviation‑aware sentence splitter, else the whole paragraph.
9. **Chunking** — `chunk_pages()` → `_pack_typed_segments` (adaptive) or `_pack_segments` (plain); greedy fill to 1000 / 850 chars; hard boundaries; whole‑sentence overlap.
10. **Metadata assembly** — per chunk: `page_number`, `section` (`" > ".join(heading_path)`), `chunk_type`, `element_number`.
11. **Embedding** — `all-MiniLM-L6-v2`, batch `encode()`, 384‑dim; token‑count warning backstop.
12. **Vector storage** — raw `INSERT` with `CAST(:embedding AS vector)`; `mark_ready()` / `mark_failed()`.

## 3.4 Hierarchical Document Representation

**Diagram:** `diagrams/08_chunking_architecture.png` (bottom panel shows the fixed output).

The hierarchy is **captured** but stored **flattened onto each chunk**, not as a separate tree:

```
Document
 └─ Heading level 1        e.g. "53. Access to Justice"
     └─ Heading level 2    e.g. "Mass claims and vulnerable populations"
         └─ Heading level 3
             └─ Segment (prose sentence | table row | image caption)
                 └─ TextChunk   section = "53. Access to Justice > Mass claims and vulnerable populations"
```

- **Why it exists:** a lawyer says "the access‑to‑justice section" meaning the level‑1 heading, or "mass claims" meaning the child — matching against **any part of the breadcrumb** is what makes both work. Keeping only the leaf (an earlier version did) silently discarded the level the lawyer actually meant.
- **How metadata is preserved:** `Segment.heading_path` carries the full ancestor tuple through extraction; `chunk.py` joins it with `" > "` into the `section` column; it flows unchanged into `ChunkResult`, the numbered prompt label, and the `Citation` row.
- **How retrieval benefits:** `keyword_search` searches `coalesce(section,'') || ' ' || content`, so a heading's own words (which never appear in its body prose) are findable; `exact_match_chunks` anchors a section *number* with `dc.section ~ '(^|> )N\.'` so "§53" matches "53. …" at the start or after a `> `, without false‑matching "530." or "5.3".
- **How citations benefit:** the citation footer shows `file.pdf, p.54, 53. Access to Justice > Mass claims …` — a lawyer can navigate straight there.
- **Honest limit for PDF:** when a DOCX's H1/H2 are exported to a PDF at the *same* font size, that two‑level distinction is genuinely gone — the detector recovers the hierarchy the PDF *visually expresses*, not the one the source logically had.

## 3.5 Chunking Strategy

**Diagram:** `diagrams/08_chunking_architecture.png`.

- **Chunk size:** `CHUNK_SIZE_CHARS = 1000` for prose, `TABLE_CHUNK_SIZE_CHARS = 850` for `table_or_list`. **Overlap:** `CHUNK_OVERLAP_CHARS = 150` (~14 %), carried as **whole trailing sentences**.
- **Splitting strategy:** paragraph breaks first where the source preserves them (DOCX double‑newlines), then the shared abbreviation‑aware sentence splitter, then a word‑boundary hard split only for a single segment longer than the whole budget (a long run‑on table row).
- **Paragraph‑level handling:** `_segments_for()` collapses intra‑paragraph newlines to spaces, splits into sentences, falls back to the whole paragraph when there's no sentence punctuation at all.
- **Section awareness:** in the adaptive packer, segments are grouped into runs sharing **all** of `(heading_path, chunk_type, element_number, page_number)`; a change in any is a hard boundary. Two tables back‑to‑back under one heading can never blend into one mislabelled "Table 3".
- **Why these numbers (measured, not assumed):**
  - `all-MiniLM-L6-v2` real `max_seq_length` = **256 tokens** (loaded and checked, not guessed).
  - This corpus's legal text = **~5.0–5.1 chars/token** (number/citation/currency‑heavy → less token‑efficient than prose), measured with the real tokenizer across every `Apex_Meridian_*` fixture (130+ chunks).
  - `1000` is the largest sweep value (1400 → 800 tested) that produced **0 / 418** real chunks over the 256‑token limit (max observed 216, ~15 % margin).
  - Table rows measure ~3.8–4 chars/token → the tighter 850 budget (one table chunk hit 264 tokens at 994 chars before this).
- **Evolution:** `2800/400` raw char slice with mid‑word cuts and a fake `page_number` → per‑page sentence‑boundary chunking with real page numbers → `1000/150` after the token‑limit measurement → DOCX‑adaptive `Segment` packer → PDF‑adaptive via `pdfplumber` → real page numbers from `<w:br>` markers → `section` as full breadcrumb. (Full timeline: `RAG-Pipeline-Development-History.md`.)
- **Fixed output:** `TextChunk(content, index, page_number: int | None, metadata: {section, chunk_type, element_number})` — every downstream stage consumes this one shape.

## 3.6 Metadata Architecture

**Diagram:** `diagrams/09_citation_architecture.png` (source‑chunk box).

Actual columns on `document_chunks` (`database/schema/schema.ts`) and their use:

| Metadata field | Purpose | Used during retrieval? | Used for citation? |
|---|---|---|---|
| `page_number` (int, nullable) | The real 1‑indexed page (PDF/image; DOCX only when `<w:br w:type="page"/>` markers exist) | **Yes** — `exact_match_chunks` (`dc.page_number = :n`); also the `(Page N)` prompt label | **Yes** — `Citation.page_number`, shown as `p.54` |
| `section` (text, nullable) | Full heading breadcrumb, e.g. `"53. Access to Justice > Mass claims …"` | **Yes** — folded into `keyword_search`'s `tsvector`; `exact_match_chunks` section‑number anchor; `(Section: "…")` prompt label | **Yes** — `Citation.section` |
| `chunk_type` (text, `default 'prose'`) | `prose` \| `table_or_list` \| `image` — which segmentation produced the chunk | **Yes** — `exact_match_chunks` disambiguates Table N vs. Image N; drives the label ("Table 3" vs "Image 2") | Indirectly (via the label the excerpt is presented under) |
| `element_number` (int, nullable) | The Nth table / Nth image, document‑wide, 1‑indexed (counted only among tables/images that produced content) | **Yes** — `exact_match_chunks` (`element_number = :n AND chunk_type = …`) | Indirectly |
| `content` (text) | The chunk text itself | **Yes** — `vector_search` embeds it; `keyword_search` matches it | **Yes** — `excerpt = content[:300]` |
| `embedding` (`vector(384)`) | Semantic vector | **Yes** — `vector_search` (`<=>` cosine) | No |
| `document_id` (FK, `ON DELETE CASCADE`) | Owning document | **Yes** — the `matter_id`/`status` join goes through it | **Yes** — `Citation.document_id` (`ON DELETE SET NULL`) + joined `file_name` |

**Document‑level metadata** (`DocumentMetadata`, computed, not stored): `file_name`, `page_count = max(document_chunks.page_number)` per `ready` Document (`NULL` for DOCX with no page markers). Offered to the LLM as trailing numbered "Document metadata" items and citeable with a Python‑computed excerpt ("`file.pdf` has 11 pages.") — a **non‑hallucinatable surface**: it can answer "how many documents / pages" even when zero content chunks clear the relevance threshold.

**Why each matters:** `page_number` + `section` are the two things a lawyer navigates by, so they must be both *retrievable* and *citeable*. `chunk_type` + `element_number` exist because "Table 3" and "Image 2" are how lawyers refer to non‑prose content, and without them "explain table 3" is a lexical accident.

## 3.7 Embedding Pipeline

- **What is embedded:** the chunk `content` string (for a table chunk, the `col: value; …` row text; for an image chunk, the combined OCR + vision‑caption text). The `section` heading is **not** part of the embedded string (it's folded into keyword search instead).
- **Model:** `all-MiniLM-L6-v2` via `sentence-transformers` 5.7 (`app/infrastructure/embedding.py`).
- **Why:** runs fully locally, no API key, no per‑call cost — the low‑budget constraint. ~53 ms/chunk after a ~6.5 s one‑time model load. Retrieval‑quality tuning was deliberately deferred to "when there's an LLM in the loop to validate against."
- **How generated:** `_get_model().encode(texts)` on the full list of chunk strings (batched by the library), each vector `.tolist()`‑ed. The query is embedded the same way at chat time: `self.embedder.embed([question])[0]`.
- **Batch processing:** ingestion embeds all of a document's chunks in one `encode()` call (`[c.content for c in chunks]`).
- **Vector dimensions:** **384**, verified in three places — the model, `SentenceTransformerEmbedder`'s docstring, and `database/schema/schema.ts`'s `vector(384)` `customType`.
- **Storage:** `INSERT INTO document_chunks (… embedding …) VALUES (…, CAST(:embedding AS vector), now())`, the vector serialised as `"[f1,f2,…,f384]"`.
- **Safety net:** before `encode()`, each text's real token count (`model.tokenizer.encode(text, add_special_tokens=True)`) is compared to `model.max_seq_length` (256); over‑limit → a `WARNING` log with a text preview. Embedding still proceeds — "a degraded embedding beats no embedding" — but the truncation is no longer silent.

## 3.8 Retrieval Architecture

**Diagram:** `diagrams/05_retrieval_architecture.png`.

Reached **only** when `total_chars > FULL_CONTEXT_CHAR_CAP` (otherwise every chunk is sent and none of this runs). Every query below is hard‑scoped to `d.matter_id = :m AND d.status = 'ready'` in SQL (BR‑005 / Grounding Rule 1).

**1. Exact‑identifier match** (`identifier_query.py` + `chat_repository.py::exact_match_chunks`)
- Regex over `page|pg|section|sec|table|tbl|image|img|figure|fig`, optional `no.` / `#`, then digits → deduplicated `(kind, N)` pairs. Zero false positives on "470 million dollars" or "what happened in 1991" (spike‑verified).
- One SQL branch per ref, `UNION`‑ed:
  - `page` → `dc.page_number = :n`
  - `table` → `dc.element_number = :n AND dc.chunk_type = 'table_or_list'`
  - `image` → `dc.element_number = :n AND dc.chunk_type = 'image'`
  - `section` → `dc.section ~ ('(^|> )' || :n || '\.')` (breadcrumb‑anchored so "1" doesn't match "10.")
- **No `LIMIT`. No ranking. Bypasses the relevance‑threshold refusal.** A page's own chunk count is small and bounded; capping it would re‑introduce the incompleteness this exists to fix. Treated like `document_metadata` — a provable structural hit, never "low confidence".

**2. Vector similarity** (`vector_search`)
- `embed([question])[0]` with the **same** model used at ingestion.
- `ORDER BY dc.embedding <=> CAST(:q AS vector) LIMIT 20` (pgvector cosine distance, `CANDIDATE_POOL_SIZE = 20`).
- Catches paraphrase / conceptual matches.

**3. Keyword / full‑text** (`keyword_search`)
- `searchable = to_tsvector('english', coalesce(dc.section,'') || ' ' || dc.content)` — section folded in so heading words are matchable.
- `q = to_tsquery('english', replace(plainto_tsquery('english', :query)::text, ' & ', ' | '))` — reuse Postgres's stemming/stopword handling but **OR** the terms so one word absent from the source doesn't zero the match.
- `WHERE searchable @@ q ORDER BY ts_rank(searchable, q) DESC LIMIT 20`.

**4. Fusion** (`retrieval.py::reciprocal_rank_fusion`, `k = 60`)
- `fused[id] = Σ 1 / (60 + rank)` across the vector list and the keyword list (1‑indexed rank). A chunk both methods rank highly outscores one only one liked. Pure function, unit‑tested. No hand‑tuned blend weight between two different score scales.

**5. Threshold gate & assembly**
- No exact hit **and** `max(fused) < RELEVANCE_THRESHOLD (0.01)` → **no LLM call**: try a metadata‑only answer if metadata exists, else persist the fixed `NOT_FOUND` string.
- Otherwise: `chunks = exact_chunks (uncapped) + top of the fused ranking to fill CONTEXT_SIZE (8)`; then every `ready` Document's metadata row is appended.
- `low_confidence = (no exact hit) AND (max(fused) < CONFIDENT_THRESHOLD (0.02))` → the answer is still returned, with a UI note.

**Reranking:** **not implemented.** A cross‑encoder rerank is noted as a possible future step, deferred because picking a reranker is itself a vendor decision with the same risk profile as the embedding‑model choice, and hybrid+RRF hasn't been shown insufficient in practice.

**Conversation context:** the last `RECENT_TURNS = 4` messages of the **current branch** (`history_before(user_message_id, limit=4)`, walking `parent_id` backward — not "last 4 rows for the matter", which could pull a superseded branch) go into the prompt so follow‑ups resolve. Retrieval itself always runs on the **current question only**.

## 3.9 Query → Retrieval → Context Flow

**Diagram:** `diagrams/04_query_processing_architecture.png` + `diagrams/05_retrieval_architecture.png`.

```
User question (current turn)
      │
      ▼
ready_document_count == 0 ?  ──yes──► HTTP 422 (never a guess)
      │ no
      ▼
fetch all_ready_chunks + document_metadata   (SQL: matter_id + status='ready')
      │
      ▼
Σ chunk chars ≤ 400,000 ?
   ├─ yes → FULL CONTEXT: every chunk, no ranking, no gate            full_context = True
   └─ no  → HYBRID:
             exact_match_chunks(refs)  (uncapped, gate-bypassing)
             vector_search(top 20)  ┐
             keyword_search(top 20) ┘→ Reciprocal Rank Fusion (k=60)
             max fused < 0.01 & no exact hit → metadata-only OR fixed NOT_FOUND (no LLM call)
             else → exact + top-ranked to fill CONTEXT_SIZE=8
             low_confidence = no-exact-hit AND max fused < 0.02
      │
      ▼
Assemble numbered context:  [i] (label) content …  + "Document metadata" items
      │
      ▼
prepend last 4 branch turns  →  Context: … Question: …
      │
      ▼
gpt-4o-mini (temp 0)  →  verify_citations  →  [1 corrective regen]  →  persist ChatMessage + Citations
```

## 3.10 Cross‑Reference Resolution

**Status: NOT implemented as follow‑the‑pointer retrieval.** This is stated plainly because the prompt describes the requirements' scope but the retrieval layer does not do it.

- `identifier_query.py`'s docstring: *"Scope deliberately limited to page/section/table/image — the only identifiers `document_chunks` actually stores as queryable columns today. Clause/exhibit/annexure references have no column to exact‑match against yet."*
- RAG history Phase 5: *"Deliberately out of scope (confirmed with the user before building): clause/paragraph/exhibit/annexure references… adding regex recognition now would be dead code."*

**What *does* exist that's adjacent:**
- **Breadcrumb matching:** a question about either the parent heading ("53. Access to Justice") or the child ("Mass claims and vulnerable populations") matches the same `section` string — the prompt instructs the model to match against *any part* of the breadcrumb.
- **Disclosed approximate section‑name matching:** for a section named *by name* (not by number), if no heading is an exact match but one is clearly the closest on topic, the model may explain that one — **but only while saying so plainly and naming the real heading it used**. For a section named *by number* the rule stays strict exact‑or‑refuse (relaxing it would reopen the citation‑index‑guessing bug).

**Why it matters for legal documents:** contracts are full of "subject to Section 8.2", "as defined in Schedule 3", "the Indemnified Parties (Clause 11)". Full resolution would need a clause‑level identifier column populated at ingestion. Flagged as a real future improvement, not a claimed feature.

## 3.11 Citation Architecture

**Diagram:** `diagrams/09_citation_architecture.png`.

The chain, from answer text to a stored row:

```
Answer sentence   "The 1989 settlement required US$470 million [7]."
      │
Marker [7]        position in THIS prompt's numbered list — NOT a page/section number
      │
Retrieved item #7 the chunk (or metadata row) actually offered to the model this call
      │
Source chunk      document_chunks row: content, page_number, section, chunk_type, element_number
      │
Document          documents row: file_name, storage_key
      ▼
Citation row      chat_message_id · document_id (SET NULL on delete) · page_number · section
                  · excerpt = chunk.content[:300]   (+ joined file_name)
```

- **`verify_citations`** produces `cited_chunk_numbers` (1‑indexed, first‑cited order, deduplicated). `_citation_for(n)` maps each to `(document_id, page_number, content[:300], file_name, section)`; if `n` is a metadata item, the excerpt is the Python‑computed fact string and `page_number` is `None`.
- **Rules for the set** (`06-AI-Architecture.md §4`): multi‑fact answers from different locations get **multiple** rows (never one blanket citation); a `NOT_FOUND`/`OUT_OF_SCOPE` answer gets **zero**; `validate_assistant_message` (BR‑006) makes an uncited factual answer unconstructible.
- **Permanence:** citations are persisted with the message and **never recomputed**. `Citation.document_id` is `ON DELETE SET NULL` — deleting a cited Document doesn't break the delete and doesn't erase the excerpt/page; it just loses the link (`citations_for` uses a `LEFT JOIN`).
- **UI:** `chat-panel.tsx` renders each citation as a link to `GET /api/documents/:id/download` showing `fileName, p.{pageNumber}, {section}` and the excerpt in quotes; a citation whose `documentId` is null renders as `"{fileName} (deleted)"`.
- **Example (from the project's own live verification):** *"The 1989 settlement required US$470 million [107]. The settlement was judicially reviewed by the Supreme Court of India in 1991 … [107]."* — each sentence individually marked, both tracing to the same real chunk on page 17 / the settlement‑amount row.

## 3.12 Generation Architecture

- **Prompt construction** (`_format_context`, `_format_history`, `SYSTEM_PROMPT`):
  - `SYSTEM_PROMPT` (~1.8 KB) — the load‑bearing instructions: answer **only** from the numbered items, never outside knowledge; restating/organising is expected and fine, inferring a legal conclusion/prediction/liability call is not; reproduce every monetary amount, date, percentage, statute/section number, party/company name **verbatim** (`"US$470 million"`, not "a substantial settlement"); a section/page/table/image label tells you **where** an item is, never **what** it says; cover **every** context item under the thing asked about, not a subset; **every** factual sentence needs its **own** `[n]` marker (checked mechanically, sentence by sentence) — with a concrete right‑vs‑wrong example; `[N]` is a list position, never a real page/section number — match a lawyer's stated number only against a real parenthetical label; use the fixed `NOT_FOUND` string only when the topic is genuinely absent; use `OUT_OF_SCOPE` when the question asks for a strategic/adversarial judgment.
  - Two recognised broad‑question archetypes get a structured header format (matter overview → Client / Opposing Party / Forum; complete assessment → Matter / Client / Matter Type / Current Stage / Summary / Key Issues / Strong Evidence) — with the per‑sentence citation rule **restated at the template definition** (a real regression happened when it wasn't).
  - `USER` prompt = `_format_history(recent)` + `"Context:\n" + _format_context(chunks, metadata) + "\n\nQuestion: " + question`.
- **Retrieved context:** each item `[i] (label) content`; metadata items appended under a "Document metadata" header.
- **LLM invocation:** `OpenAIChatLLM.generate(system_prompt, user_prompt)` → `client.chat.completions.create(model="gpt-4o-mini", temperature=0, messages=[system, user])` → `response.choices[0].message.content or ""`.
- **Output handling:** straight to `verify_citations` (3.13). No secrets in the prompt or logs; `OPENAI_API_KEY` is env‑only with no default.

## 3.13 Validation Architecture

**Diagram:** `diagrams/06_generation_validation.png`.

```
retrieved evidence → LLM generation → verify_citations → [corrective regen ×1] → BR-006 write gate → persist
```

**What is actually validated** (`domain/citation_verification.py::verify_citations`, pure function, unit‑tested):
- The answer is split into sentences (the shared abbreviation‑aware splitter, whitespace preserved so markdown structure survives reassembly).
- For each sentence: `markers = every [n]`; `valid = markers where 1 ≤ n ≤ (chunks + metadata items offered this call)`.
- **No valid marker** → the sentence is **dropped** (Grounding Rule 4). **Some valid + some invalid** → kept, but the whole answer gets a gap note.
- Nothing survives → the fixed `NOT_FOUND_RESPONSE`. `all_valid = (nothing was dropped)`.
- If `all_valid == False`: **one** corrective regeneration ("cite ONLY items 1..n, state only what those items directly support"); the retry is used only if it verifies clean, else the first stripped answer + gap note is kept — **never** left in as if verified.
- `validate_assistant_message()` (BR‑006) then refuses to persist an assistant row that has content but no citations, unless it's the fixed `NOT_FOUND` / `OUT_OF_SCOPE` string.

**What is *not* done — stated explicitly so the post doesn't overclaim:**
- There is **no independent fact‑checking model**, no NLI/entailment check that the *claim* matches the *cited text* — only that a marker exists and resolves to a retrieved item.
- There is **no external truth source**.
- The verification can strip a **correct** sentence the model simply failed to mark (this happened during development and is the reason for the explicit per‑sentence rule + example) — the system is built to fail toward "visible gap", not "silent claim".
- A prompt instruction is not equivalent to a mechanical guarantee — cross‑section conflation is *mitigated by prompt*, reported as an ongoing model‑precision limitation, not claimed solved.

## 3.14 Context Window / Large‑Corpus Handling

**Diagram:** `diagrams/10_context_window_management.png`.

| Corpus size (Σ `ready`‑chunk chars for the Matter) | Regime | Guarantee | Signal to lawyer |
|---|---|---|---|
| **≤ 400 000** (`FULL_CONTEXT_CHAR_CAP`) | Full‑context: every chunk sent, no ranking, no threshold gate | Genuine completeness for "summarise everything" | `full_context = True` |
| **> 400 000** | Hybrid retrieval + RRF + `CONTEXT_SIZE = 8`, with exact‑identifier chunks added uncapped | Best‑effort; a named page/table/section still can't be missed; below `RELEVANCE_THRESHOLD` → no LLM call | `full_context = False` → UI note: *"This Matter is large — this answer used the most relevant sections rather than the entire document. For a guaranteed complete answer, ask about a specific page, section, table, or image."* |

- **Small documents / typical matters:** below the cap — the common case. Whole‑document calls measured **10–15.5 s** (over the 8 s p95 target); narrow single‑fact questions on the same matter **2–7 s**. The below‑threshold no‑LLM guarantee does **not** apply here — the model always sees the corpus, and citation verification is the backstop.
- **How the cap was set (real spike, not assumed):** a 712 694‑char prompt failed with the API's own error (`max context 128000 tokens … resulted in 142,948 tokens` → real ~4.99 chars/token for this corpus); a ~416 K‑char prompt succeeded in 10.6 s; a ~464 K‑char prompt succeeded in 37.1 s — latency here is **variance‑dominated, not a clean function of size**, so 400 K was chosen for ~34 % headroom under the hard token ceiling rather than by fitting a latency curve. It comfortably covers the real 353 336‑char matter that motivated raising it from the original 150 K.
- **Deliberately not built:** a map‑reduce / chunked‑multi‑call architecture (the only way to get true completeness at *any* scale). No real matter in the database needs it — even the largest fits one call — so it's logged as a deferred option, revisited only if a real matter exceeds 400 K.

## 3.15 Failure Modes & Limitations

For each: **Failure → Cause → Current mitigation → Remaining risk.**

1. **Scanned (image‑only) PDF not ingested.** *Cause:* `pdfplumber` finds no text layer; only standalone `image/*` uploads go through OCR. *Mitigation:* the Document resolves to `failed` with a visible message, not a silent nothing. *Remaining risk:* a lawyer must know to export/OCR such a PDF elsewhere first; a common real‑world file type is unsupported.
2. **Retrieval miss on a large matter.** *Cause:* above the 400 K cap, a broad question with no keywords may not rank the right chunks; only the top 8 fused go to the model. *Mitigation:* full‑context below the cap (most matters); exact‑identifier bypass for named locations; the `full_context = False` UI note. *Remaining risk:* "list every clause" on a >400 K matter is best‑effort, and the lawyer is told so but not shown what was omitted.
3. **Correct sentence stripped by verification.** *Cause:* the model writes a multi‑sentence cluster and marks only the last sentence. *Mitigation:* explicit per‑sentence rule + example in the prompt; one corrective regeneration; a gap note when anything is dropped. *Remaining risk:* an answer can come back thinner than the evidence supported, with a gap note but no recovery of the dropped fact if the retry also fails.
4. **Cross‑section conflation.** *Cause:* the model generalises a fact stated about one specific ledger/claim to a related one. *Mitigation:* explicit prompt instruction against it. *Remaining risk:* only *partially* effective — a milder version still appears; reported honestly, not claimed fixed. Not mechanically detectable.
5. **Pattern‑completion from a heading label.** *Cause:* a descriptive `section` label is a strong topical cue the model may fill in from. *Mitigation:* "a label says where, never what" prompt rule; per‑sentence marker verification catches the *unmarked* fabrications. *Remaining risk:* a fabricated sentence that *is* marked with a valid (but wrong‑for‑the‑claim) chunk number passes verification — the check is marker‑resolves, not claim‑entails.
6. **OCR / vision caption errors.** *Cause:* EasyOCR misreads; the vision model paraphrases or errs. *Mitigation:* OCR (character‑exact) and caption (structure) are combined, not either alone; `NO_CONTENT` drops blanks. *Remaining risk:* an OCR digit error in a figure inside a diagram is not caught; the "recovers a genuinely textless‑but‑meaningful diagram" case is unverified for lack of a real fixture.
7. **Table extraction imperfect.** *Cause:* `pdfplumber`'s ruling‑line/whitespace table detection; merged/nested cells. *Mitigation:* row → `col: value` so context isn't lost; table region excluded from the prose pass. *Remaining risk:* an unruled or irregular table can be mis‑segmented; not separately validated per document.
8. **Cross‑reference not followed.** *Cause:* no clause‑level identifier column; deliberate scope limit. *Mitigation:* breadcrumb + disclosed approximate section‑name matching. *Remaining risk:* "what does the section referenced in Clause 11 say" is not resolved.
9. **Embedding truncation (rare).** *Cause:* a single unbreakable dense segment over 256 tokens. *Mitigation:* conservative chunk sizing (0/418 in fixtures) + a runtime warning log. *Remaining risk:* the backstop only logs; such a chunk is still written with a half‑embedding.
10. **Latency over target for broad questions.** *Cause:* whole‑document full‑context calls. *Mitigation:* narrow questions stay fast; the cost was accepted with sign‑off. *Remaining risk:* 10–15.5 s (occasionally 37 s near the cap) is a real UX cost; not optimised.
11. **Stale `--reload` / orphaned processes (dev only).** *Cause:* `uvicorn --reload` has served stale code; force‑killed `java.exe`/`node.exe` leave file locks. *Mitigation:* documented in `CLAUDE.md §4` — restart fresh when verifying a fix. *Remaining risk:* a dev/verification hazard, not a production one.

## 3.16 RAG Design Trade‑offs

- **Chunk size vs. context integrity.** 1000 chars keeps every chunk safely under the 256‑token embedding limit (measured) at the cost of more chunks and tighter windows; a heading/page/table change forces an early cut even mid‑thought, because a citation pointing at one clean location is worth more than a maximally‑packed chunk.
- **Recall vs. precision (keyword search).** The `&`→`|` flip in `tsquery` buys recall (natural phrasing stops zeroing the match) at some precision cost; `ts_rank` claws back ordering. Deliberately *not* applied to Java's name/title search, where AND is correct.
- **Full context vs. retrieval.** Below 400 K: completeness, at 10–15.5 s. Above: speed and a token‑ceiling‑safe prompt, at "best‑effort" for broad questions — with the regime disclosed to the lawyer so the trade‑off isn't hidden.
- **Metadata richness vs. complexity.** Four structural columns + a breadcrumb + computed document metadata add real ingestion and prompt‑assembly complexity (and were the source of several bugs), but they're what turns "explain page 54" from a coin flip into a direct SQL fetch.
- **Latency vs. retrieval depth.** `CANDIDATE_POOL_SIZE = 20` per method, `CONTEXT_SIZE = 8` to the model — small enough to keep the prompt cheap, large enough that RRF has something to fuse. No reranker (another model call) by choice.
- **Accuracy vs. computational cost.** Local 384‑dim MiniLM embeddings (zero marginal cost, not a frontier retriever) + one paid `gpt-4o-mini` call + one *conditional* corrective regeneration. The corrective retry roughly doubles worst‑case latency for an answer that failed verification — accepted because the alternative is shipping an unverified answer.
- **Grounding strictness vs. helpfulness.** The verification pass will strip a correct‑but‑unmarked sentence and can leave an answer thinner than the evidence — a deliberate bias toward "visible gap" over "silent claim".

## 3.17 Post 3 Carousel (12 slides)

| # | Title | Exact on‑slide text | Diagram | Technical note |
|---|---|---|---|---|
| 1 | **When "Chat with PDF" isn't enough** | "Top‑K retrieval can't answer 'give me the complete chronology' when it's spread across 40 pages. For most matters, this system doesn't rank at all." | `05_retrieval_architecture.png` (teaser crop) | Hook + thesis. |
| 2 | **Naive RAG vs. legal‑document RAG** | "Generic: blob → fixed chunks → vectors → top‑K → LLM. Legal: structure is discarded, tables become word soup, broad questions fall through top‑K, exact tokens get blurred, citations are guesses." | side‑by‑side text | Be explicit this slide is the *generic* sketch. |
| 3 | **The real document‑processing pipeline** | "PDF: font metrics → headings · `find_tables()` + bbox exclusion · content‑stream image check. DOCX: real styles, real `<w:tbl>`, real page‑break markers. Diagrams: OCR **+** vision caption. One fixed chunk shape out." | `03_document_ingestion_architecture.png` | Emphasise "adaptive strategy, fixed output". |
| 4 | **Hierarchical representation** | "`Document > Heading 1 > Heading 2 > Segment > Chunk`. Stored flattened onto every chunk as a `section` breadcrumb — so 'the access‑to‑justice section' matches the parent *or* the child heading." | `08_chunking_architecture.png` (bottom) | Note the PDF H1/H2‑flattening limit. |
| 5 | **Chunking + metadata** | "1000 chars prose / 850 tables / 150 overlap (whole sentences). Hard boundary on page, heading, chunk‑type, element‑number change. Columns: `page_number`, `section`, `chunk_type`, `element_number`." | `08_chunking_architecture.png` | The "measured, not assumed" story: 256‑token limit, ~5.0 chars/token. |
| 6 | **Embedding pipeline** | "`all-MiniLM-L6-v2`, 384‑dim, **local**, zero per‑call cost. Query embedded with the same model. Runtime token‑count check warns before silent truncation." | (metadata/embedding crop of 03) | Honest: not a frontier retriever; a deliberate budget choice. |
| 7 | **Retrieval architecture** | "Exact‑identifier SQL match (uncapped, gate‑bypassing) + vector (top 20) + keyword (top 20, OR‑flipped `tsquery`, section folded in) → Reciprocal Rank Fusion (k=60)." | `05_retrieval_architecture.png` | The centrepiece. Explain why *exact* match is separate. |
| 8 | **Cross‑references: what's real, what's not** | "Breadcrumb matching (parent/child heading) ✅. Disclosed approximate section‑name matching ✅. Following 'see Section 8.2' inside a chunk ❌ — no clause‑level column yet. Deliberately scoped." | text + small crop of 09 | Credibility comes from naming the gap. |
| 9 | **Citation architecture** | "Answer sentence → marker `[7]` (a list position, not a page) → retrieved item #7 → source chunk → Document. One `Citation` row per source: file + page + section + `content[:300]` excerpt. `ON DELETE SET NULL`." | `09_citation_architecture.png` | Provenance threaded end‑to‑end, persisted, never recomputed. |
| 10 | **Generation + validation** | "`gpt-4o-mini`, temp 0, citation‑required prompt. Then: split into sentences → drop any with no valid `[n]` marker → 1 corrective regen → BR‑006 write gate. No independent fact‑checker — 'grounded', not 'hallucination‑free'." | `06_generation_validation.png` | The most important honesty slide. |
| 11 | **Large‑document / context management** | "≤ 400K chars → send the whole matter (real completeness, 10–15.5s). Above → hybrid + top‑8. Cap set by a real API spike (128K‑token ceiling, ~5 chars/token). The answer tells the lawyer which regime it used." | `10_context_window_management.png` | Map‑reduce deliberately deferred. |
| 12 | **Lessons & limitations** | "The bug that mattered most wasn't the LLM call — it was 45–100% of chunks silently truncated before embedding. Real limits: scanned PDFs, cross‑refs, cross‑section conflation, broad questions on huge matters." | text slide | Close with the failure‑modes table. GitHub ↓ |

---

# ARCHITECTURE DIAGRAM INDEX

All in `/diagrams/` as **PNG** (1680 px wide, rendered at 2× → 3360 px, LinkedIn‑ready) **and** editable **SVG**; regenerate with `python diagrams/gen_diagrams.py && python diagrams/render_pngs.py`.

| File | Title | Use in | Notes |
|---|---|---|---|
| `01_high_level_architecture.png` | Three services, one database, one hard rule | **Post 2** (hero); Post 1 (optional) | Browser → Next.js → Java → Python + data/external layers. |
| `02_user_journey.png` | From an empty Matter to a cited answer | **Post 1** (caption image); Post 2 | 9 steps, upload → cited answer; matches J1. |
| `03_document_ingestion_architecture.png` | Document ingestion — adaptive by content | **Post 2** & **Post 3** | Extraction (PDF/DOCX/image/diagram) → chunk → embed → persist. |
| `04_query_processing_architecture.png` | Query processing — two regimes | **Post 2** & **Post 3** | Full‑context vs. hybrid decision, threshold gate. |
| `05_retrieval_architecture.png` | Hybrid retrieval: exact + semantic + lexical, fused | **Post 3** (centrepiece) | Three columns → RRF → numbered context window. |
| `06_generation_validation.png` | Generation is cheap; the grounding around it is the product | **Post 2** & **Post 3** | Prompt → model → per‑sentence verify → corrective regen → write gate. |
| `07_data_architecture.png` | One Postgres schema, owned by neither backend | **Post 2** | Key tables, FK delete behaviour, Java/Python write ownership. |
| `08_chunking_architecture.png` | Adaptive strategy, one fixed chunk shape | **Post 3** | Evolution timeline + the packer + why the numbers. |
| `09_citation_architecture.png` | Every sentence traces to one real location | **Post 3** | Answer → marker → chunk → Document → `Citation` row. |
| `10_context_window_management.png` | Same question, different guarantee at different sizes | **Post 3** | The 400K cap, how it was spiked, the `full_context` signal. |

*Not created (would duplicate the above or aren't backed by the implementation): a standalone "RAG architecture" diagram (covered by 04+05+06), a LangGraph/agent‑workflow diagram (no agent framework exists — 04 is the real control flow), a standalone cross‑reference‑resolution diagram (not implemented; covered by a carousel slide).* 

**Diagram design notes:** light background (`#EEF1F6`), serif headline (`Georgia`) + sans body (`Segoe UI`), consistent role colours — navy = Java/CRUD, purple = Python/AI, teal = retrieval/DB reads, amber = external paid services, green = validation/grounding, red = failure/refusal. Every box label is a real identifier from the code.

---

# SCREENSHOT INDEX

Capture these from the running app (light theme, 110–125 % zoom).

| # | Screenshot | Feature | What must be visible | Why it matters | Post |
|---|---|---|---|---|---|
| S1 | Matter Detail — Chat tab, empty | Product overview | Three tabs (Documents / Chat / Deadlines); Chat disabled with "Upload a document first" | Establishes the workspace + the Matter‑scoped model | 1 |
| S2 | Document upload panel mid‑flight | Ingestion | Two file chips at "Processing", one at "Ready" | Shows the async pipeline + status model (REQ‑004) | 1, 2 |
| S3 | A failed upload | Reliability | A chip at "Failed" with the `error_message` and a retry affordance | "No failure is invisible" | 2 |
| S4 | Broad question → structured cited answer | Core value | The full answer with per‑paragraph citation links (`file, p.N, section`) + excerpts | The differentiator vs. flat chunking | 1, 3 |
| S5 | A single citation click → source document open | Provenance | New tab / viewer on the cited page | REQ‑006 — a citation must be traceable | 1, 3 |
| S6 | "What's on page 54?" answer | Exact retrieval | The answer naming the real section, citation carrying `p.54` | `exact_match_chunks` / label mechanism | 3 |
| S7 | "Which side has the stronger case?" → `OUT_OF_SCOPE` | Scope boundary | The exact fixed refusal sentence | The "declines a legal judgment" beat | 1 |
| S8 | A genuinely‑absent question → `NOT_FOUND` | Grounding | The exact fixed "I couldn't find that…" sentence | Refuses rather than guesses | 1, 3 |
| S9 | An answer with the low‑confidence note | Honesty | "This answer is based on limited matching content — verify against the source documents." | The confidence signal | 3 |
| S10 | An answer with the large‑matter `fullContext=false` note | Scale transparency | "This Matter is large — this answer used the most relevant sections…" | Tells the lawyer which regime answered | 2, 3 |
| S11 | The chat edit / branch switcher | Conversation state | The `‹ 2/3 ›` version switcher on an edited question | ChatGPT‑style branching over a persisted tree | 2 |
| S12 | Deadlines tab + a blocked "Close Matter" | Business rules in the UI | The inline message naming the specific open Deadline(s) (BR‑003) | Shows domain rules surfaced, not generic errors | 2 |
| S13 | Draft generation modal | Document generation | Template picker + pre‑filled fields from Matter/Client data | V0.8 — templates become queryable documents | 2 |
| S14 | Global search results | Cross‑entity search | Clients + Matters grouped, "why it matched" | SD‑009, Postgres FTS (name/title search, AND semantics) | 2 |
| S15 | (Optional) pgAdmin/`psql` on `document_chunks` | Under the hood | A few rows showing `page_number`, `section` breadcrumb, `chunk_type`, `element_number` | Proof the structure is real, queryable data | 3 |

*Retrieval "evidence" beyond the rendered citations is not exposed in the UI — there is no debug/trace panel, so S15 (a DB peek) is the only way to show retrieved chunks directly.*

---

# LINKEDIN MEDIA PLAN

| Post | Main media | Supporting media | Count | Purpose |
|---|---|---|---|---|
| **Post 1 — Product / Demo** | Cinematic screen‑recording video (60–75 s, storyboard §1.4) | Thumbnail frame (S4 — the cited answer); optionally S5 + S7 as inline images | 1 video + 1–3 images | Make a non‑technical audience *want* the product; show citations + refusal |
| **Post 2 — Architecture** | Carousel, 10 slides (§2.11) | `01`, `03`, `04`, `07` diagrams; screenshots S2, S3, S10, S11, S12 | 1 carousel (10) + up to 5 images if posted as a thread | Prove there's serious engineering; explain the whole system without the deepest RAG detail |
| **Post 3 — RAG deep dive** | Carousel, 12 slides (§3.17) | `03`, `04`, `05`, `06`, `08`, `09`, `10` diagrams; screenshots S4, S6, S8, S9, S15 | 1 carousel (12) + diagrams | Demonstrate genuine RAG‑engineering depth to AI/ML engineers and hiring managers |

**Format tips:** LinkedIn carousels are PDFs — build at 1200×1500 (4:5) or 1080×1080; the diagram PNGs here are 3:2‑ish and 3360 px wide, so place them on a slide with a title bar rather than full‑bleed. Video: MP4, ≤ 10 min (you'll use ~1), captions burned in (most people watch muted).

---

# TECHNICAL GLOSSARY (use identical terms across all three posts)

| Term | Meaning in this project |
|---|---|
| **Firm / Client / Matter** | Tenancy hierarchy. A *Matter* is a case; it belongs to a *Client*; the *Client* belongs to a *Firm*. Everything (documents, chat, deadlines) hangs off a Matter. |
| **Document** | An uploaded file (PDF/DOCX/image) **or** a generated draft, belonging to one Matter. Has a `status`: `uploading → processing → ready \| failed`. |
| **Ingestion** | The Python pipeline that turns a Document into searchable `document_chunks`: extract → chunk → embed → persist. |
| **Extraction** | Getting text + structure out of a file — format‑specific and structure‑aware (font metrics for PDF, styles for DOCX, OCR + vision caption for images/diagrams). |
| **Segment** | An intermediate unit produced by extraction: one sentence / table row / image caption, tagged with `heading_path`, `chunk_type`, `element_number`, `page_number`. |
| **Chunk** (`document_chunks` row / `TextChunk`) | The unit of retrieval: ~1000 chars of `content` (850 for tables), a 384‑dim `embedding`, and structural metadata. Never spans two pages, headings, tables, or images. |
| **Section** | The **full heading breadcrumb** a chunk sits under, e.g. `"53. Access to Justice > Mass claims and vulnerable populations"`. A real `document_chunks` / `citations` column. `NULL` for unstructured content. |
| **`element_number`** | The Nth table or Nth image in a document (document‑wide, 1‑indexed) — how "Table 3" / "Image 2" is addressed. |
| **Metadata** | (a) per‑chunk structural columns (`page_number`, `section`, `chunk_type`, `element_number`); (b) per‑Document computed facts (`file_name`, `page_count`) offered to the LLM as a separate non‑hallucinatable surface. |
| **Embedding** | A 384‑dim vector from `all-MiniLM-L6-v2` (local), stored in a `pgvector` `vector(384)` column. |
| **Retrieval** | Selecting the chunks to put in the prompt. Either *full‑context* (every chunk, ≤ 400 K chars) or *hybrid* (exact‑identifier SQL + vector + keyword, fused with RRF, threshold‑gated). |
| **Exact‑identifier match** | A regex‑detected `page/section/table/image` number → direct SQL on the real column, uncapped, bypassing the relevance gate. |
| **RRF (Reciprocal Rank Fusion)** | Merging the vector and keyword result lists by `Σ 1/(60 + rank)` per chunk — no hand‑tuned blend weight. |
| **Full‑context path** | Sending every `ready` chunk of a Matter to the LLM with no ranking, used when the corpus fits under `FULL_CONTEXT_CHAR_CAP` (400 000 chars). |
| **Context** | The assembled prompt payload: last 4 branch turns + the numbered, labelled chunk list + "Document metadata" items + the question. |
| **Evidence** | The specific chunk(s) a given answer sentence rests on — surfaced to the reader as citations, not as a separate panel. |
| **Citation** | A persisted `citations` row: `document_id` (+ `file_name`), `page_number`, `section`, `excerpt` (`content[:300]`), linked to one `ChatMessage`. Survives deletion of the source Document (`ON DELETE SET NULL`). |
| **Grounding** | The set of *structural* controls that keep answers tied to retrieved text: SQL matter‑scope, no‑LLM‑call‑below‑threshold, context‑only prompt, per‑sentence citation verification, one corrective regeneration, temperature 0, the BR‑006 write‑path invariant. |
| **Validation / citation verification** | The post‑generation `verify_citations` pass: drop any factual sentence without a marker resolving to a retrieved item; one corrective regeneration; gap note. **Not** an independent fact‑checker. |
| **`NOT_FOUND` response** | The fixed sentence *"I couldn't find that in this Matter's documents."* — returned (HTTP 200) when nothing clears the relevance threshold. Not an error. |
| **`OUT_OF_SCOPE` response** | The fixed sentence returned when the question asks for a legal‑strategy / adversarial judgment ("which side is stronger", "should we settle") — the documents may cover the topic, but that call is the lawyer's. |
| **`low_confidence`** | Flag (ephemeral, per‑response): retrieval cleared the "no relevant data" floor but not the "confident" band — the answer is shown with a "verify against the source" note. |
| **`full_context`** | Flag (ephemeral, per‑response): `True` if every chunk was considered, `False` if ranked retrieval was used — surfaced to the lawyer as a "this Matter is large…" note. |
| **Agent** | *Not used here.* There is no agent framework, planner, or tool‑calling loop — the pipeline is a deterministic function with one data‑driven branch and one bounded corrective‑regeneration step. |
| **Knowledge base** | Informally, the set of `document_chunks` for one Matter's `ready` Documents. There is no cross‑Matter knowledge base — BR‑005 forbids it at the SQL level. |

---

# FACT CHECK & IMPLEMENTATION VALIDATION

| # | Claim (as it appears in the posts) | Verified against | Status |
|---|---|---|---|
| 1 | Three services; frontend has no DB access / no API routes | `05-System-Architecture.md §1–2`; `CLAUDE.md §0`; `frontend/` has no DB driver, only `lib/api/*` | ✅ Verified |
| 2 | Java owns auth + all CRUD; Python owns ingestion + chat | `backend-java/.../web/controller/*`, `application/*`; `backend-python/app/web/{ingest,chat}_router.py` | ✅ Verified |
| 3 | Browser never calls Python directly; Java proxies chat after auth + BR‑008 | `ChatController.java` (`CurrentLawyerResolver.resolve` + `matterService.get(firmId, matterId)` then `chatService.ask`); `HttpChatGateway.java` | ✅ Verified |
| 4 | Ingestion hand‑off is fire‑and‑forget; chat hand‑off is blocking | `HttpIngestionTrigger.java` (`CompletableFuture.supplyAsync`); `HttpChatGateway.java` (`client.send(...)`, 30 s timeout) | ✅ Verified |
| 5 | PDF extraction uses font size/weight for headings; running header/footer filter = >50% of pages | `extraction.py::_pdf_body_font_size`, `_pdf_heading_candidate_sizes`, `_pdf_running_header_footer_keys` | ✅ Verified |
| 6 | PDF images verified via content‑stream `Do` check; OCR once per unique image (SHA‑256) | `extraction.py::_truly_drawn_xobject_identities`, `image_content_cache` keyed by `hashlib.sha256(img.data).digest()` | ✅ Verified |
| 7 | DOCX walk in true document order; heading stack from `paragraph.style`; page numbers from `<w:br w:type="page"/>` | `extraction.py::_iter_block_items`, `_docx_style_heading_level`, `_paragraph_has_page_break` | ✅ Verified |
| 8 | Embedded diagrams get OCR **and** `gpt-4o-mini` vision caption, combined | `extraction.py::_combine_ocr_and_caption`; `vision.py::OpenAIImageCaptioner` | ✅ Verified |
| 9 | Standalone image upload = OCR only; scanned (text‑less) PDF is **not** ingested → `failed` | `extraction.py::_extract_image`; `DocumentTextExtractor` docstring; `ingestion_service.py` `mark_failed("No extractable text found…")` | ✅ Verified |
| 10 | `CHUNK_SIZE_CHARS = 1000`, `CHUNK_OVERLAP_CHARS = 150`, `TABLE_CHUNK_SIZE_CHARS = 850` | `app/domain/chunk.py` constants | ✅ Verified |
| 11 | Hard chunk boundary on page / heading / chunk‑type / element‑number change | `chunk.py::_pack_typed_segments` grouping condition | ✅ Verified |
| 12 | Embedding model `all-MiniLM-L6-v2`, 384‑dim, local, 256‑token limit, runtime truncation warning | `embedding.py`; `config.py` (`EMBEDDING_MODEL_NAME`); `schema.ts` `vector(384)` | ✅ Verified |
| 13 | Persist via raw SQL with `CAST(:embedding AS vector)` | `repository.py::SqlAlchemyIngestionRepository.save_chunks` | ✅ Verified |
| 14 | `FULL_CONTEXT_CHAR_CAP = 400_000`; below it → every chunk, no ranking, no gate | `chat_service.py` constant + `_answer` (`if total_chars <= FULL_CONTEXT_CHAR_CAP`) | ✅ Verified |
| 15 | Cap set by real API spike (712K fail, ~416K→10.6s, ~464K→37.1s); raised from 150K | `chat_service.py` `FULL_CONTEXT_CHAR_CAP` comment; `RAG-Pipeline-Development-History.md` Phase 8 | ✅ Verified (project's own record) |
| 16 | Hybrid = exact‑identifier + vector(20) + keyword(20) → RRF(k=60) | `chat_service.py::_answer`; `chat_repository.py`; `retrieval.py::reciprocal_rank_fusion` | ✅ Verified |
| 17 | Exact‑identifier match is uncapped and bypasses the relevance gate | `chat_service.py` (`if not exact_chunks and (… < RELEVANCE_THRESHOLD)`), `exact_match_chunks` has no `LIMIT` | ✅ Verified |
| 18 | Identifier regex scoped to page/section/table/image only; clause/exhibit out of scope | `identifier_query.py` regex + docstring | ✅ Verified |
| 19 | `RELEVANCE_THRESHOLD = 0.01`, `CONFIDENT_THRESHOLD = 0.02`, `CONTEXT_SIZE = 8`, `CANDIDATE_POOL_SIZE = 20`, `RECENT_TURNS = 4` | `chat_service.py` constants | ✅ Verified |
| 20 | Below threshold with no exact hit → no LLM call; try metadata‑only, else fixed `NOT_FOUND` | `chat_service.py::_answer` | ✅ Verified |
| 21 | `keyword_search` OR‑flips `plainto_tsquery` and folds `section` into the `tsvector` | `chat_repository.py::keyword_search` (`replace(... ' & ', ' | ')`, `coalesce(dc.section,'') || ' ' || dc.content`) | ✅ Verified |
| 22 | Generation: `gpt-4o-mini`, `temperature=0`, single completion, no streaming | `llm.py::OpenAIChatLLM.generate` | ✅ Verified |
| 23 | Per‑sentence citation verification; drop unmarked sentences; one corrective regeneration | `citation_verification.py::verify_citations`; `chat_service.py::_generate_and_persist` (`if not verified.all_valid: … retry once`) | ✅ Verified |
| 24 | BR‑006 write‑path invariant: an uncited factual assistant message can't be persisted | `domain/chat.py::validate_assistant_message`; called in `_persist_answer` | ✅ Verified |
| 25 | No independent fact‑checking model / NLI entailment check | absence in `citation_verification.py` (only marker range check); `06-AI-Architecture.md §3` Rule 5 | ✅ Verified (by absence) |
| 26 | `Citation` rows: `document_id` `ON DELETE SET NULL`; `excerpt = content[:300]`; survive file delete | `schema.ts` `citations`; `chat_service.py::_citation_for`; `chat_repository.py::citations_for` (`LEFT JOIN documents`) | ✅ Verified |
| 27 | `full_context` / `low_confidence` flags threaded to the UI as notes | `chat_service.py::AskResult`; `chat_router.py` (`response["fullContext"]`); `chat-panel.tsx` (`m.fullContext === false`, `m.lowConfidence`) | ✅ Verified |
| 28 | The answer "stream" is a client‑side reveal over a single payload — not token streaming | `chat-panel.tsx::StreamingBubble` docstring: "no token stream… client‑side 'streaming' reveal" | ✅ Verified |
| 29 | No LangGraph/LangChain/agent framework | `backend-python/requirements.txt` (no such deps); `chat_service.py` is a plain class | ✅ Verified |
| 30 | Chat is branchable (ChatGPT‑style edit); regenerate = edit with same text | `chat_service.py::edit/activate_branch`; `chat-panel.tsx::regenerate` calls `postEdit(precedingQuestion.id, precedingQuestion.content)` | ✅ Verified |
| 31 | Document generation (V0.8) renders `.txt`, not real DOCX/PDF | memory `v08_draft_generation.md`; `08-Technology-Decision-Log` — **not re‑read line‑by‑line this pass** | ⚠️ Partially verified |
| 32 | Measured latency: full‑context 10–15.5 s; narrow 2–7 s; over the 8 s p95 target | `06-AI-Architecture.md §2`; `RAG-Pipeline-Development-History.md` Phase 2 (project's own measurements, not re‑run here) | ⚠️ Partially verified (project's record, no independent benchmark) |
| 33 | "45–100% of chunks silently truncated" before the 2026‑08‑19 fix | `06-AI-Architecture.md §2` addendum; `chunk.py` `CHUNK_SIZE_CHARS` comment | ⚠️ Partially verified (project's record) |
| 34 | Railway hosting; BullMQ/Redis planned | `05-System-Architecture.md §6` — intent only; nothing deployed/wired in the repo | ❌ Not verified as implemented (correctly described as planned) |
| 35 | pgvector has no ANN index (exact scan) | no index DDL in `schema.ts` for `embedding`; `vector_search` is a plain `ORDER BY … <=> …` | ✅ Verified (by absence); whether an index is *planned* — ❌ Not verified |
| 36 | 108 backend‑python tests / Java suite / Playwright 5 journeys | `RAG-Pipeline-Development-History.md` Phase 8 ("all 108 backend‑python tests… pass"); `tests/e2e/*.spec.ts` — count not re‑run this pass | ⚠️ Partially verified |
| 37 | Session token SHA‑256, password BCrypt(12) | `CLAUDE.md §4`; `05-System-Architecture.md §5`; `schema.ts` comments — Java crypto classes not opened this pass | ⚠️ Partially verified |

**Removed / softened during fact‑check:** any phrasing implying real‑time streaming; any "eliminates hallucinations" / "production‑ready" / accuracy‑percentage claim; "cross‑reference resolution" moved from a feature to an explicit non‑feature; "image understanding" qualified to Tier‑1 (embedded diagrams, ingestion‑time caption only).

---

# "DO NOT SAY" SECTION

| Don't say | Say instead | Why |
|---|---|---|
| "Eliminates hallucinations" / "hallucination‑free" | "Designed to ground answers in retrieved evidence — with structural controls, not just a prompt" | Verification checks *marker resolves*, not *claim entails*; conflation and label‑pattern‑completion still occur and are documented. |
| "Real‑time streaming" / "streams tokens" | "Reveals the answer with a client‑side typing animation (the response is a single payload)" | `chat-panel.tsx` is explicit that there is no token stream. |
| "Production‑ready" | "A working end‑to‑end build with tests and live verification; not yet deployed, no queue, dev filesystem storage" | Railway/R2/BullMQ are intent, not implementation. |
| "Understands legal documents like a lawyer" / "legal reasoning" | "Retrieves and organises what the documents say, with citations; it declines to make legal judgments" | The system explicitly refuses strategy/adversarial questions (`OUT_OF_SCOPE`). |
| "Independent validation layer" / "fact‑checks every answer" | "A mechanical per‑sentence citation‑marker check plus one corrective regeneration" | There is no second model / truth source. |
| "Resolves cross‑references" / "follows 'see Section 8.2'" | "Matches heading breadcrumbs and does disclosed approximate section‑name matching" | Follow‑the‑pointer retrieval is explicitly out of scope (no clause‑level column). |
| "99% accurate" / any accuracy figure | "Verified by unit tests, live manual testing, and Playwright journeys" (quote the 2/9 → 14/14 chronology example as an illustration, labelled as a single manual check) | No eval harness or benchmark exists. |
| "Full image understanding" / "answers questions about any image" | "OCRs and vision‑captions embedded diagrams at ingestion time" | No persisted image bytes, no live per‑image Q&A (Tier 2 deferred). |
| "Handles any document" | "Handles native‑text PDF and DOCX, and standalone images; scanned image‑only PDFs are not yet supported" | Real limitation surfaced as `failed`. |
| "Unlimited context" / "reads the entire document at any size" | "Sends the whole matter when it's under ~400K chars; above that, retrieves — and tells the lawyer which" | The `full_context` signal exists precisely because this isn't unlimited. |
| "Enterprise‑grade multi‑tenant isolation, battle‑tested" | "Firm‑level isolation enforced as a SQL predicate plus an explicit per‑request authorization call" | Accurate and still impressive; avoid unverifiable superlatives. |

---

# RECOMMENDED POSTING SEQUENCE

1. **Post 1 (Product / Demo)** — a Tuesday–Thursday morning. Lead with the video. Pin the GitHub link in the first comment (LinkedIn suppresses reach on posts with outbound links in the body — putting `[GITHUB LINK]` in a comment is a common workaround; keep the placeholder in the body too if you prefer clarity over reach).
2. **Wait 3–5 days.** Reply to every substantive comment on Post 1; note recurring questions — they're material for Post 2/3.
3. **Post 2 (Architecture)** — same time slot. Open by referencing Post 1 ("Part 1 showed the product; here's what's underneath"). Carousel as the main media.
4. **Wait 3–5 days.**
5. **Post 3 (RAG deep dive)** — same slot. This one is for the technical audience; expect fewer likes, higher‑quality comments, and DMs from engineers/recruiters. Link back to Parts 1 and 2 at the top.
6. **After all three:** a short "wrap" comment or a fourth lightweight post linking the series + the repo, for anyone who finds it later.

---

# FINAL QUALITY CHECKLIST

- [ ] Every architectural claim in the three captions maps to a row in the Fact Check table (✅ or explicitly ⚠️/❌).
- [ ] No sentence implies real‑time streaming, zero hallucinations, production readiness, cross‑reference resolution, or an accuracy percentage.
- [ ] "Implemented" vs. "planned" vs. "deferred" is unambiguous everywhere (queue, R2, Railway, reranker, map‑reduce, Tier‑2 vision, clause‑level cross‑refs = **not implemented**).
- [ ] Terminology matches the glossary across all three posts (Chunk, Section, Citation, Grounding, Agent‑not‑used, Knowledge base).
- [ ] Every diagram referenced exists in `/diagrams/` as PNG, is legible at LinkedIn display size, and its labels are real code identifiers.
- [ ] Post 1 is understandable with zero technical background and still makes the value obvious.
- [ ] Post 2 lets a software engineer draw the system from memory: 3 services, 1 DB, the two hand‑offs, the ingestion stages, the two query regimes.
- [ ] Post 3 gives an AI engineer enough to ask a sharp question: what's the reranker story, why RRF over a tuned blend, how is the 400K cap justified, what does verification actually check, why isn't cross‑ref resolved.
- [ ] Each major component's *why* is stated, not just its *what*.
- [ ] The series reads as one arc: problem → product → system → RAG internals → honest limits.
- [ ] The GitHub placeholder `[GITHUB LINK]` is replaced in all three posts before publishing.
- [ ] Screenshots S1–S15 captured on a seeded, pre‑warmed environment (no cold‑start latency on camera).
- [ ] The "DO NOT SAY" table has been used as a final read‑through filter on all three captions and both carousels.
