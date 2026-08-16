def reciprocal_rank_fusion(*ranked_id_lists: list[str], k: int = 60) -> dict[str, float]:
    """AI Architecture §2: merge parallel vector + keyword result lists with
    Reciprocal Rank Fusion rather than hand-tuning a blend weight between two
    different score scales. Pure function — no I/O, no framework dependency.

    Each input is a list of chunk ids already ranked best-first by its own
    method. A chunk's fused score is the sum of 1/(k + rank) across every
    list it appears in (1-indexed rank), so a chunk ranked highly by both
    methods outscores one only one method liked."""
    scores: dict[str, float] = {}
    for ranked_ids in ranked_id_lists:
        for rank, chunk_id in enumerate(ranked_ids, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return scores


def top_n_by_score(scores: dict[str, float], n: int) -> list[str]:
    return sorted(scores, key=lambda chunk_id: scores[chunk_id], reverse=True)[:n]
