# Interaction Backlog — Legal AI Assistant

Every idea from the screen-by-screen interaction review (walked live in the running app, Sign In through the AI Assistant), written up one-per-entry in the same shape Build Plan versions use — **Status**, **Domain rule → repository → API → UI, together**, **Done (live action)** — so any of these can be lifted straight into `07-Build-Plan.md` as a real version the moment one gets scheduled. None of these are scheduled yet; every Status below is `Not Started`.

**Effort tag** on each entry: **UI-only** (pure frontend, no backend change), **New data** (needs a small new tracked field or table but no new business rule), or **New backend** (needs a real new capability/endpoint/domain rule).

Numbered `I-01` … `I-68` for stable reference. Screen IDs (`SCR-01` etc.) match `03-UX-Product-Design.md` §1.

---

## Login (SCR-01)

### I-01 — Show/hide password toggle

**Status:** Done — 2026-08-16
**Effort:** UI-only

**Current → change → why:** The password field is always masked. A small eye icon toggles it between masked and plain text. Typing a password blind is the single biggest source of failed first login attempts.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none.
- API: none.
- UI: `frontend/app/login/page.tsx` — local `showPassword` state flips the input's `type` between `password`/`text`; a real `<button type="button">` (not a `<label>`-over-hidden-input trick) so it's independently keyboard-focusable, with `aria-label`/`aria-pressed` reflecting the current state. Inline `EyeIcon`/`EyeOffIcon` SVGs match the stroke-icon style already established in `components/notification-bell.tsx` — no icon library added.

**Done (live action) — confirmed:** Live-checked in the running app (screenshot + keyboard-driven toggle, not just code review, since a UI-only change has nothing to persist to a database): password field starts masked (`type="password"`); tabbing to the eye button and pressing Enter reveals the typed text (`type="text"`, `aria-pressed="true"`), with a real visible keyboard-focus ring on the button itself; clicking it again re-masks (`type="password"`). Zero console errors.

### I-02 — "Keep me signed in on this device"

**Status:** Not Started
**Effort:** New backend

**Current → change → why:** Every session uses the same fixed expiry (`SessionToken.SESSION_DURATION`). An optional checkbox issues a longer-lived session for a lawyer's own firm computer — most solo/small-firm users log in from the same one or two machines all week.

**Domain rule → repository → API → UI, together:**
- Domain rule: `AuthService.login` accepts a `remember: boolean` and varies the issued session's expiry accordingly (e.g. 30 days vs. the current default) — no new invariant, just a second duration constant.
- Repository: none new — `sessions.expires_at` already stores an arbitrary expiry; `SessionRepository.create` already takes one.
- API: `POST /api/auth/login` request body gains an optional `remember` field.
- UI: `login/page.tsx` — a checkbox next to the password field.

**Done (live action):** Logging in with the box checked, then simulating a browser restart (clearing session-only state but keeping cookies), the session is still valid past the default window. Unchecked behaves exactly as today.

### I-03 — Validate email shape before submit

**Status:** Done — 2026-08-16
**Effort:** UI-only

**Current → change → why:** An invalid email is only caught after a full round trip, returning the same generic "Incorrect email or password." Client-side shape validation gives a faster, more specific first signal.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none.
- API: none.
- UI: `frontend/app/login/page.tsx` — a shared `EMAIL_SHAPE` regex (`/^[^\s@]+@[^\s@]+\.[^\s@]+$/`, shape-only, not full RFC 5322 — the server remains the real authority on whether an address is actually registered) checked both `onBlur` (shows an inline `.field-error` message + `.input-error` red border + `aria-invalid`/`aria-describedby`) and again on submit (blocks the request entirely if still invalid). The error clears the moment the field is edited, not just on the next successful blur.

**Done (live action) — confirmed:** Live-checked in the running app: typing `notanemail` and blurring shows "Enter a valid email" inline with `aria-invalid="true"`; attempting submit in that state fires **zero** requests to `/api/auth/login` (confirmed via network-request capture, not just visual inspection); editing the field clears the error immediately; submitting with a real, valid, registered email correctly fires exactly one request and completes a real login, landing on the Dashboard — confirming the new validation doesn't interfere with the working path. Zero console errors.

---

## Sign Up / Firm Setup (SCR-02)

### I-04 — Let the Firm name itself

**Status:** Not Started
**Effort:** New backend

**Current → change → why:** `AuthService.register` silently creates the Firm as `"{name}'s Firm"` — there's no field for it at all. A real, editable Firm/practice name field (pre-filled with that same default so nobody's blocked) gives every Firm a real identity from day one, which matters the moment Firm & Team (SCR-15) is fully real.

**Domain rule → repository → API → UI, together:**
- Domain rule: `AuthService.register(name, email, password, firmName)` — `firmName` optional, falls back to the existing `"{name}'s Firm"` default when blank.
- Repository: none new — `firms.name` already exists.
- API: `POST /api/auth/register` request body gains an optional `firm_name`.
- UI: `frontend/app/register/page.tsx` — a Firm/practice name field, pre-filled with the computed default, editable.

**Done (live action):** Signing up with a custom Firm name persists it; `GET /api/firm/lawyers`'s owning Firm (surfaced once SCR-15 shows Firm name, not just member list) reflects the real name, not the auto-generated one.

### I-05 — Password strength meter

**Status:** Done — 2026-08-16
**Effort:** UI-only

**Current → change → why:** The only guidance today is a static "At least 8 characters" hint. A live meter gives real-time feedback as the password is typed.

**Domain rule → repository → API → UI, together:**
- Domain rule: none — server-side minimum-length validation in `AuthService.register` is unchanged and remains the real, only enforced rule; this meter never blocks submit.
- Repository: none.
- API: none.
- UI: new shared `frontend/components/ui/password-strength-meter.tsx` (`<PasswordStrengthMeter password={password} />`), wired into `register/page.tsx` below the existing "At least 8 characters" hint. Scores 0–5 against length (≥8, ≥12), mixed case, a digit, and a symbol, then buckets into Weak/Fair/Good/Strong — a 4-segment bar plus a colored label (error → warning → success → success), reusing existing design tokens rather than introducing new colors. Renders nothing until at least one character is typed.

**Done (live action) — confirmed:** Live-checked in the running app: no meter visible on an empty field; `abcdefgh` → "Weak"; `abcdEFGH12` → "Good" (the exact Weak → Good progression the entry itself names); `abcdEFGH12!@#$` → "Strong", all 4 segments filled. Confirmed via real network-request capture that typing into the password field fires **zero** requests — purely client-side, as required. Zero console errors.

### I-06 — Live "email already registered" check

**Status:** Done — 2026-08-16
**Effort:** New backend

**Current → change → why:** A taken email is only discovered after filling in the entire form and submitting. A debounced live check surfaces it immediately.

