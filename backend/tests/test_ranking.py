import numpy as np
from app.services.ranking import cosine, jaccard, mean_vector, rank_related


def test_jaccard_handles_empty_and_overlapping_sets():
    assert jaccard(set(), set()) == 0.0
    assert jaccard({"a"}, {"b"}) == 0.0
    assert jaccard({"a", "b"}, {"b", "c"}) == 1 / 3


def test_cosine_is_zero_for_missing_or_zero_vectors():
    assert cosine(None, np.ones(3)) == 0.0
    assert cosine(np.zeros(3), np.ones(3)) == 0.0
    assert cosine(np.array([1.0, 0.0]), np.array([0.0, 1.0])) == 0.0


def test_mean_vector_averages_components():
    result = mean_vector([np.array([1.0, 3.0]), np.array([3.0, 5.0])])
    assert result is not None
    assert result.tolist() == [2.0, 4.0]


def test_rank_related_excludes_target_and_combines_scores():
    candidates = [
        {"site_id": 1, "name": "target", "images": [(10, np.array([1.0, 0.0]))], "tags": {"a"}},
        {"site_id": 2, "name": "close", "images": [(20, np.array([1.0, 0.0]))], "tags": {"a"}},
        {"site_id": 3, "name": "far", "images": [(30, np.array([0.0, 1.0]))], "tags": {"b"}},
    ]
    ranked = rank_related(
        target_site_id=1,
        target_images=[(10, np.array([1.0, 0.0]))],
        target_tags={"a"},
        candidates=candidates,
        alpha=0.5,
        limit=5,
    )
    assert [row["site_id"] for row in ranked] == [2, 3]
    assert ranked[0]["clip_similarity"] == 1.0
    assert ranked[0]["tag_overlap"] == 1.0
    assert ranked[0]["score"] == 1.0
    assert ranked[0]["shared_tags"] == ["a"]
    assert ranked[0]["evidence"] == {"image_a": 10, "image_b": 20}
    assert ranked[1]["score"] == 0.0


def test_rank_related_respects_limit():
    candidates = [
        {"site_id": index, "name": str(index), "images": [], "tags": set()} for index in range(1, 6)
    ]
    assert len(rank_related(1, [], set(), candidates, 0.6, 2)) == 2
