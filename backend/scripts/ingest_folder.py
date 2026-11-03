"""Ingest a local folder of photographs (CLI only).

Usage (from the repo root, after scripts/init_db.py):
    python backend/scripts/ingest_folder.py data/trip
    python backend/scripts/ingest_folder.py data/trip --radius-m 300 --author "A. Photographer"

Re-running the same folder is safe: files are content-addressed by SHA-256 and an existing
image is reported as a duplicate instead of being stored again. Jobs are reused while a
pending or running job exists. Progress is committed as the batch advances, so an interrupted
run leaves a batch with partial counts that can be inspected via GET /ingest/batches/{id}.
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import max_upload_bytes, upload_dir  # noqa: E402
from app.db import connect  # noqa: E402
from app.ml import InvalidImageError  # noqa: E402
from app.repositories import images as images_repo  # noqa: E402
from app.repositories import ingestion as ingestion_repo  # noqa: E402
from app.repositories import sites as sites_repo  # noqa: E402
from app.services.images import (  # noqa: E402
    SavedImage,
    UploadTooLargeError,
    extract_captured_at,
    extract_gps,
    save_image,
)
from app.services.ingestion import (  # noqa: E402
    DEFAULT_CLUSTER_RADIUS_M,
    DRAFT_SITE_NAME,
    NO_GPS_SITE_NAME,
    ScanEntry,
    cluster_points,
    scan_folder,
)
from PIL import Image  # noqa: E402


def _record(entry, status: str, **fields) -> dict:
    record = {"file": entry.relative_path, "status": status}
    record.update(fields)
    return record


def ingest_folder(
    folder: Path,
    radius_m: int = DEFAULT_CLUSTER_RADIUS_M,
    author: str | None = None,
    licence: str | None = None,
    licence_url: str | None = None,
    source_url: str | None = None,
) -> dict:
    entries = scan_folder(folder)
    root = upload_dir()
    report: dict = {
        "folder": str(folder),
        "radius_m": radius_m,
        "attribution": {
            "author": author or "unknown",
            "licence": licence or "unknown",
            "licence_url": licence_url or "unknown",
            "source_url": source_url or "unknown",
        },
        "files": [],
        "error": None,
    }
    records: list[dict | None] = [None] * len(entries)

    with connect() as conn:
        batch = ingestion_repo.create_batch(conn, str(folder))
        batch_id = int(batch["id"])
        conn.commit()
        counts = {
            "total_files": len(entries),
            "accepted": 0,
            "duplicates": 0,
            "rejected": 0,
            "gps_images": 0,
            "clusters": 0,
        }
        try:
            pending: list[tuple[int, ScanEntry, SavedImage]] = []
            pending_by_sha: dict[str, int] = {}
            for index, entry in enumerate(entries):
                try:
                    with entry.path.open("rb") as stream:
                        saved = save_image(stream, entry.path.name, root, max_upload_bytes())
                except (InvalidImageError, UploadTooLargeError, OSError) as exc:
                    counts["rejected"] += 1
                    records[index] = _record(entry, "rejected", error=str(exc))
                    continue
                existing = images_repo.find_by_sha256(conn, saved.sha256)
                if existing:
                    counts["duplicates"] += 1
                    records[index] = _record(
                        entry,
                        "duplicate",
                        image_id=int(existing["id"]),
                        site_id=int(existing["site_id"]),
                        sha256=saved.sha256,
                    )
                    continue
                duplicate = pending_by_sha.get(saved.sha256)
                if duplicate:
                    counts["duplicates"] += 1
                    records[index] = _record(
                        entry,
                        "duplicate",
                        duplicate_of=entries[duplicate].relative_path,
                        sha256=saved.sha256,
                    )
                    continue
                pending_by_sha[saved.sha256] = index
                pending.append((index, entry, saved))

            gps_points = [
                (index, saved.lat, saved.lon)
                for index, _, saved in pending
                if saved.lat is not None and saved.lon is not None
            ]
            clusters = cluster_points(gps_points, radius_m)
            site_for: dict[int, int] = {}
            for cluster in clusters:
                site = sites_repo.create_draft_site(
                    conn,
                    DRAFT_SITE_NAME,
                    cluster.lat,
                    cluster.lon,
                    "exif_cluster",
                    "Draft cluster from EXIF GPS. Not a verified monument.",
                )
                for index in cluster.image_ids:
                    site_for[index] = int(site["id"])
            if any(index not in site_for for index, _, _ in pending):
                no_gps = sites_repo.create_draft_site(
                    conn,
                    NO_GPS_SITE_NAME,
                    None,
                    None,
                    "exif_cluster_no_gps",
                    "Draft cluster for photographs without EXIF GPS.",
                )
                for index, _, _ in pending:
                    site_for.setdefault(index, int(no_gps["id"]))
            counts["clusters"] = len(clusters)
            counts["gps_images"] = len(gps_points)
            ingestion_repo.update_progress(conn, batch_id, **counts)
            conn.commit()

            for index, entry, saved in pending:
                image = images_repo.create_image(
                    conn,
                    site_for[index],
                    saved,
                    author=author or "unknown",
                    licence=licence or "unknown",
                    licence_url=licence_url or "unknown",
                    source_url=source_url or "unknown",
                )
                images_repo.create_job(conn, int(image["id"]))
                counts["accepted"] += 1
                records[index] = _record(
                    entry,
                    "accepted",
                    image_id=int(image["id"]),
                    site_id=site_for[index],
                    sha256=saved.sha256,
                    gps=saved.lat is not None,
                    captured_at=saved.captured_at.isoformat()
                    if isinstance(saved.captured_at, datetime)
                    else None,
                )
                if counts["accepted"] % 10 == 0:
                    ingestion_repo.update_progress(conn, batch_id, **counts)
                    conn.commit()

            report["files"] = [record for record in records if record is not None]
            ingestion_repo.update_progress(conn, batch_id, **counts)
            batch = ingestion_repo.finish_batch(conn, batch_id, status="completed", report=report)
            conn.commit()
            return batch
        except Exception as exc:  # noqa: BLE001 - the batch must be marked failed, then re-raise
            conn.rollback()
            report["files"] = [record for record in records if record is not None]
            report["error"] = f"{type(exc).__name__}: {exc}"
            ingestion_repo.update_progress(conn, batch_id, **counts)
            ingestion_repo.finish_batch(conn, batch_id, status="failed", report=report)
            conn.commit()
            raise


def dry_run(folder: Path, radius_m: int = DEFAULT_CLUSTER_RADIUS_M) -> dict:
    """Scan and cluster without touching the database or writing uploaded copies.

    Useful on a real trip folder before a database is available; it reports GPS coverage,
    corrupt files and duplicate content, but creates no draft sites.
    """
    entries = scan_folder(folder)
    seen: dict[str, str] = {}
    points: list[tuple[int, float, float]] = []
    records: list[dict] = []
    for index, entry in enumerate(entries):
        digest = hashlib.sha256(entry.path.read_bytes()).hexdigest()
        if digest in seen:
            records.append(
                {
                    "file": entry.relative_path,
                    "status": "duplicate",
                    "duplicate_of": seen[digest],
                }
            )
            continue
        seen[digest] = entry.relative_path
        try:
            with Image.open(entry.path) as image:
                lat, lon = extract_gps(image)
                captured_at = extract_captured_at(image)
        except (OSError, ValueError):
            records.append({"file": entry.relative_path, "status": "rejected"})
            continue
        if lat is not None and lon is not None:
            points.append((index, lat, lon))
        records.append(
            {
                "file": entry.relative_path,
                "status": "accepted",
                "gps": lat is not None and lon is not None,
                "captured_at": captured_at.isoformat() if captured_at else None,
            }
        )
    clusters = cluster_points(points, radius_m)
    return {
        "folder": str(folder),
        "radius_m": radius_m,
        "total_files": len(entries),
        "accepted": sum(record["status"] == "accepted" for record in records),
        "duplicates": sum(record["status"] == "duplicate" for record in records),
        "rejected": sum(record["status"] == "rejected" for record in records),
        "gps_images": len(points),
        "clusters": len(clusters),
        "cluster_sizes": [len(cluster.image_ids) for cluster in clusters],
        "files": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a folder of heritage photographs")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--radius-m", type=int, default=DEFAULT_CLUSTER_RADIUS_M)
    parser.add_argument("--author")
    parser.add_argument("--licence")
    parser.add_argument("--licence-url")
    parser.add_argument("--source-url")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="scan, hash and cluster only; no database writes",
    )
    args = parser.parse_args()
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")
    if args.dry_run:
        print(json.dumps(dry_run(args.folder.resolve(), args.radius_m), indent=2))
        return
    batch = ingest_folder(
        args.folder.resolve(),
        radius_m=args.radius_m,
        author=args.author,
        licence=args.licence,
        licence_url=args.licence_url,
        source_url=args.source_url,
    )
    print(
        f"batch {batch['id']}: {batch['accepted']} accepted, {batch['duplicates']} duplicates, "
        f"{batch['rejected']} rejected, {batch['gps_images']} with GPS, "
        f"{batch['clusters']} draft clusters"
    )


if __name__ == "__main__":
    main()
