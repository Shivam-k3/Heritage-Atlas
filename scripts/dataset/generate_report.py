"""Write a factual dataset report from the manifest and validation output.

Usage (from the repo root):
    python -m scripts.dataset.generate_report
"""

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "data" / "dataset" / "manifest.json"
DEFAULT_VALIDATION = REPO_ROOT / "data" / "dataset" / "validation.json"
DEFAULT_REPORT = REPO_ROOT / "data" / "dataset" / "REPORT.md"


def _load(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def build(manifest: dict[str, Any], validation: dict[str, Any]) -> str:
    sites = manifest.get("sites", [])
    images = [image for site in sites for image in site.get("images", [])]
    by_region = Counter(str(site.get("region", "")) for site in sites)
    by_category = Counter(str(site.get("category", "")) for site in sites)
    by_licence = Counter(str(image.get("licence", "")) for image in images)
    total_bytes = sum(int(image.get("file_size", 0)) for image in images)
    lines = [
        "# Dataset report",
        "",
        "Generated from `data/dataset/manifest.json` and `validation.json`. "
        "These are dataset facts, not model metrics.",
        "",
        "## Summary",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| Sites | {len(sites)} |",
        f"| Images | {len(images)} |",
        f"| Unique images | {validation.get('unique_images', len(images))} |",
        f"| Total size | {total_bytes / (1024 * 1024):.1f} MB |",
        f"| Validation errors | {len(validation.get('errors', []))} |",
        f"| Validation warnings | {len(validation.get('warnings', []))} |",
        "",
        "## Sites by region",
        "",
        "| Region | Sites |",
        "|---|---|",
        *[f"| {name or 'unknown'} | {count} |" for name, count in sorted(by_region.items())],
        "",
        "## Sites by category",
        "",
        "| Category | Sites |",
        "|---|---|",
        *[f"| {name or 'unknown'} | {count} |" for name, count in sorted(by_category.items())],
        "",
        "## Images by licence",
        "",
        "| Licence | Images |",
        "|---|---|",
        *[f"| {name or 'missing'} | {count} |" for name, count in sorted(by_licence.items())],
        "",
        "## Images per site",
        "",
        "| Site | Region | Category | Images |",
        "|---|---|---|---|",
        *[
            f"| {site['name']} | {site.get('region', '')} | {site.get('category', '')} | "
            f"{len(site.get('images', []))} |"
            for site in sites
        ],
        "",
    ]
    if validation.get("errors"):
        lines += ["## Validation errors", "", *[f"- {item}" for item in validation["errors"]], ""]
    if validation.get("warnings"):
        lines += [
            "## Validation warnings",
            "",
            *[f"- {item}" for item in validation["warnings"]],
            "",
        ]
    lines += [
        "## Source",
        "",
        "Images were downloaded from Wikimedia Commons at thumbnail width 1600 px. "
        "Each image row keeps its original file page, author, licence and source URL. "
        "Raw images are not committed; rerun `python -m scripts.dataset.download_wikimedia` "
        "to recreate `data/raw/`.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    manifest = _load(args.manifest, {"sites": []})
    validation = _load(args.validation, {})
    report = build(manifest, validation)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(f"Report written to {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