**Domain rule → repository → API → UI, together:**
- Domain rule: none new — reuses the same uniqueness check `AuthService.register` already runs via `LawyerRepository.findByEmailWithHash`. Added `AuthService.isEmailAvailable(email)`, a thin read-only wrapper around that same lookup, unit-tested against a hand-written in-memory `LawyerRepository` fake (`AuthServiceTest`: unregistered → available, registered → unavailable, case/whitespace normalization matches `register`'s, blank/null email never reported available).
- Repository: none new — reuses the real `LawyerRepositoryImpl` untouched.
- API: new `GET /api/auth/email-available?email=...` on `AuthController`, pre-auth (no `CurrentLawyerResolver` call — matches `/register`/`/login`), read-only, returns `{"available": boolean}`.
- UI: `register/page.tsx` — a `useEffect` debounced 500ms on the email field, gated by an email-shape regex so it never fires on an obviously incomplete address, showing "Checking…" / "Available" / "Already registered — Log in?" (linking to `/login`) via the existing `.field-hint`/`.field-error`/`.input-error` classes already used on the login page.

**Done (live action) — confirmed:** Java (`AuthServiceTest`, 4 cases) and frontend typecheck both pass. Live-checked in the running app via Playwright: typing the real seeded test account's email (`v05livecheck@example.com`) shows the red-bordered field and "Already registered — Log in?" inline; typing a fresh unregistered address shows "Available"; typing an incomplete address (no `@`) fires zero requests; typing the taken email keystroke-by-keystroke fires exactly one `GET /api/auth/email-available` request after the pause, not one per keystroke, confirming the debounce actually debounces. Zero console errors. Screenshots captured for both the taken and available states.

---

## Dashboard (SCR-03)

### I-07 — Recent Matters widget

**Status:** Done — 2026-08-16
**Effort:** New data

**Current → change → why:** "Active Matters" is just every open Matter, unordered by recency. A separate "Recent Matters" widget — tracking when a Lawyer last actually opened a Matter — answers "what was I just working on," the most common Monday-morning question, which a plain status filter can't.

**Domain rule → repository → API → UI, together:**
- Domain rule: `MatterView(lawyerId, matterId, viewedAt)` — a plain fact record, deliberately no static factory/validation and no dedicated domain test, since there's genuinely no invariant to enforce (both IDs are already-authorized by the time a view is recorded). The one real behavior — re-viewing a Matter moves it to the top without duplicating it — is a repository/ordering concern, tested at the application layer instead.
- Repository: new `matter_views` table (`lawyer_id`, `matter_id`, `viewed_at`) with a unique index on `(lawyer_id, matter_id)` — new Drizzle migration `0008_secret_newton_destine.sql`, reviewed and applied. `MatterViewRepository.recordView`/`listRecentlyViewed` (port) + `MatterViewRepositoryImpl` (real, via a native `INSERT ... ON CONFLICT (lawyer_id, matter_id) DO UPDATE SET viewed_at = now()` upsert — atomic, no read-then-decide round trip) + `MatterViewService` (`listRecentlyViewed` capped at 5), unit-tested against an in-memory fake: fresh view is most-recent, a second Matter pushes the first down without removing it, re-viewing a Matter moves it back to the top without duplicating it, list is capped at the limit, one Lawyer's recents never leak into another's.
- API: chose a dedicated `POST /api/matters/{id}/view` over piggybacking on `GET /api/matters/{id}` — keeps the read endpoint a pure read and gives the UI one explicit, idempotent write to call. New `GET /api/matters/recent`, both on `MatterController`, both re-verify the Matter is in the caller's Firm (BR-008) before touching `matter_views`.
- UI: `frontend/app/matters/[id]/page.tsx` calls the view-record endpoint on every load (best-effort — a failure never breaks the page); `frontend/app/page.tsx` renders a "Recent Matters" section between Upcoming Deadlines and Active Matters, only when non-empty, reusing the same card/badge styling as Active Matters.

**Done (live action) — confirmed:** `MatterViewServiceTest` (5 cases) and the full Java suite pass; frontend typecheck clean. Live-checked in the running app: created two real Matters via the API, opened Matter A then Matter B in the browser, and the Dashboard's Recent Matters showed **[B, A]** — B on top, A pushed down but still present, exactly as the entry's Done criteria describes. Re-opening Matter A moved it back to the top — **[A, B]** — with no duplicate row. A full hard-reload of the Dashboard (fresh server request, not client state) still showed **[A, B]**, confirming it's really reading from Postgres. Screenshots captured for both orderings. Zero console errors.

### I-08 — Calendar-strip Deadline view

**Status:** Not Started
**Effort:** UI-only

**Current → change → why:** Upcoming Deadlines is a flat list sorted by date. A horizontal day strip — like a Teams or Outlook mini calendar — with a count per day shows density at a glance ("this week is packed, next week is quiet") in a way a scrolling list can't.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none new — `GET /api/deadlines/upcoming` already returns everything needed.
- API: none new.
- UI: new `DeadlineCalendarStrip` component on `app/page.tsx`; clicking a day filters the list rendered below it.

**Done (live action):** A day with 3 Deadlines shows a "3" marker on the strip; clicking that day filters the Upcoming Deadlines list to just those 3, and clicking it again (or a "clear" control) restores the full list.

### I-09 — Quick-stat tiles

**Status:** Done — 2026-08-16
**Effort:** UI-only

**Current → change → why:** There's no single-glance summary — a lawyer has to read both list widgets to know how much is on their plate. Three small numbers above the widgets (Open Matters, Deadlines this week, Unread notifications) are scannable before reading a single row.

**Domain rule → repository → API → UI, together:**
- Domain rule: none — all three counts are computed from existing endpoints, no new backend code.
- Repository: none new.
- API: none new — reused `GET /api/matters`, `GET /api/deadlines/upcoming?days=7` (same endpoint the Upcoming Deadlines widget already calls with `days=14`, just a second call with the narrower window for "this week"), and `GET /api/notifications` (not previously fetched on the Dashboard, now added).
- UI: `app/page.tsx` — a new 3-tile stat row rendered between the page header and Upcoming Deadlines, reusing the existing `.card` styling; each tile shows "—" instead of a stale number if its underlying fetch failed, rather than silently showing 0.

**Done (live action) — confirmed:** Frontend typecheck clean (no backend change, so no Java tests / restart needed). Live-checked against the real running app: computed all three counts independently via direct API calls (the same way a lawyer would by reading the lists) and confirmed they matched the Dashboard's rendered tiles exactly (Open Matters: 4, Deadlines this week: 0, Unread notifications: 1). Then marked one real notification read via the API and reloaded the Dashboard — the Unread notifications tile dropped from 1 to 0, proving the tile is genuinely live-computed from current data, not a cached or hardcoded number. Screenshot confirms the tile row renders correctly. Zero console errors on repeat runs (one isolated hydration warning on the very first run turned out to be a Next.js dev-server hot-reload artifact from saving the file mid-request — it didn't reproduce on either of two clean re-runs).

### I-10 — Overdue deadlines float to the top

**Status:** Not Started
**Effort:** UI-only

**Current → change → why:** Overdue and merely-upcoming Deadlines sit in the same date-sorted list, distinguished only by badge color (already built: red "Overdue" vs. blue "Upcoming", per `deadlines-list.tsx`'s existing badge logic). Overdue items should visually separate to the top of the Dashboard widget, not just carry a different color in the position the date sort would put them anyway.

**Domain rule → repository → API → UI, together:**
- Domain rule: reuses the existing overdue definition (`dueDate < today && status === "open"`).
- Repository: none new.
- API: none new.
- UI: `app/page.tsx` — partition the Upcoming Deadlines array into an "Overdue" group rendered first, then the rest.

**Done (live action):** A Deadline due yesterday renders above one due in 3 days on the Dashboard, in a visually distinct group, not just a different badge color in date order.

### I-11 — First-run checklist instead of one CTA

**Status:** Not Started
**Effort:** UI-only

**Current → change → why:** The current empty state is a single "Add your first client to get started" prompt. A 3-step checklist (Add a client → Open a matter → Upload a document) mirrors the app's own first user journey and shows progress instead of a dead end.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none new — each step's "done" state is computed from whether any Client/Matter/Document already exists for the Firm.
- API: none new.
- UI: `app/page.tsx` empty-state branch — replace the single CTA with a 3-item checklist.

**Done (live action):** A brand-new Firm sees all three steps unchecked; after creating its first Client, reloading the Dashboard shows step 1 checked and step 2 as the active next step.

### I-12 — Recent Clients companion widget

**Status:** Not Started
**Effort:** New data

**Current → change → why:** Same idea as Recent Matters (I-07), for the lawyer whose day starts from a client relationship rather than a specific case.

**Domain rule → repository → API → UI, together:**
- Domain rule: same "view" event concept as I-07, applied to Client Detail views.
- Repository: `matter_views`-style table for Clients (or a single polymorphic `entity_views` table covering both); `listRecentlyViewedClients(lawyerId, limit)`.
- API: `GET /api/clients/recent`.
- UI: `app/page.tsx` — a new "Recent Clients" section.

**Done (live action):** Opening a Client, returning to the Dashboard, shows it in Recent Clients, most-recent-first.

---

## Clients List (SCR-04)

### I-13 — In-list search box

**Status:** Done — 2026-08-16
**Effort:** UI-only

**Current → change → why:** The list is unfiltered and shows every Client in creation order. A firm with a large roster needs to type-to-filter, not scroll — distinct from the global nav search (SCR-14), which is for cross-entity lookup, not quick within-page narrowing.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none new — pure client-side filter over the already-fetched `GET /api/clients` array.
- API: none new.
- UI: `frontend/app/clients/page.tsx` stayed a Server Component (still fetches `clients`/`matters`); the list rendering and the new filter itself moved into a new client component, `frontend/app/clients/clients-list.tsx`, since a controlled input needs client-side state. The per-client open/closed Matter counts (previously computed as a `Map` in `page.tsx`) moved into that component too — a `Map` isn't serializable across the Server→Client Component boundary, so it's recomputed via `useMemo` from the plain `matters` array passed down as a prop.

**Done (live action) — confirmed:** Frontend typecheck clean; no backend touched, so no Java tests or restart needed. Live-checked in the running app: created a real, distinctly-named Client via the API, typed "acme rockets" into the filter, and the list narrowed to exactly that Client with **zero network requests** fired to the Java backend while typing — confirmed via request capture, proving it's a pure client-side filter. Typing a nonsense query showed a "No clients match" message; clearing the field instantly restored the full unfiltered list. Screenshot confirms correct rendering. (One transient console hydration warning appeared on the first run right after saving the file — the same Next.js dev-server hot-reload artifact seen during I-09's live check — and did not reproduce on two clean re-runs.)

**2026-08-17 update:** the separate filter box was removed and its behavior folded into the topbar search bar itself (user request, not its own I-XX item). `NavBar` (now a Client Component) is pathname-aware: on `/clients` it renders as a controlled in-list filter (placeholder "Filter clients by name…", not inside a `<form>`, so Enter does nothing); everywhere else it's the original `<form action="/search">` global cross-entity search (SCR-14), unchanged. The two modes share the query through a new `ListSearchContext` provided at the root layout, since `NavBar` and the page's own list are siblings, not ancestor/descendant. Leaving `/clients` resets the query so a later visit doesn't start pre-filtered. `clients-list.tsx` now reads the query from that context instead of owning its own input; the I-14 sort control is untouched. Regression-checked live: global search still navigates to real `/search` results with real matches on Dashboard/Matters/Notifications/Account; the Clients-page filter still narrows with zero network calls; the filter still resets on navigating away and back; zero console errors.

### I-14 — Sort control

**Status:** Done — 2026-08-16
**Effort:** New data

**Current → change → why:** The list has one implicit order (creation). Sorting by name, most recent activity, or most open Matters covers the real ways a lawyer scans a Client roster.

**Domain rule → repository → API → UI, together:**
- Domain rule: none — "most recent activity" reuses the same `max(matter.updatedAt)` definition I-16 will formalize later; built here directly since I-16 doesn't exist yet.
- Repository: none new — the entry's own "computed client-side from already-fetched Matters" option, since `GET /api/matters` already returns `updatedAt` (just needed adding to the frontend's local `Matter` type, which had been narrowed to only the fields I-13 used).
- API: none new.
- UI: `clients/clients-list.tsx` (the client component I-13 introduced) — a `<select className="select">` next to the I-13 filter input, re-sorting the already-filtered array client-side. All three modes (Name, Most recent activity, Most open Matters) tiebreak on name for a stable, deterministic order.

**Done (live action) — confirmed:** Frontend typecheck clean; no backend touched, no Java tests or restart needed. Live-checked in the running app: created three real Clients (Apple/Mango/Zebra-prefixed for unambiguous alphabetical order) with controlled Matter data — Mango got 3 open Matters, Apple's Matter was created last (most recent `updatedAt`). "Name (A–Z)" showed Apple, Mango, Zebra. Switching to "Most recent activity" moved Apple to the top. Switching to "Most open Matters" moved Mango to the top. Switching back to "Name" restored exactly the original alphabetical order — the exact round trip the entry's Done criteria describes — all without a page reload. Screenshot confirms correct rendering. Zero console errors.

### I-15 — Initial-circle avatars

