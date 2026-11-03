"""Download a licensed heritage photo set from Wikimedia Commons.

Usage (from the repo root):
    python -m scripts.dataset.download_wikimedia --per-site 5

Raw images go to data/raw/<site-slug>/ and are gitignored. The manifest keeps the
author, licence, source URL and original dimensions for every downloaded file.
"""

import argparse
import hashlib
import json
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image

from .commons_client import (
    IMAGE_MIME,
    download_file,
    file_candidates,
    image_info,
    resolve_category,
    wikipedia_page,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.licences import clean_text, is_reusable, normalise_licence  # noqa: E402

logger = logging.getLogger("dataset.download")
DEFAULT_SITES = Path(__file__).with_name("sites.json")
DEFAULT_RAW = REPO_ROOT / "data" / "raw"
DEFAULT_MANIFEST = REPO_ROOT / "data" / "dataset" / "manifest.json"
BATCH_SIZE = 20


def _meta(info: dict[str, Any], key: str) -> str:
    return clean_text(str((info.get("extmetadata") or {}).get(key, {}).get("value", "")))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"generated_at": None, "source": "Wikimedia Commons", "sites": []}


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    manifest["generated_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _image_record(
    info: dict[str, Any], local_path: Path, size: int, raw_dir: Path
) -> dict[str, Any]:
    licence = normalise_licence(_meta(info, "LicenseShortName"))
    with Image.open(local_path) as handle:
        local_width, local_height = handle.size
    try:
        local = local_path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        local = local_path.as_posix()
    return {
        "file_title": info["title"],
        "local_path": local,
        "source_url": str(info.get("descriptionurl", "")),
        "thumb_url": str(info.get("thumburl", info.get("url", ""))),
        "original_url": str(info.get("url", "")),
        "author": _meta(info, "Artist") or "Unknown",
        "licence": licence,
        "licence_url": _meta(info, "LicenseUrl"),
        "credit": _meta(info, "Credit"),
        "description": _meta(info, "ImageDescription"),
        "width": int(info.get("width", 0)),
        "height": int(info.get("height", 0)),
        "local_width": local_width,
        "local_height": local_height,
        "mime_type": str(info.get("mime", "")),
        "file_size": size,
        "sha256": _sha256(local_path),
        "sha1": str(info.get("sha1", "")),
        "relative_dir": local_path.parent.relative_to(raw_dir).as_posix(),
    }


def _eligible(info: dict[str, Any], min_width: int, min_height: int, seen: set[str]) -> bool:
    if str(info.get("mime", "")) not in IMAGE_MIME:
        return False
    if int(info.get("width", 0)) < min_width or int(info.get("height", 0)) < min_height:
        return False
    if str(info.get("sha1", "")) in seen:
        return False
    licence = normalise_licence(_meta(info, "LicenseShortName"))
    return bool(licence) and is_reusable(licence)


def download_site(
    site: dict[str, Any],
    raw_dir: Path,
    per_site: int,
    min_width: int,
    min_height: int,
    seen: set[str],
) -> list[dict[str, Any]]:
    candidates = file_candidates(site, per_site)
    images: list[dict[str, Any]] = []
    for start in range(0, len(candidates), BATCH_SIZE):
        batch = candidates[start : start + BATCH_SIZE]
        for info in image_info(batch):
            if len(images) >= per_site:
                return images
            if not _eligible(info, min_width, min_height, seen):
                continue
            destination = raw_dir / site["slug"]
            try:
                path, size = download_file(info, destination)
            except Exception as exc:  # noqa: BLE001 - one broken file must not stop the run
                logger.warning("skip %s: %s", info.get("title"), exc)
                continue
            seen.add(str(info.get("sha1", "")))
            images.append(_image_record(info, path, size, raw_dir))
            logger.info("%s: %s (%s)", site["slug"], path.name, images[-1]["licence"])
            time.sleep(0.1)
    return images


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sites", type=Path, default=DEFAULT_SITES)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--per-site", type=int, default=5)
    parser.add_argument("--min-width", type=int, default=1200)
    parser.add_argument("--min-height", type=int, default=600)
    parser.add_argument(
        "--force", action="store_true", help="re-download sites already in manifest"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sites = json.loads(args.sites.read_text(encoding="utf-8-sig"))
    manifest = _load_manifest(args.manifest)
    existing = {site["slug"]: site for site in manifest.get("sites", [])}
    seen = {
        image["sha1"]
        for site in existing.values()
        for image in site.get("images", [])
        if image.get("sha1")
    }
    args.raw_dir.mkdir(parents=True, exist_ok=True)

    for index, site in enumerate(sites, start=1):
        slug = site["slug"]
        previous = existing.get(slug)
        if previous and len(previous.get("images", [])) >= args.per_site and not args.force:
            logger.info("[%s/%s] %s already complete", index, len(sites), slug)
            continue
        category = resolve_category(site)
        if not category:
            logger.warning("[%s/%s] no Commons category for %s", index, len(sites), site["name"])
            category = ""
        logger.info("[%s/%s] %s via %s", index, len(sites), site["name"], category or "search")
        page = wikipedia_page(site.get("wikipedia") or site["name"])
        images = download_site(
            site, args.raw_dir, args.per_site, args.min_width, args.min_height, seen
        )
        existing[slug] = {
            **site,
            "commons_category": category,
            "description": page.get("description", ""),
            "description_source": (
                f"https://en.wikipedia.org/wiki/{page['title'].replace(' ', '_')}"
                if page.get("description")
                else ""
            ),
            "lat": page.get("lat") or site.get("lat"),
            "lon": page.get("lon") or site.get("lon"),
            "images": images,
        }
        manifest["sites"] = list(existing.values())
        _write_manifest(args.manifest, manifest)
        logger.info("[%s/%s] %s: %s images", index, len(sites), slug, len(images))

    _write_manifest(args.manifest, manifest)
    total = sum(len(site.get("images", [])) for site in manifest["sites"])
    print(
        f"Manifest written to {args.manifest} with {len(manifest['sites'])} sites, {total} images"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
