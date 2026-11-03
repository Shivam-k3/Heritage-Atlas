"""Turn the download manifest into portable metadata files and the tracking CSV.

Usage (from the repo root):
    python -m scripts.dataset.generate_metadata
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "data" / "dataset" / "manifest.json"
DEFAULT_CSV = REPO_ROOT / "data" / "sites.csv"
CSV_FIELDS = [
    "site_name",
    "region",
    "category",
    "lat",
    "lon",
    "description",
    "description_source",
    "image_file",
    "author",
    "licence",
    "source_url",
    "labelled_tags",
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_images(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for site in manifest.get("sites", []):
        for image in site.get("images", []):
            rows.append(
                {
                    "site_slug": site["slug"],
                    "site_name": site["name"],
                    "region": site.get("region"),
                    "category": site.get("category"),
                    "lat": site.get("lat"),
                    "lon": site.get("lon"),
                    "site_description": site.get("description", ""),
                    "site_description_source": site.get("description_source", ""),
                    **image,
                }
            )
    return rows


def write_csv(manifest: dict[str, Any], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = flatten_images(manifest)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "site_name": row["site_name"],
                    "region": row.get("region") or "",
                    "category": row.get("category") or "",
                    "lat": row.get("lat") if row.get("lat") is not None else "",
                    "lon": row.get("lon") if row.get("lon") is not None else "",
                    "description": " ".join(str(row.get("site_description") or "").split()),
                    "description_source": row.get("site_description_source") or "",
                    "image_file": row["local_path"],
                    "author": row.get("author") or "",
                    "licence": row.get("licence") or "",
                    "source_url": row.get("source_url") or "",
                    "labelled_tags": "",
                }
            )
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args()

    manifest = _load(args.manifest)
    dataset_dir = args.manifest.parent
    sites: list[dict[str, Any]] = []
    for site in manifest.get("sites", []):
        sites.append(
            {key: value for key, value in site.items() if key != "images"}
            | {"image_count": len(site.get("images", []))}
        )
    images = flatten_images(manifest)

    dataset_dir.mkdir(parents=True, exist_ok=True)
    (dataset_dir / "sites.json").write_text(
        json.dumps(sites, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (dataset_dir / "images.json").write_text(
        json.dumps(images, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    count = write_csv(manifest, args.csv)
    print(f"Wrote {len(sites)} sites, {count} image rows to {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
