# Requirements — Legal AI Assistant

## 1. Functional Requirements

### Must

| ID | Requirement |
|---|---|
| REQ-001 | Lawyer can create a Client profile (name, contact info, notes). |
| REQ-002 | Lawyer can create a Matter linked to exactly one Client, with a status of Open or Closed. |
| REQ-003 | Lawyer can upload Documents (PDF, DOCX, scanned images) to a Matter. |
| REQ-004 | Uploaded Documents are extracted/indexed (including OCR for scanned/image files) and become queryable by the AI Assistant immediately after upload. |
| REQ-005 | Lawyer can chat with an AI Assistant scoped to a single Matter; the Assistant answers only from that Matter's Documents. |
| REQ-006 | Every AI Assistant answer includes a citation (source Document + page/section) for each factual claim it makes. |
| REQ-007 | If the requested information isn't present in the Matter's Documents, the AI Assistant states that explicitly instead of guessing. |
| REQ-008 | Lawyer can create a Deadline (title, due date, linked Matter). |
| REQ-009 | System sends a Notification ahead of an approaching Deadline (default: 3 days before + day-of). |
| REQ-010 | Lawyer can mark a Matter Closed; Closed Matters, their Documents, and Deadlines remain fully readable and searchable (no data loss). |
| REQ-011 | Lawyer can search/filter Clients and Matters by name, status, and date. |
| REQ-012 | All client/case data requires authentication (login) before access. |
| REQ-013 | Lawyer can view a list of a Client's Matters (past and present) from the Client's profile. |

### Should

| ID | Requirement |
|---|---|
| REQ-014 | Multiple lawyers within one Firm account can share access to the same Clients/Matters. |
| REQ-015 | Lawyer can generate a draft document (agreement/notice) from a reusable template, pre-filled with Matter/Client details. |
| REQ-016 | Lawyer can customize a Deadline's notification lead time per Deadline. |
| REQ-017 | Dashboard shows upcoming Deadlines across all of a lawyer's Matters. |
| REQ-018 | Lawyer can bulk-upload multiple Documents to a Matter in one action. |
| REQ-027 | Lawyer can delete an uploaded Document from a Matter (unrestricted — not gated on Matter status). |

### Could

| ID | Requirement |
|---|---|
| REQ-019 | Lawyer can tag/categorize Documents within a Matter (e.g., "Evidence," "Correspondence"). |
| REQ-020 | Lawyer can export a Matter's Documents plus an AI-generated case summary as a single PDF. |
| REQ-021 | AI Assistant can answer questions across multiple Matters belonging to the same Client, when the lawyer explicitly broadens scope. |
| REQ-022 | Lawyer can use voice input to chat with the AI Assistant. |

### Won't (this version)

| ID | Requirement |
|---|---|
| REQ-023 | No integration with court e-filing or government case-tracking systems. |
| REQ-024 | No billing, invoicing, or payment processing. |
| REQ-025 | No native mobile app — web-responsive only. |
| REQ-026 | No real-time multi-user collaborative editing of documents. |

## 2. Non-Functional Requirements

| ID | Category | Requirement | Measurable Target |
|---|---|---|---|
| NFR-001 | Performance | AI Assistant chat response time | ≤ 8s (p95) for a query against a Matter with up to 200 pages of Documents. |
| NFR-002 | Performance | Document ingestion latency | Newly uploaded Document (≤ 20 pages, including OCR if needed) is queryable within 60s (p95) of upload. |
| NFR-003 | Security | Data encryption | TLS 1.2+ in transit; AES-256 at rest, for all Client/Matter/Document data. |
| NFR-004 | Security | Data isolation | No lawyer/Firm account can read or write another account's data — verified by an access-control check on every data-fetching endpoint. |
| NFR-005 | Security | No model training on client data | No Document or chat content is used to train any third-party model; LLM/OCR providers used must offer no-retention/no-training terms. |
| NFR-006 | Scalability | Per-account capacity | Supports ≥ 50 concurrent Matters with up to 500 Documents each without breaching NFR-001/NFR-002 targets. |
| NFR-007 | Availability | Uptime | ≥ 99% monthly uptime, best-effort (consistent with solo/self-funded constraint), planned maintenance excluded. |
| NFR-008 | Compliance | DPDP Act 2023 | Lawful basis for processing recorded per account; data minimization applied; breach-notification process defined before first real user's data is stored. |
| NFR-009 | Data Durability | Backup | Documents and case data backed up ≥ daily; Recovery Point Objective (RPO) ≤ 24 hours. |

## 3. Business Rules

