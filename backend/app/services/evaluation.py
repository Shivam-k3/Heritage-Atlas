"""Pure tagging-evaluation helpers. No database, model or FastAPI imports.

Scores are raw CLIP cosine similarities. Nothing here converts a score into a probability.
"""

import hashlib
from collections.abc import Mapping, Sequence
from typing import Literal

Split = Literal["train", "tune", "test"]


def site_split(site_id: int) -> Split:
    """Deterministic 60/20/20 site-wise split.

    Hashing the site id keeps a site in the same split when new images are added. The
    dataset is small, so the realised split is reported by the scripts rather than assumed.
    """
    bucket = int(hashlib.sha256(str(site_id).encode("utf-8")).hexdigest()[:8], 16) % 10
    if bucket < 6:
        return "train"
    if bucket < 8:
        return "tune"
    return "test"


def choose_thresholds(
    truth: Mapping[int, set[str]],
    scores: Mapping[int, Mapping[str, float]],
    labels: Sequence[str],
) -> dict[str, float | None]:
    """Pick a per-label cosine cut-off that maximises F1 on the tuning rows.

    A label with no positive example in the tuning rows is left unset, which means it can
    never be emitted. Ties prefer the higher cut-off, i.e. fewer false positives. The test
    split must never be passed to this function.
    """
    thresholds: dict[str, float | None] = {}
    for label in labels:
        positive = [scores[i][label] for i in truth if label in truth[i] and label in scores[i]]
        negative = [scores[i][label] for i in truth if label not in truth[i] and label in scores[i]]
        if not positive or not negative:
            thresholds[label] = None
            continue
        best_f1 = 0.0
        best_threshold: float | None = None
        for candidate in sorted(set(positive + negative)):
            tp = sum(score >= candidate for score in positive)
            fp = sum(score >= candidate for score in negative)
            fn = len(positive) - tp
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
            if f1 > best_f1 or (f1 == best_f1 and candidate > (best_threshold or -1.0)):
                best_f1 = f1
                best_threshold = float(candidate)
        thresholds[label] = round(best_threshold, 4) if best_f1 > 0 and best_threshold else None
    return thresholds


def predict(
    scores: Mapping[str, float],
    thresholds: Mapping[str, float | None],
    max_features: int = 4,
) -> set[str]:
    accepted: list[tuple[str, float]] = []
    for label, score in scores.items():
        limit = thresholds.get(label)
        if limit is not None and score >= limit:
            accepted.append((label, score))
    accepted.sort(key=lambda item: item[1], reverse=True)
    return {label for label, _ in accepted[:max_features]}


def evaluate(
    truth: Mapping[int, set[str]],
    predictions: Mapping[int, set[str]],
    labels: Sequence[str],
) -> dict[str, object]:
    """Per-label and aggregate metrics. Labels absent from a row count as not present."""
    per_label: dict[str, dict[str, float | int]] = {}
    total_tp = total_fp = total_fn = 0
    false_positive_images = 0
    no_confident_images = 0
    predicted_counts: dict[str, int] = {label: 0 for label in labels}

    for image_id, expected in truth.items():
        predicted = predictions.get(image_id, set())
        if not predicted:
            no_confident_images += 1
        if predicted - expected:
            false_positive_images += 1
        for label in predicted:
            predicted_counts[label] = predicted_counts.get(label, 0) + 1

    for label in labels:
        tp = sum(label in truth[i] and label in predictions.get(i, set()) for i in truth)
        fp = sum(label not in truth[i] and label in predictions.get(i, set()) for i in truth)
        fn = sum(label in truth[i] and label not in predictions.get(i, set()) for i in truth)
        if tp + fp + fn == 0:
            continue
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_label[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
        total_tp += tp
        total_fp += fp
        total_fn += fn

    images = len(truth)
    macro_f1 = (
        sum(float(metrics["f1"]) for metrics in per_label.values()) / len(per_label)
        if per_label
        else None
    )
    micro_precision = total_tp / (total_tp + total_fp) if total_tp + total_fp else 0.0
    micro_recall = total_tp / (total_tp + total_fn) if total_tp + total_fn else 0.0
    micro_f1 = (
        2 * micro_precision * micro_recall / (micro_precision + micro_recall)
        if micro_precision + micro_recall
        else 0.0
    )
    return {
        "images_evaluated": images,
        "labels_evaluated": len(per_label),
        "macro_f1": None if macro_f1 is None else round(macro_f1, 4),
        "micro_precision": round(micro_precision, 4),
        "micro_recall": round(micro_recall, 4),
        "micro_f1": round(micro_f1, 4),
        "false_positive_frequency": (round(false_positive_images / images, 4) if images else None),
        "no_confident_feature_frequency": (
            round(no_confident_images / images, 4) if images else None
        ),
        "predicted_label_counts": predicted_counts,
        "per_label": per_label,
    }
