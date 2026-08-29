# Legal AI Assistant

**A case-workspace web app for small law firms, with a retrieval-augmented assistant that answers questions about a matter's own documents — and cites every sentence.**

Upload the files for a case, and the assistant answers questions grounded in *those* documents only, with clickable citations to the exact file, page, and section heading. If the documents don't cover the question, it says so. If the question asks for a legal judgment, it declines. Grounding is enforced in code — a SQL tenant filter, a below-threshold refusal that never reaches the model, and a per-sentence citation check after generation — not left to a prompt.

> **Status:** working end-to-end build with automated tests. Not deployed, not a production system, and not a substitute for professional legal advice. See [Project status](#project-status) and [Limitations](#known-limitations).

<p align="center">
  <img src="diagrams/01_high_level_architecture.png" alt="High-level architecture: three services, one database" width="880">
</p>

---

## Table of contents

- [Why this exists](#why-this-exists)
- [What makes it different from "chat with PDF"](#what-makes-it-different-from-chat-with-pdf)
- [Architecture](#architecture)
- [The RAG pipeline](#the-rag-pipeline)
- [Technology stack](#technology-stack)
- [Repository layout](#repository-layout)
- [Getting started](#getting-started)
- [Running the app](#running-the-app)
- [Testing](#testing)
- [Project status](#project-status)
- [Known limitations](#known-limitations)
- [Design documentation](#design-documentation)
- [License & disclaimer](#license--disclaimer)

---

## Why this exists

Solo and small-firm lawyers manage clients, cases, documents, and deadlines across email, chat, local folders, and paper. To answer a simple question about a case — *"what did the opposing party argue in their reply?"* — they re-read whole documents by hand. Closed matters become effectively unsearchable. Routine drafts get rebuilt from scratch.

The Legal AI Assistant is a single system of record for **Firms → Clients → Matters → Documents / Deadlines**, with an AI assistant scoped to one matter at a time. The bar it's built to: *every factual claim in an answer must be traceable to a specific source and location, and the assistant must say "not found" rather than guess.*

## What makes it different from "chat with PDF"

| A basic "chat with PDF" | This project |
|---|---|
| One flat text blob, fixed-size character chunks | **Structure-aware ingestion** — heading hierarchy, tables extracted row-by-row (`column: value`), embedded diagrams OCR'd **and** vision-captioned. A chunk never crosses a page, heading, table, or image. |
| Vector search, top-K, hope | **Hybrid retrieval** — exact-identifier SQL match (`page 54`, `Table 3`, `§15`) + vector similarity + Postgres full-text, merged with Reciprocal Rank Fusion. |
| "Answer from the context" in a prompt | **Grounding as code** — matter isolation is a SQL `WHERE` clause; below a relevance threshold the model is never called; after generation every citation marker is checked against the chunks actually retrieved, and unsupported sentences are stripped. |
| Citations are page guesses | **`Citation` rows** persisted with `document_id`, `page_number`, `section` breadcrumb, and the actual quoted excerpt — and they survive deletion of the source file. |
| Same behaviour at any size | **Full context** below ~400K characters (genuine completeness for "summarise everything"); hybrid + ranked retrieval above it — and the answer **tells the lawyer which regime produced it**. |
| "I can't find that" == error | A fixed `NOT_FOUND` string (not an error), plus a separate `OUT_OF_SCOPE` string for *"you're asking me to make a legal judgment."* |

Feature highlights:

- **Clients & Matters** — firm-scoped CRUD; a Matter is the unit of work (documents, chat, deadlines hang off it).
- **Document ingestion** — PDF, DOCX, and image uploads; adaptive extraction; visible `uploading → processing → ready | failed` status.
- **AI chat per Matter** — grounded answers with inline citations; ChatGPT-style message editing / branching / regenerate; pinned answers; voice input and read-aloud (browser APIs).
- **Deadlines & notifications** — per-Matter deadlines with lead-time reminders; an idempotent scan job; a business rule that blocks closing a Matter with open deadlines and names them.
- **Draft generation** — pre-authored templates rendered with a Matter/Client's data into a new Document that becomes queryable like any upload *(currently rendered as plain text)*.
- **Cross-entity search** — Postgres full-text over Clients and Matters.

## Architecture

**Three services, one database, one rule that is never bent: the browser never touches the database.** Every read/write is an HTTP call to a backend.

| Service | Owns | Notes |
|---|---|---|
| **`/frontend`** — Next.js 15 (App Router), React 19 | UI only | No DB driver, no API routes of its own. Server Components forward the session cookie explicitly; client components use `credentials: 'include'`. |
| **`/backend-java`** — Spring Boot 4.1, Java 21 | Auth + all CRUD | Self-hosted auth (BCrypt passwords, SHA-256 session tokens, httpOnly cookie, per-request DB check). Firm isolation is a SQL predicate **plus** an explicit authorization call at the top of every controller method. Proxies AI calls to Python after checking auth + matter ownership. |
| **`/backend-python`** — FastAPI, Python 3.13 | All AI | Document ingestion and the chat retrieval/generation pipeline. Internal only — never called by the browser. Layered `domain → application (Protocol ports) → infrastructure → web`. |
| **`/database`** — Drizzle Kit (TypeScript) | The Postgres schema | A standalone migration CLI, owned by neither backend's ORM. Both backends map onto it with validate-only. |

Both backends connect to the same **PostgreSQL 16 + `pgvector`** instance. Files live outside the DB — a local `/uploads` directory in dev (Java writes, Python reads), behind a `StorageService` interface that a Cloudflare R2 implementation slots into for production.

The Java → Python hand-off is **fire-and-forget for ingestion** (the upload response doesn't wait) and **blocking for chat** (the browser is waiting on an answer). There is no message queue yet — a deliberate scope decision; every failure still resolves to a visible `Document.status`.

<p align="center">
  <img src="diagrams/04_query_processing_architecture.png" alt="Query processing: two regimes chosen by corpus size" width="880">
</p>

More diagrams (PNG + editable SVG) live in [`/diagrams`](diagrams/): document ingestion, retrieval, citation architecture, the data model, chunking, context-window management, and the end-to-end user journey.

## The RAG pipeline

*(Full write-up: [`06-AI-Architecture.md`](06-AI-Architecture.md) and [`RAG-Pipeline-Development-History.md`](RAG-Pipeline-Development-History.md).)*

**Ingestion** (`backend-python/app`): `IngestionService.ingest()` → fetch → extract → chunk → embed → persist, always terminating in `ready` or `failed`.

- **Extraction** branches on MIME type. **PDF** (`pdfplumber` + `pypdf`): per-character font metrics → heading levels; `find_tables()` with bounding-box exclusion from the prose pass; real page numbers; embedded images verified via the page content stream (`Do` operator) and attributed to every page that truly draws them. **DOCX** (`python-docx`): a true document-order walk, heading stack from real paragraph styles, tables from real `<w:tbl>` objects, page numbers from `<w:br w:type="page"/>` markers when present. **Embedded diagrams** are OCR'd (EasyOCR, character-exact) **and** vision-captioned (`gpt-4o-mini`, structure/flow), then combined.
- **Chunking** (`app/domain/chunk.py`, pure) branches on data *shape*, not file type. Sentence-boundary greedy packing, ~1000 chars (850 for tables), ~150-char whole-sentence overlap. A page / heading / chunk-type / element-number change is a **hard boundary** — so a chunk maps to exactly one real location, and a citation is never a guess.
- **Embedding**: `all-MiniLM-L6-v2` (384-dim), local, no API key, no per-call cost. A runtime check warns if a text would exceed the model's real 256-token limit.
- **Storage**: raw SQL `INSERT` into `document_chunks` with an explicit `CAST(:embedding AS vector)`.

**Query** (`ChatService._answer`):

- If the Matter has no `ready` Document → HTTP 422 (never a fabricated answer).
- **Corpus ≤ ~400,000 characters** → *full-context path*: every chunk goes to the model, no ranking, no threshold. `full_context = True`.
- **Otherwise** → *hybrid path*: a regex pulls any `page / section / table / image` number → direct SQL (uncapped, bypasses the relevance gate); the question is embedded → `vector_search` (top 20) and `keyword_search` (top 20, OR-flipped `tsquery`, section folded into the searchable text); results merged with **Reciprocal Rank Fusion** (`k = 60`). Below the relevance threshold with no exact hit → no LLM call (try metadata-only, else the fixed `NOT_FOUND` string).

**Generation & grounding**:

- `gpt-4o-mini`, `temperature = 0`, with a citation-required system prompt and each context item prefixed by its real `(Page N)` / `(Section: "…")` / `(Table N)` label.
- `verify_citations()` (pure function): split into sentences; drop any factual sentence whose `[n]` marker doesn't resolve to a chunk retrieved this call; if anything was dropped, attempt **one** corrective regeneration; otherwise keep the stripped answer plus a visible gap note.
- `validate_assistant_message()` (BR-006): an assistant row with content but no citations cannot be persisted — unless it's the fixed `NOT_FOUND` / `OUT_OF_SCOPE` string.

> This is a **deterministic pipeline, not an agent framework** — no LangGraph, no planner, no tool-calling loop. One data-driven branch, one bounded corrective-regeneration step.

## Technology stack

| Area | Choice | Why |
|---|---|---|
| Frontend | Next.js 15 · React 19 · TypeScript (strict) · pnpm | UI only; TypeScript catches shape drift against the backend DTOs. |
| CRUD backend | Java 21 · Spring Boot 4.1 · Spring Data JPA · Maven Wrapper | Everything that must simply be correct, in a boring, statically-typed stack. |
| Auth | `spring-security-crypto` BCrypt (cost 12) + SHA-256 session-token hashing | Self-hosted; no third-party auth provider. |
| AI backend | Python 3.13 · FastAPI · SQLAlchemy (raw `text()` + `::vector`) | Python's OCR / embedding / LLM ecosystem is the reason for the split. |
| Database | PostgreSQL 16 + `pgvector` (`vector(384)`) | One database for relational data *and* embeddings at this scale. |
| Migrations | Drizzle Kit (TypeScript), standalone in `/database` | One schema-authoring tool across two backend languages. |
| LLM | OpenAI `gpt-4o-mini`, `temperature = 0` | The only paid external API. Also used for embedded-diagram vision captions. |
| Embeddings | `sentence-transformers` · `all-MiniLM-L6-v2` (384-dim) | Runs locally, no API key, zero per-call cost. |
| OCR | EasyOCR 1.7.2 (CPU) | No system binary needed; installs via pip. |
| PDF / DOCX | `pypdf` · `pdfplumber` · `python-docx` · `cryptography` (AES-encrypted PDFs) | Structure-aware extraction. |
| Storage | Local filesystem in dev; Cloudflare R2 in production (same interface) | No R2 credentials in this environment. |
| Testing | JUnit 5 (Java) · pytest (Python) · Playwright (end-to-end) | Domain tests are plain; application tests use hand-written in-memory fakes. |

## Repository layout

```
/frontend         Next.js 15 — UI only. No database access, no API routes.
/backend-java     Spring Boot — auth + all CRUD (Firm, Client, Matter, Deadline,
                  Notification, Template, Search).
/backend-python   FastAPI — AI: document ingestion + the chat RAG pipeline.
/database         Drizzle schema + migrations. A CLI tool, not an application.
/uploads          Shared local-dev file storage (gitignored). Java writes, Python reads.
/tests            Playwright end-to-end tests (the 5 core UX journeys).
/diagrams         Architecture / flow diagrams (PNG + editable SVG + generator).

01-Charter-and-Discovery.md      Problem statement, users, scope.
02-Requirements.md               REQ / NFR / BR / AC identifiers.
03-UX-Product-Design.md          16 screens, information architecture, user journeys.
04-Design-System.md              Visual tokens.
05-System-Architecture.md        Services, modules (SD-00x), schema, API, auth flow.
06-AI-Architecture.md            Ingestion + retrieval + grounding rules + failure modes.
07-Build-Plan.md                 Versioned build history.
08-Technology-Decision-Log.md    Every technology decision, dated, with the spike behind it.
RAG-Pipeline-Development-History.md  The RAG component's evolution — every real bug and fix.
CLAUDE.md                        Working conventions + a running list of stack gotchas.
```

## Getting started

### Prerequisites

- **Docker** (for PostgreSQL + `pgvector`)
- **Node.js 20+** and **pnpm** (`npm i -g pnpm`)
- **JDK 21**
- **Python 3.13**
- An **OpenAI API key** (`gpt-4o-mini` access) — the only paid dependency

### 1. Database

```bash
# from the repo root
docker compose up -d                       # starts Postgres 16 + pgvector on :5432

# enable the vector extension (once)
docker compose exec postgres psql -U legal_ai -d legal_ai_assistant \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"

cd database
pnpm install
# .env.local must contain:
#   DATABASE_URL=postgresql://legal_ai:legal_ai_dev_password@localhost:5432/legal_ai_assistant
pnpm db:migrate                            # apply all migrations
psql postgresql://legal_ai:legal_ai_dev_password@localhost:5432/legal_ai_assistant \
  -f seed-templates.sql                    # seed the system draft templates
# optional: pnpm db:studio                 # Drizzle Studio GUI
```

### 2. Java backend (`:8080`)

```bash
cd backend-java
./mvnw spring-boot:run
```

Configuration lives in `src/main/resources/application.properties` (DB URL, `app.frontend-origin`, `app.python-api-url`, `app.storage.local-dir`). Defaults match the Docker Compose setup above.

### 3. Python backend (`:8000`)

```bash
cd backend-python
python -m venv .venv
source .venv/Scripts/activate          # Windows;  source .venv/bin/activate on macOS/Linux

# install CPU-only torch first so EasyOCR / sentence-transformers don't pull CUDA
pip install --index-url https://download.pytorch.org/whl/cpu torch
pip install -r requirements.txt

# secrets — OPENAI_API_KEY has no default and must be set
cat > .env <<'EOF'
OPENAI_API_KEY=sk-...
# DATABASE_URL, STORAGE_DIR, EMBEDDING_MODEL_NAME, OPENAI_CHAT_MODEL have working defaults
EOF

uvicorn app.main:app --port 8000 --reload
```

The first request loads the embedding model (~7 s) and, on first use, downloads the EasyOCR model (~30 s). On Windows, set `PYTHONIOENCODING=utf-8` for that first OCR download.

### 4. Frontend (`:3000`)

```bash
cd frontend
pnpm install
cp .env.local.example .env.local           # JAVA_API_URL + NEXT_PUBLIC_JAVA_API_URL → http://localhost:8080
pnpm dev
```

Open **http://localhost:3000**, register a firm, create a Client and a Matter, upload a document, and ask a question once it's `ready`.

> **Low-RAM machines (~8 GB):** running the Java backend and the Next.js dev server together at default heap can OOM. Start them constrained:
> `MAVEN_OPTS="-Xmx384m" ./mvnw spring-boot:run -Dspring-boot.run.jvmArguments="-Xmx256m"` and
> `NODE_OPTIONS="--max-old-space-size=512" pnpm dev`.

## Running the app

| Task | Command | From |
|---|---|---|
| Frontend dev server | `pnpm dev` | `/frontend` |
| Type-check frontend | `pnpm typecheck` | `/frontend` |
| Java backend | `./mvnw spring-boot:run` | `/backend-java` |
| Python backend | `uvicorn app.main:app --port 8000 --reload` (in `.venv`) | `/backend-python` |
| Generate a migration | `pnpm db:generate` | `/database` |
| Apply migrations | `pnpm db:migrate` | `/database` |
| Inspect data (GUI) | `pnpm db:studio` | `/database` |

## Testing

```bash
# Java — domain + application-layer (JUnit 5)
cd backend-java && ./mvnw test

# Python — domain / application / infrastructure (pytest)
cd backend-python && source .venv/Scripts/activate && pytest

# End-to-end — the 5 core UX journeys (Playwright), all services live
cd tests
pnpm install
pnpm exec playwright install
pnpm test:e2e
```

Testing conventions ([`CLAUDE.md §2`](CLAUDE.md)): every business rule (BR-001–008) has at least one test proving it is *enforced*; every API endpoint has a happy-path test and a cross-firm isolation test (a foreign record returns 404, not 403); AI answers are asserted on **structural properties** (a citation exists and resolves to a real document; the "not found" path is taken when nothing clears the threshold), never on exact text.

## Project status

Built and verified end-to-end (`07-Build-Plan.md`):

- **V0.1** Walking skeleton — self-hosted auth, Client round-trip
- **V0.2** Clients & Matters
- **V0.3** Document ingestion (OCR + chunk + embed)
- **V0.4** AI Chat (hybrid retrieval + grounded generation + citation verification)
- **V0.5** Deadlines & Notifications
- **V0.6** Cross-entity Search
- **V0.8** Draft Generation *(V0.7 firm-invites deferred)*

The RAG pipeline has since had eight documented rounds of real-bug fixes and architecture changes (`RAG-Pipeline-Development-History.md`), including: a full chunking rebuild after page numbers turned out to be chunk indices; a chunk-size correction after the embedding model was found to be silently truncating most of the corpus; DOCX- and PDF-adaptive structure detection; exact-match retrieval for numbered identifiers; vision captioning of embedded diagrams; and raising the full-context cap from 150K to 400K characters against a real API spike, with a `full_context` transparency signal added end-to-end.

**Not built (deliberately deferred, not forgotten):** message queue for ingestion retry (BullMQ/Redis), Cloudflare R2 storage, deployment (Railway), an ANN index on the embedding column, a cross-encoder reranker, a map-reduce path for unbounded corpora, Tier-2 image Q&A (persisted image bytes + live per-image calls), firm invites (V0.7), and email delivery for reminders (Resend).

## Known limitations

Honest, and traceable to code:

- **Scanned (image-only) PDFs are not ingested** — no text layer ⇒ the Document resolves to `failed`. Only standalone `image/*` uploads go through OCR.
- **Validation is not fact-checking.** `verify_citations` checks that each factual sentence carries a marker resolving to a retrieved chunk — not that the *claim* is entailed by the *cited text*. There is no independent fact-checking model and no external truth source. "Grounded in retrieved evidence" — not "hallucination-free."
- **Cross-references inside a document are not followed.** "See Section 8.2" is not resolved (there is no clause-level identifier column). Heading-breadcrumb matching and disclosed approximate section-name matching *are* implemented.
- **The answer reveal is a client-side typing animation over a single response payload** — not token streaming.
- **Broad questions on very large Matters (> ~400K chars) are best-effort**, not complete — and the answer says so (`full_context = False`).
- **Latency:** whole-document (full-context) calls have been measured at 10–15.5 s, over the 8 s p95 target; narrow questions stay 2–7 s.
- **No formal evaluation harness** — verification is unit tests, live manual testing, and the Playwright journeys.
- Draft generation renders **plain text**, not real DOCX/PDF.

## Design documentation

The `NN-*.md` files at the repo root are the living design record. Start with [`01-Charter-and-Discovery.md`](01-Charter-and-Discovery.md) for the problem, [`05-System-Architecture.md`](05-System-Architecture.md) for the system, and [`06-AI-Architecture.md`](06-AI-Architecture.md) + [`RAG-Pipeline-Development-History.md`](RAG-Pipeline-Development-History.md) for the RAG design and its evolution. [`CLAUDE.md`](CLAUDE.md) holds the working conventions and a running list of stack gotchas.

## License & disclaimer

No license file is included yet — until one is added, all rights are reserved by the author. Add a `LICENSE` before any external use or contribution.

This is a portfolio / learning project. It is **not** a production legal system, does **not** provide legal advice, and makes no guarantee of accuracy or completeness. Do not rely on it for real casework.
