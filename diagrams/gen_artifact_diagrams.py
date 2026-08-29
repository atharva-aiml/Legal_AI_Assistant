"""
Rebuilds the 4 diagrams from the "Chunk & Retrieve" artifact report, UPDATED to
match the current implementation after Phases 5-8 of RAG-Pipeline-Development-History.md:
  * exact-match retrieval for numbered identifiers      (gap #1, Phase 5)
  * vision captioning of embedded diagrams              (gap #2 Tier 1, Phase 6)
  * PDF images attributed to every real drawing page    (gap #6, Phase 7)
  * FULL_CONTEXT_CHAR_CAP 150K -> 400K + full_context signal  (gap #7, Phase 8)

Amber fill / [UPDATED] tag = changed since the report.

Run:  python gen_artifact_diagrams.py   then   python render_pngs.py A_ B_ C_ D_
"""
from gen_diagrams import (
    SVG, footer, title_block,
    PANEL, PANEL_BRD, INK, MUTE, FAINT, ARROW,
    NAVY, PURPLE, PURPLE_2, TEAL, AMBER, GREEN, RED,
    CARD, CARD_T, CARD_N, MONO,
)

UPD = "#FBF3E4"


def tag(s, x, y, text="UPDATED"):
    w = 20 + len(text) * 7.4
    s.rect(x - w, y, w, 22, rx=11, fill=AMBER, stroke="none", sw=0)
    s.text(x - w / 2, y + 15, text, size=11, fill="#fff", weight=700, anchor="middle")


