"""Explainable ranking helpers. No cross-space similarity is computed here."""

from collections.abc import Sequence

import numpy as np


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def mean_vector(vectors: Sequence[np.ndarray]) -> np.ndarray | None:
    if not vectors:
        return None
    matrix = np.vstack([np.asarray(vector, dtype=np.float32).reshape(-1) for vector in vectors])
    return matrix.mean(axis=0)


def cosine(left: np.ndarray | None, right: np.ndarray | None) -> float:
    if left is None or right is None:
        return 0.0
    left_norm = float(np.linalg.norm(left))
    right_norm = float(np.linalg.norm(right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    score = float(np.dot(left, right) / (left_norm * right_norm))
    return max(-1.0, min(1.0, score))


def rank_related(
    target_site_id: int,
    target_images: Sequence[tuple[int, np.ndarray]],
    target_tags: set[str],
    candidates: Sequence[dict],
    alpha: float,
    limit: int,
) -> list[dict]:
    """Combine mean CLIP similarity and Jaccard tag overlap. alpha weights CLIP."""
    target_mean = mean_vector([vector for _, vector in target_images])
    ranked: list[dict] = []
    for candidate in candidates:
        if candidate["site_id"] == target_site_id:
            continue
        candidate_images: list[tuple[int, np.ndarray]] = candidate["images"]
        candidate_mean = mean_vector([vector for _, vector in candidate_images])
        clip_similarity = cosine(target_mean, candidate_mean)
        overlap = jaccard(target_tags, candidate["tags"])
        evidence: dict[str, int | None] = {"image_a": None, "image_b": None}
        best_pair = -2.0
        for target_id, target_vector in target_images:
            for candidate_id, candidate_vector in candidate_images:
                pair_score = cosine(target_vector, candidate_vector)
                if pair_score > best_pair:
                    best_pair = pair_score
                    evidence = {"image_a": target_id, "image_b": candidate_id}
        ranked.append(
            {
                "site_id": candidate["site_id"],
                "name": candidate["name"],
                "score": round(alpha * clip_similarity + (1 - alpha) * overlap, 6),
                "clip_similarity": round(clip_similarity, 6),
                "tag_overlap": round(overlap, 6),
                "shared_tags": sorted(target_tags & candidate["tags"]),
                "evidence": evidence,
            }
        )
    ranked.sort(key=lambda item: (-item["score"], item["site_id"]))
    return ranked[:limit]