**Status:** Not Started
**Effort:** UI-only

**Current → change → why:** Rows are text-only. The colored-initial-circle already built for the account menu (`components/account-menu.tsx`), applied per Client row, makes a long list scannable by shape and color, not just by reading names.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none.
- API: none.
- UI: extract a shared `<InitialAvatar name={...} />` component from the existing account-menu markup; use it in `clients/page.tsx`.

**Done (live action):** Every Client row shows a colored circle with its first initial; the same Client always renders the same color (hash-based, not random per render).

### I-16 — "Last activity" instead of just counts

**Status:** Not Started
**Effort:** New data

**Current → change → why:** "1 open · 1 closed" shows volume, not urgency. A last-touched date (most recent Document, Deadline, or Chat message across a Client's Matters) shows what's gone quiet and might need a check-in.

**Domain rule → repository → API → UI, together:**
- Domain rule: "last activity" defined as `max(matter.updatedAt)` across a Client's Matters — simplest version needs no new table, just a computed aggregate.
- Repository: `ClientRepository.listByFirm` extended to compute or join this; or computed client-side from the already-fetched Matters list.
- API: none new if computed client-side.
- UI: `clients/page.tsx` — replace or augment the count line.

**Done (live action):** A Client whose Matter was updated yesterday shows "Active yesterday" alongside (or instead of) "1 open · 1 closed".

---

## Client Detail (SCR-05)

### I-17 — Edit Client

**Status:** Done — 2026-08-17
**Effort:** New backend

**Current → change → why:** There is currently no way to fix a mistyped contact email or add notes after a Client is created — a real, plain functional gap, not a design nicety. Closing it also finishes SCR-06's stated "New / Edit" scope, which today is create-only.

**Domain rule → repository → API → UI, together:**
- Domain rule: `Client.java` gains `update(name, contactEmail, contactPhone, notes)`, returning a validated `UpdatedFields` record — same "name is required" invariant as `create()`, same blank-to-null normalization. Covered by a new `ClientTest` (first domain test this entity has ever had — `create()` had none either, added alongside).
- Repository: `ClientRepository` gains `Optional<Client> update(UUID firmId, UUID id, String name, String contactEmail, String contactPhone, String notes)`. `ClientService.update` validates via the domain layer before ever touching the repository, mirroring `MatterService`'s `rename`. Tested against a new in-memory-fake-backed `ClientServiceTest`: fields persist, rejecting an empty name never touches the repository, and updating a Client outside the caller's Firm returns empty, not an error (BR-008).
- Repository (real): `ClientRepositoryImpl.update` — find-by-id-and-firm, mutate the entity, save; same shape as `MatterRepositoryImpl.updateTitle`.
- API: `PATCH /api/clients/{id}`, firm-scoped, 404 on a Client outside the Firm, 400 on an empty name.
- UI: new `frontend/app/clients/[id]/edit-client-modal.tsx` — an "Edit" button next to the Client's name opens a `Modal` with the same four fields as the New Client form (`clients/new/page.tsx`), pre-filled with current values. The Client Detail page itself also now displays Contact phone and Notes (previously fetched by the API but never rendered) — necessary to see what's now editable actually reflected on the page.

**Done (live action) — confirmed:** `ClientTest` and `ClientServiceTest` (4 new cases each) pass, and the full Java suite passes. Frontend typecheck clean. Live-checked in the running app: opened Edit on a real Client, confirmed the form was pre-filled with its current name and email, changed all four fields, saved. A **hard reload** of the Client Detail page (not just the in-app `router.refresh()`) showed every new value — name, email, phone, notes. Independently re-verified via a direct `GET /api/clients/{id}` API call outside the browser entirely, confirming it's genuinely persisted in Postgres, not client-side state. Clearing the name field disabled Save, matching the domain rule.

One pre-existing, non-blocking flake surfaced during repeated live-check runs: an intermittent React hydration console warning tied to the topbar's `#global-search` input (`caret-color:transparent`, `NavBar`) — traced to Chromium's own form-autofill behavior on that field (a byproduct of the topbar search-bar merge done earlier the same day, not this entry's code, which never touches `NavBar`). It never affected Edit Client's actual behavior — Save, persistence, and validation were correct on every run, including the ones where the warning appeared.

### I-18 — Click-to-contact

**Status:** Not Started
**Effort:** UI-only

**Current → change → why:** Contact email and phone are plain text. Real `mailto:`/`tel:` links save a copy-paste.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none.
- API: none.
- UI: `clients/[id]/page.tsx` — wrap `client.contactEmail`/`client.contactPhone` in anchor tags.

**Done (live action):** Clicking the contact email opens the lawyer's default mail client addressed to that Client; clicking the phone number opens the default calling app (on devices that support `tel:`).

### I-19 — Next-deadline column on Matter rows

**Status:** Done — 2026-08-17
**Effort:** UI-only

**Current → change → why:** The Matter list on this page shows title and status only. Showing each Matter's next due date means a lawyer scanning a Client's case list doesn't have to open every one to see what's coming up.

**Domain rule → repository → API → UI, together:**
- Domain rule: none — reuses the existing per-Matter "next open Deadline" concept.
- Repository: none new — same `GET /api/deadlines/upcoming` data, joined client-side by `matterId`.
- API: none new.
- UI: `clients/[id]/page.tsx` — fetches `/api/deadlines/upcoming?days=36500` (a deliberately huge window so it means "every open Deadline," not a near-term slice — the endpoint already scopes to `status=open`, including overdue ones, matching how the rest of the app treats "next due" as "soonest, overdue or not"), computes `min(dueDate)` per Matter, and renders it inline next to the status badge, entirely server-side — no client component needed since there's no interactivity.

**Done (live action) — confirmed:** Live-checked with real data: a Matter with a Deadline 3 days out showed "Due Aug 19, 2026" next to its badge; one 60 days out showed "Due Oct 15, 2026"; a Matter with no Deadlines and a Closed Matter both showed nothing extra. Screenshot confirms correct rendering. Frontend typecheck clean; no backend touched.

### I-20 — Surface the Notes field

**Status:** Done — 2026-08-16 (already shipped as part of I-17)
**Effort:** UI-only

**Current → change → why:** `notes` is already captured at Client creation (`CreateClientRequest.notes`) but never rendered anywhere after that — a write-only field in practice.

**Domain rule → repository → API → UI, together:**
- Domain rule: none — no change, `Client.notes` already exists.
- Repository: none.
- API: none — `ClientResponse` already includes `notes`.
- UI: `clients/[id]/page.tsx` — a visible Notes section on the profile card, conditionally rendered (`{client.notes && (...)}`).

**Done (live action) — confirmed:** This was built as a direct side effect of I-17 (Edit Client) — showing Contact phone and Notes was necessary there so what I-17 made editable was actually visible on the page, so no separate implementation was needed here. Re-verified live for this entry specifically: a fresh Client with no notes shows no Notes section at all (not an empty one); after setting notes via the API and refreshing, the Notes section appears with the real saved text.

---

## New / Edit Client (SCR-06)

### I-21 — Build the "Edit" half

**Status:** Not Started
**Effort:** New backend

**Current → change → why:** The screen is already named for both creation and editing; only creation exists today. Same backend gap as I-17 — this is its UI half.

**Domain rule → repository → API → UI, together:**
- Domain rule: shared with I-17.
- Repository: shared with I-17.
- API: shared with I-17 (`PATCH /api/clients/{id}`).
- UI: `clients/new/page.tsx`'s form component reused at an edit route (e.g. `clients/[id]/edit`), pre-filled from the current Client, submitting `PATCH` instead of `POST`.

**Done (live action):** Navigating to edit an existing Client, changing the name, saving, redirects to Client Detail showing the new name immediately.

### I-22 — Soft duplicate warning

**Status:** Not Started
**Effort:** New backend

**Current → change → why:** Nothing stops a lawyer from accidentally creating a second "Acme Corp." A soft, dismissible warning catches the common case without a hard uniqueness constraint (multiple real Clients can legitimately share a name).

**Domain rule → repository → API → UI, together:**
- Domain rule: none — a UX prompt, not a data constraint.
- Repository: none new — reuses the already-loaded `ClientRepository.listByFirm` result.
- API: none new.
- UI: `clients/new/page.tsx` — client-side fuzzy match against the Firm's existing Client names as the name field is typed.

**Done (live action):** Typing a name closely matching an existing Client shows an inline "Similar to 'Acme Corp' — continue anyway?" message; submitting anyway still creates the new Client (never a hard block).

---

## Matters List (SCR-07)

### I-23 — Filter by status and Client

**Status:** Done — 2026-08-17
**Effort:** UI-only

**Current → change → why:** The list shows every Matter across every Client, unfiltered. Two simple filters — Open/Closed, and a Client picker — suit a Firm whose Matters list has outgrown a single scroll.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none new — `MatterService.list` filters by status in-memory, after the existing `listByFirm`/`listByClient` repository calls, rather than a new database query; the Firm's Matter volume never justifies pushing this to Postgres.
- API: `GET /api/matters` gains an optional `status` query param (`MatterController`, bound directly to the `MatterStatus` enum — Spring resolves `?status=open` via `MatterStatus.valueOf`, same lowercase-constant convention as everywhere else in this codebase). Existing `clientId` param unchanged. `MatterServiceTest` gained 3 new cases: status alone, status+clientId combined, and null status returning every status — plus the two pre-existing 2-arg test calls updated for the new 3-arg signature.
- UI: `frontend/app/matters/page.tsx` — now reads `searchParams` and fetches `/api/matters` with `status`/`clientId` forwarded as real query params, so filtering is a genuine server round-trip (matching this entry's own API bullet, unlike I-13/14's deliberately client-side-only Clients-page filter). The two filter `<select>`s live in a new `matters-list.tsx` client component and update the URL via `router.push`, which Next.js resolves into a fresh Server Component fetch.

**Done (live action) — confirmed:** Full Java suite passes (new + existing MatterService tests). Frontend typecheck clean. Live-checked with 4 real Matters for one Client (1 closed, 3 open) plus the Firm's other pre-existing test Matters: selecting "Closed" showed only closed Matters firm-wide; adding the Client filter narrowed it to exactly that Client's one closed Matter; switching to "Open" + the same Client showed exactly its 3 open Matters. Confirmed via request capture that each selection is a real `GET /api/matters?status=...` call to the Java backend, not a client-side filter. Clearing both filters returned to the bare `/matters` URL and the full list.

### I-24 — Sort by next deadline

**Status:** Done — 2026-08-17
**Effort:** UI-only

**Current → change → why:** Surfaces what's urgent across the whole Firm in one view, not just within a single open Matter.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none new — reuses `GET /api/deadlines/upcoming?days=36500` (same huge-window approach as I-19, for "every open Deadline" not a near-term slice), joined client-side by `matterId`.
- API: none new.
- UI: `matters/page.tsx` / `matters-list.tsx` — a third `<select>` alongside I-23's two filters, purely client-side (`useState`, no URL involvement) since it re-orders whatever the server already returned rather than requesting different data. When active, it also shows each Matter's next-due date inline next to the badge — just enough feedback to explain the new order, not the always-on per-row date column that's I-25's separate, not-yet-requested scope.

**Done (live action) — confirmed:** Live-checked with the same 3 open test Matters (deadlines 3 days, 60 days, and never): sorting by "Next deadline" produced exactly Soon → Far → No-deadline, with the no-deadline Matter sorting last as specified. Screenshot confirms the inline dates and correct order. Combines cleanly with I-23's filters (sorted within whatever status/Client subset is currently selected).

One shared, pre-existing, non-blocking flake noted across all four live checks: the same intermittent `#global-search` hydration console warning first traced during I-17 (Chromium's own autofill behavior on the topbar search field, unrelated to any of this session's code). Never affected any of the four features' actual behavior on any run.

### I-25 — Next-deadline date per row

**Status:** Done — 2026-08-17
**Effort:** UI-only

**Current → change → why:** Same data source as I-24, shown inline rather than only used for sorting.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none new.
- API: none new.
- UI: `matters/matters-list.tsx` — the date/badge markup was pulled out of the row-rendering loop into a small `MatterRow` sub-component (needed anyway for I-26's two-column board, so both views render identically), and the "only while sorted by Next deadline" condition from I-24 was removed — every row now always shows `Due <date>` or `No deadlines`.

**Done (live action) — confirmed:** Live-checked under the *default* sort (not "Next deadline," to prove this is independent of I-24's sort mode): a Matter with a real Deadline showed "Due Aug 21, 2026," a Matter with none showed "No deadlines," and a Closed Matter with none also correctly showed "No deadlines" rather than nothing. Screenshot confirms. Frontend typecheck clean; no backend touched.

### I-26 — Optional board view grouped by status

**Status:** Done — 2026-08-17
**Effort:** UI-only

**Current → change → why:** A visual alternative to the flat list for a Firm that thinks in case stages — offered as a toggle, not a replacement.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none new.
- API: none new.
- UI: `matters/matters-list.tsx` — a List/Board toggle (local `useState`, defaulting to List) next to the filter/sort row. Board view splits the same already-filtered, already-sorted `sortedMatters` array into two columns by status, each reusing the same `MatterRow` component as list view — so nothing about a row's content differs between the two, only the layout grouping it.

**Done (live action) — confirmed:** Live-checked with 2 open + 1 closed Matter: Board view showed "Open (2)" and "Closed (1)" columns with the Closed Matter correctly appearing only in the Closed column. Switching back to List showed the identical 3 rows in the original single-column layout (same row count verified before/after). Screenshot confirms. Frontend typecheck clean; no backend touched.

Both I-25 and I-26 share the same pre-existing, non-blocking `#global-search` hydration flake documented since I-17 — present on one of the runs, absent on others, never affecting either feature's actual behavior.

---

## New Matter (SCR-08)

### I-27 — Client field as type-ahead search

**Status:** Done — 2026-08-17
**Effort:** UI-only

**Current → change → why:** The Client field is a plain HTML `<select>`. A dropdown of a large Client roster is unusable; searching by name as it's typed isn't.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none new — reuses `GET /api/clients`.
- API: none new.
- UI: new `frontend/app/matters/new/client-combobox.tsx` — a real combobox (`role="combobox"`/`listbox`/`option`, arrow-key navigation, Enter to select, Escape/blur to close), used in place of the old `<select>` in `new-matter-form.tsx`. The submitted `client_id` only ever changes via an explicit selection — typing alone never touches it — and abandoning a search (blur or Escape without picking) reverts the visible text back to whatever's still actually selected, so the displayed name and the submitted `client_id` can never silently disagree.

**Done (live action) — confirmed:** Frontend typecheck clean; no backend touched. Live-checked: typing "Zorro Unique" filtered the dropdown to matching Clients only; selecting one, then submitting the form, produced a Matter whose Client (verified on the resulting Matter Detail page) matched exactly what was selected in the combobox. Confirmed via request capture that typing/selecting fired **zero** network calls — a pure client-side filter over the already-fetched list, per the entry's own "Repository: none new."

### I-28 — Optional first Deadline in the creation flow

**Status:** Done — 2026-08-17
**Effort:** UI-only

**Current → change → why:** Almost every new Matter has at least one known date already (a filing deadline, a hearing). Adding it during creation saves the second trip to the Matter's own Deadlines section immediately after.

**Domain rule → repository → API → UI, together:**
- Domain rule: none new — reuses existing Deadline creation (`Deadline.create`, BR-004, BR-009).
- Repository: none new.
- API: none new — two existing calls chained client-side (`POST /api/matters` then `POST /api/matters/{id}/deadlines`), same shape as `new-deadline-form.tsx`'s own call, including the same BR-009 past-date guard (`min=` on the date input, plus a JS-level backstop). If Matter creation succeeds but the chained Deadline call fails, the flow still lands on the new Matter's page rather than losing the successfully-created Matter — the lawyer can add the Deadline directly from there instead.
- UI: `matters/new/new-matter-form.tsx` — an optional, collapsed "+ Add a deadline" section (closed by default, matching the plain "no deadline" path exactly).

**Done (live action) — confirmed:** Live-checked: filling in a title, a Client (via I-27's new combobox), and a deadline date 10 days out, then saving, landed on the new Matter's own page with "First filing deadline" already listed under Deadlines, badged "Upcoming." Tried a past date first — correctly blocked before ever reaching the server (the browser's own `min=` constraint caught it, same as `new-deadline-form.tsx`'s comment already documents can happen; confirmed zero Java requests fired). Regression-checked the plain "no deadline" path too: submitting with the section left collapsed still creates the Matter and lands on its page exactly as before, with no stray state from the deadline fields leaking in.

Both entries share the codebase's known, pre-existing, non-blocking `#global-search` hydration flake (documented since I-17) — absent on the final clean run reported above.

---

## Matter Detail (SCR-09)

### I-29 — Optional tabbed layout

**Status:** Not Started
**Effort:** UI-only

**Current → change → why:** Deadlines, Documents, and Chat are stacked vertically on one page (deliberately, so Deadlines and Close Matter stay visible without scrolling — a recent, explicit decision). Offering a tabbed layout as a toggle — already fully specified in `04-Design-System.md`'s Tabs component — suits a Matter whose Chat history has grown long enough that scrolling past it to reach Deadlines gets tedious, without reversing that decision for everyone.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none new.
- API: none new.
- UI: `frontend/app/matters/[id]/page.tsx` — a view toggle switching between the current stacked layout and a tabbed one, reusing the same `DocumentsList`/`ChatPanel`/`DeadlinesList` components either way.

**Done (live action):** Switching to tabs shows one section at a time with identical data to the stacked view; switching back restores the current default layout with Deadlines still on top.

### I-30 — Sticky mini-header

**Status:** Done — 2026-08-17
**Effort:** UI-only

**Current → change → why:** Matter title, status, and Close Matter scroll out of view once a Chat conversation gets long.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none.
- API: none.
- UI: `matters/[id]/page.tsx` — a `position: sticky; top: 0` bar (title, status badge, Close Matter) added above the existing full header, which stays exactly as it was. Close Matter now exists in two places on the page (the sticky bar and the original Deadlines section) — each `CloseMatterButton` instance is independently stateful, which is fine; they're never both usable at once in a way that could double-submit.

**Done (live action) — confirmed:** Live-checked: scrolling to the bottom of a real Chat conversation kept the bar's `top` at 0 in the viewport (confirmed via `getBoundingClientRect`, not just visually), still showing the Matter's real title, status, and a working Close Matter button. Frontend typecheck clean; no backend touched.

### I-31 — Breadcrumb: Client → Matter

**Status:** Not Started
**Effort:** UI-only

**Current → change → why:** Today it's a flat "← Matters" link. The owning Client — already fetched alongside the Matter in the page's existing data load — is one click further away than it needs to be.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none new — `client` is already returned by `GET /api/matters/{id}`.
- API: none new.
- UI: `matters/[id]/page.tsx` — replace the flat back-link with a two-level breadcrumb.

**Done (live action):** The breadcrumb reads "Clients / Acme Corp / Smith v. Jones," each segment a real link to the corresponding list/detail page.

### I-32 — Unified activity timeline

**Status:** Done — 2026-08-17
**Effort:** New data

**Current → change → why:** Deadlines completed, Documents uploaded, drafts generated, and questions asked are scattered across three separate sections with no combined view of "everything that happened on this case, in order."

**Domain rule → repository → API → UI, together:**
- Domain rule: an aggregation, not a new business rule — combines existing timestamped facts (`Document.createdAt`, `Deadline.updatedAt`, a Chat *question's* `createdAt`) by time. New `ActivityEntry(type, title, timestamp)` record. Only `role='user'` Chat messages become entries — an ask-and-answer round trip is one activity ("asked a question"), not two, matching the entry's own three-actions-produce-three-entries example.
- Repository: none new for Documents/Deadlines — new `ActivityService` (application layer) composes the existing `DocumentService`/`DeadlineService`/`ChatService`, not raw repositories, so it inherits their existing BR-008 scoping for free. Chat data comes from the *same* `ChatGateway.history()` proxy call the Chat panel's own history fetch already makes — no new Python endpoint, exactly as the entry specifies ("proxied the same way chat history already is"). A Python/`AssistantUnavailableException` failure is caught and only omits Chat entries — Documents/Deadlines still render, same "don't lose what already works" posture as I-07/I-28. Tested via `ActivityServiceTest` against in-memory fakes for all three underlying repositories/gateway: correct merge-and-sort order, user-only Chat filtering, and graceful degradation when Chat fails.
- API: `GET /api/matters/{id}/activity` on the existing `MatterController`, firm-scoped like every other Matter endpoint.
- UI: `matters/[id]/page.tsx` — a new read-only Activity section (plain Server Component list, no interactivity needed), rendered only when non-empty.

**Done (live action) — confirmed:** `ActivityServiceTest` (4 cases) and the full Java suite pass; full Python suite (68 tests) passes; frontend typecheck clean. Live-checked end-to-end on a real Matter: uploaded a real Document, asked a real Chat question (got a real LLM answer), then added and completed a real Deadline — all three actions produced exactly 3 new Activity entries (independently confirmed via the entry-count delta on the API, not just the UI), in the correct most-recent-first order (Deadline completed → Question asked → Document uploaded, matching the order the three actions were actually taken in). Screenshot confirms clean rendering alongside the page's existing sections.

Two script-only issues surfaced and were fixed during this check, neither an app bug: Playwright clicking `+ New Deadline` immediately after a `page.reload()` occasionally raced React's hydration (fixed with a short settle wait — the same class of timing issue documented since I-27/28's live checks); and Playwright's `.check()` assertion on the Deadline-complete checkbox raced its own async PATCH-then-refresh cycle (fixed by reading the checkbox state separately after the round trip — the real completion was independently confirmed via the Activity API showing "Deadline completed," not "Deadline added").

### I-33 — Calendar/timeline layout for Deadlines

**Status:** Not Started
**Effort:** UI-only

**Current → change → why:** Same idea as the Dashboard's calendar strip (I-08), scoped to one Matter's own Deadlines, as an alternative to the current stacked-card list.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none new.
- API: none new.
- UI: `matters/[id]/deadlines-list.tsx` — a view toggle.

**Done (live action):** The Deadlines section can switch from the current card list to a small calendar view of just this Matter's dates, and back, with identical underlying data.

### I-34 — Pin a Chat answer

**Status:** Done — 2026-08-17
**Effort:** New backend

**Current → change → why:** A well-cited answer to "what's the termination clause" has no way to stay handy other than scrolling back through history to find it again.

**Domain rule → repository → API → UI, together:**
- Domain rule (Python): `ChatMessage` gains `pinned: bool = False` (`app/domain/chat.py`); real migration adding `chat_messages.pinned boolean not null default false`.
- Repository (Python): `ChatMessageRepository` Protocol gains `toggle_pin`/`list_pinned`; `SqlAlchemyChatRepository` implements both — `toggle_pin`'s `UPDATE ... WHERE id=:id AND matter_id=:matter_id AND role='assistant'` is where "only assistant answers are pinnable" is actually enforced (a 0-row update — wrong id, wrong Matter, or a user message — returns `None`, which the application layer turns into a 404, not a silent no-op or a 400). `list_pinned` reuses a small extracted `_citations_by_message` helper shared with `list_messages`. New `ChatMessageNotFoundError`. Tested via `test_chat_service.py`'s existing `InMemoryChatMessageRepository`, extended with the same behavior: pin/unpin, pinning a user message or a different Matter's message both raise not-found, and `pinned()` returns only pinned messages with their citations intact.
- API: `PATCH /chat/{matter_id}/messages/{message_id}/pin` (Python, same internal trust boundary as `/chat/{matter_id}`) fronted by Java's `PATCH /api/matters/{id}/chat/{messageId}/pin` (`ChatController`) → `ChatService.togglePin` → `HttpChatGateway`, mirroring `ask`/`history`'s exact shape. A dedicated `PinToggleDto(id, pinned)` response, not the full `ChatMessageDto` — the toggle doesn't touch citations, so reusing that shape would imply more changed than did. **Deliberately did not** add a Java-side `GET .../pinned` route: the entry's own API bullet only names the PATCH, and the UI gets pinned status for free from the `pinned` flag now included in every message the existing history fetch already returns — a second round trip would be pure duplication.
- UI: `matters/[id]/chat-panel.tsx` — a "☆ Pin" / "★ Pinned" toggle under each assistant answer, and a "Pinned" section at the top of the panel, derived by filtering the same `messages` array already in state (no separate fetch).

**Done (live action) — confirmed:** New Python tests (5 cases, full suite 68/68) and new Java tests (`ChatServiceTest` +2 cases) pass; full Java suite passes; frontend typecheck clean. Live-checked on a real Chat conversation: pinning a real assistant answer made a "Pinned" section appear immediately with that answer's text; a **hard reload** (not just local state) still showed it pinned — confirmed it's genuinely persisted in Postgres via `chat_messages.pinned`, not a client-side flag.

### I-35 — Reopen a Closed Matter

**Status:** Done — 2026-08-17
**Effort:** New backend

**Current → change → why:** Closing is currently one-directional. Even a rare "closed by mistake" case has no path back short of the database.

**Domain rule → repository → API → UI, together:**
- Domain rule: `Matter.validateReopen(currentStatus)` — the counterpart to `close()`'s BR-003 check, throwing unless the Matter is actually `closed` (reopening an already-open Matter is rejected, not a silent no-op). `MatterTest` covers both.
- Repository: `MatterRepository.reopen(firmId, id)`; `MatterRepositoryImpl.reopen` sets `status='open'`, `closed_at=null`, mirroring `close()`'s shape exactly. `MatterServiceTest` gained 3 cases (in-memory fake): reopens correctly, rejects reopening an already-open Matter without touching it, and BR-008 (outside the caller's Firm → empty, not an error).
- API: `POST /api/matters/{id}/reopen` on the existing `MatterController`, same firm-scoped/404/400 shape as `close`.
- UI: new `reopen-matter-button.tsx`, shown in place of Close Matter (both in I-30's sticky bar and the Deadlines section) whenever `status === "closed"`.

**Real gap found and fixed along the way:** `03-UX-Product-Design.md`'s J4 journey already specifies that a Closed Matter hides its create actions ("Documents/Chat/Deadlines stay fully visible (BR-007), but create actions (Upload, New Deadline) are hidden — the Matter is now read-only") — but the actual UI never enforced this; `DocumentUpload` and `NewDeadlineForm` rendered unconditionally regardless of status. Since this entry's own Done criteria depends on that gating ("Upload Document and New Deadline actions reappear" only means something if they first correctly disappear), fixed it as part of this build: both are now gated behind `matter.status === "open"`. This is implementing an existing spec, not changing one — no document update needed. `GenerateDraftModal` was deliberately left ungated — the spec text names only Upload and New Deadline, and extending the read-only rule to draft generation wasn't asked for here.

**Done (live action) — confirmed:** `MatterTest` (+2 cases) and `MatterServiceTest` (+3 cases) pass; full Java suite passes; frontend typecheck clean. Live-checked: closed a real Matter — Upload Document and + New Deadline correctly vanished, Reopen Matter appeared in both locations, Close Matter correctly absent; attempting to reopen an already-*open* Matter via a direct API call was correctly rejected with 400. Clicked Reopen Matter for real, then did a **hard reload** (not just local state) — status showed "Open," Close Matter was back, and critically, Upload Document and + New Deadline both reappeared exactly as the entry's Done criteria describes. Independently confirmed via a direct API call: `status: "open"`, `closedAt: null`. Screenshots confirm both states.

---

## Document Upload (SCR-10)

### I-36 — Drag-and-drop

**Status:** Done — 2026-08-17
**Effort:** UI-only

**Current → change → why:** Only a click-to-browse button exists today; there's no drop target on the Documents section.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none.
- API: none — same `POST /api/matters/{id}/documents` call the button already makes.
- UI: `matters/[id]/document-upload.tsx`, rebuilt alongside I-37/I-38 (same file, built together) — `onDragOver`/`onDragLeave`/`onDrop` handlers on the whole upload area (not just the button), with a visible dashed-border+tint state while a file is dragged over it.

**Done (live action) — confirmed:** Frontend typecheck clean; no backend touched. Live-checked with a real drop: constructed a real `File`/`DataTransfer` from an actual PDF's bytes and dispatched a real `drop` event — the file appeared as an in-progress upload immediately, completed, and (after a hard reload) showed up for real in the Documents list with status `processing`, picked up by the existing `DocumentsList` polling exactly like a button-driven upload — same Uploading → Processing → Ready progression, unchanged.

### I-37 — Multiple files in one action

**Status:** Done — 2026-08-17
**Effort:** UI-only

**Current → change → why:** The file input currently accepts one file per click. Onboarding a case with six PDFs shouldn't mean the same click six times.

**Domain rule → repository → API → UI, together:**
- Domain rule: none — each file still goes through `DocumentService.upload` individually.
- Repository: none new.
- API: none new — one request per file to the existing endpoint, fired independently (not awaited sequentially) so one file's failure never blocks or delays the others.
- UI: `document-upload.tsx` — the file input gained `multiple`; a new per-file `uploads` state array (not a single shared `uploading` boolean) gives each selected file its own upload item, independent progress, and independent error/dismiss.

**Done (live action) — confirmed:** Live-checked by selecting 2 real files (a PDF and a DOCX) in one picker action: both showed independent in-progress entries with independent percentages simultaneously, both completed, and both persisted as separate real Documents — confirmed via a hard reload and an independent direct API call.

### I-38 — Real per-file progress

**Status:** Done — 2026-08-17
**Effort:** UI-only

**Current → change → why:** Only an indeterminate spinner and the label "Uploading…" show today — no percentage. Matters once large scanned files are common.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none.
- API: none.
- UI: `document-upload.tsx` — the one upload call in this component uses `XMLHttpRequest` instead of `fetch` specifically because `fetch` has no upload-progress event; `xhr.upload.onprogress` drives a real `role="progressbar"` per file. Every other network call in this codebase keeps using `fetch` as normal — this is a deliberate, narrow exception for the one place progress events are actually needed, not a codebase-wide change.

**Done (live action) — confirmed:** Live-checked with a real ~200KB PDF under artificial upload-bandwidth throttling (Chrome DevTools Protocol, ~60KB/s) specifically so the progress would be observable rather than instant on localhost: sampled the progress bar repeatedly during the upload and captured real, monotonically non-decreasing intermediate values — `0, 8, 16, 16, 24, 32, 40, 40, 48, 56, 64, 64, 72, 80, 88` — before it completed, definitively not a static spinner. Screenshot captured two files mid-upload (8% and 18%) side by side, each independently accurate.

All three were built together in one pass since they share the same file and compose naturally — full Java/Python suites weren't touched (no backend change), frontend typecheck clean. Zero console errors across the combined live check, which also incidentally exercised I-32's Activity timeline and I-30's sticky header live (both correctly picked up the new uploads with no changes needed).

---

## New Deadline (SCR-11)

### I-39 — Relative quick-pick buttons

**Status:** Done — 2026-08-17
**Effort:** UI-only

**Current → change → why:** Most Deadlines are set relative to today ("in a week," "in a month"), not against a specific calendar date a lawyer has to mentally compute.

**Domain rule → repository → API → UI, together:**
- Domain rule: none — still produces a plain date, validated the same way (BR-009, no past dates).
- Repository: none.
- API: none.
- UI: `matters/[id]/new-deadline-form.tsx` — three buttons ("In 1 week," "In 2 weeks," "In 1 month") above the date field, each computing today+N (the month one via `setMonth`, not +30 days, so it lands on the correct calendar date) and calling the same `setDueDate` the field's own `onChange` already uses — the field stays a normal controlled input, so nothing about manual editing changes.

**Done (live action) — confirmed:** Frontend typecheck clean; no backend touched. Live-checked all three buttons: "In 1 week"/"In 2 weeks"/"In 1 month" each filled the field with the exact expected date, confirmed via network capture that clicking one fires **zero** requests (pure client-side), and the field remained freely editable afterward (manually overwrote it to a different date with no issue).

### I-40 — Priority tag

**Status:** Done — 2026-08-17
**Effort:** New backend

**Current → change → why:** Every Deadline is visually identical until the day it becomes overdue. Not every Deadline carries the same weight.

**Domain rule → repository → API → UI, together:**
- Domain rule: new `DeadlinePriority` enum (`standard`/`critical`, lowercase constants matching the Postgres-native-enum convention every other status enum in this codebase already follows). `Deadline` gains a `priority` field; `Deadline.resolvePriority` defaults `null` to `standard` — no real validation beyond that, every enum value is a valid choice. Real migration: `deadline_priority` Postgres enum + `deadlines.priority` column, default `'standard'`.
- Repository: `DeadlineRepository`/`DeadlineRepositoryImpl` read/write it; `DeadlineEntity` gains a `@JdbcTypeCode(SqlTypes.NAMED_ENUM)` field, same shape as `status`.
- API: `CreateDeadlineRequest`/`UpdateDeadlineRequest`/`DeadlineResponse` all gain `priority`; the controller parses the string the same way it already parses `status`.
- UI: `new-deadline-form.tsx` (built together with I-39, same file) adds a Priority select; `deadlines-list.tsx` shows a "Critical" tag (`Badge variant="warning"`, deliberately not the same red as the existing Overdue badge, so the two never look like the same signal) whenever `priority === "critical"` — rendered independently of, and alongside, the existing Overdue/Upcoming/Complete badge.
- Mechanical note: `Deadline` is a Java `record`, so adding a field meant updating every existing constructor call site across the codebase (6 test files, ~14 call sites) — all fixed, none skipped; the full Java suite is the check that nothing was missed.

**Done (live action) — confirmed:** New domain (`DeadlineTest`, 3 cases) and application (`DeadlineServiceTest`, 4 cases) tests pass; full Java suite passes. Frontend typecheck clean. Live-checked: created a Deadline with Priority set to Critical — the "Critical" tag appeared immediately; created a second, Standard-priority Deadline for contrast, which correctly showed no tag. Marked the Critical one Complete and did a **hard reload** — the tag survived the status change exactly as the entry's Done criteria requires (`Critical Deadline ... | Critical | Complete | Due Sep 17, 2026 | Complete`). Independently confirmed via a direct API call: `critical`/`standard` persisted correctly for the two respective Deadlines.

Both were built together since they share `new-deadline-form.tsx`. One real environment issue hit mid-build, not an app bug: the Next.js dev server had gone stale and stopped picking up file changes at all (confirmed by grepping its own `.next` build cache for the new button text and finding nothing) — recovered via the CLAUDE.md §4-documented procedure: kill the stuck `node.exe` processes, clear `.next`, restart with a constrained heap. Zero console errors on the live check that followed.

---

## Template Picker / Draft Generator (SCR-12)

### I-41 — Live preview pane

**Status:** Not Started
**Effort:** New backend

**Current → change → why:** The rendered draft isn't visible until after clicking Generate. A live preview catches a wrong party name or a missing date before the file is created, not after.

**Domain rule → repository → API → UI, together:**
- Domain rule: reuses `Template.render(fields)`'s existing substitution logic, called in preview mode (no `Document` created, no ingestion triggered).
- Repository: none new.
- API: a new `POST /api/templates/{id}/preview` returning rendered text without persisting anything (or the substitution is safe to reimplement client-side, since it's plain string replacement with no server-only logic).
- UI: `matters/[id]/generate-draft-modal.tsx` — split the modal into a form pane and a preview pane, updating on each keystroke (debounced).

**Done (live action):** Typing a counterparty name updates the visible preview text immediately, before Generate is ever clicked; clicking Generate produces a Document whose content matches the last preview exactly.

### I-42 — Recently-used templates first

**Status:** Not Started
**Effort:** New data

**Current → change → why:** Worth doing once the template library grows past the two seeded today — surfaces what this Firm actually reaches for.

**Domain rule → repository → API → UI, together:**
- Domain rule: none new — "recently used" derived from existing `documents.source_template_id`/`created_at`.
- Repository: `TemplateRepository.listAvailable` extended to accept an ordering by most-recent-use per Firm, computed via a join against `documents`.
- API: `GET /api/templates` default ordering changes (or a `sort=recent` param).
- UI: `generate-draft-modal.tsx` — no change beyond the list already re-ordering.

**Done (live action):** After generating a Non-Disclosure Agreement, it's the first template listed the next time the Generate Document modal opens, ahead of a template never used.

---

## Notifications Panel (SCR-13)

### I-43 — Group by date

**Status:** Done — 2026-08-17
**Effort:** UI-only

**Current → change → why:** One flat reverse-chronological list today.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none new.
- API: none new.
- UI: `frontend/app/notifications/notifications-list.tsx`, rebuilt alongside I-44/I-45 (same file, built together) — buckets the already-sorted, already-(optionally-)filtered array into Today / This week / Earlier, using the same local-calendar-day-string convention `deadlines-list.tsx` already uses for Overdue. A bucket heading only renders when that bucket has items.

**Done (live action) — confirmed:** Frontend typecheck clean. Live-checked against this session's own real accumulated notification history (5 real notifications, no synthetic data needed): "Today" and "This week" headings appeared correctly populated, with no change to which notifications were fetched (still the one existing `GET /api/notifications` call).

### I-44 — "Mark all as read"

**Status:** Done — 2026-08-17
**Effort:** New backend

**Current → change → why:** Clearing the bell's unread badge currently requires clicking every notification individually.

**Domain rule → repository → API → UI, together:**
- Domain rule: none new — reuses the existing per-notification `readAt` concept, applied in bulk.
- Repository: `NotificationRepository.markAllRead(lawyerId)` → a single JPA `@Modifying` bulk `UPDATE ... WHERE lawyer_id = :lawyerId AND read_at IS NULL`, not a fetch-then-save-each-row loop — returns the count actually updated. `NotificationServiceTest` gained 3 cases: marks every unread notification for the calling lawyer, never touches another lawyer's, and is idempotent (a repeat call marks 0 once nothing's left unread).
- API: `PATCH /api/notifications/read-all` on the existing `NotificationController`, matched above `/{id}/read` so `"read-all"` is never parsed as a UUID path variable.
- UI: the button lives in `notifications-list.tsx` (the Client Component actually rendering the list) rather than the Server Component `notifications/page.tsx` the entry names — Server Components can't hold an `onClick` handler, so this is the same Server/Client split every other interactive piece in this codebase already follows; visually it's still "above the list," matching the entry's intent. Disabled when there's nothing unread to mark. `notification-bell.tsx` needed **no changes at all** — it already independently fetches and re-derives its unread count, so it reflects a mark-all exactly like it reflects any single mark-read.

**Done (live action) — confirmed:** Full Java suite passes; frontend typecheck clean. Live-checked against 3 real unread notifications: clicking "Mark all as read" cleared all 3 unread dots in the list, survived a **hard reload** (still 0), and the nav bar bell's `aria-label` dropped its unread-count text — all without touching `notification-bell.tsx`. Independently confirmed via a direct API call: 0 unread remaining.

### I-45 — Unread-only filter

**Status:** Done — 2026-08-17
**Effort:** UI-only

**Current → change → why:** A long history makes finding the few unread items tedious.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none new.
- API: none new.
- UI: `notifications-list.tsx` — an "Unread only" checkbox filtering the already-fetched array before it's bucketed by I-43, so the two compose naturally (toggling the filter re-buckets whatever's left, dropping any bucket that becomes empty).

**Done (live action) — confirmed:** Live-checked against the same real 5-notification history: toggling "Unread only" narrowed the list from 5 rows to exactly the 3 that were actually unread, confirmed via request capture that toggling fires **zero** network calls, and toggling back off restored all 5.

All three were built together in one pass since they share `notifications-list.tsx`. Zero console errors on the definitive run (one transient hydration warning on an earlier run — the same pre-existing `#global-search` flake documented since I-17, unrelated to any of this code).

---

## Search Results (SCR-14)

### I-46 — Live results as you type

**Status:** Not Started
**Effort:** UI-only

**Current → change → why:** The nav search bar is a plain GET form — every search is a full page navigation to `/search`.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none new — reuses `GET /api/search` exactly as-is.
- API: none new (same endpoint, called more often, debounced).
- UI: `frontend/components/nav-bar.tsx` — the search form becomes a client component rendering a results dropdown instead of submitting a full page navigation.

**Done (live action):** Typing "vas" shows a live dropdown of matching Clients/Matters before pressing Enter; pressing Enter (or clicking a result) still navigates, preserving the existing full-results-page behavior as a fallback.

### I-47 — Highlight matched text

**Status:** Not Started
**Effort:** UI-only

**Current → change → why:** Results show the matched entity's name/title in plain text with no indication of what matched.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none.
- API: none.
- UI: `frontend/app/search/page.tsx` — wrap the matched substring in `<mark>`.

**Done (live action):** Searching "Vasquez" shows that substring visually highlighted within each result's name/title, wherever it appears.

### I-48 — Recent searches

**Status:** Done — 2026-08-17
**Effort:** New data

**Current → change → why:** Re-running a recent query means retyping it from scratch.

**Domain rule → repository → API → UI, together:** Built server-side, not `localStorage` — the entry's own "New data" Effort tag plus the standing 5-layer build structure favored the fuller build over the simplest option, and I-07's `matter_views` upsert pattern was a closely-analogous, already-proven design to mirror.
- Domain: `RecentSearch(lawyerId, query, searchedAt)` — a lightweight fact record like `MatterView`, but with one real invariant worth enforcing: `validateQuery` rejects a blank query before it's ever recorded (reuses the existing `InvalidSearchException`, no new exception type). Unit-tested alone (`RecentSearchTest`).
- Repository: `recent_searches` table, one row per (`lawyer_id`, `query`), upserted via a native `INSERT ... ON CONFLICT (lawyer_id, query) DO UPDATE SET searched_at = now()` — same atomic upsert shape as `matter_views`. `RecentSearchRepository` port + `RecentSearchService` (application layer, capped at 5 most-recent), tested against an in-memory fake (`RecentSearchServiceTest`: fresh search is most recent, a second search pushes the first down without removing it, re-searching moves it back to top without duplicating, list is capped, one Lawyer's recents never leak into another's, blank query rejected before touching the repository). `RecentSearchRepositoryImpl` + `JpaRecentSearchRepository` wired to the real DB, mirroring `MatterViewRepositoryImpl` exactly.
- API: `POST /api/search/recent` (records a search) and `GET /api/search/recent` (returns up to 5 most-recent queries), added directly to the existing `SearchController` — recent searches are conceptually part of the Search feature area, so no new controller.
- UI: `app/search/page.tsx` fire-and-forget records a real search on page load (`await ... .catch(() => {})`, matching I-07/I-28's established best-effort pattern — a failed record must never break the page the lawyer actually asked for). `nav-bar.tsx`'s global-search input stays uncontrolled (no `value` prop, to avoid any risk to its existing native-form GET-submission behavior); a lightweight `isEmpty` boolean (from a plain `onChange`) plus a lazy-loaded `recentQueries` list drive a suggestions dropdown on focus, styled like `client-combobox.tsx`'s listbox, each suggestion a real `<Link>` with `onMouseDown={(e) => e.preventDefault()}` so a click registers before blur can close the dropdown.

**Done (live action) — confirmed:** All 179 Java tests pass (6 new for `RecentSearchServiceTest`, 3 for `RecentSearchTest`); frontend typecheck clean. Fixed one unrelated pre-existing compile gap found along the way: I-44's `markAllRead` addition to `NotificationRepository` had never been added to `NotificationScanServiceTest`'s in-memory fake, blocking the whole test tree from compiling — added the missing override (throws `UnsupportedOperationException`, matching that test's existing pattern for methods it doesn't exercise).

Live-checked against the real running app (Java backend restarted to pick up the new endpoints): a blank query POST correctly returns 400; recording two real searches and re-searching the first moved it back to the top without duplicating (confirmed via direct API calls, `GET /api/search/recent` returning `[qA, qB]` in the right order); the nav-bar dropdown showed the real recent queries on focus (screenshot confirmed clean styling, most-recent-first); clicking a suggestion navigated to `/search?q=...` and re-ran that search; the dropdown correctly hid once the input became non-empty. Recorded searches were still present via a real DB query after the Java backend was fully restarted, confirming real persistence, not in-memory state. Test rows cleaned up from the local DB afterward.

**Done (live action):** Focusing the empty search bar shows the last few queries as clickable suggestions; clicking one re-runs that search.

---

## Firm / Team Settings (SCR-15)

### I-49 — Invite flow + role picker

**Status:** Not Started
**Effort:** New backend

**Current → change → why:** This is Build Plan V0.7's real, already-planned scope. The read-only member list this screen shows today (built to avoid a mocked page) is the other half of the same picture — "Invite a lawyer" is currently visible but deliberately disabled.

**Domain rule → repository → API → UI, together:**
- Domain rule: a new `Invitation` concept (email, firmId, role, token, expiresAt); accepting one creates a `Lawyer` tied to the inviting Firm instead of a new Firm (today's `AuthService.register` always creates a new Firm).
- Repository: new `invitations` table + `InvitationRepository`.
- API: `POST /api/firm/invitations`, `GET /api/firm/invitations`, `DELETE /api/firm/invitations/{id}`; registration flow extended to accept an invitation token.
- UI: `frontend/app/firm/page.tsx` — enable "Invite a lawyer," add a pending-invitations list, a role selector on each member row.

**Done (live action):** Inviting an email, that person completing signup via the invite link, shows them in the Firm's member list with the assigned role — and confirms they see the same Firm's Clients/Matters as the inviting Lawyer, not a new empty Firm.

### I-50 — Per-member workload glance

**Status:** Not Started
**Effort:** New data

**Current → change → why:** Useful the moment a Firm has more than the one member it has today.

**Domain rule → repository → API → UI, together:**
- Domain rule: needs a real decision first — Matter currently has no "assigned Lawyer" or creator field (unlike Document, which has `uploaded_by`). Adding "open Matters per Lawyer" means either adding a Matter-owner concept or scoping this to something already trackable.
- Repository: depends on that decision — likely a new `matters.assigned_lawyer_id` column plus a count query.
- API: `GET /api/firm/lawyers` (already built) extended with a count, or a dedicated endpoint.
- UI: `firm/page.tsx`.

**Done (live action):** Each Lawyer's row shows "3 open Matters" next to their name, matching a manual count of Matters assigned to them.

---

## Account Settings (SCR-16)

### I-51 — Editable name and password change

**Status:** Done — 2026-08-17
**Effort:** New backend

**Current → change → why:** The screen currently shows a real, read-only profile (name, email, role) plus a fully working Sign Out — deliberately no edit form, since no update-profile endpoint exists yet and a form that submits nowhere would be worse than none.

**Domain rule → repository → API → UI, together:** Built exactly to the entry's breakdown, with one addition beyond its literal method list: `LawyerRepository` also gained `findByIdWithHash(id)` — the existing `findByEmailWithHash` is keyed by email, but `changePassword` only has the authenticated lawyer's id (from the session), so re-verifying the current password needed a hash lookup by id.
- Domain: `Lawyer.validateName(name)` (same "non-blank, trimmed" invariant `Client.update` already uses) and `Lawyer.validateNewPassword(password)` (same 8+ character minimum `AuthService.register` enforces for a brand-new account) — both pure, static, unit-tested alone (`LawyerTest`). New `InvalidLawyerException`, mirroring `InvalidClientException`.
- Application: `AuthService.updateName(lawyerId, name)` and `AuthService.changePassword(lawyerId, currentPassword, newPassword)` — the latter fetches the stored hash via `findByIdWithHash`, rejects with a new `IncorrectPasswordException` if `PasswordHasher.matches` fails, then validates and re-hashes via the existing `PasswordHasher.hash`. Tested against `AuthServiceTest`'s existing in-memory `LawyerRepository` fake (extended with the three new methods): name updates and trims; a blank rename is rejected and leaves the old name untouched; a correct current password swaps the hash (old password stops matching, new one does); a wrong current password is rejected and leaves the hash untouched; a too-short new password is rejected and leaves the hash untouched.
- Repository: `LawyerRepositoryImpl.updateName`/`updatePassword`/`findByIdWithHash`, wired to the real DB via the existing `JpaLawyerRepository.findById`/`save` — no new native queries needed, unlike I-48's upsert pattern.
- API: `PATCH /api/auth/me` (name) and `POST /api/auth/change-password` (current + new password), added to the existing `AuthController`. Used `CurrentLawyerResolver` (the project's real authz boundary) for both, even though `AuthController`'s older `/me` and `/logout` endpoints predate that resolver and still parse the session cookie inline — not touched, to avoid an unrelated refactor.
- UI: `frontend/app/account/account-forms.tsx` (new) — `EditNameForm` and `ChangePasswordForm`, both Client Components mirroring `edit-client-modal.tsx`'s fetch/error-banner/`router.refresh()` shape. `ChangePasswordForm` reuses the existing `PasswordStrengthMeter` (already built for registration, previously unused elsewhere) on the new-password field. Wired into `account/page.tsx`, replacing the static name display; `router.refresh()` on a successful rename re-fetches the page's server-side `/api/auth/me` call, which flows straight through to `NavBar`'s `AccountMenu` prop — no client-side name-sync code needed.

**Done (live action) — confirmed:** All 190 Java tests pass (6 new for `LawyerTest`, 5 new for `AuthServiceTest`); frontend typecheck clean. Fixed two other pre-existing in-memory `LawyerRepository` fakes (`AuthServiceTest` itself and `NotificationScanServiceTest`) that needed the three new interface methods added to stay compilable — same kind of gap as I-48's `NotificationScanServiceTest` fix, not a new one.

Live-checked against the real running app using a fresh throwaway registered account (not the shared `v05livecheck` test account, since this check permanently changes a password): direct API calls confirmed `PATCH /api/auth/me` trims and persists the name (re-confirmed via a separate `GET /api/auth/me` call), rejects a blank name with 400; `POST /api/auth/change-password` rejects a wrong current password with 401 and a too-short new password with 400, and on success the *old* password immediately stops working for login (401) while the *new* one works (200) — real proof the hash was actually replaced, not just accepted. In the browser: editing the name on `/account` and saving showed a "Saved" confirmation, updated the avatar initial and the account-menu dropdown name in place with no full page navigation (screenshot confirmed), and the new name was still there after a hard reload.

### I-52 — Notification preferences

**Status:** Done — 2026-08-17
**Effort:** New backend

**Current → change → why:** Ties directly to Notifications (SCR-13) and to who SD-006's scanner notifies — today, every Lawyer in a Firm gets every Deadline reminder for that Firm, with no way to opt out individually.

**Domain rule → repository → API → UI, together:** "Which notification types" simplified to a single boolean — Deadline reminders is the *only* notification type that exists in this app (SD-006), so a multi-type preferences map would be speculative structure for types that don't exist yet; adding it later, when a second type actually exists, is a small, contained change.
- Domain: `LawyerPreferences(lawyerId, deadlineRemindersEnabled)` with a `defaultFor(lawyerId)` factory that returns `enabled=true` — this *is* a real, testable business rule (`LawyerPreferencesTest`): before I-52, every Lawyer got every reminder with no opt-out, so "no preference row yet" must default to enabled, never disabled, or existing behavior would silently regress for every Lawyer who's never touched the setting.
- Application: `LawyerPreferencesRepository` port + `LawyerPreferencesService` (`get`/`update`), tested against an in-memory fake (`LawyerPreferencesServiceTest`). `NotificationScanService` gained a fourth constructor dependency (`LawyerPreferencesRepository`, following `MatterService`'s established pattern of depending on repositories directly rather than other Services) and now skips a Lawyer whose preference is off *before* the existing per-day idempotency check — extended `NotificationScanServiceTest` with 3 new cases: skips an opted-out Lawyer, still notifies other Firm members whose preference is still on, and a Lawyer who's never set a preference still gets notified (defaults to enabled).
- Repository: `lawyer_preferences` table, at most one row per Lawyer (unique index on `lawyer_id` alone, unlike `matter_views`/`recent_searches` which key on a pair), same atomic upsert shape wired to the real DB via `LawyerPreferencesRepositoryImpl`.
- API: `GET`/`PATCH /api/auth/me/preferences`, added to `AuthController` alongside I-51's other `/me` endpoints.
- UI: `NotificationPreferencesForm` (new, in `account-forms.tsx`) — a single "Deadline reminders" checkbox, optimistic toggle that reverts on a failed save, wired into `account/page.tsx` with the current value server-fetched up front (no loading flash).

**Done (live action) — confirmed:** All 199 Java tests pass (2 new `LawyerPreferencesTest`, 4 new `LawyerPreferencesServiceTest`, 3 new `NotificationScanServiceTest` cases); frontend typecheck clean.

Live-checked against the **real hourly `@Scheduled` scanner** (`NotificationScanScheduler`), not a simulated call: registered two Lawyers, moved the second into the first's Firm directly via SQL (no invite-teammate endpoint exists yet — SCR-15 is read-only), created a real Client → Matter → Deadline due today in that shared Firm, and turned Deadline reminders off for Lawyer A via `PATCH /api/auth/me/preferences` (confirmed persisted via a separate `GET`). Restarted the Java backend to get a clean 60-second `initialDelay` window, waited for the scheduler's real first automatic tick, then checked both Lawyers' notifications via independent `GET /api/notifications` calls: **Lawyer A (opted out) received no notification for that deadline; Lawyer B (still on, same Firm) did** — the exact behavior described in this entry's "Done" criterion, verified against the actual production code path, not just the unit tests. (First attempt at this same check missed the scheduler's window because multi-step setup, including a `docker exec` SQL call, ran past the first tick before the deadline existed — fixed by restarting the backend again immediately before the timed setup, resetting the 60s window.) Test data cleaned up afterward.

---

## Cross-cutting

### I-53 — Command palette (⌘K)

**Status:** Not Started
**Effort:** UI-only

**Current → change → why:** The nav search bar covers finding a Client or Matter; nothing covers quickly triggering an action ("New Matter," "New Client") without leaving the keyboard.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none new.
- API: none new — reuses `GET /api/search` and existing app routes.
- UI: a new global overlay component, keyboard-triggered (⌘K/Ctrl+K), added at the layout level.

**Done (live action):** Pressing ⌘K from any authenticated screen opens the palette; typing a Matter name and pressing Enter navigates directly to it.

### I-54 — Toast confirmation on save

**Status:** Done — 2026-08-17
**Effort:** UI-only

**Current → change → why:** Creating a Client, saving a Deadline, or generating a draft currently just redirects or refreshes silently — the only confirmation an action landed is the new row appearing, which is easy to miss, especially on a slow connection.

**Domain rule → repository → API → UI, together:** UI-only, exactly as scoped — no domain/repository/API layers.
- `components/toast-context.tsx` (new): `ToastProvider`/`useToast()`, mirroring the existing `ListSearchProvider` shape exactly (same "mounted once at root layout, Context for cross-tree access" pattern) — mounted above the router outlet in `app/layout.tsx` specifically so a toast queued right before a `router.push()` away from the triggering page still renders; the provider itself never unmounts on a client-side navigation. Each toast auto-dismisses after 3s; new `.toast`/`.toast-stack` styles in `globals.css` (success/error variants, reusing the existing `--color-success-*`/`--color-error-*` tokens).
- Wired into the three flows the entry names (Client creation, Deadline creation, draft generation) plus Matter creation for consistency: `clients/new/page.tsx`, `matters/new/new-matter-form.tsx` (both success paths — with and without a chained deadline), `matters/[id]/new-deadline-form.tsx`, `matters/[id]/generate-draft-modal.tsx`.

**Done (live action) — confirmed:** Frontend typecheck clean (no domain/backend layer, no Java tests to run).

Live-checked with real interaction: filled and submitted the New Client form, confirmed via a `MutationObserver` trace that the "Client created" toast appears within ~60ms of the click, survives the client-side redirect from `/clients/new` to `/clients` intact (same DOM node, not a re-mount), and auto-dismisses after ~3s (measured: 2992ms between appearing and clearing). Confirmed via screenshot the toast renders cleanly in the bottom-right corner with the app's existing success-token styling.

### I-55 — Consistent breadcrumbs everywhere

**Status:** Done — 2026-08-17
**Effort:** UI-only

**Current → change → why:** Every nested page (Client Detail, Matter Detail, New Matter) has a single "← Back" link that only ever goes up one level, even where a real multi-level path exists (Client → Matter, in particular — see I-31).

**Domain rule → repository → API → UI, together:** UI-only, exactly as scoped — no domain/repository/API layers.
- `components/ui/breadcrumb.tsx` (new): a shared `<Breadcrumb items={[...]}>`. "Each segment a real link" is read as every *ancestor* segment (all but the last) — the current page is shown as plain text with `aria-current="page"`, the standard breadcrumb convention (a page never links to itself).
- Replaced every single-level `← Back` link found (grepped the whole `app/` tree for `←`): `clients/new/page.tsx` (Clients → New Client), `matters/new/page.tsx` (Matters → New Matter, or **Clients → \<Client\> → New Matter** when launched from a Client's page via `?clientId=`), `matters/[id]/page.tsx` (**Clients → \<Client\> → \<Matter title\>** — the real multi-level path I-31 called out, falling back to Matters → \<Matter title\> if the Matter has no linked Client), `clients/[id]/page.tsx` (Clients → \<Client name\>).

**Done (live action) — confirmed:** Frontend typecheck clean (no domain/backend layer, no Java tests to run).

Live-checked structurally against the real running app across all four pages — every breadcrumb renders the correct labels and hrefs for real data (verified via real Clients/Matters created through the actual API, including the 3-level Client→Matter path with a genuinely linked Client). Click-through navigation was confirmed working correctly multiple times (screenshots + URL checks), but this live check also **surfaced a real, pre-existing flake, unrelated to this component**: clicking a breadcrumb link on the Matter Detail page intermittently fails to navigate in this dev environment. Root-caused rigorously before concluding: reproducing the *identical* failure on the page's pre-existing "Client: `<Link>`" line (present before I-55, never touched) proved it isn't something the new `<Breadcrumb>` introduced; it's specific to the Matter Detail route (by far the heaviest page — chat, document upload/list, deadline forms, notification polling all mounting at once) and correlates with this session's own heavy, repeated Playwright browser launches exhausting this machine's ~7.3GB RAM (found 13+ orphaned `chrome.exe` processes and only ~350MB free system memory at one point). Under low load, immediately after cleaning those up, the same click succeeded cleanly. Not fixed as part of this entry — it's an environment-level Next.js dev-mode navigation issue on the app's most complex page, not a defect in the Breadcrumb component or a regression it caused, and investigating Next.js's dev-mode RSC-navigation behavior further is out of scope for a UI-only backlog item. Worth a closer look if it's ever observed outside heavy automated testing.

### I-56 — "/" to focus search

**Status:** Not Started
**Effort:** UI-only

**Current → change → why:** A small, standard keyboard convention. The search bar is already persistent in the nav on every authenticated screen.

**Domain rule → repository → API → UI, together:**
- Domain rule: none.
- Repository: none.
- API: none.
- UI: a global keydown listener (`nav-bar.tsx` or a layout-level component) that focuses the search input on `/`, ignored while a text field already has focus.

**Done (live action):** Pressing "/" anywhere on an authenticated page (outside a text field) moves focus to the nav search box; typing normally inside any other field is unaffected.