# ===========================================================================
# A — UPLOAD TO STORED CHUNK   (artifact §02, updated)
# ===========================================================================
def dA():
    s = SVG(1680, 1140, "Upload to stored chunk")
    title_block(s, "Chunk & Retrieve · §02 — updated", "Upload → stored chunk",
                "IngestionService.ingest(): fetch → extract (adaptive) → chunk → embed → persist.  Amber = changed since the report.")

    s.banner(590, 132, 500, "POST /ingest/{document_id}   (Java writes /uploads · Python reads)", fill=NAVY, size=15)
    s.decision(620, 200, 440, "branch on MIME type", "app/infrastructure/extraction.py", stroke=PURPLE)

    by = 296
    s.node(60, by, 360, 208, "application/pdf → pdfplumber + pypdf", [
        "per-character font size + bold →",
        "  heading levels (body = weighted mode)",
        "find_tables() + bbox-exclude from prose",
        "real page numbers from PDF structure",
        "pypdf: embedded image objects",
    ], fill=CARD, stroke=PURPLE_2, title_fill=PURPLE, title_size=14)
    s.node(440, by, 360, 208, ".docx → python-docx", [
        "iter_block_items() = true document order",
        "'Heading N' / 'Title' styles → heading stack",
        "real <w:tbl> → rows as 'col: value' pairs",
        "<w:br w:type=\"page\"/> → real page counter",
        "  (only if the file has any; else None)",
    ], fill=CARD, stroke=PURPLE_2, title_fill=PURPLE, title_size=14)
    s.node(820, by, 320, 208, "image/*  and  text/plain", [
        "image → whole image OCR'd (EasyOCR),",
        "  one page, page_number = 1",
        "text/plain → UTF-8 decode, page = None",
        "  (generated drafts, V0.8)",
        "→ plain ExtractedPage, no segments",
    ], fill=PANEL, stroke=PANEL_BRD, title_size=14)

    # amber sidebar — the two things that changed since the report
    s.rect(1160, 200, 460, 304, rx=16, fill=UPD, stroke=AMBER, sw=2)
    tag(s, 1160 + 460 - 16, 186)
    s.text(1180, 232, "Embedded-image handling", size=15.5, fill=AMBER, weight=700)
    s.text(1180, 252, "(inside PDF & DOCX)", size=12, fill=MUTE)
    s.lines(1180, 282, [
        "gap #2 (Tier 1) — OCR alone was lossy:",
        "EasyOCR (character-exact) + gpt-4o-mini",
        "vision caption (step / arrow structure)",
        "→ _combine_ocr_and_caption() keeps both.",
        "NO_CONTENT sentinel → image dropped,",
        "never a placeholder chunk.",
    ], size=12.2, lh=17.5)
    s.lines(1180, 408, [
        "gap #6 — PDF's shared /Resources tree:",
        "_truly_drawn_xobject_identities() checks the",
        "page content stream (Do operator) → attribute",
        "to EVERY real drawing page; OCR + caption",
        "computed once per unique image (SHA-256).",
    ], size=12.2, lh=17.5)

    s.line(840, 252, 240, 296); s.line(840, 252, 620, 296); s.line(840, 252, 980, 296)

    s.text(600, 556, "PDF / DOCX  →  list[Segment]   (text · heading_path · chunk_type ∈ {prose, table_or_list, image} · element_number · page_number)",
           size=12.4, fill=MUTE, anchor="middle")
    s.text(600, 578, "image / text  →  plain ExtractedPage", size=12.4, fill=MUTE, anchor="middle")
    s.poly([(240, 504), (240, 530), (600, 530)], marker=False)
    s.poly([(620, 504), (620, 530), (600, 530)], marker=False)
    s.poly([(980, 504), (980, 530), (600, 530)], marker=False)
    s.line(600, 530, 600, 592, marker=True)

    s.node(90, 596, 1500, 150, "chunk_pages()   —   app/domain/chunk.py  (pure; branches on data SHAPE, not file type)", [
        "segments populated  →  _pack_typed_segments : greedy-pack to ~1000 chars (850 for table_or_list); NEVER merges across a",
        "                       heading / chunk_type / element_number / page_number change  ⇒  one chunk = exactly one real location",
        "no segments         →  _pack_segments : sentence-boundary greedy pack, ~150-char whole-sentence overlap",
        "shared abbreviation-aware sentence splitter (Pvt. / Ltd. / Rs. / month names / initials)",
    ], fill=CARD_T, stroke=TEAL, title_fill=TEAL, title_size=15)
    s.line(840, 746, 840, 780)

    s.node(90, 784, 720, 156, "Embed   —   app/infrastructure/embedding.py", [
        "all-MiniLM-L6-v2 · 384-dim · local · no API key · no per-call cost",
        "batch: embedder.embed([c.content for c in chunks])",
        "",
        "safety net: real token count vs the model's 256-token limit →",
        "WARNING log if it would still truncate  (backstop, not a block)",
    ], fill=PANEL, stroke=PANEL_BRD, title_size=15)
    s.node(870, 784, 720, 156, "Persist + terminal state   —   repository.py", [
        "INSERT INTO document_chunks (content, embedding, page_number,",
        "   section, chunk_type, element_number)  VALUES (…, CAST(:e AS vector), now())",
        "",
        "no extractable text → status = 'failed'  ·  any exception → 'failed'",
        "success → status = 'ready'   (Java marks 'failed' if Python is unreachable)",
    ], fill="#F3F6F2", stroke=GREEN, title_fill=GREEN, title_size=15)
    s.poly([(450, 940), (450, 968), (840, 968)], marker=False)
    s.poly([(1230, 940), (1230, 968), (840, 968)], marker=False)
    s.line(840, 968, 840, 992, marker=True)
    s.banner(590, 996, 500, "Document.status = 'ready'  →  queryable in chat", fill=NAVY, size=15)

    footer(s, "Legal AI Assistant  ·  updated from ingestion_service.py / extraction.py / chunk.py  ·  gaps #2 (Tier 1) & #6 closed 2026-08-25")
    s.save("A_upload_to_stored_chunk.svg")


