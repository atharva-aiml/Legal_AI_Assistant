# CLAUDE.md — Legal AI Assistant

Conventions for working in this codebase. Traces to [05-System-Architecture.md](05-System-Architecture.md) (stack, modules, schema) and [04-Design-System.md](04-Design-System.md) (UI tokens). This file is living — when a gotcha bites, add it to §4 immediately, don't wait for a cleanup pass.

## 0. Repo Layout — Frontend + One Backend

```
/frontend       — Next.js 15, UI only. No database access, no API routes of its own.
/backend-python — FastAPI. The whole backend, one process:
                   • public /api/* — auth + all CRUD (Firm, Client, Matter, Deadline,
                     Notification, Template, Search, Document upload/download);
                   • AI — Document Ingestion (SD-004) and AI Chat (SD-005), which /api
                     reaches in-process (app/infrastructure/ai_bridges.py), never over HTTP.
/database       — Drizzle schema + migrations. A CLI tool, not an application — the
                   backend maps onto what it produces, never creates/alters tables itself.
/uploads        — local-dev file storage (repo root, gitignored), standing in for
                   Cloudflare R2 (System Architecture §6).
```

Until 2026-11-20 auth/CRUD lived in a separate Spring Boot service (`/backend-java`) that called Python over HTTP. It was ported to Python with response-for-response parity (08-Technology-Decision-Log.md); don't reintroduce a second backend language without a real reason.

Every read/write from the frontend goes over HTTP to the backend. Never add a database driver or an `/api` route back into `/frontend` — that boundary is the point of the split (explicit user requirement, System Architecture §1).

## 1. Coding Conventions

### Frontend (`/frontend`)
**Package manager:** pnpm only — a mixed lockfile breaks the Railway build (§4).
**Language:** TypeScript, strict mode. `any` requires a one-line comment explaining why it couldn't be typed.
**Framework:** Next.js 15 App Router. Server Components by default; `'use client'` only where real interactivity or a browser API is needed.
**Calling the backend:** Server Components use `lib/api/java-client.ts`'s `javaFetch()` (forwards the session cookie explicitly — server-to-server calls don't do this automatically). Client components use `lib/api/public-config.ts`'s `JAVA_API_URL_PUBLIC` with `fetch(..., { credentials: 'include' })`. The "Java" in those names (and in `JAVA_API_URL`/`NEXT_PUBLIC_JAVA_API_URL`) is historical — they point at the Python backend on `:8080`. Never call `fetch("/api/...")` with a relative path — there's no local API to hit.
**Naming:** Files/folders kebab-case (`matter-detail.tsx`). Components PascalCase. Functions/variables camelCase. Env vars `SCREAMING_SNAKE_CASE`.

### Backend (`/backend-python`)
**Layering** — `app/domain/` → `app/application/` → `app/infrastructure/` → `app/web/`, the same for CRUD and AI:
- `domain/` — frozen dataclasses + static factory/validation methods enforcing business rules (`Matter.create(...)` raises `InvalidMatterError`). Zero framework dependencies, zero I/O. Status enums are `StrEnum`s whose values equal the Postgres enum labels byte-for-byte.
- `application/` — services plus ports as `typing.Protocol` classes: `ports.py` (AI) and `crud_ports.py` (CRUD). One service class per entity (`MatterService`, `ClientService`, ...). Multi-repository writes that must be all-or-nothing go through the `UnitOfWork` port (`with self.unit_of_work.transaction():`).
- `infrastructure/` — real adapters. DB access is raw SQL via SQLAlchemy `text()` (not the ORM), originally to control the `::vector` cast explicitly (§4) and kept for CRUD for consistency. CRUD repositories live in `infrastructure/persistence/` and open connections through `persistence/connection.py`'s `connection()`, which joins the request's open `SqlUnitOfWork` transaction if there is one.
- `web/` — `web/api/*_routes.py` are the public `/api` routers; `web/api/container.py` is the composition root; `web/api/common.py` holds error shapes, the session cookie, serializers and strict param parsing. `web/chat_router.py` / `web/ingest_router.py` are the AI module's own routers — called in-process by `ai_bridges.py`, and **not mounted** on the app unless `EXPOSE_INTERNAL_AI_ROUTES=true` (they have no auth of their own).
- **Auth is explicit, per handler:** call `resolve_lawyer(request)` at the top of every route that needs auth — this is the real authorization boundary (§4), not a global middleware.

