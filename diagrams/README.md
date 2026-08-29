# Legal AI Assistant — LinkedIn series diagrams

Architecture / flow diagrams for the 3-part LinkedIn series. Every label is a real
identifier from the source tree (`backend-python/app/**`, `backend-java/src/**`,
`database/schema/schema.ts`) or the project docs.

## Files

| PNG (3360 px wide, 2×) | Title | Used in |
|---|---|---|
| `01_high_level_architecture.png` | Three services, one database, one hard rule | Post 2 (hero) |
| `02_user_journey.png` | From an empty Matter to a cited answer | Post 1 |
| `03_document_ingestion_architecture.png` | Document ingestion — adaptive by content | Post 2 & 3 |
| `04_query_processing_architecture.png` | Query processing — two regimes by corpus size | Post 2 & 3 |
| `05_retrieval_architecture.png` | Hybrid retrieval: exact + semantic + lexical, fused | Post 3 |
| `06_generation_validation.png` | Generation + per-sentence citation verification | Post 2 & 3 |
| `07_data_architecture.png` | One Postgres schema, owned by neither backend | Post 2 |
| `08_chunking_architecture.png` | Adaptive strategy, one fixed chunk shape | Post 3 |
| `09_citation_architecture.png` | Every sentence traces to one real location | Post 3 |
| `10_context_window_management.png` | Same question, different guarantee at different sizes | Post 3 |

Each PNG has a matching editable `.svg`.

## Regenerate

```bash
python gen_diagrams.py      # writes the .svg files
python render_pngs.py       # renders each .svg -> 2x .png via headless Chrome
# render_pngs.py NN_        # re-render only files whose name contains "NN_"
```

`render_pngs.py` expects Chrome at
`C:\Program Files\Google\Chrome\Application\chrome.exe` (edit `CHROME` if different).

Edit copy/layout in `gen_diagrams.py` — it's a small SVG DSL (`box`, `node`,
`arrow`, `banner`, `decision`, `lines`). Colours: navy = Java/CRUD,
purple = Python/AI, teal = retrieval/DB, amber = external paid API,
green = validation/grounding, red = failure/refusal.

## From the "Chunk & Retrieve" artifact report (updated to current code)

The artifact report contained 4 mermaid diagrams. They are rebuilt here in the
same house style, **updated** where the implementation changed after Phases 5–8 of
`RAG-Pipeline-Development-History.md` (amber fill / [UPDATED] tag marks each change):

| File | From artifact § | Updated because |
|---|---|---|
| `A_upload_to_stored_chunk` | §02 Upload → stored chunk | embedded-diagram OCR **+ gpt-4o-mini vision caption** (gap #2 Tier 1); PDF images attributed to every real drawing page via content-stream `Do`-check (gap #6) |
| `B_two_retrieval_paths` | §04 The two retrieval paths | `FULL_CONTEXT_CHAR_CAP` 150K → **400K** (gap #7); new **exact-identifier match** leg — uncapped, bypasses the threshold gate (gap #1); `full_context` signal on the response |
| `C_query_trace_sequence` | §07 Full trace | example corpus size 210K → 520K (so it still lands on the hybrid path past the 400K cap); explicit `extract_identifier_refs` step shown |
| `D_grounding_validation` | §08 Grounding | logic **unchanged** — restyled only |

Regenerate: `python gen_artifact_diagrams.py && python render_pngs.py A_ B_ C_ D_`