# ===========================================================================
# B — THE TWO RETRIEVAL PATHS   (artifact §04, updated)
# ===========================================================================
def dB():
    s = SVG(1680, 1320, "The two retrieval paths")
    title_block(s, "Chunk & Retrieve · §04 — updated", "The two retrieval paths",
                "Cap raised 150K → 400K chars; an exact-identifier leg added; the answer now carries a full_context signal.  Amber = changed.")

    s.banner(620, 128, 440, "Lawyer asks a question", fill=NAVY, size=15)
    s.decision(600, 200, 480, "Matter has ≥ 1 ready Document?", "ready_document_count(matter)", stroke=RED)
    s.text(1120, 244, "no  →  HTTP 422  NO_READY_DOCUMENTS", size=12.5, fill=RED)
    s.line(840, 282, 840, 312)
    s.decision(600, 316, 480, "save user ChatMessage → Σ len(chunk.content)", "over ALL ready chunks", stroke=TEAL)
    s.line(840, 398, 840, 430)

    s.decision(560, 434, 560, "Σ chars  ≤  FULL_CONTEXT_CHAR_CAP  =  400,000",
               "was 150,000 — raised 2026-08-25 after a real API spike (~80K tokens)", stroke=AMBER, h=88)
    tag(s, 560 + 560 - 8, 420)

    s.line(700, 522, 430, 556); s.line(980, 522, 1250, 556)
    s.text(430, 550, "≤ CAP  ·  FULL CONTEXT", size=12.5, fill=GREEN, weight=700, anchor="middle")
    s.text(1250, 550, "> CAP  ·  HYBRID RETRIEVAL", size=12.5, fill=AMBER, weight=700, anchor="middle")

    # left column
    s.rect(80, 564, 660, 470, rx=16, fill="#F1F6F2", stroke=GREEN, sw=2)
    s.node(100, 582, 620, 150, "Every ready chunk → the LLM", [
        "no ranking · no threshold gate · no top-K",
        "nothing a broad question could miss",
        "the common case in practice",
    ], fill=PANEL, stroke=GREEN, title_fill=GREEN)
    s.node(100, 748, 620, 118, "full_context = True", [
        "returned to the lawyer on the response.",
        "The below-threshold no-LLM guarantee does",
        "NOT apply here — verification is the backstop.",
    ], fill=UPD, stroke=AMBER, title_fill=AMBER)
    tag(s, 100 + 620 - 8, 734)
    s.node(100, 882, 620, 130, "measured cost", [
        "whole-document calls 10–15.5 s (over the 8 s",
        "p95 target); narrow questions 2–7 s.",
        "Accepted with the user's sign-off.",
    ], fill=PANEL, stroke=PANEL_BRD)

    # right column
    s.rect(760, 564, 840, 588, rx=16, fill="#FBF6EC", stroke=AMBER, sw=2)
    s.node(780, 582, 800, 148, "Exact-identifier match   —   NEW (gap #1, 2026-08-25)", [
        "extract_identifier_refs(question) → any (page | section | table | image, N)?",
        "→ exact_match_chunks(): direct SQL on the real column",
        "   (page_number / element_number+chunk_type / section ~ '(^|> )N\\.')",
        "NO LIMIT · NO ranking · BYPASSES the relevance-threshold refusal",
    ], fill=UPD, stroke=AMBER, title_fill=AMBER, title_size=14.5)
    tag(s, 780 + 800 - 8, 568)
    s.node(780, 744, 800, 120, "Vector + keyword, in parallel", [
        "vector_search : top 20 by pgvector cosine  <=>",
        "keyword_search : top 20 by ts_rank over to_tsvector(section || ' ' || content),",
        "   OR-flipped tsquery so one absent word doesn't zero the match",
    ], fill=PANEL, stroke=AMBER, title_fill=AMBER, title_size=14.5)
    s.node(780, 878, 800, 88, "Reciprocal Rank Fusion  (k = 60)", [
        "fused[id] = Σ 1 / (60 + rank) over each list a chunk appears in — no hand-tuned weight.",
    ], fill=PANEL, stroke=PANEL_BRD, title_size=14.5)
    s.node(780, 980, 800, 152, "Gate & assemble", [
        "no exact hit  AND  max fused < 0.01  →  NO LLM call:",
        "   metadata exists → answer from real system facts only;  else fixed NOT_FOUND",
        "otherwise → exact chunks (uncapped)  +  top fused to fill CONTEXT_SIZE = 8",
        "low_confidence = (no exact hit) AND (max fused < 0.02)",
        "full_context = False   → UI note: \"this Matter is large…\"",
    ], fill=PANEL, stroke=PANEL_BRD, title_size=14.5)
    tag(s, 780 + 800 - 8, 966)

    s.poly([(410, 1034), (410, 1176), (840, 1176)], marker=False)
    s.poly([(1180, 1152), (1180, 1176), (840, 1176)], marker=False)
    s.line(840, 1176, 840, 1202, marker=True)
    s.banner(560, 1206, 560, "LLM generates, temp 0 — every factual sentence carries a [N] marker", fill=PURPLE, size=13.5)

    footer(s, "Legal AI Assistant  ·  updated from chat_service.py  ·  cap raise + full_context: Phase 8;  exact-match leg: Phase 5")
    s.save("B_two_retrieval_paths.svg")


