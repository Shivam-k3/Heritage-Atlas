"""Review queue, human decisions and append-only audit history."""

from typing import Any

import psycopg

from ..config import upload_dir
from ..services.images import public_url


def queue(
    conn: psycopg.Connection[dict[str, Any]],
    limit: int = 50,
    offset: int = 0,
    status: str = "auto",
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """SELECT it.id, it.image_id, i.site_id, s.name AS site_name, t.label, t.tag_type,
                  it.score, it.status, it.created_at, i.storage_path, i.author, i.licence,
                  i.licence_url, i.source_url, it.model_name, it.model_version, it.prompt_version
           FROM image_tags it
           JOIN tags t ON t.id=it.tag_id
           JOIN images i ON i.id=it.image_id
           JOIN sites s ON s.id=i.site_id
           WHERE it.status=%s
           ORDER BY it.score ASC NULLS LAST, it.id
           LIMIT %s OFFSET %s""",
        (status, limit, offset),
    ).fetchall()
    root = upload_dir()
    for row in rows:
        row["url"] = public_url(row.pop("storage_path"), root)
    return list(rows)


def get_image_tag(
    conn: psycopg.Connection[dict[str, Any]], image_tag_id: int
) -> dict[str, Any] | None:
    return conn.execute(
        "SELECT id, image_id, tag_id, status FROM image_tags WHERE id=%s", (image_tag_id,)
    ).fetchone()


def apply_review(
    conn: psycopg.Connection[dict[str, Any]],
    image_tag_id: int,
    action: str,
    reviewer: str,
    reviewer_id: int | None,
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, status FROM image_tags WHERE id=%s FOR UPDATE", (image_tag_id,)
    ).fetchone()
    if not row:
        return None
    previous = str(row["status"])
    new_status = "verified" if action == "confirm" else "rejected"
    conn.execute("UPDATE image_tags SET status=%s WHERE id=%s", (new_status, image_tag_id))
    conn.execute(
        """INSERT INTO tag_reviews
               (image_tag_id, reviewer, reviewer_id, action, previous_status, new_status)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (image_tag_id, reviewer, reviewer_id, action, previous, new_status),
    )
    return {
        "id": image_tag_id,
        "status": new_status,
        "previous_status": previous,
        "new_status": new_status,
    }


def add_human_tag(
    conn: psycopg.Connection[dict[str, Any]],
    image_id: int,
    label: str,
    tag_type: str,
    reviewer: str,
    reviewer_id: int | None,
) -> dict[str, Any] | None:
    image = conn.execute("SELECT id FROM images WHERE id=%s", (image_id,)).fetchone()
    if not image:
        return None
    tag = conn.execute(
        """INSERT INTO tags (label, tag_type) VALUES (%s, %s)
           ON CONFLICT (label) DO UPDATE SET label=EXCLUDED.label
           RETURNING id, tag_type""",
        (label.strip().lower(), tag_type),
    ).fetchone()
    assert tag is not None
    existing = conn.execute(
        "SELECT id, status FROM image_tags WHERE image_id=%s AND tag_id=%s FOR UPDATE",
        (image_id, tag["id"]),
    ).fetchone()
    if existing and existing["status"] == "added_by_human":
        return {
            "id": existing["id"],
            "status": "added_by_human",
            "previous_status": "added_by_human",
            "new_status": "added_by_human",
        }
    if existing:
        image_tag_id = int(existing["id"])
        previous = str(existing["status"])
        conn.execute(
            "UPDATE image_tags SET status='added_by_human', score=NULL WHERE id=%s",
            (image_tag_id,),
        )
    else:
        image_tag_id = int(
            conn.execute(
                """INSERT INTO image_tags (image_id, tag_id, score, status)
                   VALUES (%s, %s, NULL, 'added_by_human') RETURNING id""",
                (image_id, tag["id"]),
            ).fetchone()["id"]  # type: ignore[index]
        )
        previous = None
    conn.execute(
        """INSERT INTO tag_reviews
               (image_tag_id, reviewer, reviewer_id, action, previous_status, new_status)
           VALUES (%s, %s, %s, 'add', %s, 'added_by_human')""",
        (image_tag_id, reviewer, reviewer_id, previous),
    )
    return {
        "id": image_tag_id,
        "status": "added_by_human",
        "previous_status": previous,
        "new_status": "added_by_human",
    }


def history(conn: psycopg.Connection[dict[str, Any]], image_tag_id: int) -> list[dict[str, Any]]:
    return list(
        conn.execute(
            """SELECT id, image_tag_id, reviewer, reviewer_id, action, previous_status,
                      new_status, created_at
               FROM tag_reviews WHERE image_tag_id=%s ORDER BY created_at, id""",
            (image_tag_id,),
        ).fetchall()
    )
