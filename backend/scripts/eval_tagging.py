"""Tagging evaluation from hand labels. No labels means no metric is reported.

Annotation sheet (`data/dataset/tag_annotations.csv`):
    image_id,site_id,image_path,site_category,expected_features,annotator,annotation_date,split
    4,1,uploads/ab/abcd.jpg,stepwell,sculptural carvings|jali work,asha,2026-11-02,train
    5,1,uploads/cd/cdef.jpg,stepwell,none,asha,2026-11-02,train

Write `none` when a photo has no visible feature from the vocabulary. Leave
`expected_features` empty only while the row is still unlabeled. A human must fill the sheet
before running the model comparison; this script never derives labels from CLIP scores or tags.

Usage:
    python backend/scripts/eval_tagging.py --template
    python backend/scripts/eval_tagging.py

The script tunes per-label thresholds on the tuning sites only and reports on the held-out
test sites. The baseline is the pre-fix system: nine features, one generic prompt each and a
universal 0.22 cut-off. The revised systems use the versioned prompt config. `negative`
subtracts per-feature negative prompt similarity; it is only kept if the validation numbers
justify it, so nothing here claims it is better.
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app import ml  # noqa: E402
from app.db import connect  # noqa: E402
from app.services.evaluation import (  # noqa: E402
    choose_thresholds,
    evaluate,
    predict,
    site_split,
)

ANNOTATIONS = REPO_ROOT / "data" / "dataset" / "tag_annotations.csv"
OUTPUT = REPO_ROOT / "data" / "dataset" / "eval_tagging.json"
REQUIRED_COLUMNS = (
    "image_id",
    "site_id",
    "image_path",
    "site_category",
    "expected_features",
    "annotator",
    "annotation_date",
    "split",
)
BASELINE_FEATURES = (
    "carved pillars",
    "stone arches",
    "jali work",
    "domes",
    "staircases",
    "stone brackets",
    "water tank",
    "sculptural carvings",
    "decorative facade",
)
BASELINE_THRESHOLD = 0.22
MAX_FEATURES = 4


def write_template(path: Path = ANNOTATIONS, limit: int | None = None) -> int:
    """Write the annotation columns with database metadata but no model output."""
    query = """SELECT i.id, i.site_id, i.storage_path, s.category
               FROM images i JOIN sites s ON s.id=i.site_id
               WHERE i.status='processed' AND i.clip_embedding IS NOT NULL
               ORDER BY i.site_id, i.id"""
    params: list[Any] = []
    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(REQUIRED_COLUMNS)
        for row in rows:
            writer.writerow(
                [
                    row["id"],
                    row["site_id"],
                    row["storage_path"],
                    row["category"] or "unknown",
                    "",
                    "",
                    "",
                    site_split(int(row["site_id"])),
                ]
            )
    print(f"wrote {len(rows)} unlabeled rows to {path}")
    return len(rows)


def read_annotations(path: Path = ANNOTATIONS) -> dict[int, dict[str, Any]]:
    """Read completed human rows. Empty expected_features means still unlabeled."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = set(REQUIRED_COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"annotation sheet is missing columns: {', '.join(sorted(missing))}")
        annotations: dict[int, dict[str, Any]] = {}
        for row in reader:
            raw = (row.get("expected_features") or "").strip()
            if not raw:
                continue
            if (
                not (row.get("annotator") or "").strip()
                or not (row.get("annotation_date") or "").strip()
            ):
                continue
            image_id = int(row["image_id"])
            site_id = int(row["site_id"])
            expected = {
                part.strip().lower().replace("_", " ") for part in raw.split("|") if part.strip()
            }
            if expected == {"none"}:
                expected = set()
            annotations[image_id] = {
                "site_id": site_id,
                "split": site_split(site_id),
                "expected": expected,
            }
    return annotations


def _image_paths(image_ids: list[int]) -> dict[int, str]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, storage_path FROM images WHERE id = ANY(%s)", (image_ids,)
        ).fetchall()
    paths = {int(row["id"]): str(row["storage_path"]) for row in rows}
    missing = set(image_ids) - set(paths)
    if missing:
        raise ValueError(f"images not found: {sorted(missing)}")
    return paths


def _baseline_embeddings() -> Any:
    prompts = [
        f"a photo showing {feature}, Indian heritage architecture" for feature in BASELINE_FEATURES
    ]
    return ml.clip().encode(prompts, normalize_embeddings=True, batch_size=16)


