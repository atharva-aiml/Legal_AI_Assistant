from app.domain.chunk import ExtractedPage, chunk_pages
from app.infrastructure.embedding import MAX_SEQ_LENGTH, count_tokens


def _dense_legal_text(sentence_count: int) -> str:
    """A mix of clause-dense (numbers/citations/currency) and narrative
    prose sentences, calibrated to match the ~5.0-5.1 chars/token the real
    project fixtures actually measured at (see AI Architecture §2's
    2026-08-19 addendum) — a generator built from *only* the dense pattern
    tokenizes at ~3.2 chars/token, meaningfully worse than any real
    document sampled, which would test an artificial worst case rather
    than the actual regression. This mix lands at ~5.2 chars/token."""
    sentences = []
    for i in range(1, sentence_count + 1):
        if i % 3 == 0:
            sentences.append(
                f"Clause {i}.{i % 9 + 1} obligates Apex Components Pvt. Ltd. to pay Rs. {1000 + i * 137}/- "
                f"to the Receiving Party on or before the {i % 28 + 1}th day of the month, per Section {i % 12 + 1}(a)(iii)."
            )
        else:
            sentences.append(
                f"The correspondence dated in respect of matter {i} was reviewed by counsel for both parties, "
                "who noted that the obligations described therein remained consistent with the earlier "
                "understanding reached between the Disclosing Party and the Receiving Party during their prior discussions."
            )
    return " ".join(sentences)


def test_every_real_chunk_fits_within_the_embedding_models_real_token_limit():
    """The actual regression this spike found: chunk.py's char-based size
    approximation must never let a chunk's REAL token count (per the real
    model's own tokenizer) exceed the model's real max_seq_length — every
    chunk over that limit had its back half silently dropped from
    embedding, invisibly, with no error anywhere. This is the cross-layer
    contract chunk.py's CHUNK_SIZE_CHARS is tuned against; verified here
    with the real tokenizer, not another char-based guess."""
    limit = MAX_SEQ_LENGTH

    page = ExtractedPage(page_number=1, text=_dense_legal_text(200))
    chunks = chunk_pages([page])

    assert len(chunks) > 1  # actually exercises multiple chunks, not a degenerate single-chunk case

    for chunk in chunks:
        token_count = count_tokens(chunk.content)
        assert token_count <= limit, (
            f"chunk {chunk.index} has {token_count} tokens, exceeding the model's "
            f"{limit}-token limit — its back {token_count - limit} tokens would be "
            f"silently truncated by the model with no error."
        )


def test_embed_warns_but_does_not_raise_when_given_oversized_text(caplog):
    """The safety net for whatever still slips past chunk.py's sizing —
    embedding an oversized text must not crash (it's still a valid,
    if-degraded, embedding), but the truncation must be logged, not silent."""
    from app.infrastructure.embedding import OnnxEmbedder

    embedder = OnnxEmbedder()
    # One long word per token-ish, comfortably past the real limit regardless of tokenizer quirks.
    oversized_text = "Clause obligates party " * (MAX_SEQ_LENGTH * 2)

    with caplog.at_level("WARNING"):
        vectors = embedder.embed([oversized_text])

    assert len(vectors) == 1
    assert len(vectors[0]) == 384
    assert any("exceeding" in record.message for record in caplog.records)


def test_embed_does_not_warn_for_a_normally_sized_chunk(caplog):
    from app.infrastructure.embedding import OnnxEmbedder

    embedder = OnnxEmbedder()
    page = ExtractedPage(page_number=1, text=_dense_legal_text(10))
    chunks = chunk_pages([page])

    with caplog.at_level("WARNING"):
        embedder.embed([chunks[0].content])

    assert not any("exceeding" in record.message for record in caplog.records)


def test_embeddings_are_unit_length_384_dim_and_truncate_at_the_real_limit():
    """The stored vectors (and cosine retrieval) assume normalized 384-dim
    output, and that everything past MAX_SEQ_LENGTH tokens is ignored — so
    two texts identical in their first 256 tokens must embed identically."""
    from app.infrastructure.embedding import OnnxEmbedder

    head = "The lessee shall indemnify the lessor against all claims. " * 60
    a, b, short = OnnxEmbedder().embed([head + "tail one", head + "a completely different tail", "Rent is due monthly."])

    assert len(a) == 384
    assert abs(sum(x * x for x in short) - 1.0) < 1e-4
    assert max(abs(x - y) for x, y in zip(a, b)) < 1e-5
