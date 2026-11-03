"""Derive ordered trail stops from image capture metadata."""

from collections.abc import Iterable
from typing import Any


def group_visits(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """One stop per site, ordered by the earliest capture time.

    Rows must already be ordered by captured_at. Rows without a capture time or usable
    coordinates are skipped; nothing is invented.
    """
    visits: dict[int, dict[str, Any]] = {}
    for row in rows:
        if not row.get("usable"):
            continue
        site_id = int(row["site_id"])
        if site_id not in visits:
            visits[site_id] = {
                "site_id": site_id,
                "visit_date": row["captured_at"].date(),
            }
    return list(visits.values())
