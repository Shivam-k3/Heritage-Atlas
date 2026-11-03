"""Search evaluation from human relevance judgements. No judgements means no number.

Judgement file: data/dataset/search_judgements.json
    {
      "text_queries": [
        {"query": "carved pillars in stepwells", "relevant_image_ids": [4, 6, 7]}
      ],
      "image_queries": [
        {"image": "data/raw/rani-ki-vav/1.jpg", "relevant_image_ids": [4, 6]}
      ]
    }

Usage:
    python backend/scripts/eval_search.py

Precision@5 uses the judged relevant image ids. Queries without judgements are
skipped. Latency is measured after both models are loaded.
"""

import json
import statistics
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app import ml  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

JUDGEMENTS = REPO_ROOT / "data" / "dataset" / "search_judgements.json"
OUTPUT = REPO_ROOT / "data" / "dataset" / "eval_search.json"
K = 5


def _precision(hits: list[dict], relevant: set[int]) -> float:
    if not relevant:
        return 0.0
    return sum(hit["image_id"] in relevant for hit in hits[:K]) / K


def main() -> int:
    if not JUDGEMENTS.exists():
        print(f"no judgements at {JUDGEMENTS}; label top-{K} results before reporting")
        return 1
    data = json.loads(JUDGEMENTS.read_text(encoding="utf-8"))
    ml.embed_text("warmup")
    ml.embed_clip_text("warmup")

    text_scores: list[float] = []
    text_ms: list[float] = []
    image_scores: list[float] = []
    image_ms: list[float] = []
    with TestClient(app) as client:
        for item in data.get("text_queries", []):
            relevant = set(item.get("relevant_image_ids", []))
            if not relevant:
                continue
            started = time.perf_counter()
            hits = client.get("/search/images", params={"q": item["query"], "k": K}).json()
            text_ms.append((time.perf_counter() - started) * 1000)
            text_scores.append(_precision(hits, relevant))

        for item in data.get("image_queries", []):
            relevant = set(item.get("relevant_image_ids", []))
            path = REPO_ROOT / item["image"]
            if not relevant or not path.exists():
                continue
            started = time.perf_counter()
            with path.open("rb") as handle:
                hits = client.post(
                    "/search/by-image",
                    files={"file": (path.name, handle, "image/jpeg")},
                    params={"k": K},
                ).json()
            image_ms.append((time.perf_counter() - started) * 1000)
            image_scores.append(_precision(hits, relevant))

    result = {
        "k": K,
        "text_queries_scored": len(text_scores),
        "image_queries_scored": len(image_scores),
        "precision_at_5_text_to_image": (
            round(statistics.fmean(text_scores), 4) if text_scores else None
        ),
        "precision_at_5_image_to_image": (
            round(statistics.fmean(image_scores), 4) if image_scores else None
        ),
        "median_latency_ms_text_to_image": (
            round(statistics.median(text_ms), 1) if text_ms else None
        ),
        "median_latency_ms_image_to_image": (
            round(statistics.median(image_ms), 1) if image_ms else None
        ),
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not text_scores and not image_scores:
        print("no query had relevance judgements; nothing was measured")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
