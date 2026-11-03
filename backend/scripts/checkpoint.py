"""End-to-end checkpoint against a seeded database with the real CLIP/MiniLM models.

Prerequisites:
    python backend/scripts/init_db.py
    python backend/scripts/load_dataset.py
    python backend/worker.py --once
    python backend/scripts/embed_descriptions.py

Usage (from the repo root):
    python backend/scripts/checkpoint.py

The script uploads one cropped dataset photo, runs the worker, then exercises text
search, text-to-image, image-to-image, related sites, review and trails. Results are
printed and written to data/dataset/checkpoint.json.
"""

import io
import json
import sys
import time
from pathlib import Path
from typing import Any, cast

cast(Any, sys.stdout).reconfigure(encoding="utf-8")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

import worker  # noqa: E402
from app import ml  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

MANIFEST = REPO_ROOT / "data" / "dataset" / "manifest.json"
OUTPUT = REPO_ROOT / "data" / "dataset" / "checkpoint.json"


def _crop_upload(manifest: dict) -> bytes:
    first = next(site for site in manifest["sites"] if site["slug"] == "rani-ki-vav")
    path = REPO_ROOT / first["images"][0]["local_path"]
    with Image.open(path) as source:
        image = source.convert("RGB")
        side = min(image.size)
        left = (image.width - side) // 2
        top = (image.height - side) // 2
        cropped = image.crop((left, top, left + side, top + side)).resize((640, 640))
        buffer = io.BytesIO()
        cropped.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    # Load both models before timing so the numbers are steady-state, not cold start.
    ml.embed_text("warmup")
    ml.embed_clip_text("warmup")
    results: dict[str, object] = {}
    with TestClient(app) as client:
        sites = client.get("/sites", params={"limit": 5}).json()
        site_id = next(
            site["id"] for site in client.get("/sites").json() if site["name"] == "Rani ki Vav"
        )
        results["sites_sample"] = sites

        upload = client.post(
            "/images/upload",
            files={"file": ("checkpoint.jpg", _crop_upload(manifest), "image/jpeg")},
            data={
                "site_id": str(site_id),
                "author": "Heritage Atlas checkpoint",
                "licence": "CC BY-SA 4.0",
                "source_url": "https://example.org/checkpoint",
            },
        )
        results["upload_status"] = upload.status_code
        results["upload"] = upload.json()
        if upload.json()["duplicate"]:
            results["job"] = {"skipped": "duplicate upload already processed"}
        else:
            worker.main(drain=True)
            results["job"] = client.get(f"/jobs/{upload.json()['job_id']}").json()
        results["uploaded_image"] = client.get(f"/images/{upload.json()['image_id']}").json()

        started = time.perf_counter()
        text_hits = client.get(
            "/search/text", params={"q": "stepwell with carved pillars and sculptures", "k": 5}
        ).json()
        results["text_search_ms"] = round((time.perf_counter() - started) * 1000, 1)
        results["text_search"] = text_hits

        started = time.perf_counter()
        image_hits = client.get(
            "/search/images", params={"q": "ancient stepwell with geometric stone steps", "k": 5}
        ).json()
        results["image_search_ms"] = round((time.perf_counter() - started) * 1000, 1)
        results["image_search"] = image_hits

        started = time.perf_counter()
        similar = client.post(
            "/search/by-image",
            files={"file": ("query.jpg", _crop_upload(manifest), "image/jpeg")},
            params={"k": 5},
        ).json()
        results["image_to_image_ms"] = round((time.perf_counter() - started) * 1000, 1)
        results["image_to_image"] = similar

        results["related"] = client.get(f"/sites/{site_id}/related", params={"k": 5}).json()
        results["review_queue"] = client.get("/review/queue", params={"limit": 3}).json()

        trail = client.post(
            "/trails", json={"title": "Checkpoint stepwell trail", "created_by": "checkpoint"}
        ).json()
        client.post(
            f"/trails/{trail['id']}/stops",
            json={"site_id": site_id, "visit_date": "2026-10-31", "note": "Original field note"},
        )
        second = next(
            site["id"] for site in client.get("/sites").json() if site["name"] == "Adalaj Stepwell"
        )
        client.post(f"/trails/{trail['id']}/stops", json={"site_id": second})
        results["trail_summary"] = client.get(f"/trails/{trail['id']}/summary").json()
        results["trail_journal"] = client.get(f"/trails/{trail['id']}/journal").json()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