def score_annotations(
    annotations: dict[int, dict[str, Any]], method: str = "revised"
) -> dict[int, dict[str, float]]:
    """CLIP scores per annotated image. Baseline and revised do not share a vocabulary."""
    if not annotations:
        return {}
    image_ids = list(annotations)
    paths = _image_paths(image_ids)
    vectors = ml.embed_images([paths[image_id] for image_id in image_ids])
    scores: dict[int, dict[str, float]] = {}
    baseline = _baseline_embeddings() if method == "baseline" else None
    for image_id, vector in zip(image_ids, vectors, strict=True):
        if baseline is not None:
            scores[image_id] = {
                label: float(baseline[index] @ vector)
                for index, label in enumerate(BASELINE_FEATURES)
            }
        else:
            scores[image_id] = ml.feature_scores(vector, use_negatives=method == "negative")
    return scores


def _thresholds_for(
    method: str,
    tune_truth: dict[int, set[str]],
    tune_scores: dict[int, dict[str, float]],
    labels: tuple[str, ...],
) -> dict[str, float | None]:
    if method == "baseline":
        return {label: BASELINE_THRESHOLD for label in labels}
    if not tune_truth:
        return {label: None for label in labels}
    return choose_thresholds(tune_truth, tune_scores, labels)


def _predictions(
    truth: dict[int, set[str]],
    scores: dict[int, dict[str, float]],
    thresholds: dict[str, float | None],
) -> dict[int, set[str]]:
    return {
        image_id: predict(scores[image_id], thresholds, MAX_FEATURES)
        for image_id in truth
        if image_id in scores
    }


def compare(annotations: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """Run baseline and revised methods on the same site-wise hold-out."""
    splits = {
        split: {i: data for i, data in annotations.items() if data["split"] == split}
        for split in ("train", "tune", "test")
    }
    truth = {
        split: {i: data["expected"] for i, data in rows.items()} for split, rows in splits.items()
    }
    info = ml.model_info()
    methods: dict[str, Any] = {}
    for method, labels in (
        ("baseline", BASELINE_FEATURES),
        ("revised", tuple(info["features"])),
        ("negative", tuple(info["features"])),
    ):
        scores = score_annotations(annotations, method=method)
        tune_scores = {i: scores[i] for i in truth["tune"] if i in scores}
        test_scores = {i: scores[i] for i in truth["test"] if i in scores}
        thresholds = _thresholds_for(method, truth["tune"], tune_scores, labels)
        predictions = _predictions(truth["test"], test_scores, thresholds)
        metrics = evaluate(truth["test"], predictions, labels)
        methods[method] = {
            "labels": list(labels),
            "thresholds": thresholds,
            "tuned_on_images": len(truth["tune"]),
            "metrics": metrics,
        }
    return {
        "status": "measured" if truth["test"] else "not_measured",
        "reason": None if truth["test"] else "no completed labels on held-out test sites",
        "prompt_version": info["prompt_version"],
        "clip_model": info["clip_model"],
        "split_sites": {
            split: sorted({data["site_id"] for data in rows.values()})
            for split, rows in splits.items()
        },
        "split_images": {split: len(rows) for split, rows in splits.items()},
        "methods": methods,
        "notes": [
            "Scores are raw cosine similarities, not probabilities.",
            "Thresholds are tuned only on the tuning sites.",
            "The dataset is small; a four- or five-site test split is exploratory, not a generalisation claim.",
            "The baseline has nine features and a universal 0.22 cut-off; it can never predict a revised-only label.",
        ],
    }


def score(
    labels: dict[int, set[str]], predictions: dict[int, set[str]], vocabulary: set[str]
) -> dict[str, Any]:
    """Backwards-compatible wrapper used by the metric tests."""
    result = evaluate(labels, predictions, sorted(vocabulary))
    return {
        "images_labeled": result["images_evaluated"],
        "labels_evaluated": result["labels_evaluated"],
        "macro_f1": result["macro_f1"],
        "micro_precision": result["micro_precision"],
        "micro_recall": result["micro_recall"],
        "per_label": result["per_label"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", action="store_true", help="write an empty annotation sheet")
    parser.add_argument("--annotations", type=Path, default=ANNOTATIONS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    if args.template:
        write_template(args.annotations, args.limit)
        return 0
    if not args.annotations.exists():
        print(f"no annotation sheet at {args.annotations}; run with --template first")
        return 1
    annotations = read_annotations(args.annotations)
    if not annotations:
        print(f"{args.annotations} has no completed rows; nothing to score")
        return 1
    result = compare(annotations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if result["status"] != "measured":
        print("no held-out test labels; metrics were not measured")
        return 1
    print(f"full report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
