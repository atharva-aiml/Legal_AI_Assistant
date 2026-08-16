# Charter & Discovery — Legal AI Assistant

## 1. Problem Statement

Lawyers, especially those working alone or in small firms, manage clients and cases in an inconsistent, manual, and error-prone way:

- No central system for client details, client documents, or case history — everything lives across email, WhatsApp, local folders, and paper files.
- To answer a simple question about a case ("what did the opposing party argue in their reply?"), a lawyer has to re-read entire documents themselves — there's no way to query case knowledge directly.
- Deadlines (hearings, filings, client follow-ups) are tracked from memory or scattered notes, not a system — so nothing proactively warns them.
- Past clients and past cases aren't retained as reusable knowledge — closed matters are effectively archived out of reach.
- Routine documents (agreements, notices, standard filings) are recreated from scratch or copy-pasted each time instead of generated from templates/precedent, wasting hours per week.

The common thread: lawyers are spending time on document lookup, memory-dependent tracking, and repetitive drafting — time that should go to actual legal work.

## 2. Target Users

- **Individual Lawyers** — solo practitioners handling intake, drafting, research, and client communication themselves, with no support staff and the least tolerance for complex or expensive software.
- **Small Law Firms** — a handful of lawyers sharing clients and cases informally, where continuity currently depends on which specific person remembers what.

Both groups share the same core pain: no system of record, high dependency on individual memory, and low appetite for tools that require heavy setup or training.

## 3. Business Goals & Success Metrics

| Goal | Success Metric |
|---|---|
| **1. AI case assistant** — the assistant ingests case documents as soon as they're uploaded, and lawyers can chat with it to retrieve information in detail, with exact citations, zero hallucination, and nothing missed. | Every factual claim in an assistant response is traceable to a specific source document + location. No answer is given for information not present in the uploaded documents (assistant says so instead of guessing). New documents are queryable immediately after upload, without manual indexing steps. |
| **2. Efficient, user-friendly client & case management** | A lawyer can find any client's status, case status, or document in a few clicks/seconds — not by searching through folders or asking someone. |
| **3. Lawyers focus on casework, not admin** | Deadline tracking, client record-keeping, and document organization run through the assistant with minimal manual upkeep — the lawyer's manual admin time drops relative to today's baseline. |
| **4. Usable by non-technical lawyers** | A first-time user with no software background can upload a document, ask a question, and get a correct answer without instructions or onboarding help. |

Goals 1 and 3 are the highest-priority — they're what makes this different from a generic case-management tool, and everything else (client management, deadlines) is scaffolding around them.

## 4. Scope

**In scope**
- AI Assistant: document ingestion per case, chat-based Q&A over case documents, cited/grounded answers.
- Client management: client profiles, contact details, associated cases.
- Case management: active case records, linked documents, case notes.
- Notifications: reminders for deadlines and upcoming events.
- Deadline management: hearing dates, filing dates, follow-ups, tracked per case.
- Past clients and cases: closed matters remain searchable and queryable (not deleted or made inaccessible).

**Out of scope**
- Case designing (structuring legal strategy for a case).
- Case suggestions (recommending how to argue or proceed).
- Legal decisions (the assistant never decides or advises on legal outcomes — it retrieves and organizes information; the lawyer decides).

This boundary matters for both product trust and liability: the assistant is a document/knowledge layer, not a source of legal judgment.

## 5. Constraints

- **Timeline:** No fixed deadline. Build incrementally, get the AI assistant (Goal 1) working end-to-end first since it's the core differentiator, then layer client/case management and deadlines around it.
- **Budget:** Solo, self-funded, low budget. Favor free-tier and pay-per-use services over upfront-cost or fixed-subscription infrastructure; avoid self-hosted ML/OCR runtimes unless a spike shows the cost/quality tradeoff clearly favors it over an API.
- **Team size:** Solo developer (AI-assisted). No dedicated QA, design, or ops — tooling and process choices should stay low-maintenance.
- **Regulatory/compliance:** India-focused.
  - Client and case data is confidential/privileged by nature — data handling must assume worst-case sensitivity (no data used for third-party model training, no unnecessary retention elsewhere).
  - Design for India's Digital Personal Data Protection Act (DPDP), 2023 — lawful basis for processing personal data, purpose limitation, and breach-notification readiness — as a hard constraint from the start, not retrofitted later.
  - The assistant must never present itself as giving legal advice — framing and disclaimers should make clear it retrieves/organizes information only, consistent with Section 4's exclusion of legal decisions.
- **Undecided — needs a spike:** The document ingestion/retrieval pipeline (OCR for scanned documents, embeddings/vector search engine, LLM provider for citation-grounded chat) involves real environment risk — native dependencies, cost-per-document, and accuracy tradeoffs vary significantly between options. Don't lock this in here; validate with a throwaway script against real sample legal documents before committing in the Technology Decision Log.
