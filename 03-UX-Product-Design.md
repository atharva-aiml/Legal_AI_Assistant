# UX & Product Design — Legal AI Assistant

Web-responsive only (REQ-025) — no native mobile app. Layout described here is structural; visual styling (colors, type, spacing) belongs to the Design System doc.

## 1. Screen Inventory

| ID | Name | Purpose |
|---|---|---|
| SCR-01 | Login | Authenticate an existing Lawyer into their Firm account. |
| SCR-02 | Sign Up / Firm Setup | Create a new Firm account and its first Lawyer login, on first use. |
| SCR-03 | Dashboard | Landing screen after login — upcoming Deadlines and active Matters at a glance. |
| SCR-04 | Clients List | Browse, search, and filter all Clients. |
| SCR-05 | Client Detail | View/edit a Client's profile and see all their Matters, open and closed. |
| SCR-06 | New / Edit Client (modal) | Create or edit a Client profile. |
| SCR-07 | Matters List | Browse, search, and filter all Matters across every Client. |
| SCR-08 | New Matter (modal) | Create a Matter linked to a Client. |
| SCR-09 | Matter Detail | Core case workspace — Documents, AI Chat, and Deadlines for one Matter. |
| SCR-10 | Document Upload (panel) | Upload one or more files to a Matter. |
| SCR-11 | New Deadline (modal) | Create a Deadline on a Matter. |
| SCR-12 | Template Picker / Draft Generator (modal) | Pick a template and generate a pre-filled draft document. |
| SCR-13 | Notifications Panel | View reminders for upcoming/overdue Deadlines. |
| SCR-14 | Search Results | Cross-entity results (Clients + Matters) for a global search query. |
| SCR-15 | Firm / Team Settings | Manage which Lawyers belong to the Firm account. |
| SCR-16 | Account Settings | Manage the logged-in Lawyer's own profile; log out. |

## 2. Navigation / Information Architecture

