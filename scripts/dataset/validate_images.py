"""Validate downloaded images and their licence metadata.

Usage (from the repo root):
    python -m scripts.dataset.validate_images            # report, exit 0
    python -m scripts.dataset.validate_images --strict   # exit 1 on errors
"""

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.licences import is_reusable  # noqa: E402

DEFAULT_MANIFEST = REPO_ROOT / "data" / "dataset" / "manifest.json"
DEFAULT_REPORT = REPO_ROOT / "data" / "dataset" / "validation.json"
MIN_WIDTH = 800
MIN_HEIGHT = 600


def _resolve(path: str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else REPO_ROOT / value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(manifest: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    seen_hashes: dict[str, str] = {}
    images = 0
    for site in manifest.get("sites", []):
        if not site.get("images"):
            errors.append(f"{site['slug']}: no images")
        for image in site.get("images", []):
            images += 1
            label = image.get("file_title") or image.get("local_path")
            path = _resolve(image["local_path"])
            if not path.exists():
                errors.append(f"{label}: file missing at {path}")
                continue
            try:
                with Image.open(path) as handle:
                    width, height = handle.size
                    handle.verify()
            except (UnidentifiedImageError, OSError, ValueError) as exc:
                errors.append(f"{label}: unreadable image ({exc})")
                continue
            if width < MIN_WIDTH or height < MIN_HEIGHT:
                warnings.append(f"{label}: small image {width}x{height}")
            if image.get("local_width") and image.get("local_height"):
                if (width, height) != (image["local_width"], image["local_height"]):
                    warnings.append(
                        f"{label}: stored dimensions {image['local_width']}x{image['local_height']} "
                        f"differ from file {width}x{height}"
                    )
            elif not image.get("thumb_url") and image.get("width") and image.get("height"):
                if (width, height) != (image["width"], image["height"]):
                    warnings.append(
                        f"{label}: stored dimensions {image['width']}x{image['height']} "
                        f"differ from file {width}x{height}"
                    )
            if image.get("sha256") and _sha256(path) != image["sha256"]:
                errors.append(f"{label}: sha256 does not match the manifest")
            if image.get("sha256") in seen_hashes:
                errors.append(f"{label}: duplicate of {seen_hashes[image['sha256']]}")
            else:
                seen_hashes[image["sha256"]] = label
            if not is_reusable(str(image.get("licence", ""))):
                errors.append(f"{label}: missing or non-reusable licence")
            if not image.get("author") or image.get("author") == "Unknown":
                warnings.append(f"{label}: author is unknown")
            if not image.get("source_url"):
                errors.append(f"{label}: source_url is missing")
    licences = Counter(
        str(image.get("licence", ""))
        for site in manifest.get("sites", [])
        for image in site.get("images", [])
    )
    return {
        "sites": len(manifest.get("sites", [])),
        "images": images,
        "unique_images": len(seen_hashes),
        "licences": dict(sorted(licences.items())),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = validate(manifest)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"{report['sites']} sites, {report['images']} images "
        f"({report['unique_images']} unique), {len(report['errors'])} errors, "
        f"{len(report['warnings'])} warnings"
    )
    for error in report["errors"][:20]:
        print(f"ERROR {error}")
    for warning in report["warnings"][:10]:
        print(f"WARN  {warning}")
    return 1 if args.strict and report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