**Response contract:** the frontend was built against the former Java API, so `/api` keeps its exact shapes — `{ error: { code, message } }` for handled errors, Spring's `{ timestamp, status, error, path }` for framework-level 400/404/405/415/500, instants as ISO-8601 with a trailing `Z` (`common.instant()`), dates as `YYYY-MM-DD`. Use the helpers in `common.py` rather than hand-building responses.
**Settings:** `app/infrastructure/config.py` (loads `backend-python/.env`). `OPENAI_API_KEY` has no default by design.
**Virtual env:** `.venv`, activate with `source .venv/Scripts/activate` (Windows).

### Database (`/database`)
Drizzle schema (`schema/schema.ts`) + migrations, TypeScript, pnpm. Any schema change: edit `schema.ts`, run `pnpm db:generate`, review the generated SQL, `pnpm db:migrate` against local Postgres, **then** update the SQL/mappers in `backend-python` (`infrastructure/persistence/mappers.py` and the affected repositories) to match. `/database` is the single source of truth for the schema (System Architecture §3).

## 2. Testing Conventions

**What needs a test:**
- Every Business Rule (BR-001–009) gets at least one test proving it's *enforced* — e.g. BR-001 as a `domain` test (`tests/domain/test_client_matter.py`), BR-003/BR-008 as `application`-layer tests against in-memory fakes (`tests/application/test_matter_client_services.py`), and confirmed live against the real DB (`tests/web/test_api.py`).
- Every API endpoint gets one happy-path test and one isolation test (BR-008: a cross-Firm request returns 404, not 403) — `tests/web/test_api.py`.
- The AI Assistant's grounding rules (06-AI-Architecture.md §3) get dedicated coverage — a below-threshold query never calls the LLM; an unverifiable citation gets stripped or regenerated, never kept silently.

**What kind:**
- pytest throughout. Domain tests are plain. Application-layer tests use hand-written in-memory fakes implementing the Protocol ports (`tests/application/crud_fakes.py` for CRUD) — not mocks, so the fakes' behavior stays honest and readable.
- API tests (`tests/web/`) use FastAPI's `TestClient` against the real Postgres (like `tests/infrastructure/`), with ingestion swapped for a recorder so no model/LLM loads. Construct `TestClient(app)` without `with` so the hourly scheduler isn't started.
- No UI snapshot tests. A small set of Playwright end-to-end tests covering the 5 UX journeys (03-UX-Product-Design.md §3, J1–J5), run against all services live — these are what "Done" is defined against in the Build Plan.
- AI Assistant answers are non-deterministic — never assert exact text. Assert structural properties: a citation exists and resolves to a real document, the "not found" path is taken when nothing clears the relevance threshold, etc.

**Where tests live:** `backend-python/tests/`, mirroring `app/` (`domain/`, `application/`, `infrastructure/`, `web/`). `/tests` (its own `package.json`, pnpm) for Playwright, specs in `/tests/e2e`. Pattern established by the first real one (`document-status-polling.spec.ts`): use Playwright's `request` API context to set up test data (register, create Client/Matter) fast and directly against the backend, then hand that session's cookie to `page` and use the real browser only for the behavior under test.

## 3. Commands

Postgres must be running first (`docker compose up -d` from the repo root).

| Task | Command | Where |
|---|---|---|
| Start frontend dev server | `pnpm dev` | `/frontend` |
| Type-check frontend | `pnpm typecheck` | `/frontend` |
| Start backend | `uvicorn app.main:app --port 8080 --reload` (inside `.venv`) | `/backend-python` |
| Run backend tests | `pytest` | `/backend-python` |
| Generate a migration | `pnpm db:generate` | `/database` |
| Apply migrations | `pnpm db:migrate` | `/database` |
| Inspect data (GUI) | `pnpm db:studio` | `/database` |
| Run end-to-end tests | `pnpm test:e2e` | `/tests` |