**Rule:** a screen earns a top-level nav entry only if a Lawyer might need it as a *cold-start destination* — the entry point to a whole category of data (all Clients, all Matters, what's due) rather than a single record or an action on one. Everything that operates on a single record (a Client, a Matter, a Document, a Deadline) is reached only from inside the screen that owns that record, never from global nav — because it has no meaning without that context (mirrors BR-001/BR-002/BR-004: Matters belong to a Client, Documents/Deadlines belong to a Matter).

**Top-level nav** (persistent sidebar/top bar, visible on every authenticated screen):
- Dashboard (SCR-03)
- Clients (SCR-04)
- Matters (SCR-07)

**Persistent utility icons** (always visible, not counted as "sections" since they don't own a data category the way the three above do): Search → SCR-14, Notifications bell → SCR-13, Account menu → SCR-16, with Firm Settings (SCR-15) nested inside the Account menu since it's infrequent/admin-only, not daily-use.

**Contextual (reached only from within another screen):**
- SCR-05 Client Detail ← row click in SCR-04, or a Client link inside SCR-09.
- SCR-06 New/Edit Client ← "+ New Client" on SCR-04, or "Edit" on SCR-05.
- SCR-08 New Matter ← "+ New Matter" on SCR-07, or on SCR-05 (pre-fills that Client).
- SCR-09 Matter Detail ← row click in SCR-07, a Matter row in SCR-05, a widget in SCR-03, or a result in SCR-14.
- SCR-10 Document Upload ← "Upload" inside SCR-09's Documents tab.
- SCR-11 New Deadline ← "+ New Deadline" inside SCR-09's Deadlines tab.
- SCR-12 Template Picker ← "Generate Document" inside SCR-09's Documents tab.

**Pre-authentication (outside the nav entirely):** SCR-01 Login, SCR-02 Sign Up.

On narrow viewports, the sidebar collapses to a hamburger/bottom bar carrying the same three top-level entries — no new destinations are added for mobile widths.

## 3. User Journeys

**J1 — Onboard a client and get a cited answer (core value proof)**
1. Lawyer logs in (SCR-01) → lands on Dashboard (SCR-03).
2. Opens Clients (SCR-04) → "+ New Client" → fills SCR-06 → saves → lands on the new Client Detail (SCR-05).
3. Clicks "+ New Matter" → fills SCR-08 (Client pre-filled) → saves → lands on Matter Detail (SCR-09), Documents tab, empty.
4. Clicks "Upload" → SCR-10, selects 2 PDFs → each shows "Uploading" → "Processing" → "Ready" (REQ-004).
5. Switches to the Chat tab, asks a question about the uploaded files.
6. Sees an answer with inline citations pointing to the specific document + page (REQ-006); if a file is still processing, sees "Still processing, try again shortly" instead of a guess (REQ-007).

**J2 — Set a deadline and act on the reminder**
1. On Matter Detail (SCR-09), Deadlines tab → "+ New Deadline" → fills SCR-11 → saves; deadline appears in the tab and on the Dashboard's Upcoming widget.
2. Three days before the due date, a badge appears on the Notifications bell; Lawyer opens SCR-13, sees the reminder with a link back to the Matter.
3. Clicks the reminder → lands on SCR-09, Deadlines tab, that Deadline highlighted.
4. Marks it complete inline; badge clears.

**J3 — Closing a matter is blocked by an open deadline (business rule surfaced in the UI)**
1. On Matter Detail (SCR-09), Lawyer clicks "Close Matter."
2. BR-003 check fails (one Deadline still open) → action is blocked; an inline message names the specific open Deadline(s) and links to them, not a generic error.
3. Lawyer clicks the link, completes/reschedules the Deadline in the Deadlines tab.
4. Clicks "Close Matter" again → status becomes "Closed"; Documents/Chat/Deadlines stay fully visible (BR-007), but create actions (Upload, New Deadline) are hidden — the Matter is now read-only.

**J4 — Find an answer inside a closed/past matter**
1. From anywhere, Lawyer uses global Search, typing a client or matter name → SCR-14, results include Closed Matters.
2. Selects a Closed Matter → SCR-09 opens with a "Closed" badge, read-only.
3. Switches to the Chat tab, asks a question → gets a cited answer exactly as an Open Matter would (BR-005/BR-006 apply regardless of status).

**J5 — Generate a draft agreement instead of writing one from scratch**
1. On Matter Detail (SCR-09), Documents tab → "Generate Document."
2. SCR-12 opens; Lawyer picks a template (e.g., "Non-Disclosure Agreement"); fields pre-fill from the Matter's Client/Matter data.
3. Lawyer reviews/edits the pre-filled fields, clicks "Generate."
4. A draft document is added to the Matter's Document list, tagged "Draft," and becomes queryable like any uploaded Document (REQ-004 applies to generated documents too).

## 4. Per-Screen Detail

**SCR-01 — Login**
- Primary action: submit email + password to authenticate.
- Key data: email field, password field, "Forgot password" link, link to Sign Up.
- Empty: default blank form. Error: inline message under the form — "Incorrect email or password" (doesn't reveal which field failed). Loading: submit button shows a spinner and disables.

**SCR-02 — Sign Up / Firm Setup**
- Primary action: create the Firm account and first Lawyer login.
- Key data: Firm/practice name, Lawyer name, email, password.
- Empty: blank form. Error: field-level validation (e.g., "Email already registered," linking to Login). Loading: spinner on submit, form disabled.

**SCR-03 — Dashboard**
- Primary action: jump into a Matter that needs attention, via the Upcoming Deadlines or Recent Matters widget.
- Key data: Upcoming Deadlines (next 7–14 days, all Matters, soonest first), Recent/Active Matters, "+ New Client" / "+ New Matter" shortcuts.
- Empty: first-login state (no Clients/Matters yet) — single prompt "Add your first client to get started" with a button to SCR-06. Error: widget-level — "Couldn't load deadlines — retry," without blocking the rest of the dashboard. Loading: skeleton placeholders per widget.

**SCR-04 — Clients List**
- Primary action: open a Client (row click) or create one ("+ New Client").
- Key data: Client name, number of Matters (open/closed), last activity date; search box; status filter.
- Empty: no Clients yet → prompt + "+ New Client" CTA. Error: "Couldn't load clients — retry" banner, list area blank. Loading: skeleton rows.

**SCR-05 — Client Detail**
- Primary action: open a Matter (row click) or create one ("+ New Matter," Client pre-filled).
- Key data: Client profile (name, contact info, notes), list of this Client's Matters with status badges and titles.
- Empty: Client exists but has no Matters → "+ New Matter" CTA, no list shown. Error: full-panel "Couldn't load this client" with retry, profile fields blank. Loading: skeleton for profile fields and Matter rows.

**SCR-06 — New / Edit Client (modal)**
- Primary action: save (create or update) the Client record.
- Key data: name (required), contact info, notes.
- Empty: blank form (New) or pre-filled current values (Edit). Error: inline field validation (e.g., "Name is required"); save failure shows a banner inside the modal with entered data intact. Loading: Save button spinner, form disabled.

**SCR-07 — Matters List**
- Primary action: open a Matter (row click) or create one ("+ New Matter").
- Key data: Matter title, Client name, status (Open/Closed), next Deadline if any; search box; status/date filters.
- Empty: no Matters yet → prompt + CTA (or, if Clients exist but no Matters, a prompt to add a Matter for an existing Client). Error: "Couldn't load matters — retry" banner. Loading: skeleton rows.

**SCR-08 — New Matter (modal)**
- Primary action: save — creates the Matter and opens SCR-09.
- Key data: Matter title (required), linked Client — pre-filled if opened from SCR-05, otherwise a searchable Client picker (required, BR-001).
- Empty: blank form; Client picker shows "No clients yet — create one first" with a shortcut to SCR-06 if none exist. Error: inline validation (missing title/client); save failure banner. Loading: Save button spinner.

**SCR-09 — Matter Detail**
- Primary action: ask the AI Assistant a question (Chat tab, default/most-used) — secondary actions: upload a Document, add a Deadline, close the Matter.
- Key data: Matter title, Client link, status badge; three tabs — Documents (list + indexing status), Chat (message history + citations), Deadlines (due dates + complete/incomplete state); "Close Matter" button.
- Empty: new Matter → Documents tab shows "No documents yet — upload to start asking questions"; Chat tab disabled ("Upload a document first") until at least one Document is Ready; Deadlines tab empty with CTA. Error: per-tab — Documents shows failed uploads with a retry icon; Chat shows "Couldn't reach the Assistant — retry" on a failed query, never a fabricated answer (REQ-007). Loading: Documents show "Processing…" until indexed (REQ-004); Chat shows a thinking indicator while a response generates (NFR-001: ≤8s p95).

**SCR-10 — Document Upload (panel)**
- Primary action: select and upload one or more files.
- Key data: drag-and-drop/file-picker area; staged files with per-file progress and status (Uploading → Processing → Ready/Failed).
- Empty: no files selected — drop-zone prompt only. Error: per-file failure inline (e.g., "Unsupported file type," "Upload failed — retry") without blocking the rest of the batch. Loading: per-file progress bar; panel stays open until all files resolve.

**SCR-11 — New Deadline (modal)**
- Primary action: save — creates the Deadline on this Matter.
- Key data: title (required), due date (required), notification lead-time override (optional, defaults per REQ-009).
- Empty: blank form. Error: inline validation ("Due date is required"); save failure banner. Loading: Save button spinner.

**SCR-12 — Template Picker / Draft Generator (modal)**
- Primary action: pick a template, review pre-filled fields, click "Generate."
- Key data: list of available templates (name + short description); once selected, a preview/edit form pre-filled from Matter/Client data.
- Empty: "No templates available" if none are configured. Error: "Couldn't generate document — retry," entered edits preserved. Loading: spinner while the draft generates and is added to Documents.

**SCR-13 — Notifications Panel**
- Primary action: click a notification to jump to its Matter/Deadline.
- Key data: recent reminders (Deadline title, Matter, due date, sent time), read/unread state.
- Empty: "No notifications yet." Error: "Couldn't load notifications — retry"; bell shows no badge count until resolved. Loading: skeleton rows.

**SCR-14 — Search Results**
- Primary action: open a matching Client or Matter.
- Key data: query echoed at top; results grouped by type (Clients, Matters), each showing name/title, status, and why it matched.
- Empty: "No results for '<query>'," suggests checking spelling or browsing Clients/Matters directly. Error: "Search failed — retry" banner. Loading: skeleton rows. *(No latency target exists for search yet — flag for a Requirements follow-up if it proves slow in practice.)*

**SCR-15 — Firm / Team Settings**
- Primary action: invite a Lawyer to the Firm (by email) or remove one.
- Key data: current Firm members (name, email, role), pending invitations.
- Empty: only the current Lawyer listed, no pending invitations. Error: "Couldn't send invite — retry" inline. Loading: spinner on invite/remove actions.

**SCR-16 — Account Settings**
- Primary action: update own profile (name, password) or log out.
- Key data: current Lawyer's name, email, password-change fields, "Log out" button.
- Empty: n/a — always pre-filled with current values. Error: inline field validation; save failure banner. Loading: Save button spinner.