| ID | Rule |
|---|---|
| BR-001 | A Matter belongs to exactly one Client. A Client may have multiple Matters. |
| BR-002 | A Document belongs to exactly one Matter — never orphaned, never shared across Matters. |
| BR-003 | A Matter cannot be marked Closed while it has one or more open (incomplete) Deadlines. |
| BR-004 | A Deadline always has a due date and a linked Matter — it cannot exist standalone. |
| BR-005 | The AI Assistant answers only from Documents belonging to the active Matter, unless the lawyer explicitly broadens scope (REQ-021). |
| BR-006 | Every AI Assistant answer carries at least one citation, or explicitly states the information wasn't found — no uncited factual claims. |
| BR-007 | Closed Matters, their Documents, and Deadlines are retained and remain read-accessible indefinitely — never hard-deleted by the system. |
| BR-008 | A lawyer can only read or modify Clients, Matters, Documents, and Deadlines belonging to their own account/Firm. |
| BR-009 | A Deadline's due date cannot be in the past — enforced at creation and at edit, not just at initial entry. |

## 4. Non-Goals

- Case designing or legal strategy formulation.
- Case outcome suggestions or predictions.
- Legal advice or legal decisions of any kind — the system retrieves and organizes; the lawyer decides.
- Court e-filing, e-signature, or direct integration with judicial/government systems.
- Billing, invoicing, or payment processing.
- Native mobile applications (web-responsive only, this version).
- Real-time collaborative multi-user document editing.
- Compliance scope beyond India/DPDP Act 2023 (this version).

## 5. Acceptance Criteria

| ID | Requirement | Acceptance Criteria |
|---|---|---|
| AC-001 | REQ-001 | Given a logged-in lawyer, when they submit a Client form with at least a name, then a Client record is created and appears in the Client list. |
| AC-002 | REQ-002 | Given an existing Client, when the lawyer creates a Matter and selects that Client, then the Matter appears under the Client's profile with status "Open." |
| AC-003 | REQ-003 | Given an open Matter, when the lawyer uploads a PDF/DOCX/scanned-image file, then the file appears in the Matter's Document list with an "uploaded" status. |
| AC-004 | REQ-004 | Given a Document just uploaded to a Matter, when 60 seconds have passed, then a chat query referencing content unique to that Document returns a correct, cited answer. |
| AC-005 | REQ-005 | Given a Matter with uploaded Documents, when the lawyer asks the AI Assistant a question answerable from those Documents, then the response is generated using only that Matter's Documents. |
| AC-006 | REQ-006 | Given any AI Assistant answer containing a factual claim, when the answer is inspected, then each claim links to a specific source Document and location (page/section). |
| AC-007 | REQ-007 | Given a question whose answer is not present in the Matter's Documents, when the lawyer asks it, then the Assistant responds that the information was not found, without fabricating an answer. |
| AC-008 | REQ-008 | Given an open Matter, when the lawyer creates a Deadline with a title and due date, then it appears in that Matter's Deadline list. |
| AC-009 | REQ-009 | Given a Deadline due in 3 days, when the notification schedule runs, then the lawyer receives a Notification 3 days before and again on the due date. |
| AC-010 | REQ-010 | Given a Matter with no open Deadlines, when the lawyer marks it Closed, then its status changes to "Closed" and its Documents/Deadlines remain viewable and searchable. |
| AC-011 | REQ-011 | Given Clients/Matters exist, when the lawyer searches by name, status, or date, then only matching records are returned. |
| AC-012 | REQ-012 | Given no active session, when any client/case data endpoint or page is requested, then access is denied until the lawyer authenticates. |
| AC-013 | REQ-013 | Given a Client with multiple Matters (open and closed), when the lawyer opens that Client's profile, then all of the Client's Matters are listed. |
| AC-014 | REQ-027 | Given a Document exists on a Matter, when the lawyer deletes it, then it no longer appears in that Matter's Document list, its file is removed from storage, and its DocumentChunks are gone. |
| AC-015 | REQ-008 | Given the New Deadline form, when the lawyer picks a due date before today (via the date picker or manual entry) and submits, then the request is rejected with a message stating the due date can't be in the past (BR-009). |

## 6. Key Entities & Domain Concepts

| Entity | Definition |
|---|---|
| **Lawyer (User)** | An authenticated individual using the system; belongs to one Firm account (a solo practitioner is a Firm of one). |
| **Firm** | An account grouping one or more Lawyers who share access to the same Clients/Matters (REQ-014). Data isolation is enforced at the Firm boundary (BR-008, NFR-004). |
| **Client** | A person or entity the Firm represents. Has profile/contact info and one or more Matters. |
| **Matter** | A single case/engagement for a Client. Has a status (Open/Closed), Documents, and Deadlines. The primary unit the AI Assistant's answers are scoped to (BR-005). |
| **Document** | A file (PDF/DOCX/scanned image) uploaded to a Matter. Extracted and indexed for retrieval (REQ-004); the source every AI Assistant citation must point to (BR-006). |
| **Deadline** | A dated event (hearing, filing, follow-up) linked to a Matter. Drives Notifications and gates Matter closure (BR-003, BR-004). |
| **Notification** | A reminder sent to a Lawyer ahead of a Deadline. |
| **AI Assistant / Chat** | The conversational interface over a Matter's Documents; every response is grounded and cited, or explicitly states the information is unavailable (BR-005, BR-006). |
| **Citation** | A pointer from an AI Assistant claim to a specific Document + location (page/section) — the mechanism that makes REQ-006/BR-006 verifiable. |