# ===========================================================================
# C — FULL TRACE: a text query, end to end   (artifact §07, updated)
# ===========================================================================
def dC():
    s = SVG(1680, 1060, "Query trace — end to end")
    title_block(s, "Chunk & Retrieve · §07 — updated", "Full trace: \"What was the settlement amount?\"",
                "A large-Matter query through the real pipeline. Example corpus size and the explicit identifier check updated to current behaviour.")

    lanes = ["Lawyer", "ChatService", "Embedder", "Postgres", "gpt-4o-mini"]
    lx = [140, 440, 780, 1030, 1370]
    for name, x in zip(lanes, lx):
        s.rect(x - 92, 138, 184, 40, rx=10, fill="url(#navyG)", stroke="none", sw=0)
        s.text(x, 163, name, size=13.5, fill="#fff", weight=700, anchor="middle")
        s.line(x, 178, x, 980, stroke=PANEL_BRD, sw=1.4, marker=False)

    steps = [
        (0, 1, '"What was the settlement amount?"', 0),
        (1, 3, "Σ len(content) over ready chunks", 0),
        (3, 1, "520,000 chars  →  > 400,000 cap  →  HYBRID path", 1),
        (1, 1, "extract_identifier_refs(q) → []   →   no exact-match leg fires here", 1),
        (1, 2, "embed(question)  →  384-dim vector", 0),
        (1, 3, "vector_search top 20 (cosine <=>)   ·   keyword_search top 20 (tsquery OR)", 0),
        (3, 1, "two ranked id lists", 0),
        (1, 1, "Reciprocal Rank Fusion (k=60)  →  top 8  +  document-metadata items", 0),
        (1, 4, 'system prompt + "[41] (Page 54, Section: \\"53. Access to Justice > …\\") The 1989 settlement…" + question', 0),
        (4, 1, '"The settlement required US$470 million [41]."', 0),
        (1, 1, "verify_citations(): every sentence has a valid [N]? keep it.   (one corrective regen if not)", 0),
        (1, 3, "INSERT chat_messages, citations(document_id, page=54, section=…, excerpt=content[:300])", 0),
        (1, 0, 'answer + citation chip: "Apex_Meridian_…pdf, p.54, 53. Access to Justice > …"  ·  full_context = False note', 1),
    ]
    y = 214
    for a, b, label, upd in steps:
        xa, xb = lx[a], lx[b]
        if a == b:
            s.line(xa - 2, y - 12, xa + 14, y - 12, marker=True)
            tx, anchor = xa + 22, "start"
        else:
            s.line(xa, y - 12, xb, y - 12, marker=True)
            tx, anchor = min(xa, xb) + 16, "start"
        col = AMBER if upd else MUTE
        s.text(tx, y + 4, label, size=12.1, fill=col, weight=600 if upd else 400, anchor=anchor, family=MONO)
        if upd:
            s.text(tx, y + 20, "[updated vs. the report]", size=10.5, fill=AMBER, italic=True)
        y += 62 if upd else 50

    footer(s, "Legal AI Assistant  ·  updated from chat_service.py — 400K cap (Phase 8) + explicit identifier check (Phase 5)")
    s.save("C_query_trace_sequence.svg")


