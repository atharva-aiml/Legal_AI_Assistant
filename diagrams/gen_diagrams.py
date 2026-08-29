"""
Generates the Legal AI Assistant LinkedIn-series architecture diagrams as SVG.
Every box/label is derived from the actual codebase (backend-python/app/**,
backend-java/**, database/schema/schema.ts) and the project docs
(06-AI-Architecture.md, RAG-Pipeline-Development-History.md, 05-System-Architecture.md).

Run:  python gen_diagrams.py   ->  writes *.svg into this folder
Then render each to PNG with Chrome headless (see render_pngs.sh).
"""
import html
import os

OUT = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- palette / type
BG        = "#EEF1F6"
PANEL     = "#FFFFFF"
PANEL_BRD = "#D3DAE6"
INK       = "#161B26"
MUTE      = "#4A5568"
FAINT     = "#7A869A"
ARROW     = "#5B6B85"

NAVY      = "#1E3A5F"   # Java / CRUD / orchestration
NAVY_2    = "#2C4A73"
PURPLE    = "#5B3FA6"   # Python / AI
PURPLE_2  = "#6D4FBF"
TEAL      = "#1F6F70"   # retrieval / DB reads
TEAL_2    = "#2C8A8B"
SLATE     = "#2C333F"   # storage / data
AMBER     = "#9A6B12"   # external paid services
GREEN     = "#256B4A"   # validation / grounding
RED       = "#9B2C2C"   # failure / refusal
CARD      = "#F4F1FB"   # light purple fill
CARD_T    = "#E7F1F1"   # light teal fill
CARD_N    = "#E9EEF6"   # light navy fill

SERIF = "Georgia, 'Times New Roman', serif"
SANS  = "'Segoe UI', system-ui, -apple-system, Arial, sans-serif"
MONO  = "'Consolas', 'SFMono-Regular', Menlo, monospace"


def esc(s):
    return html.escape(str(s), quote=True)


