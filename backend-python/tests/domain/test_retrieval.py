from app.domain.retrieval import reciprocal_rank_fusion, top_n_by_score


def test_a_chunk_ranked_highly_by_both_methods_outscores_one_only_one_method_liked():
    vector_ranked = ["a", "b", "c"]
    keyword_ranked = ["a", "d", "e"]

    scores = reciprocal_rank_fusion(vector_ranked, keyword_ranked, k=60)

    assert scores["a"] > scores["b"]
    assert scores["a"] > scores["d"]


def test_a_chunk_appearing_in_only_one_list_still_gets_a_score():
    scores = reciprocal_rank_fusion(["a", "b"], ["c"], k=60)
    assert set(scores.keys()) == {"a", "b", "c"}
    assert scores["c"] == 1.0 / 61


def test_empty_lists_produce_no_scores():
    assert reciprocal_rank_fusion([], [], k=60) == {}


def test_top_n_by_score_orders_descending_and_truncates():
    scores = {"a": 0.5, "b": 0.9, "c": 0.1, "d": 0.7}
    assert top_n_by_score(scores, 2) == ["b", "d"]
