"""Few-shot logistic-regression probe on CLIP image embeddings.

Only explicit human decisions are used: `verified` and `added_by_human` are positive,
`rejected` is negative. Unreviewed automatic tags and images without a decision for a label
are never treated as ground truth. Splits are by site, identical to eval_tagging.py.

The probe is compared with the revised zero-shot system on the same held-out test sites.
If there are too few explicit decisions, the script writes a report saying so; it does not
claim that human verification improves the model.

Usage:
    python backend/scripts/eval_fewshot.py
    python backend/scripts/eval_fewshot.py --min-positive 10 --min-negative 10
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

import numpy as np  # noqa: E402
from app import ml  # noqa: E402
from app.db import connect  # noqa: E402
from app.services.evaluation import choose_thresholds, evaluate, site_split  # noqa: E402

OUTPUT = REPO_ROOT / "data" / "dataset" / "eval_fewshot.json"
POSITIVE = {"verified", "added_by_human"}


def load_decisions() -> tuple[dict[int, dict[str, int]], dict[int, int], dict[int, Any]]:
    """Explicit decisions only. Returns image -> label -> 1/0, image -> site, image -> vector."""
    with connect() as conn:
        rows = conn.execute(
            """SELECT i.id AS image_id, i.site_id, i.clip_embedding, t.label, it.status
               FROM image_tags it
               JOIN images i ON i.id = it.image_id
               JOIN tags t ON t.id = it.tag_id
               WHERE it.status IN ('verified', 'added_by_human', 'rejected')
                 AND i.clip_embedding IS NOT NULL
               ORDER BY i.id, t.label"""
        ).fetchall()
    decisions: dict[int, dict[str, int]] = {}
    sites: dict[int, int] = {}
    vectors: dict[int, Any] = {}
    for row in rows:
        image_id = int(row["image_id"])
        decisions.setdefault(image_id, {})[str(row["label"])] = (
            1 if row["status"] in POSITIVE else 0
        )
        sites[image_id] = int(row["site_id"])
        vectors[image_id] = row["clip_embedding"]
    return decisions, sites, vectors


def _split_images(sites: dict[int, int], split: str) -> set[int]:
    return {image_id for image_id, site_id in sites.items() if site_split(site_id) == split}


def _fit_probe(train_x: np.ndarray, train_y: np.ndarray) -> tuple[Any, Any]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler().fit(train_x)
    model = LogisticRegression(
        C=1.0, class_weight="balanced", max_iter=2000, solver="liblinear"
    ).fit(scaler.transform(train_x), train_y)
    return scaler, model


def _zero_shot(
    decisions: dict[int, dict[str, int]],
    sites: dict[int, int],
    vectors: dict[int, Any],
    label: str,
) -> tuple[float | None, dict[int, bool]]:
    """Threshold tuned on tune sites for this label; fall back to the committed config."""
    scores = {image_id: ml.feature_scores(vector) for image_id, vector in vectors.items()}
    tune = [
        image_id
        for image_id in _split_images(sites, "tune")
        if label in decisions.get(image_id, {})
    ]
    thresholds: dict[str, float | None] = {label: ml.FEATURE_THRESHOLDS.get(label)}
    if tune:
        tune_truth = {
            image_id: ({label} if decisions[image_id][label] else set()) for image_id in tune
        }
        tune_scores = {image_id: scores[image_id] for image_id in tune}
        thresholds = choose_thresholds(tune_truth, tune_scores, [label])
    threshold = thresholds.get(label)
    test = [
        image_id
        for image_id in _split_images(sites, "test")
        if label in decisions.get(image_id, {})
    ]
    predicted = {
        image_id: threshold is not None and scores[image_id][label] >= threshold
        for image_id in test
    }
    return threshold, predicted


def run(
    decisions: dict[int, dict[str, int]],
    sites: dict[int, int],
    vectors: dict[int, Any],
    min_positive: int = 5,
    min_negative: int = 5,
) -> dict[str, Any]:
    labels = sorted({label for row in decisions.values() for label in row})
    train_images = _split_images(sites, "train")
    tune_images = _split_images(sites, "tune")
    test_images = _split_images(sites, "test")
    report: dict[str, Any] = {
        "status": "insufficient_labels",
        "labels": {},
        "split_images": {
            "train": len(train_images),
            "tune": len(tune_images),
            "test": len(test_images),
        },
        "note": (
            "Explicit human decisions only. Absent labels are not negatives. "
            "A small probe on a handful of reviewed tags is not evidence of quality."
        ),
    }
    trainable: dict[str, dict[str, Any]] = {}
    for label in labels:
        train = [i for i in train_images if label in decisions.get(i, {})]
        test = [i for i in test_images if label in decisions.get(i, {})]
        positives = sum(decisions[i][label] for i in train)
        negatives = len(train) - positives
        counts = {
            "train_images": len(train),
            "train_positive": positives,
            "train_negative": negatives,
            "test_images": len(test),
            "test_positive": sum(decisions[i][label] for i in test),
            "test_negative": sum(1 - decisions[i][label] for i in test),
        }
        if positives < min_positive or negatives < min_negative:
            report["labels"][label] = {"status": "skipped", "samples": counts}
            continue
        if counts["test_positive"] < 1 or counts["test_negative"] < 1:
            report["labels"][label] = {"status": "skipped", "samples": counts}
            continue
        train_x = np.stack([np.asarray(vectors[i], dtype=np.float32) for i in train])
        train_y = np.asarray([decisions[i][label] for i in train], dtype=np.int64)
        test_x = np.stack([np.asarray(vectors[i], dtype=np.float32) for i in test])
        scaler, model = _fit_probe(train_x, train_y)
        probe = model.predict_proba(scaler.transform(test_x))[:, 1] >= 0.5
        probe_predictions = {
            image_id: {label} if hit else set() for image_id, hit in zip(test, probe, strict=True)
        }
        probe_truth = {
            image_id: ({label} if decisions[image_id][label] else set()) for image_id in test
        }
        threshold, zero_shot = _zero_shot(decisions, sites, vectors, label)
        zero_truth = probe_truth
        zero_predictions = {
            image_id: {label} if hit else set() for image_id, hit in zero_shot.items()
        }
        trainable[label] = {
            "status": "evaluated",
            "samples": counts,
            "probe": evaluate(probe_truth, probe_predictions, [label]),
            "zero_shot": evaluate(zero_truth, zero_predictions, [label]),
            "zero_shot_threshold": threshold,
        }
    report["labels"] = {**report["labels"], **trainable}
    if trainable:
        report["status"] = "measured"
        report["macro_f1"] = {
            "probe": round(
                sum(float(entry["probe"]["macro_f1"] or 0) for entry in trainable.values())
                / len(trainable),
                4,
            ),
            "zero_shot": round(
                sum(float(entry["zero_shot"]["macro_f1"] or 0) for entry in trainable.values())
                / len(trainable),
                4,
            ),
        }
        report["labels_evaluated"] = len(trainable)
    else:
        report["reason"] = (
            "not enough explicit verified/rejected decisions per label; "
            "the framework is ready but the comparison is not statistically meaningful"
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--min-positive", type=int, default=5)
    parser.add_argument("--min-negative", type=int, default=5)
    args = parser.parse_args()
    decisions, sites, vectors = load_decisions()
    result = run(decisions, sites, vectors, args.min_positive, args.min_negative)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "labels"}, indent=2))
    print(f"full report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