class SVG:
    def __init__(self, w, h, title):
        self.w, self.h = w, h
        self.parts = []
        self.title = title

    def raw(self, s):
        self.parts.append(s)

    def rect(self, x, y, w, h, rx=14, fill=PANEL, stroke=PANEL_BRD, sw=1.5, dash=None, opacity=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.raw(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{rx}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d} opacity="{opacity}"/>')

    def line(self, x1, y1, x2, y2, stroke=ARROW, sw=2, dash=None, marker=True):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        m = ' marker-end="url(#arrow)"' if marker else ""
        self.raw(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
                 f'stroke-width="{sw}"{d}{m} stroke-linecap="round"/>')

    def poly(self, pts, stroke=ARROW, sw=2, dash=None, marker=True, fill="none"):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        m = ' marker-end="url(#arrow)"' if marker else ""
        p = " ".join(f"{a},{b}" for a, b in pts)
        self.raw(f'<polyline points="{p}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"'
                 f'{d}{m} stroke-linejoin="round" stroke-linecap="round"/>')

    def text(self, x, y, s, size=17, fill=INK, weight=400, anchor="start",
             family=SANS, spacing=None, italic=False):
        ls = f' letter-spacing="{spacing}"' if spacing is not None else ""
        it = ' font-style="italic"' if italic else ""
        self.raw(f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
                 f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{ls}{it}>{esc(s)}</text>')

    def lines(self, x, y, rows, size=14.5, fill=MUTE, lh=20, anchor="start", weight=400, family=SANS):
        for i, r in enumerate(rows):
            self.text(x, y + i * lh, r, size=size, fill=fill, anchor=anchor, weight=weight, family=family)

    def node(self, x, y, w, h, title, rows=None, fill=PANEL, stroke=PANEL_BRD,
             title_fill=INK, rx=14, title_size=17.5, badge=None, badge_fill=None):
        self.rect(x, y, w, h, rx=rx, fill=fill, stroke=stroke, sw=1.8)
        self.text(x + 18, y + 30, title, size=title_size, fill=title_fill, weight=700)
        if badge:
            bw = 8 + len(badge) * 7.2
            self.rect(x + w - bw - 14, y + 14, bw, 22, rx=11,
                      fill=badge_fill or "#00000010", stroke="none", sw=0)
            self.text(x + w - bw / 2 - 14, y + 29, badge, size=12, fill="#fff",
                      weight=700, anchor="middle", family=SANS)
        if rows:
            self.lines(x + 18, y + 56, rows, size=13.8, lh=19.5, fill=MUTE)

    def chip(self, x, y, w, s, fill, tcol="#fff", h=34, size=13.5, weight=700, rx=9):
        self.rect(x, y, w, h, rx=rx, fill=fill, stroke="none", sw=0)
        self.text(x + w / 2, y + h / 2 + 5, s, size=size, fill=tcol, weight=weight, anchor="middle")

    def banner(self, x, y, w, s, sub=None, fill=NAVY, size=17):
        h = 62 if sub else 48
        cx = x + w / 2
        need = len(s) * size * 0.56 + 56
        w = max(w, need)
        x = cx - w / 2
        self.rect(x, y, w, h, rx=12, fill=fill, stroke="none", sw=0)
        self.text(cx, y + (27 if sub else 30), s, size=size, fill="#fff",
                  weight=700, anchor="middle", family=SERIF)
        if sub:
            self.text(cx, y + 48, sub, size=13, fill="#ffffffcc", weight=400, anchor="middle")

    def decision(self, x, y, w, title, sub, stroke=INK, h=82):
        cx = x + w / 2
        self.rect(x, y, w, h, rx=12, fill=PANEL, stroke=stroke, sw=1.9)
        self.text(cx, y + 32, title, size=15.5, fill=INK, weight=700, family=MONO, anchor="middle")
        self.text(cx, y + 56, sub, size=11.8, fill=MUTE, anchor="middle")

    def render(self):
        head = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">
<defs>
<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
  <path d="M0,0 L10,5 L0,10 z" fill="{ARROW}"/>
</marker>
<linearGradient id="navyG" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="{NAVY_2}"/><stop offset="1" stop-color="{NAVY}"/>
</linearGradient>
<linearGradient id="purpG" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="{PURPLE_2}"/><stop offset="1" stop-color="{PURPLE}"/>
</linearGradient>
<linearGradient id="tealG" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="{TEAL_2}"/><stop offset="1" stop-color="{TEAL}"/>
</linearGradient>
</defs>
<rect width="{self.w}" height="{self.h}" fill="{BG}"/>'''
        return head + "\n" + "\n".join(self.parts) + "\n</svg>\n"

    def save(self, name):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(self.render())
        print("wrote", name)


def footer(s, txt="Legal AI Assistant  ·  architecture derived from source  ·  Part 2/3 of the LinkedIn series"):
    s.text(s.w - 30, s.h - 22, txt, size=12, fill=FAINT, anchor="end")


def title_block(s, kicker, title, sub=None):
    s.text(40, 46, kicker.upper(), size=13, fill=PURPLE, weight=700, spacing="2.5")
    s.text(40, 82, title, size=30, fill=INK, weight=700, family=SERIF)
    if sub:
        s.text(40, 110, sub, size=15, fill=MUTE)


# ===========================================================================
# 01 — HIGH-LEVEL SYSTEM ARCHITECTURE
# ===========================================================================
def d01():
    s = SVG(1680, 1140, "High-level architecture")
    title_block(s, "System architecture", "Three services, one database, one hard rule",
                "The browser never touches the database. Every read/write is an HTTP call to Java (CRUD/auth) or Python (AI).")

    # Browser
    s.node(660, 140, 360, 66, "Lawyer's browser", fill="url(#navyG)", stroke="none", title_fill="#fff")
    s.text(840, 186, "Next.js 15 App Router · React 19 · UI only", size=12.5, fill="#ffffffcc", anchor="middle")

    # Frontend
    s.node(560, 250, 560, 96, "Frontend  —  Next.js (SD-001)", fill=PANEL, stroke=PANEL_BRD)
    s.lines(578, 300, [
        "Server Components call javaFetch() (forwards session cookie server-side);",
        "client components fetch JAVA_API_URL_PUBLIC with credentials:'include'.",
        "No DB driver. No /api routes. No business logic. Renders 16 screens.",
    ], size=12.7, lh=17)

    s.line(840, 346, 840, 392)

    # Java
    s.rect(120, 400, 720, 250, rx=16, fill=CARD_N, stroke=NAVY, sw=2)
    s.text(140, 432, "Java backend — Spring Boot 4.1 / Java 21  (SD-002 / SD-003)", size=16.5, fill=NAVY, weight=700)
    s.text(140, 456, "Owns auth + all CRUD  ·  \"the rest of the backend\"", size=12.8, fill=MUTE)
    for i, (t, d) in enumerate([
        ("Auth", "BCrypt(12) · SHA-256 session token · httpOnly cookie · per-request DB check"),
        ("Domain CRUD", "Firm · Client · Matter · Document · Deadline · Notification · Template"),
        ("Isolation", "CurrentLawyerResolver.resolve() per controller method — BR-008, 404 not 403"),
        ("AI gateway", "HttpChatGateway / HttpIngestionTrigger — calls Python, relays response verbatim"),
    ]):
        y = 476 + i * 42
        s.chip(140, y, 130, t, NAVY, size=12.5)
        s.text(285, y + 23, d, size=12.6, fill=MUTE)

    # Python
    s.rect(880, 400, 680, 250, rx=16, fill=CARD, stroke=PURPLE, sw=2)
    s.text(900, 432, "Python backend — FastAPI / Python 3.13  (SD-004 / SD-005)", size=16.5, fill=PURPLE, weight=700)
    s.text(900, 456, "Owns all AI  ·  internal only — never called by the browser", size=12.8, fill=MUTE)
    for i, (t, d) in enumerate([
        ("Ingestion", "extract → adaptive chunk → embed (all-MiniLM-L6-v2) → write document_chunks"),
        ("AI Chat", "full-context OR hybrid retrieval → grounded prompt → gpt-4o-mini → verify citations"),
        ("Grounding", "SQL matter-scope · below-threshold refusal · per-sentence citation check"),
        ("Layering", "domain (pure) → application (Protocol ports) → infrastructure → web"),
    ]):
        y = 476 + i * 42
        s.chip(900, y, 130, t, PURPLE, size=12.5)
        s.text(1045, y + 23, d, size=12.6, fill=MUTE)

    s.line(480, 400, 480, 346, marker=True)
    s.text(492, 372, "HTTPS / JSON  (today)", size=12, fill=MUTE)
    s.poly([(700, 346), (700, 375), (1180, 375), (1180, 400)], dash="5 5")
    s.text(940, 370, "chat & upload proxied through Java (auth + BR-008 first)", size=11.5, fill=FAINT, anchor="middle")

    s.line(300, 650, 300, 706)
    s.line(1180, 650, 1180, 706)
    s.line(430, 650, 620, 706, marker=True)

    # Data layer
    s.rect(120, 714, 900, 210, rx=16, fill=PANEL, stroke=PANEL_BRD, sw=1.8)
    s.text(140, 746, "Data layer", size=16.5, fill=SLATE, weight=700)
    s.node(140, 762, 270, 140, "PostgreSQL 16", [
        "+ pgvector (vector 384)",
        "schema owned by /database",
        "(Drizzle Kit, TS) — neither",
        "backend's ORM authors it;",
        "both map with validate-only",
    ], fill=CARD_T, stroke=TEAL, title_fill=TEAL)
    s.node(430, 762, 270, 140, "Local filesystem  /uploads", [
        "dev stand-in for Cloudflare R2",
        "Java writes · Python reads",
        "same directory, both services",
        "R2StorageService swaps in",
        "behind one interface later",
    ], fill=PANEL, stroke=PANEL_BRD)
    s.node(720, 762, 280, 140, "No message queue (yet)", [
        "Java → Python ingestion is a",
        "direct fire-and-forget HTTP call",
        "chat call is blocking (browser",
        "waits). BullMQ/Redis deferred",
        "until a real reliability need.",
    ], fill=PANEL, stroke=PANEL_BRD)

    # External
    s.rect(1060, 714, 500, 210, rx=16, fill=PANEL, stroke=AMBER, sw=1.8)
    s.text(1080, 746, "External services", size=16.5, fill=AMBER, weight=700)
    s.node(1080, 762, 210, 140, "OpenAI gpt-4o-mini", [
        "chat generation (temp 0)",
        "+ vision captioning of",
        "embedded diagrams",
        "the only paid API in the",
        "system",
    ], fill="#FBF3E4", stroke=AMBER, title_fill=AMBER)
    s.node(1310, 762, 230, 140, "Runs locally (no API)", [
        "EasyOCR 1.7.2  (CPU)",
        "all-MiniLM-L6-v2  (384-dim,",
        "sentence-transformers)",
        "→ zero per-call cost, fits the",
        "solo / low-budget constraint",
    ], fill=PANEL, stroke=PANEL_BRD)

    s.poly([(1180, 650), (1180, 690), (1185, 690), (1185, 714)], marker=True)

    footer(s)
    s.save("01_high_level_architecture.svg")


# ===========================================================================
# 02 — USER JOURNEY  (J1: upload -> cited answer)
# ===========================================================================
def d02():
    s = SVG(1680, 1000, "User journey")
    title_block(s, "User journey  ·  J1 (core value proof)", "From an empty Matter to a cited answer",
                "What actually happens between a lawyer dropping a PDF and reading an answer with page-level citations.")

    steps = [
        ("1  Open a Matter", "SCR-09 Matter Detail. Chat tab is disabled — \"Upload a document first.\"", NAVY),
        ("2  Upload files", "POST /api/matters/:id/documents (multipart). Java stores the file, writes a\nDocument row (status=processing), fires ingestion at Python without waiting.", NAVY),
        ("3  Ingestion runs", "Python: extract text/tables/images → OCR + vision caption diagrams →\nadaptive chunk → embed each chunk → INSERT document_chunks → status=ready.", PURPLE),
        ("4  Poll to Ready", "Frontend polls /documents every 3s. \"Uploading → Processing → Ready.\"\nA bad/empty file resolves to status=failed with a visible error_message.", NAVY),
        ("5  Ask a question", "POST /api/matters/:id/chat { question }. Java checks session + Matter\nownership (BR-008), then proxies to Python's internal /chat/:matterId.", PURPLE),
        ("6  Retrieve", "Corpus ≤ 400K chars → send every chunk. Otherwise hybrid retrieval:\nexact-identifier + vector + keyword → Reciprocal Rank Fusion → threshold gate.", TEAL),
        ("7  Generate", "Numbered context + document metadata + last 4 turns → gpt-4o-mini at\ntemperature 0, with a citation-required system prompt.", AMBER),
        ("8  Verify citations", "Every factual sentence must carry a [n] marker resolving to a real\nretrieved item. Unsupported sentences are stripped; one corrective retry.", GREEN),
        ("9  Persist + render", "Save ChatMessage + one Citation row per distinct source. UI reveals the\nanswer with a client-side typing effect; citations link to document + page/section.", NAVY),
    ]
    x = 60
    w = 1560
    y = 150
    for i, (t, d, col) in enumerate(steps):
        h = 78 if "\n" in d else 62
        s.rect(x, y, w, h, rx=12, fill=PANEL, stroke=PANEL_BRD, sw=1.6)
        s.rect(x, y, 8, h, rx=0, fill=col, stroke="none", sw=0)
        s.text(x + 26, y + 28, t, size=16.5, fill=INK, weight=700)
        for j, ln in enumerate(d.split("\n")):
            s.text(x + 320, y + 24 + j * 19, ln, size=13, fill=MUTE)
        if i < len(steps) - 1:
            s.line(x + w / 2, y + h + 1, x + w / 2, y + h + 13, sw=1.8)
        y += h + 14

    footer(s, "Legal AI Assistant  ·  journey J1 from 03-UX-Product-Design.md, verified end-to-end by tests/e2e/chat.spec.ts")
    s.save("02_user_journey.svg")


# ===========================================================================
# 03 — DOCUMENT INGESTION ARCHITECTURE
# ===========================================================================
def d03():
    s = SVG(1680, 1180, "Document ingestion architecture")
    title_block(s, "Pipeline  ·  SD-004  (backend-python)", "Document ingestion — adaptive by content, one fixed chunk shape",
                "IngestionService.ingest(): fetch → extract → chunk → embed → persist. Every path ends in a visible Document status.")

    s.banner(560, 140, 560, "POST /ingest/{document_id}   (called once by Java right after upload)", fill=NAVY)

    # extraction lane
    s.rect(60, 230, 1560, 300, rx=16, fill=PANEL, stroke=PURPLE, sw=1.8)
    s.text(80, 262, "1 · Extraction   —   app/infrastructure/extraction.py   (branches on MIME type)", size=16, fill=PURPLE, weight=700)

    s.node(80, 282, 360, 228, "PDF  →  pdfplumber + pypdf", [
        "• body font size = char-weighted mode",
        "• bold & larger-than-body ⇒ heading level",
        "• running header/footer = repeats on >50%",
        "  of real pages (not a raw count)",
        "• find_tables() + bbox-exclude from prose",
        "• real page numbers from PDF structure",
        "• images: content-stream Do-check →",
        "  every true drawing page, SHA-256 dedup",
    ], fill=CARD, stroke=PURPLE_2, title_fill=PURPLE, title_size=14.5)

    s.node(460, 282, 360, 228, "DOCX  →  python-docx", [
        "• iter_block_items() = true document order",
        "• heading stack from paragraph.style 'Heading N'",
        "• real <w:tbl> objects → row = 'col: value' pairs",
        "• page numbers from <w:br w:type=\"page\"/>",
        "  markers when present, else honest None",
        "• embedded images via blip relationships",
        "• image caption cached by content hash",
    ], fill=CARD, stroke=PURPLE_2, title_fill=PURPLE, title_size=14.5)

    s.node(840, 282, 350, 228, "Images  →  EasyOCR", [
        "• standalone image upload = 1 OCR pass",
        "• page_number = 1",
        "• plain text path (no segments)",
        "",
        "text/plain  → UTF-8 decode",
        "(generated drafts, V0.8)",
    ], fill=PANEL, stroke=PANEL_BRD, title_size=14.5)

    s.node(1210, 282, 390, 228, "Embedded diagrams  →  OCR + Vision", [
        "EasyOCR: character-exact but loses",
        "structure.  gpt-4o-mini vision caption:",
        "reconstructs the step/arrow flow.",
        "_combine_ocr_and_caption() keeps both.",
        "NO_CONTENT sentinel ⇒ blank/decorative",
        "image dropped, never a placeholder chunk.",
    ], fill="#FBF3E4", stroke=AMBER, title_fill=AMBER, title_size=14.5)

    s.text(840, 555, "Output of extraction:  a list of ExtractedPage, each carrying raw text OR a list of typed Segment "
                     "(heading_path, chunk_type ∈ {prose, table_or_list, image}, element_number, page_number)",
           size=12.8, fill=MUTE, anchor="middle")

    s.line(840, 568, 840, 600)

    # chunk lane
    s.rect(60, 604, 1560, 210, rx=16, fill=PANEL, stroke=TEAL, sw=1.8)
    s.text(80, 636, "2 · Chunking   —   app/domain/chunk.py   (pure, zero I/O — branches on data SHAPE, not file type)", size=16, fill=TEAL, weight=700)
    s.node(80, 656, 470, 144, "Greedy sentence-boundary packer", [
        "CHUNK_SIZE_CHARS = 1000  (~200 tokens at this",
        "corpus's real ~5.0 chars/token)   overlap = 150",
        "TABLE_CHUNK_SIZE_CHARS = 850  (denser text)",
        "shared abbreviation-aware sentence splitter",
        "(Pvt. / Ltd. / Rs. / month names / initials)",
    ], fill=CARD_T, stroke=TEAL_2, title_fill=TEAL, title_size=14)
    s.node(570, 656, 480, 144, "Hard chunk boundaries (never merged across)", [
        "• a real page change      • a heading change",
        "• a chunk_type change     • an element_number change",
        "⇒ a chunk never spans two pages, two sections,",
        "  or two different tables — so a citation always",
        "  points at exactly one real location.",
    ], fill=PANEL, stroke=PANEL_BRD, title_size=14)
    s.node(1070, 656, 530, 144, "Safety net", [
        "SentenceTransformerEmbedder checks each text's",
        "real token count vs the model's 256-token limit",
        "and logs a warning if it would still truncate —",
        "a silent truncation must never be silent twice.",
        "(a real bug: old 2800-char size truncated 45–100% of chunks)",
    ], fill=PANEL, stroke=PANEL_BRD, title_size=14)

    s.line(840, 818, 840, 850)

    # embed + persist
    s.rect(60, 854, 1560, 250, rx=16, fill=PANEL, stroke=SLATE, sw=1.8)
    s.text(80, 886, "3 · Embed & persist   —   app/infrastructure/embedding.py  +  repository.py", size=16, fill=SLATE, weight=700)
    s.node(80, 906, 470, 180, "Embed", [
        "all-MiniLM-L6-v2  (sentence-transformers 5.7)",
        "384 dimensions · runs locally · no API key",
        "no per-call cost · ~53 ms per chunk",
        "model loaded once per process (lazy singleton)",
        "batch: embedder.embed([c.content for c in chunks])",
    ], fill=PANEL, stroke=PANEL_BRD, title_size=14.5)
    s.node(570, 906, 480, 180, "Persist  (raw SQL, explicit ::vector cast)", [
        "INSERT INTO document_chunks",
        "  (document_id, page_number, section,",
        "   chunk_type, element_number, content,",
        "   embedding, created_at)",
        "  VALUES (…, CAST(:embedding AS vector), now())",
    ], fill=PANEL, stroke=PANEL_BRD, title_size=14.5)
    s.node(1070, 906, 530, 180, "Terminal state — no failure is invisible", [
        "no extractable text  → mark_failed(\"No extractable",
        "                       text found in this document.\")",
        "any exception        → mark_failed(str(e)[:500])",
        "success              → mark_ready(); status='ready'",
        "Java marks 'failed' if it can't even reach Python.",
    ], fill="#F3F6F2", stroke=GREEN, title_fill=GREEN, title_size=14.5)

    footer(s, "Legal AI Assistant  ·  from app/application/ingestion_service.py, extraction.py, chunk.py  ·  Part 3/3")
    s.save("03_document_ingestion_architecture.svg")


# ===========================================================================
# 04 — QUERY PROCESSING ARCHITECTURE
# ===========================================================================
def d04():
    s = SVG(1680, 1270, "Query processing architecture")
    title_block(s, "Pipeline  ·  SD-005  ChatService._answer()", "Query processing — two regimes, chosen by corpus size",
                "One code path, one decision: does the whole Matter fit in a single model call, or does retrieval have to gate and rank?")

    s.banner(590, 138, 500, "POST /api/matters/:id/chat  →  Java (auth + BR-008)  →  Python", fill=NAVY, size=15)

    s.decision(560, 218, 560, "ready_document_count(matter) == 0 ?",
               "if yes  →  HTTP 422  NoReadyDocumentsError  ·  \"upload a document first\", never a guess", stroke=RED)
    s.line(840, 300, 840, 336)

    s.decision(540, 340, 600, "all_ready_chunks(matter) · document_metadata(matter)",
               "matter-scoped + status='ready', hard-filtered in SQL (BR-005)", stroke=TEAL)
    s.line(840, 422, 840, 458)

    s.decision(560, 462, 560, "Σ len(chunk.content)  ≤  FULL_CONTEXT_CHAR_CAP  (400,000)",
               "~34% headroom under gpt-4o-mini's 128K-token ceiling", stroke=INK)

    s.poly([(700, 544), (700, 566), (435, 566), (435, 588)], marker=True)
    s.poly([(980, 544), (980, 566), (1245, 566), (1245, 588)], marker=True)
    s.text(455, 560, "SMALL CORPUS", size=12.5, fill=GREEN, weight=700)
    s.text(1118, 560, "LARGE CORPUS", size=12.5, fill=AMBER, weight=700)

    # left: full context
    s.rect(90, 592, 690, 476, rx=16, fill="#F1F6F2", stroke=GREEN, sw=2)
    s.text(110, 626, "Full-context path   (the common case)", size=16, fill=GREEN, weight=700)
    s.node(110, 644, 650, 158, "Send every Ready chunk — no ranking", [
        "• no relevance threshold, no top-K cutoff",
        "• a broad question (\"complete chronology\",",
        "  \"every important date\") cannot miss content",
        "  that simply wasn't in a ranked top-8",
        "• full_context = True  → returned to the lawyer",
    ], fill=PANEL, stroke=GREEN, title_fill=GREEN)
    s.node(110, 818, 650, 110, "Real, disclosed tradeoff", [
        "Whole-document calls measured 10–15.5 s — over",
        "the 8 s p95 target. Narrow questions stay 2–7 s.",
        "Accepted with the user's sign-off, for completeness.",
    ], fill=PANEL, stroke=PANEL_BRD)
    s.node(110, 944, 650, 108, "The below-threshold no-LLM guarantee does NOT apply here", [
        "the model always gets the corpus and decides what's",
        "answerable — backed by post-generation citation",
        "verification, not by a pre-LLM refusal gate.",
    ], fill=PANEL, stroke=PANEL_BRD, title_size=14.5)

    # right: ranked
    s.rect(900, 592, 690, 476, rx=16, fill="#FBF6EC", stroke=AMBER, sw=2)
    s.text(920, 626, "Hybrid retrieval + RRF  (large Matters only)", size=16, fill=AMBER, weight=700)
    s.node(920, 644, 650, 132, "Three parallel lookups, all matter-scoped", [
        "exact_match_chunks(refs)  — regex pulls \"page 54\",",
        "   \"table 3\" etc. → direct SQL on the real column",
        "vector_search  — pgvector cosine, 20 candidates",
        "keyword_search — Postgres FTS (OR-flipped), 20 cand.",
    ], fill=PANEL, stroke=AMBER, title_fill=AMBER)
    s.node(920, 792, 650, 96, "Fuse  —  Reciprocal Rank Fusion (k=60)", [
        "score(chunk) = Σ 1/(k + rank) over the lists it appears in.",
        "No hand-tuned blend weight between two score scales.",
    ], fill=PANEL, stroke=PANEL_BRD)
    s.node(920, 904, 650, 148, "Threshold gate  (content only)", [
        "max fused score < 0.01  → no LLM call. Try metadata-",
        "  only if a structural question; else fixed NOT_FOUND.",
        "< 0.02 → answer, flagged low_confidence in the UI.",
        "exact-match hit → always included, bypasses the gate,",
        "  never capped at CONTEXT_SIZE (8), never low-confidence.",
    ], fill=PANEL, stroke=PANEL_BRD)

    s.poly([(435, 1068), (435, 1098), (840, 1098), (840, 1120)], marker=True)
    s.poly([(1245, 1068), (1245, 1098), (840, 1098)], marker=False)
    s.banner(560, 1124, 560, "→  Generation & citation verification  (next diagram)", fill=PURPLE, size=15)

    footer(s, "Legal AI Assistant  ·  from app/application/chat_service.py  ·  numbers are current constants, not final-tuned")
    s.save("04_query_processing_architecture.svg")


# ===========================================================================
# 05 — RETRIEVAL ARCHITECTURE  (deep)
# ===========================================================================
def d05():
    s = SVG(1680, 980, "Retrieval architecture")
    title_block(s, "RAG deep-dive  ·  retrieval", "Hybrid retrieval: exact + semantic + lexical, fused",
                "Legal text leans on exact tokens — party names, statute numbers, \"§54\". Semantic search blurs those; keyword search catches them; RRF merges both without a magic weight.")

    s.node(660, 150, 360, 60, "User question  (current turn only)", fill="url(#navyG)", stroke="none", title_fill="#fff")
    s.text(840, 232, "retrieval always re-runs on the current question — never the whole conversation (prevents topic drift)", size=12, fill=MUTE, anchor="middle")

    # three columns
    cols = [
        (70, TEAL, "Exact-identifier match", [
            "extract_identifier_refs(question) — pure regex over",
            "page / pg / section / sec / table / tbl / image / img /",
            "figure / fig  (+ optional \"no.\" / \"#\") → (kind, N) pairs.",
            "",
            "SQL, one branch per ref, UNION'd:",
            "  page   → dc.page_number = N",
            "  table  → element_number = N AND chunk_type='table_or_list'",
            "  image  → element_number = N AND chunk_type='image'",
            "  section→ dc.section ~ '(^|> )N\\.'   (breadcrumb-anchored)",
            "",
            "No LIMIT. No ranking. A page's own chunk count is",
            "small and bounded — capping it would re-break the",
            "completeness this exists to guarantee.",
        ]),
        (580, PURPLE, "Vector similarity", [
            "embed the question with the SAME model used at",
            "ingestion — all-MiniLM-L6-v2, 384-dim.",
            "",
            "ORDER BY dc.embedding <=> CAST(:q AS vector)",
            "LIMIT 20      (pgvector cosine distance)",
            "",
            "Catches paraphrase / conceptual matches:",
            "\"how long is the lease\" ≈ \"the term is 36 months\".",
            "",
            "WHERE matter_id = :m AND documents.status='ready'",
            "— the isolation is a SQL predicate, not a prompt",
            "instruction the model could ignore.",
        ]),
        (1090, AMBER, "Keyword / full-text", [
            "Postgres to_tsvector / to_tsquery, English config.",
            "",
            "searchable = section || ' ' || content   — a heading's",
            "own words never appear in its body prose, so folding",
            "section in is what makes \"Access to Justice\" findable.",
            "",
            "plainto_tsquery ANDs every word ⇒ one word absent",
            "from the source zeroes the match. Fix: reuse its",
            "stemming but flip '&' → '|' so any word hits;",
            "ts_rank still favours chunks matching more words.",
            "LIMIT 20.",
        ]),
    ]
    for x, col, t, rows in cols:
        s.rect(x, 250, 500, 320, rx=16, fill=PANEL, stroke=col, sw=2)
        s.text(x + 20, 284, t, size=16.5, fill=col, weight=700)
        s.lines(x + 20, 312, rows, size=12.1, lh=16.6, fill=MUTE, family=MONO)

    s.poly([(320, 570), (320, 600), (840, 600)], marker=False)
    s.poly([(1340, 570), (1340, 600), (840, 600)], marker=False)
    s.line(830, 570, 830, 636, marker=True)

    s.node(540, 640, 600, 92, "Reciprocal Rank Fusion   (reciprocal_rank_fusion, k=60)", [
        "fused[id] = Σ  1 / (60 + rank)  over the vector list and the keyword list.",
        "A chunk both methods rank highly outscores one only one liked. Pure fn, unit-tested.",
    ], fill=CARD_T, stroke=TEAL, title_fill=TEAL, title_size=15)

    s.line(840, 732, 840, 762)
    s.node(210, 766, 1260, 150, "Assemble the numbered context window  →  generation", [
        "exact-match chunks (uncapped)  +  top of the fused ranking, filling CONTEXT_SIZE = 8  +  every Ready Document's metadata row.",
        "each item numbered [1..n], prefixed with its REAL verified label:",
        "     [7] (Page 12) …    [10] (Section: \"53. Access to Justice > Mass claims …\") …    [4] (Table 3) …    [9] (Image 2) …",
        "low_confidence  =  (no exact-match hit)  AND  (max fused score < 0.02).",
    ], fill=PANEL, stroke=PANEL_BRD, title_size=15)

    footer(s, "Legal AI Assistant  ·  from chat_repository.py (SQL) + retrieval.py (RRF) + chat_service.py  ·  Part 3/3")
    s.save("05_retrieval_architecture.svg")


# ===========================================================================
# 06 — GENERATION + VALIDATION
# ===========================================================================
def d06():
    s = SVG(1680, 1080, "Generation and validation architecture")
    title_block(s, "RAG deep-dive  ·  generation + grounding", "Generation is cheap. The grounding around it is the product.",
                "Temperature 0. A citation-required prompt. Then a mechanical, per-sentence verification pass the model is never trusted to self-police.")

    s.node(90, 160, 700, 250, "1 · Prompt assembly   (_format_context / _format_history)", [
        "SYSTEM_PROMPT (~1.8 KB): answer ONLY from the numbered items · no",
        "outside knowledge · restating/organising is allowed, inferring a legal",
        "conclusion is not · reproduce every amount/date/name/section-number",
        "verbatim · a label says WHERE an item is, never WHAT it says · every",
        "factual sentence needs its OWN [n] marker · use the fixed NOT_FOUND",
        "string only if the topic is genuinely absent · use OUT_OF_SCOPE for",
        "\"which side is stronger / should we settle\" — that judgment is the lawyer's.",
        "",
        "USER: last 4 turns on this branch  +  numbered context  +  the question",
    ], fill=CARD, stroke=PURPLE, title_fill=PURPLE, title_size=15)

    s.node(890, 160, 700, 250, "2 · Model call   (OpenAIChatLLM.generate)", [
        "OpenAI gpt-4o-mini · temperature = 0  (fact-retrieval, not creative)",
        "system + user messages · single completion, no streaming",
        "",
        "Chosen by asking the user directly (paid API on legal data), spiked",
        "for real before any pipeline code: a 2-chunk grounded prompt produced",
        "correct [1]/[2] citations and correctly refused an uncovered question.",
        "",
        "gpt-4o-mini vision reused for embedded-diagram captions at ingestion —",
        "no second vendor.",
    ], fill="#FBF3E4", stroke=AMBER, title_fill=AMBER, title_size=15)

    s.line(440, 410, 440, 452)
    s.line(1240, 410, 1240, 452, marker=False)
    s.poly([(1240, 430), (1240, 452)], marker=True)
    s.poly([(890, 285), (840, 285)], marker=True)
    s.text(866, 305, "raw answer", size=11.5, fill=FAINT, anchor="middle")

    s.node(90, 456, 1500, 250, "3 · Citation verification   (verify_citations — pure function, unit-tested, no I/O)", [
        "Split the answer into sentences (the shared abbreviation-aware splitter). For each sentence:",
        "   • markers = every [n] it contains        • valid = markers where 1 ≤ n ≤ (chunks + metadata items)",
        "   • no valid marker            → DROP the sentence (unsupported claim, Grounding Rule 4)",
        "   • some valid + some invalid  → keep it, but flag the whole answer with a gap note",
        "If nothing survives  → the fixed NOT_FOUND_RESPONSE.   Otherwise: kept text + first-cited-order [n] list + all_valid flag.",
        "",
        "cited_chunk_numbers → one Citation row each:  (document_id, page_number, section, excerpt = chunk.content[:300], file_name).",
    ], fill="#F1F6F2", stroke=GREEN, title_fill=GREEN, title_size=15)

    s.line(590, 706, 590, 748)
    s.text(610, 732, "all_valid == False", size=12, fill=RED)
    s.node(90, 752, 900, 116, "4 · One corrective regeneration", [
        "Re-prompt: \"…cite ONLY items 1..n, state only what they directly support.\"",
        "If the retry verifies clean → use it. If it still doesn't → keep the first,",
        "already-stripped answer + gap note. Never left in as if it were verified.",
    ], fill=PANEL, stroke=RED, title_fill=RED, title_size=14.5)

    s.node(1030, 752, 560, 116, "5 · Persist   (BR-006 gate on the write path)", [
        "validate_assistant_message(): an assistant row with content but zero",
        "citations cannot be constructed — unless it's the fixed NOT_FOUND or",
        "OUT_OF_SCOPE string. Enforced in code, not just asked of the model.",
    ], fill=PANEL, stroke=PANEL_BRD, title_size=14.5)

    s.text(840, 930, "Grounding is structural, not a polite request:  SQL matter-scope  ·  no-call-below-threshold  ·  "
                     "context-only prompt  ·  per-sentence marker check  ·  one corrective retry  ·  temp 0  ·  write-path invariant",
           size=13, fill=INK, anchor="middle", weight=600)
    s.text(840, 958, "What it does NOT do: no independent fact-checking model, no external truth source. "
                     "\"Grounded in retrieved evidence\" — not \"hallucination-free\".",
           size=12.5, fill=MUTE, anchor="middle", italic=True)

    footer(s, "Legal AI Assistant  ·  from chat_service.py + domain/citation_verification.py + domain/chat.py  ·  Part 3/3")
    s.save("06_generation_validation.svg")


# ===========================================================================
# 07 — DATA MODEL
# ===========================================================================
def d07():
    s = SVG(1680, 1000, "Storage and data architecture")
    title_block(s, "Storage / data architecture", "One Postgres schema, owned by neither backend",
                "Drizzle Kit in /database is the single migration tool. Java and Python both map onto it read/write, validate-only. Files live outside the DB.")

    def tbl(x, y, name, rows, col, w=340):
        h = 44 + len(rows) * 22
        s.rect(x, y, w, h, rx=10, fill=PANEL, stroke=col, sw=2)
        s.rect(x, y, w, 34, rx=10, fill=col, stroke="none", sw=0)
        s.rect(x, y + 22, w, 12, rx=0, fill=col, stroke="none", sw=0)
        s.text(x + 14, y + 23, name, size=14.5, fill="#fff", weight=700, family=MONO)
        for i, r in enumerate(rows):
            s.text(x + 14, y + 54 + i * 22, r, size=12.3, fill=MUTE, family=MONO)
        return (x, y, w, h)

    tbl(60, 150, "matters", [
        "id  ·  firm_id → firms  (BR-008)",
        "client_id → clients  (BR-001)",
        "title · status open|closed",
        "active_root_message_id → chat_messages",
    ], NAVY)

    tbl(60, 330, "documents", [
        "id  ·  matter_id → matters  (BR-002)",
        "uploaded_by → lawyers",
        "file_name · storage_key · mime_type",
        "status uploading|processing|ready|failed",
        "is_draft · source_template_id · error_message",
    ], NAVY)

    tbl(60, 560, "deadlines / notifications", [
        "deadline: matter_id · due_date · status",
        "  priority · notification_lead_days",
        "notification: lawyer_id · deadline_id",
        "  (ON DELETE CASCADE)",
    ], NAVY)

    tbl(560, 300, "document_chunks", [
        "id  ·  document_id → documents",
        "        (ON DELETE CASCADE)",
        "page_number      int   nullable",
        "section          text  nullable  (breadcrumb)",
        "chunk_type       prose|table_or_list|image",
        "element_number   int   nullable  ('Table 3')",
        "content          text",
        "embedding        vector(384)   ← pgvector",
    ], TEAL, w=380)

    tbl(560, 590, "chat_messages", [
        "id · matter_id → matters  (BR-005)",
        "lawyer_id  (null when role=assistant)",
        "role user|assistant · content · pinned",
        "parent_id → chat_messages  (CASCADE)",
        "active_child_id → chat_messages  (branch tree)",
    ], PURPLE, w=380)

    tbl(1060, 590, "citations", [
        "id · chat_message_id → chat_messages",
        "        (ON DELETE CASCADE)",
        "document_id → documents",
        "        (ON DELETE SET NULL)  ← survives delete",
        "page_number · section · excerpt",
    ], PURPLE, w=380)

    tbl(1060, 300, "firms / lawyers / sessions", [
        "lawyer: firm_id · email uniq · password_hash",
        "        (BCrypt 12) · role owner|member",
        "session: lawyer_id · token_hash (SHA-256)",
        "        expires_at  (7 days)",
    ], SLATE, w=380)

    # relationships
    s.line(400, 250, 560, 340, marker=True)
    s.line(400, 400, 560, 400, marker=True)
    s.line(750, 470, 750, 590, marker=True)
    s.line(940, 660, 1060, 660, marker=True)
    s.poly([(1250, 470), (1250, 540), (1250, 590)], marker=True)
    s.text(1264, 545, "SET NULL", size=10.5, fill=PURPLE, family=MONO)

    # ownership
    s.node(60, 740, 740, 150, "Owned by Java (writes)", [
        "firms · lawyers · sessions · clients · matters · deadlines ·",
        "notifications · templates · matter_views · recent_searches ·",
        "lawyer_preferences   +   documents.status transitions",
        "Cascade deletes done in-transaction (ClientService.deleteCascade)",
        "— most FKs are NO ACTION, the DB won't cascade for you.",
    ], fill=CARD_N, stroke=NAVY, title_fill=NAVY, title_size=15)
    s.node(830, 740, 770, 150, "Owned by Python (writes)", [
        "document_chunks · chat_messages · citations",
        "+ documents.status → ready / failed",
        "Raw SQL via SQLAlchemy text() with an explicit CAST(:v AS vector)",
        "— deliberately not the ORM layer, to control the pgvector type.",
        "Files: /uploads on disk (dev) → Cloudflare R2 (prod), same interface.",
    ], fill=CARD, stroke=PURPLE, title_fill=PURPLE, title_size=15)

    footer(s, "Legal AI Assistant  ·  from database/schema/schema.ts  ·  Part 2/3")
    s.save("07_data_architecture.svg")


# ===========================================================================
# 08 — CHUNKING STRATEGY
# ===========================================================================
def d08():
    s = SVG(1680, 1000, "Chunking architecture")
    title_block(s, "RAG deep-dive  ·  chunking", "Adaptive strategy, one fixed chunk shape",
                "Uploaded documents have no fixed structure — hierarchical, flat, tabular, image-bearing, any mix. So the strategy adapts; the output never changes.")

    # evolution strip
    s.text(40, 150, "How it got here", size=15, fill=INK, weight=700, family=SERIF)
    ev = [
        ("2026-08-14", "join all pages → text[start:end] slice, ~2800 chars", "mid-word cuts; page_number held the chunk index", RED),
        ("2026-08-15", "ExtractedPage per real page → chunk_pages() per page", "sentence-boundary split, whole-sentence overlap, real page #", GREEN),
        ("2026-08-19", "CHUNK_SIZE 2800 → 1000  (measured 5.0 ch/tok, 256-tok limit)", "old size silently truncated 45–100% of chunks at embed time", GREEN),
        ("2026-08-19", "DOCX-adaptive: Segment + heading-aware packer", "section / chunk_type columns; branch on data shape not file type", GREEN),
        ("2026-08-20", "PDF-adaptive via pdfplumber font metrics + real page #s", "table & image element_number; label shown to the LLM", GREEN),
    ]
    for i, (d, a, b, col) in enumerate(ev):
        y = 168 + i * 46
        s.rect(40, y, 150, 34, rx=8, fill=col, stroke="none", sw=0)
        s.text(115, y + 22, d, size=12, fill="#fff", weight=700, anchor="middle", family=MONO)
        s.text(210, y + 15, a, size=13, fill=INK, weight=600)
        s.text(210, y + 32, b, size=12, fill=MUTE)

    # the packer
    s.node(40, 430, 780, 300, "The packer   (_pack_typed_segments / _pack_segments)", [
        "1.  segments arrive typed: (text, heading_path, chunk_type,",
        "        element_number, page_number)",
        "2.  group runs that share ALL of heading_path + chunk_type +",
        "        element_number + page_number  — a change in ANY is a",
        "        hard boundary (a chunk never straddles one)",
        "3.  greedy-fill to the size budget:",
        "        prose  → 1000 chars     table_or_list → 850 chars",
        "4.  overlap ≈ 150 chars, carried as WHOLE trailing sentences",
        "        (never a raw character slice) → next chunk starts clean",
        "5.  a single over-budget segment (long table row) → word-boundary",
        "        hard split, last resort only",
    ], fill=CARD_T, stroke=TEAL, title_fill=TEAL, title_size=15)

    s.node(860, 430, 780, 300, "Why these numbers", [
        "• all-MiniLM-L6-v2 max_seq_length = 256 tokens (checked against",
        "   the loaded model, not assumed)",
        "• this corpus's legal text: ~5.0–5.1 chars/token (number- and",
        "   citation-heavy → less token-efficient than prose)",
        "• 1000 chars = largest sweep value with 0 / 418 real fixture",
        "   chunks over the limit  (max observed 216 tokens, ~15% margin)",
        "• table rows measure ~3.8–4 chars/token → tighter 850 budget",
        "• overlap ratio kept at ~14% (was 400/2800, now 150/1000)",
        "• runtime token-count check logs a warning if a rare dense",
        "   segment would still truncate — a backstop, not a guarantee",
    ], fill=PANEL, stroke=PANEL_BRD, title_size=15)

    s.node(40, 760, 1600, 150, "Fixed output — TextChunk", [
        "content   ·   index   ·   page_number (int | None)   ·   metadata{ section, chunk_type, element_number }",
        "",
        "Every downstream stage — embedding, vector/keyword search, the numbered prompt context, and every Citation row —",
        "consumes this one shape, whether it came from a 4-level-nested DOCX, a flat paragraph brief, or a scanned image.",
    ], fill=CARD_N, stroke=NAVY, title_fill=NAVY, title_size=15)

    footer(s, "Legal AI Assistant  ·  from app/domain/chunk.py + RAG-Pipeline-Development-History.md Phases 1,3,4  ·  Part 3/3")
    s.save("08_chunking_architecture.svg")


# ===========================================================================
# 09 — CITATION ARCHITECTURE
# ===========================================================================
def d09():
    s = SVG(1680, 980, "Citation architecture")
    title_block(s, "RAG deep-dive  ·  citations & provenance", "Every sentence traces to one real location",
                "A citation a lawyer can't open and check in the time it takes to read the excerpt doesn't count.")

    # chain
    chain = [
        ("Answer sentence", "\"The 1989 settlement required US$470 million [7].\"", NAVY),
        ("Marker [7]", "position in THIS prompt's numbered list — never a page/section number", PURPLE),
        ("Retrieved item #7", "the chunk (or metadata row) actually offered to the model this call", TEAL),
        ("Source chunk", "document_chunks row: content, page_number, section, chunk_type, element_number", TEAL),
        ("Document", "documents row: file_name, storage_key", NAVY),
    ]
    x = 60
    for i, (t, d, col) in enumerate(chain):
        y = 150 + i * 96
        s.rect(x, y, 560, 78, rx=12, fill=PANEL, stroke=col, sw=2)
        s.text(x + 20, y + 30, t, size=15.5, fill=col, weight=700)
        s.text(x + 20, y + 54, d, size=12.2, fill=MUTE, family=MONO)
        if i < len(chain) - 1:
            s.line(x + 280, y + 78, x + 280, y + 96)

    # citation row
    s.node(720, 200, 900, 300, "→  one Citation row per distinct source location", [
        "chat_message_id   → the specific answer it backs",
        "document_id       → documents  (ON DELETE SET NULL — the row and its",
        "                     excerpt survive the source file being deleted)",
        "page_number       → where determinable (PDF/image; real page-break DOCX)",
        "section           → heading breadcrump  \"53. Access to Justice > Mass",
        "                     claims and vulnerable populations\"  (DOCX / adaptive PDF)",
        "excerpt           → chunk.content[:300] — the actual source text, never",
        "                     LLM-authored. A metadata citation's excerpt is a",
        "                     Python-computed fact string (\"file.pdf has 11 pages.\").",
        "",
        "Persisted permanently with the message · never recomputed · not cached.",
    ], fill=CARD, stroke=PURPLE, title_fill=PURPLE, title_size=15.5)

    s.node(720, 540, 900, 200, "Rules for the set", [
        "• multi-fact answer from different locations → MULTIPLE rows, one per",
        "   source — never one blanket citation over everything",
        "• NOT_FOUND / OUT_OF_SCOPE answer → zero citations (nothing to cite)",
        "• BR-006 is a write-path invariant: an uncited factual assistant message",
        "   cannot be constructed through this codebase",
        "• UI renders each as a link → GET /api/documents/:id/download,",
        "   showing \"file.pdf, p.54, 53. Access to Justice > …\"  +  the excerpt",
    ], fill="#F1F6F2", stroke=GREEN, title_fill=GREEN, title_size=15.5)

    s.line(620, 250, 712, 250, marker=True)

    footer(s, "Legal AI Assistant  ·  from 06-AI-Architecture.md §4 + citation_verification.py + chat_repository.py  ·  Part 3/3")
    s.save("09_citation_architecture.svg")


# ===========================================================================
# 10 — CONTEXT WINDOW / LARGE CORPUS MANAGEMENT
# ===========================================================================
def d10():
    s = SVG(1680, 940, "Context window and large-corpus handling")
    title_block(s, "RAG deep-dive  ·  scale", "The same question gets a different guarantee at different sizes — and the lawyer is told which",
                "\"Summarise everything\" is complete below the cap, best-effort above it. That difference used to be silent.")

    # scale bar
    bx, by, bw = 80, 200, 1520
    s.rect(bx, by, bw, 44, rx=10, fill=PANEL, stroke=PANEL_BRD, sw=1.6)
    s.rect(bx, by, bw * 0.62, 44, rx=10, fill="#E7F1EC", stroke="none", sw=0)
    s.line(bx + bw * 0.62, by - 10, bx + bw * 0.62, by + 54, stroke=INK, sw=2, marker=False)
    s.text(bx + bw * 0.31, by + 27, "FULL-CONTEXT PATH   ·   every Ready chunk sent   ·   full_context = True", size=13, fill=GREEN, weight=700, anchor="middle")
    s.text(bx + bw * 0.81, by + 27, "HYBRID RETRIEVAL + RRF + top-8", size=13, fill=AMBER, weight=700, anchor="middle")
    s.text(bx + bw * 0.62, by - 18, "FULL_CONTEXT_CHAR_CAP = 400,000 chars", size=12.5, fill=INK, weight=700, anchor="middle")
    s.text(bx, by + 74, "0", size=12, fill=MUTE)
    s.text(bx + bw, by + 74, "→ corpus size (Σ chunk chars for the Matter's Ready Documents)", size=12, fill=MUTE, anchor="end")

    s.node(80, 320, 500, 300, "Small / typical Matter", [
        "• below the cap — the common case in practice",
        "• no ranking, no threshold gate, no top-K",
        "• a broad question genuinely considers all content",
        "• measured cost: whole-document calls 10–15.5 s;",
        "   narrow questions on the same Matter 2–7 s",
        "",
        "The below-threshold no-LLM guarantee does NOT",
        "apply here — the model always sees the corpus and",
        "citation verification is the backstop.",
    ], fill="#F1F6F2", stroke=GREEN, title_fill=GREEN, title_size=15.5)

    s.node(600, 320, 480, 300, "Large Matter (> 400K chars)", [
        "• hybrid retrieval + RRF + CONTEXT_SIZE = 8",
        "• exact-identifier chunks added uncapped, so",
        "   \"page 54\" / \"table 3\" still can't be missed",
        "• below RELEVANCE_THRESHOLD (0.01) → no LLM",
        "   call; try metadata, else fixed NOT_FOUND",
        "• below CONFIDENT_THRESHOLD (0.02) → answer",
        "   flagged low_confidence",
        "",
        "full_context = False → UI note: \"this Matter is",
        "large … ask about a specific page/section/table.\"",
    ], fill="#FBF6EC", stroke=AMBER, title_fill=AMBER, title_size=15.5)

    s.node(1100, 320, 500, 300, "How the cap was set", [
        "Spiked against the real API, not assumed:",
        "• 712,694-char prompt → API error: \"max context",
        "   128000 tokens … resulted in 142,948 tokens\"",
        "   (⇒ real ~4.99 chars/token for this corpus)",
        "• ~416K-char prompt → OK in 10.6 s",
        "• ~464K-char prompt → OK in 37.1 s  (variance-",
        "   dominated — not a clean function of size)",
        "→ 400K = round number, ~34% headroom under the",
        "   hard token ceiling, covers the real 353K-char",
        "   Matter that motivated the raise from 150K.",
    ], fill=PANEL, stroke=PANEL_BRD, title_size=15.5)

    s.text(840, 690, "Deliberately NOT built: a map-reduce / multi-call architecture for unbounded corpora.", size=13.5, fill=INK, anchor="middle", weight=600)
    s.text(840, 714, "No real Matter needs it yet — the largest fits one call. Logged as a deferred option, not a gap left unnoticed.", size=12.5, fill=MUTE, anchor="middle", italic=True)

    footer(s, "Legal AI Assistant  ·  from chat_service.py constants + RAG-Pipeline-Development-History.md Phases 2 & 8  ·  Part 3/3")
    s.save("10_context_window_management.svg")


if __name__ == "__main__":
    d01(); d02(); d03(); d04(); d05(); d06(); d07(); d08(); d09(); d10()
    print("done")