# ===========================================================================
# D — GROUNDING: why answers can't free-float   (artifact §08, unchanged logic)
# ===========================================================================
def dD():
    s = SVG(1680, 1060, "Grounding — why answers can't free-float")
    title_block(s, "Chunk & Retrieve · §08 — still current", "Grounding: why answers can't free-float",
                "Unchanged since the report — verification is code, not trust. Restyled for consistency; the logic is identical.")

    s.node(80, 168, 470, 128, "LLM generates a raw answer", [
        "temperature = 0",
        "every factual sentence must carry a [N] marker",
        "(system-prompt rule, with a right-vs-wrong example)",
    ], fill=CARD, stroke=PURPLE, title_fill=PURPLE)
    s.line(550, 232, 604, 232)
    s.node(604, 150, 540, 164, "verify_citations()  —  pure function, code not trust", [
        "split into sentences (abbreviation-aware splitter)",
        "for each: markers = every [N];  valid = 1 ≤ N ≤ num_sources",
        "  valid marker present → keep the sentence, record the marker",
        "  no marker / all out of range → DROP the sentence",
    ], fill="#F1F6F2", stroke=GREEN, title_fill=GREEN, title_size=15)

    s.line(874, 314, 874, 352)
    s.decision(654, 356, 440, "any sentence dropped?", "", stroke=INK, h=62)

    s.line(700, 418, 380, 460); s.text(470, 448, "yes", size=12, fill=MUTE)
    s.line(1050, 418, 1330, 460); s.text(1180, 448, "no", size=12, fill=MUTE)

    s.node(120, 464, 520, 118, "one corrective regeneration", [
        '"cite ONLY items 1..N, state only what they support"',
        "retried exactly once",
    ], fill=UPD, stroke=AMBER, title_fill=AMBER)
    s.node(1120, 464, 470, 96, "answer stands as-is", [
        "nothing was unsupported — pass straight through",
    ], fill=PANEL, stroke=PANEL_BRD)

    s.line(360, 582, 360, 620)
    s.decision(150, 624, 460, "retry fully grounded?", "", stroke=INK, h=62)
    s.line(270, 686, 270, 724); s.text(250, 712, "yes", size=12, fill=MUTE)
    s.node(120, 728, 360, 96, "use the retry", ["it verified clean"], fill=PANEL, stroke=PANEL_BRD)
    s.line(500, 686, 560, 724); s.text(560, 712, "no", size=12, fill=MUTE)
    s.node(500, 728, 580, 96, "keep the first stripped version", ["+ a visible gap note appended to the answer"], fill=PANEL, stroke=PANEL_BRD)

    s.poly([(300, 824), (300, 872), (860, 872)], marker=False)
    s.poly([(790, 824), (790, 872), (860, 872)], marker=False)
    s.poly([(1355, 560), (1355, 872), (860, 872)], marker=False)
    s.line(860, 872, 860, 898, marker=True)
    s.banner(560, 902, 560, "validate_assistant_message()  —  BR-006 write-path invariant", fill=NAVY, size=13.5)
    s.text(840, 972, "content must be the fixed NOT_FOUND / OUT_OF_SCOPE string, OR carry ≥ 1 real citation — otherwise an exception, and the row is never written.",
           size=12, fill=MUTE, anchor="middle")

    footer(s, "Legal AI Assistant  ·  from citation_verification.py + chat_service.py + domain/chat.py  ·  logic unchanged since the report")
    s.save("D_grounding_validation.svg")


if __name__ == "__main__":
    dA(); dB(); dC(); dD()
    print("done")
