"""Review statistics by tag. These are review counts, not model accuracy.

Usage:
    python backend/scripts/eval_review_stats.py
"""

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.db import connect  # noqa: E402

OUTPUT = REPO_ROOT / "data" / "dataset" / "eval_review_stats.json"


def main() -> int:
    with connect() as conn:
        by_status = {
            row["status"]: row["count"]
            for row in conn.execute(
                "SELECT status, count(*) AS count FROM image_tags GROUP BY status ORDER BY status"
            )
        }
        by_label = [
            dict(row)
            for row in conn.execute(
                """SELECT t.label,
                          count(*) FILTER (WHERE it.status='auto') AS auto,
                          count(*) FILTER (WHERE it.status='verified') AS verified,
                          count(*) FILTER (WHERE it.status='rejected') AS rejected,
                          count(*) FILTER (WHERE it.status='added_by_human') AS added_by_human
                   FROM tags t JOIN image_tags it ON it.tag_id=t.id
                   GROUP BY t.label ORDER BY t.label"""
            )
        ]
        by_action = {
            row["action"]: row["count"]
            for row in conn.execute(
                "SELECT action, count(*) AS count FROM tag_reviews GROUP BY action ORDER BY action"
            )
        }
        summary = conn.execute("SELECT count(*) AS count FROM tag_reviews").fetchone()
        assert summary is not None
        reviews = summary["count"]

    result = {
        "image_tags_by_status": by_status,
        "tag_reviews_total": reviews,
        "tag_reviews_by_action": by_action,
        "by_label": by_label,
        "note": "review statistics, not model accuracy",
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "by_label"}, indent=2))
    print(f"per-label counts: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