Each component's `package.json`/`requirements.txt` is the contract for its own scripts — this table just says where to run them from.

## 4. Known Gotchas

Add to this list the moment something costs more than a few minutes to figure out — a one-line entry here saves the next session from rediscovering it.

- **Use pnpm, not npm/yarn**, in `/frontend` and `/database`. A mixed lockfile produces different dependency resolutions locally vs. on a deploy build, causing "works on my machine" failures.
- **"Today" is the UTC calendar day, everywhere in the backend** — use `app/domain/clock.py`'s `utc_today()`/`utc_now()`, never `date.today()`/`datetime.now()`. This machine's local zone is IST (`Asia/Calcutta`, which Postgres's tzdata also rejects as a session TimeZone), and the old Java backend ran its JVM in UTC, so BR-009's past-date check, the Upcoming widget's cutoff and the hourly reminder scan have always used UTC days. Mixing in local dates silently shifts those boundaries by 5.5 hours. Likewise never do day math with a Postgres `::date` cast (it depends on the session TimeZone) — compute day boundaries in Python (`search_repositories.py`, `notification_repository.py`).
- **Cookie scoping is domain-based, not port-based** — a cookie the backend (`localhost:8080`) sets for `localhost` is also sent by the browser to the frontend (`localhost:3000`). This makes local dev auth work without special configuration, but don't assume it generalizes to production, where frontend and backend will likely be on different real domains needing a shared parent domain or a reverse proxy.
- **`resolve_lawyer(request)` in each `/api` handler is the real authorization boundary** — not `middleware.ts`'s cookie-presence check in the frontend (that's just a fast-redirect hint). A route that forgets to call it is reachable unauthenticated even though the frontend "protects" the page.
- **Session tokens are hashed before storage, passwords are hashed with bcrypt — don't mix these up.** `password_hash` uses bcrypt (slow, salted, resists brute force on low-entropy human passwords, cost 12). `sessions.token_hash` uses plain SHA-256 (fast, no salt) because the token itself is 256 bits of randomness — already unguessable, so a slow hash would just waste CPU on every request. The lawyers table holds both `$2a$` (Spring-era) and `$2b$` (Node/Python-era) bcrypt hashes; both verify. `bcrypt>=5` raises on passwords over 72 bytes — `BcryptPasswordHasher` turns that into a 400 on register/change-password and a plain non-match on login, and treats a malformed stored hash as a non-match, never a 500.
- **A service class with a method named `list` breaks `list[...]` annotations later in the same class body** (`TypeError: 'function' object is not subscriptable` at import) — the method shadows the builtin inside the class namespace. Every application service with a `list()` method starts with `from __future__ import annotations`; keep it when adding one.
- **`chat_messages` is a tree — delete it set-based, never row by row.** `parent_id` is `ON DELETE CASCADE`, so deleting a parent already removes its children. The old Java/Hibernate `deleteByMatterId` loaded rows and deleted them one at a time, hit an already-cascaded child (`StaleStateException`) and rolled back — every Matter/Client delete with chat history 500'd, and because file deletion isn't transactional, document files were already gone from `/uploads` while their rows survived. `SqlChatMessageRepository.delete_by_matter` is one `DELETE ... WHERE matter_id = :id`; keep it that way. Regression test: `tests/web/test_api.py::test_deleting_a_matter_with_branched_chat_history_cascades_regression`.
- **No FK-level `ON DELETE CASCADE` exists from `clients` → `matters`, or from `matters` → `documents`/`deadlines`/`chat_messages`/`matter_views`** (`database/schema/schema.ts` — plain `references()`, so Postgres defaults to `NO ACTION`). Only `document_chunks` (off `documents`), `notifications` (off `deadlines`), and `citations.chat_message_id` (off `chat_messages`) cascade at the DB level; `citations.document_id` is `SET NULL`, deliberately, so a citation survives its source Document being deleted. Deleting a Client or Matter must delete children in dependency order inside one `UnitOfWork` transaction (`MatterService.delete_cascade`, reused by `ClientService.delete_cascade`).
- **`SqlChatMessageRepository` is the CRUD layer's one deliberate touch of AI-owned data** — a bulk delete-by-matter for the cascade, nothing else. Reading chat content from the CRUD side goes through the `ChatGateway` port (`InProcessChatGateway`), not SQL.
- **The AI module's routers return `JSONResponse` for business errors (404/400/422/502) rather than raising** — `ai_bridges._call()` maps those status codes to `ChatMessageNotFoundError`/`InvalidEditTargetError`/`NoReadyDocumentsError`/`AssistantUnavailableError`, exactly as the old Java `HttpChatGateway` mapped HTTP codes. If you add a new chat route, add its mapping there too.
- **An exhausted/invalid OpenAI key shows up as `502 ASSISTANT_UNAVAILABLE` on chat with no traceback in the log** — `ChatService` catches the LLM exception and the router returns a `JSONResponse`. Before debugging retrieval, test the key directly (a one-line `openai` call); on 2026-11-20 the account had `insufficient_quota`. Ingestion degrades gracefully instead (image captions are skipped, the Document still reaches `ready`).
- **The vanilla `postgres:16` Docker image doesn't ship pgvector at all** — `CREATE EXTENSION vector` fails with "extension is not available," not just "not enabled." Needed the `pgvector/pgvector:pg16` image instead (a drop-in replacement); `docker compose up -d` recreates the container against the same named volume, so existing data survives the swap. *Then* run `CREATE EXTENSION IF NOT EXISTS vector;` before the first migration touching `document_chunks`.
- **Swapping the Postgres Docker image can trigger a collation-version mismatch warning** (`database was created using collation version X, but the operating system provides version Y`) even though queries still work. Fix properly rather than ignore: `ALTER DATABASE legal_ai_assistant REFRESH COLLATION VERSION;`.
- **Python: `x or default` silently uses `default` when `x` is an empty container** (`{}`, `[]`, `""` are all falsy) — caught a real test bug this way (`storage_files or {"key1": ...}` ignored an intentionally-empty `{}` passed to force a failure case). Use `x if x is not None else default` when empty-but-present is a meaningful, distinct case from absent.
- **Installing `sentence-transformers` or `easyocr` via plain `pip install`** pulls the default PyPI `torch` wheel, which includes CUDA libraries this machine doesn't need (much larger, slower install). Install CPU-only `torch` first, explicitly: `pip install --index-url https://download.pytorch.org/whl/cpu torch`, then install the rest normally — both libraries share that one `torch` install.
- **EasyOCR's download progress bar crashes on Windows with `UnicodeEncodeError: 'charmap' codec can't encode character '█'`** (the `█` block character, under the default `cp1252` console encoding) the first time it downloads a model. Run with `PYTHONIOENCODING=utf-8` set, at least for that first run (models are cached to disk after).
- **`pypdf` can't read AES-encrypted PDFs without the `cryptography` package** — raises `DependencyError: cryptography>=3.1 is required for AES algorithm`. This isn't a rare edge case: many corporate/bank/financial-system-generated PDFs (e.g. HR portals, PF/bank statements) apply AES encryption with an empty user password purely for permissions (no visible password prompt), so this hits real documents constantly. `cryptography` is in `backend-python/requirements.txt` — don't drop it as "unused."
- **Don't set a Redis eviction policy (e.g. `allkeys-lru`) on the BullMQ Redis instance**, once background jobs exist. An eviction policy can silently drop queued jobs under memory pressure — a Document would sit in "processing" forever with no error, directly violating the "no failure is invisible" rule (System Architecture §7).
- **Cloudflare R2's S3-compatible client needs `region: 'auto'`.** A real AWS region string causes a signature-mismatch error on upload/download that looks like a credentials problem but isn't.
- **Server Components can't touch `window`/browser-only APIs.** Anything with real interactivity needs `'use client'` — plan the component boundary before writing it, not after hitting the error.
- **Killing a stray `next dev` (or Uvicorn) process on Windows can orphan processes holding file locks or ports** — e.g. `node.exe` holding `.next/trace`, causing the next `pnpm dev` to crash with `EPERM`, or an old `python.exe` still listening on `:8080` and answering with old code. Fix: `tasklist //FI "IMAGENAME eq node.exe"` (or `python.exe`), force-kill leftovers (`taskkill //F //PID ...` or PowerShell `Stop-Process -Force`), confirm `netstat -ano | grep :8080` is empty, clear the lock target (`rm -rf .next`) before restarting.
- **On Windows, Git Bash's `mv` can fail with `Permission denied` on a directory that PowerShell's `Move-Item -Force` handles without complaint.** If `mv` fails on a directory with no obvious lock holder, try `Move-Item` before assuming something's actually locked.
- **Drizzle has no built-in `vector` column type.** Define `DocumentChunk.embedding` with `customType` (or a pgvector helper package) rather than letting `db:generate` infer it.
- **This machine has only ~7.3 GB RAM.** The backend (torch + the embedding model once loaded) plus the Next.js dev server fit, but start Next.js constrained: `NODE_OPTIONS="--max-old-space-size=512" pnpm dev` (otherwise SWC can fail with `The paging file is too small for this operation to complete`).
- **`plainto_tsquery` ANDs every significant word together** — a natural-language question that includes even one word absent from the source text (e.g. asking "how **long**" when the document says "the term is 36 months") matches **zero** rows, silently zeroing out keyword search's contribution to hybrid retrieval. AI Chat uses `to_tsquery('english', replace(plainto_tsquery('english', :query)::text, ' & ', ' | '))` to OR the same stemmed/stopword-filtered terms. (Client/Matter *name* search keeps plain AND semantics on purpose.)
- **`uvicorn --reload` on this machine has silently served stale code at least twice** — the StatReload log line ("Reloading...") appears, `/health` even returns `200`, but the worker never finished swapping in the new module (or swapped in a half-edited state) and kept answering with pre-edit logic, with no error anywhere. Bit hard during the 2026-08-20 chat-context debugging session. When verifying a real backend fix against the live dev server, don't trust that a reload happened — kill every `python.exe` serving the port and relaunch `uvicorn` fresh, or run without `--reload` for a debugging session and restart manually on every change.
- **Ingestion is designed to run exactly once per Document, right after upload — re-running it on an already-`ready` Document duplicates its `document_chunks` rows** (it only ever `INSERT`s). Harmless in the real app, but a trap when manually re-triggering ingestion while debugging (via `EXPOSE_INTERNAL_AI_ROUTES=true` + `POST /ingest/{id}`, or calling `ingest_router.ingest()` from a shell) — `DELETE FROM document_chunks WHERE document_id = ...` first, or the Matter's retrieval silently sees every chunk twice.
- **`pypdf`'s `page.images` can report the same embedded image on every page of a PDF, not just the one page it's actually drawn on** — the page tree can share one `/Resources` dictionary across pages. A 60-page PDF with 3 real diagrams reported all 3 on all 60 pages, and OCR-ing every one turned a ~1-minute ingestion into a 5+ minute hang. `extraction.py`'s PDF path deduplicates by SHA-256 content hash across the whole document before OCR-ing — always do this for any code that walks `page.images` per-page.
- **A port (Protocol) can have more than one hand-written fake implementing it** (e.g. `InMemoryChatGateway` in `tests/application/crud_fakes.py` and the AI tests' own fakes) — adding a method to a port means updating every fake. Run the whole `pytest` suite after changing a port, not just the tests for the service that owns it.
- **The Playwright specs in `/tests/e2e` predate the latest UI redesign** (commits `5a204ed`–`c8e6189`): they wait for `#document-upload-input` and a literal "Ready" badge, neither of which the current UI renders (the Matter panel shows a status label only *while* a Document isn't ready, and only the open Chat panel polls for readiness). They fail before reaching any backend behavior — update the selectors before treating an e2e failure as a backend regression.
