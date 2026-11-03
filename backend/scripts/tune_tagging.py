"""Tune per-feature CLIP acceptance thresholds on the tuning sites only.

The tuning split comes from the human annotation sheet (see eval_tagging.py). Test sites are
never read. Thresholds are raw cosine cut-offs, not probabilities; a feature without a
positive tuning example stays unset and can never be emitted.

Usage:
    python backend/scripts/tune_tagging.py                 # report only
    python backend/scripts/tune_tagging.py --write         # update feature_prompts.json

Committing feature_prompts.json after --write records the calibrated thresholds with the
prompt version that produced them. Re-run the evaluation on the untouched test sites.
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPTS.parent
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(SCRIPTS))

import eval_tagging as tagging  # noqa: E402
from app import config, ml  # noqa: E402
from app.services.evaluation import choose_thresholds  # noqa: E402

ANNOTATIONS = tagging.ANNOTATIONS
OUTPUT = REPO_ROOT / "data" / "dataset" / "tagging_thresholds.json"


def tune(annotations: dict[int, dict[str, Any]], method: str = "revised") -> dict[str, Any]:
    tuning = {image_id: data for image_id, data in annotations.items() if data["split"] == "tune"}
    truth = {image_id: data["expected"] for image_id, data in tuning.items()}
    scores = tagging.score_annotations(tuning, method=method)
    labels = tuple(ml.FEATURES)
    thresholds = choose_thresholds(truth, scores, labels)
    return {
        "method": method,
        "prompt_version": ml.model_info()["prompt_version"],
        "clip_model": ml.model_info()["clip_model"],
        "tuning_images": len(tuning),
        "tuning_sites": sorted({data["site_id"] for data in tuning.values()}),
        "positive_labels": sorted(
            label for label, threshold in thresholds.items() if threshold is not None
        ),
        "thresholds": thresholds,
    }


def write_thresholds(result: dict[str, Any], path: Path | None = None) -> None:
    """Persist tuned cut-offs next to the prompt variants they belong to."""
    config_path = path or config.feature_prompts_path()
    data = json.loads(config_path.read_text(encoding="utf-8"))
    thresholds = result["thresholds"]
    for feature in data["features"]:
        feature["threshold"] = thresholds.get(str(feature["label"]).strip().lower())
    data["threshold_tuning"] = {
        "date": date.today().isoformat(),
        "method": result["method"],
        "tuning_images": result["tuning_images"],
        "tuning_sites": result["tuning_sites"],
        "prompt_version": result["prompt_version"],
        "clip_model": result["clip_model"],
    }
    config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotations", type=Path, default=ANNOTATIONS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--method", choices=("revised", "negative"), default="revised")
    parser.add_argument("--write", action="store_true", help="update feature_prompts.json")
    args = parser.parse_args()
    if not args.annotations.exists():
        print(f"no annotation sheet at {args.annotations}; run eval_tagging.py --template first")
        return 1
    annotations = tagging.read_annotations(args.annotations)
    if not annotations:
        print("no completed annotation rows; thresholds were not tuned")
        return 1
    result = tune(annotations, method=args.method)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not result["positive_labels"]:
        print("no feature had a positive tuning example; thresholds left unset")
        return 1
    if args.write:
        write_thresholds(result)
        print(f"updated thresholds in {config.feature_prompts_path()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
