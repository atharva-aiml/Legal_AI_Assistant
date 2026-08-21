# CLAUDE.md — Legal AI Assistant

Conventions for working in this codebase. Traces to [05-System-Architecture.md](05-System-Architecture.md) (stack, modules, schema) and [04-Design-System.md](04-Design-System.md) (UI tokens). This file is living — when a gotcha bites, add it to §4 immediately, don't wait for a cleanup pass.

## 0. Repo Layout — Three Services

```
/frontend       — Next.js 15, UI only. No database access, no API routes of its own.
/backend-java   — Spring Boot. Owns auth + all CRUD ("rest of the backend"): Firm, Client,
                   Matter, Deadline, Notification, Template, Search.
/backend-python — FastAPI. Owns AI: Document Ingestion (V0.3, done), AI Chat (V0.4, not yet).
/database       — Drizzle schema + migrations. A CLI tool, not an application — owned by
                   neither backend's runtime. Both backends map onto what it produces.
/uploads        — shared local-dev file storage (repo root). Java writes, Python reads —
                   both point at the same directory, matching how they'd both read/write R2
                   directly in production (System Architecture §6). Gitignored.
```

Every read/write from the frontend goes over HTTP to Java (today) or Python (from V0.3). Never add a database driver or an `/api` route back into `/frontend` — that boundary is the point of this split (explicit user requirement, System Architecture §1).

## 1. Coding Conventions

### Frontend (`/frontend`)
**Package manager:** pnpm only — a mixed lockfile breaks the Railway build (§4).
**Language:** TypeScript, strict mode. `any` requires a one-line comment explaining why it couldn't be typed.
**Framework:** Next.js 15 App Router. Server Components by default; `'use client'` only where real interactivity or a browser API is needed.
**Calling the backend:** Server Components use `lib/api/java-client.ts`'s `javaFetch()` (forwards the session cookie explicitly — server-to-server calls don't do this automatically). Client components use `lib/api/public-config.ts`'s `JAVA_API_URL_PUBLIC` with `fetch(..., { credentials: 'include' })`. Never call `fetch("/api/...")` with a relative path — there's no local API to hit anymore.
**Naming:** Files/folders kebab-case (`matter-detail.tsx`). Components PascalCase. Functions/variables camelCase. Env vars `SCREAMING_SNAKE_CASE`.

### Java (`/backend-java`)
**Build tool:** Maven via the wrapper (`./mvnw`), not a system-wide Maven install — this machine has no admin rights to install one, and `mvnw` self-bootstraps per-project with none needed (§4).
**Layering** (`com.legalai.backend.*`), same domain → application → infrastructure → web pattern the original TypeScript code established, kept on the Java side:
- `domain/` — plain records + static factory methods enforcing business rules (`Matter.create(...)` throws `InvalidMatterException`). Zero framework dependencies, zero I/O.
- `application/<entity>/` — a repository **interface** (the port) + one `@Service` class per entity consolidating what create/list/get/rename would otherwise be as four separate use-case classes — idiomatic Spring, not a functionality change.
- `infrastructure/persistence/` — `@Entity` classes + Spring Data JPA repositories + one adapter class per entity implementing the application-layer interface. `ddl-auto=validate` always — Hibernate maps onto `/database`'s schema, never generates or alters it.
- `web/controller/` — `@RestController`s. Call `CurrentLawyerResolver.resolve(request)` explicitly at the top of every method that needs auth — this is the real authorization boundary, not a global filter (§4).

### Python (`/backend-python`)
Same domain → application → infrastructure → web layering as Java, in `app/domain/`, `app/application/`, `app/infrastructure/`, `app/web/` — established for real in V0.3 (Document Ingestion), reuse it for V0.4 (AI Chat) too, don't invent a different structure per language. Ports are `typing.Protocol` classes (`app/application/ports.py`), not ABCs — application-layer tests use hand-written in-memory fakes against those Protocols, same spirit as Java's `InMemoryMatterRepository`. DB access is raw SQL via SQLAlchemy `text()` (not the ORM layer) specifically to control the `::vector` cast explicitly — see CLAUDE.md §4's pgvector note. Virtual env: `.venv`, activate with `source .venv/Scripts/activate` (Windows).

### Database (`/database`)
Drizzle schema (`schema/schema.ts`) + migrations, TypeScript, pnpm. Any schema change: edit `schema.ts`, run `pnpm db:generate`, review the generated SQL, `pnpm db:migrate` against local Postgres, **then** update the entity classes in `backend-java` (and `backend-python`, once it touches the DB) to match. `/database` is the single source of truth for the schema regardless of how many backend languages read it (System Architecture §3).

## 2. Testing Conventions

**What needs a test:**
- Every Business Rule (BR-001–008) gets at least one test proving it's *enforced* — e.g. BR-001 as a `domain` test (`MatterTest`), BR-008 as an `application`-layer test against the in-memory fake (`MatterServiceTest`), and ideally confirmed live against the real DB too (this project's habit: curl + `psql` regression passes after every slice).
- Every API endpoint gets one happy-path test and one isolation test (BR-008: a cross-Firm request returns 404, not 403).
- The AI Assistant's grounding rules (06-AI-Architecture.md §3) get dedicated coverage once Python's AI Chat exists — a below-threshold query never calls the LLM; an unverifiable citation gets stripped or regenerated, never kept silently.

**What kind:**
- Java: JUnit 5. Domain tests are plain (no Spring context). Application-layer tests use a hand-written in-memory fake implementing the repository interface (see `MatterServiceTest`'s `InMemoryMatterRepository`) — not Mockito mocks, so the fake's behavior stays honest and readable.
- Python: pytest, same domain/application split (`tests/domain/`, `tests/application/`, mirroring `app/`).
- No UI snapshot tests. A small set of Playwright end-to-end tests covering the 5 UX journeys (03-UX-Product-Design.md §3, J1–J5), run against all services live — these are what "Done" is defined against in the Build Plan.
- AI Assistant answers are non-deterministic — never assert exact text. Assert structural properties: a citation exists and resolves to a real document, the "not found" path is taken when nothing clears the relevance threshold, etc.

**Where tests live:** Java: `src/test/java`, mirroring `src/main/java`'s package structure. Python: `tests/`, mirroring `app/`. `/tests` (its own `package.json`, pnpm) for Playwright, specs in `/tests/e2e`. Pattern established by the first real one (`document-status-polling.spec.ts`): use Playwright's `request` API context to set up test data (register, create Client/Matter) fast and directly against Java, then hand that session's cookie to `page` and use the real browser only for the actual behavior under test — don't drive the whole setup flow through UI clicks when an API call does the same thing in a fraction of the time.

## 3. Commands

Three services — start what you need. Postgres must be running first (`docker compose up -d` from the repo root) for either backend to connect.

| Task | Command | Where |
|---|---|---|
| Start frontend dev server | `pnpm dev` | `/frontend` |
| Type-check frontend | `pnpm typecheck` | `/frontend` |
| Start Java backend | `./mvnw spring-boot:run` | `/backend-java` |
| Run Java tests | `./mvnw test` | `/backend-java` |
| Start Python backend | `uvicorn app.main:app --port 8000 --reload` (inside `.venv`) | `/backend-python` |
| Run Python tests | `pytest` | `/backend-python` |
| Generate a migration | `pnpm db:generate` | `/database` |
| Apply migrations | `pnpm db:migrate` | `/database` |
| Inspect data (GUI) | `pnpm db:studio` | `/database` |
| Run end-to-end tests | `pnpm test:e2e` | `/tests` |

Each service's `package.json`/`pom.xml`/`requirements.txt` is the contract for its own scripts — this table just says where to run them from.

## 4. Known Gotchas

Add to this list the moment something costs more than a few minutes to figure out — a one-line entry here saves the next session from rediscovering it.

- **Use pnpm, not npm/yarn**, in `/frontend` and `/database`. A mixed lockfile produces different dependency resolutions locally vs. on a deploy build, causing "works on my machine" failures.
- **No admin rights on this machine — Maven must be the wrapper, not a global install.** `choco install maven` fails with `Access to the path ... is denied`. Spring Initializr-generated projects already include `mvnw`/`mvnw.cmd`, which self-bootstraps the correct Maven version into `~/.m2/wrapper` with no elevation needed. Always use `./mvnw`, never assume a system `mvn`.
- **This machine's JVM reports its default timezone as `Asia/Calcutta`** (a deprecated tz alias from the `en_IN` locale), which Postgres's tzdata rejects outright on connect (`FATAL: invalid value for parameter "TimeZone"`). Fixed via `-Duser.timezone=UTC` configured directly in `backend-java/pom.xml`'s `spring-boot-maven-plugin` and `maven-surefire-plugin` blocks — **must be a real JVM startup flag**; setting it in application code (even a static initializer) runs too late, because Spring's `SpringApplication.run(BackendApplication.class, ...)` passes a class literal, which per JLS 12.4.1 does not trigger `BackendApplication`'s own static initializers.
- **Postgres native enum columns (`matter_status`, `lawyer_role`) map to Java via `@JdbcTypeCode(SqlTypes.NAMED_ENUM)`** (Hibernate 6+), with the Java enum constants deliberately **lowercase** (`MatterStatus.open`, not `.OPEN`) so `Enum#name()` matches the Postgres label exactly — verified against real data via a spike before committing to this over a custom `AttributeConverter`.
- **On Windows, Git Bash's `mv` can fail with `Permission denied` on a directory that PowerShell's `Move-Item -Force` handles without complaint** — happened moving `app/api`, `app/clients`, `lib/db` during the frontend/backend split. If `mv` fails on a directory with no obvious lock holder, try `Move-Item` before assuming something's actually locked.
- **Cookie scoping is domain-based, not port-based** — a cookie the Java backend (`localhost:8080`) sets for `localhost` is also sent by the browser to the frontend (`localhost:3000`). This makes local dev auth work without special configuration, but don't assume it generalizes to production, where frontend and backend will likely be on different real domains needing a shared parent domain or a reverse proxy.
- **`CurrentLawyerResolver.resolve(request)`'s call in each Java controller method is a UX/security shortcut's opposite** — it's the *real* authorization boundary, not `middleware.ts`'s cookie-presence check in the frontend (that's just a fast-redirect hint). A Java endpoint that forgets to call it is reachable unauthenticated even though the frontend "protects" the page.
- **Session tokens are hashed before storage, passwords are hashed with BCrypt — don't mix these up.** `password_hash` uses BCrypt (slow, salted, resists brute force on low-entropy human passwords, cost 12). `Session.token_hash` uses plain SHA-256 (fast, no salt) because the token itself is 256 bits of `SecureRandom` — already unguessable, so a slow hash would just waste CPU on every request for no security benefit.
- **The vanilla `postgres:16` Docker image doesn't ship pgvector at all** — `CREATE EXTENSION vector` fails with "extension is not available," not just "not enabled." Needed the `pgvector/pgvector:pg16` image instead (a drop-in replacement); `docker compose up -d` recreates the container against the same named volume, so existing data survives the swap. *Then* run `CREATE EXTENSION IF NOT EXISTS vector;` before the first migration touching `document_chunks`.
- **Swapping the Postgres Docker image can trigger a collation-version mismatch warning** (`database was created using collation version X, but the operating system provides version Y`) even though queries still work. Fix properly rather than ignore: `ALTER DATABASE legal_ai_assistant REFRESH COLLATION VERSION;`.
- **Python: `x or default` silently uses `default` when `x` is an empty container** (`{}`, `[]`, `""` are all falsy) — caught a real test bug this way (`storage_files or {"key1": ...}` ignored an intentionally-empty `{}` passed to force a failure case). Use `x if x is not None else default` when empty-but-present is a meaningful, distinct case from absent.
- **Installing `sentence-transformers` or `easyocr` via plain `pip install`** pulls the default PyPI `torch` wheel, which includes CUDA libraries this machine doesn't need (much larger, slower install). Install CPU-only `torch` first, explicitly: `pip install --index-url https://download.pytorch.org/whl/cpu torch`, then install the rest normally — both libraries share that one `torch` install.
- **EasyOCR's download progress bar crashes on Windows with `UnicodeEncodeError: 'charmap' codec can't encode character '█'`** (the `█` block character, under the default `cp1252` console encoding) the first time it downloads a model. Run with `PYTHONIOENCODING=utf-8` set, at least for that first run (models are cached to disk after).
- **`pypdf` can't read AES-encrypted PDFs without the `cryptography` package** — raises `DependencyError: cryptography>=3.1 is required for AES algorithm`. This isn't a rare edge case: many corporate/bank/financial-system-generated PDFs (e.g. HR portals, PF/bank statements) apply AES encryption with an empty user password purely for permissions (no visible password prompt), so this hits real documents constantly. `cryptography` is now in `backend-python/requirements.txt` — don't drop it as "unused."
- **Don't set a Redis eviction policy (e.g. `allkeys-lru`) on the BullMQ Redis instance**, once background jobs exist. An eviction policy can silently drop queued jobs under memory pressure — a Document would sit in "processing" forever with no error, directly violating the "no failure is invisible" rule (System Architecture §7).
- **Cloudflare R2's S3-compatible client needs `region: 'auto'`.** A real AWS region string causes a signature-mismatch error on upload/download that looks like a credentials problem but isn't.
- **Server Components can't touch `window`/browser-only APIs.** Anything with real interactivity needs `'use client'` — plan the component boundary before writing it, not after hitting the error.
- **Killing a stray `next dev` (or Java/Uvicorn process) on Windows can orphan processes holding file locks** — e.g. `node.exe` holding `.next/trace`, causing the next `pnpm dev` to crash with `EPERM`. Fix: `tasklist //FI "IMAGENAME eq node.exe"` (or the relevant image name), force-kill leftovers via PowerShell `Stop-Process -Force`, then clear the lock target (`rm -rf .next`) before restarting.
- **Drizzle has no built-in `vector` column type.** Define `DocumentChunk.embedding` with `customType` (or a pgvector helper package) rather than letting `db:generate` infer it.
- **Spring Boot 4.1's Jackson is Jackson 3.x, under the `tools.jackson.*` package/Maven-groupId — not `com.fasterxml.jackson.databind.*`.** `com.fasterxml.jackson.databind.ObjectMapper` doesn't exist on this classpath at all; use `tools.jackson.databind.ObjectMapper` (run `./mvnw dependency:tree | grep -i jackson` if unsure what's actually pulled in). `jackson-annotations` stayed at the old `com.fasterxml.jackson.annotation` package, so only `databind`/`core` moved — a mixed-package import is the usual symptom. Jackson 3 also folds java.time (de)serialization directly into `jackson-databind`; there is no separate `jackson-datatype-jsr310`/`JavaTimeModule` to register.
- **This machine has only ~7.3 GB RAM — running the Java backend and the Next.js dev server together at default heap settings can OOM.** Symptoms: Spring Boot dies with `insufficient memory... Native memory allocation (mmap) failed to map ... bytes for Failed to commit metaspace`; Next.js's SWC binary fails with `The paging file is too small for this operation to complete`. Start both with constrained heaps: `MAVEN_OPTS="-Xmx384m" ./mvnw spring-boot:run -Dspring-boot.run.jvmArguments="-Xmx256m"` for Java, `NODE_OPTIONS="--max-old-space-size=512" pnpm dev` for the frontend. A failed launch under memory pressure can also leave orphaned `java.exe`/`node.exe` processes behind (same family as the existing Windows-orphan-process gotcha below) — check `Get-CimInstance Win32_Process` for stray `spring-boot:run`/`next dev` command lines and kill them before retrying, or the retry will fight the orphan for the same port/memory.
- **`plainto_tsquery` ANDs every significant word together** — a natural-language question that includes even one word absent from the source text (e.g. asking "how **long**" when the document says "the term is 36 months") matches **zero** rows, silently zeroing out keyword search's contribution to hybrid retrieval. Use `to_tsquery('english', replace(plainto_tsquery('english', :query)::text, ' & ', ' | '))` to OR the same stemmed/stopword-filtered terms instead — reuses Postgres's own linguistic analysis rather than reimplementing tokenization.
- **`uvicorn --reload` on this machine has silently served stale code at least twice** — the StatReload log line ("Reloading...") appears, `/health` even returns `200`, but the actual worker never finished swapping in the new module (or swapped in an intermediate half-edited state) and kept answering with pre-edit logic, with no error anywhere. Bit hard during the 2026-08-20 chat-context debugging session: two separate rounds of "the fix isn't working" turned out to be this, not the code. When verifying a real backend fix against the live dev server, don't trust that a reload happened — `taskkill //F //PID <all python.exe>` and relaunch `uvicorn` fresh (with or without `--reload`) before testing, or just run without `--reload` for the rest of a debugging session and restart manually on every change.
- **`POST /ingest/{document_id}` is designed to run exactly once, right after upload — calling it again on an already-`ready` Document duplicates its `document_chunks` rows** (it only ever `INSERT`s, no delete-existing-first step, because Java never re-triggers it in the real product flow). Harmless in the real app, but a real trap when manually re-triggering ingestion from a script/shell while debugging — `DELETE FROM document_chunks WHERE document_id = ...` before re-running it, or the Matter's retrieval silently sees every chunk twice (doubled citations, distorted `FULL_CONTEXT_CHAR_CAP` math).
- **`pypdf`'s `page.images` can report the same embedded image on every page of a PDF, not just the one page it's actually drawn on** — a real PDF-structure quirk where the page tree shares/inherits one `/Resources` dictionary across pages, so `page.images` (which just enumerates that dictionary) sees every image on every page regardless of whether that page's own content stream actually draws it. Bit a real user upload hard: a 60-page PDF with 3 real embedded diagrams reported all 3 on all 60 pages (180 "occurrences"), and OCR-ing every one turned a ~1-minute ingestion into a 5+ minute hang that read as a failed upload. `extraction.py`'s PDF path now deduplicates by SHA-256 content hash across the whole document before OCR-ing — always do this for any code that walks `page.images` per-page rather than assuming one occurrence = one real page.
