"""Explorer Trails persistence."""

from datetime import date
from typing import Any

import psycopg
from psycopg import sql

TRAIL_COLUMNS = "id, title, description, created_by, is_public, created_at"

TRAIL_UPDATABLE = {"title": "title", "description": "description", "is_public": "is_public"}

STOP_SELECT = """SELECT ts.id, ts.site_id, s.name AS site_name, s.region, s.category,
                        s.lat, s.lon, ts.stop_order, ts.visit_date, ts.note
                 FROM trail_stops ts JOIN sites s ON s.id=ts.site_id"""


def create_trail(conn: psycopg.Connection[dict[str, Any]], data: dict[str, Any]) -> dict[str, Any]:
    row = conn.execute(
        """INSERT INTO trails (title, description, created_by, is_public)
           VALUES (%s, %s, %s, %s)
           RETURNING id, title, description, created_by, is_public, created_at""",
        (
            data["title"],
            data.get("description"),
            data.get("created_by"),
            data.get("is_public", False),
        ),
    ).fetchone()
    assert row is not None
    row["stops"] = []
    return row


def list_trails(
    conn: psycopg.Connection[dict[str, Any]],
    created_by: str | None = None,
    is_public: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    params: list[Any] = []
    if created_by:
        conditions.append("created_by=%s")
        params.append(created_by)
    if is_public is not None:
        conditions.append("is_public=%s")
        params.append(is_public)
    where = sql.SQL(" WHERE " + " AND ".join(conditions)) if conditions else sql.SQL("")
    params.extend([limit, offset])
    query = sql.SQL("SELECT {cols} FROM trails{where} ORDER BY id DESC LIMIT %s OFFSET %s").format(
        cols=sql.SQL(TRAIL_COLUMNS), where=where
    )
    return list(conn.execute(query, params).fetchall())


def get_trail(conn: psycopg.Connection[dict[str, Any]], trail_id: int) -> dict[str, Any] | None:
    trail = conn.execute(
        """SELECT id, title, description, created_by, is_public, created_at
           FROM trails WHERE id=%s""",
        (trail_id,),
    ).fetchone()
    if not trail:
        return None
    trail["stops"] = stops(conn, trail_id)
    return trail


def update_trail(
    conn: psycopg.Connection[dict[str, Any]], trail_id: int, data: dict[str, Any]
) -> dict[str, Any] | None:
    fields = [
        (TRAIL_UPDATABLE[key], value) for key, value in data.items() if key in TRAIL_UPDATABLE
    ]
    if not fields:
        return get_trail(conn, trail_id)
    assignments = sql.SQL(", ").join(
        sql.SQL("{} = %s").format(sql.Identifier(column)) for column, _ in fields
    )
    row = conn.execute(
        sql.SQL("UPDATE trails SET {} WHERE id=%s RETURNING id").format(assignments),
        [value for _, value in fields] + [trail_id],
    ).fetchone()
    if not row:
        return None
    return get_trail(conn, trail_id)


def stops(conn: psycopg.Connection[dict[str, Any]], trail_id: int) -> list[dict[str, Any]]:
    return list(
        conn.execute(
            STOP_SELECT + " WHERE ts.trail_id=%s ORDER BY ts.stop_order, ts.id",
            (trail_id,),
        ).fetchall()
    )


def get_stop(conn: psycopg.Connection[dict[str, Any]], stop_id: int) -> dict[str, Any] | None:
    return conn.execute(STOP_SELECT + " WHERE ts.id=%s", (stop_id,)).fetchone()


def add_stop(
    conn: psycopg.Connection[dict[str, Any]],
    trail_id: int,
    site_id: int,
    visit_date: date | None,
    note: str | None,
) -> dict[str, Any] | None:
    if not conn.execute("SELECT id FROM trails WHERE id=%s", (trail_id,)).fetchone():
        return None
    if not conn.execute("SELECT id FROM sites WHERE id=%s", (site_id,)).fetchone():
        return None
    order = conn.execute(
        "SELECT COALESCE(MAX(stop_order), 0) + 1 AS next FROM trail_stops WHERE trail_id=%s",
        (trail_id,),
    ).fetchone()
    assert order is not None
    row = conn.execute(
        """INSERT INTO trail_stops (trail_id, site_id, stop_order, visit_date, note)
           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        (trail_id, site_id, order["next"], visit_date, note),
    ).fetchone()
    assert row is not None
    return get_stop(conn, int(row["id"]))


def reorder(
    conn: psycopg.Connection[dict[str, Any]], trail_id: int, stop_ids: list[int]
) -> list[dict[str, Any]]:
    existing = {
        int(row["id"])
        for row in conn.execute(
            "SELECT id FROM trail_stops WHERE trail_id=%s", (trail_id,)
        ).fetchall()
    }
    if len(stop_ids) != len(set(stop_ids)):
        raise ValueError("stop_ids contains duplicates")
    if set(stop_ids) != existing:
        raise ValueError("stop_ids must be a permutation of this trail's stops")
    for order, stop_id in enumerate(stop_ids, start=1):
        conn.execute(
            "UPDATE trail_stops SET stop_order=%s WHERE id=%s AND trail_id=%s",
            (order, stop_id, trail_id),
        )
    return stops(conn, trail_id)


def remove_stop(conn: psycopg.Connection[dict[str, Any]], trail_id: int, stop_id: int) -> bool:
    deleted = conn.execute(
        "DELETE FROM trail_stops WHERE id=%s AND trail_id=%s RETURNING id",
        (stop_id, trail_id),
    ).fetchone()
    if not deleted:
        return False
    remaining = conn.execute(
        "SELECT id FROM trail_stops WHERE trail_id=%s ORDER BY stop_order, id",
        (trail_id,),
    ).fetchall()
    for order, row in enumerate(remaining, start=1):
        conn.execute(
            "UPDATE trail_stops SET stop_order=%s WHERE id=%s",
            (order, int(row["id"])),
        )
    return True


def images_with_visit_data(
    conn: psycopg.Connection[dict[str, Any]], image_ids: list[int] | None = None
) -> list[dict[str, Any]]:
    """Images ordered by capture time, flagged usable when a stop coordinate is known."""
    condition = sql.SQL("")
    params: list[Any] = []
    if image_ids is not None:
        condition = sql.SQL(" AND i.id = ANY(%s)")
        params.append(image_ids)
    query = sql.SQL(
        """SELECT i.id, i.site_id, i.captured_at,
                  (i.captured_at IS NOT NULL AND s.lat IS NOT NULL AND s.lon IS NOT NULL)
                  AS usable
           FROM images i JOIN sites s ON s.id=i.site_id
           WHERE true{} ORDER BY i.captured_at NULLS LAST, i.id"""
    ).format(condition)
    return list(conn.execute(query, params).fetchall())


def photo_counts(conn: psycopg.Connection[dict[str, Any]], trail_id: int) -> dict[int, int]:
    rows = conn.execute(
        """SELECT ts.site_id, count(i.id) AS photos
           FROM trail_stops ts LEFT JOIN images i ON i.site_id=ts.site_id
           WHERE ts.trail_id=%s GROUP BY ts.site_id""",
        (trail_id,),
    ).fetchall()
    return {int(row["site_id"]): int(row["photos"]) for row in rows}


def total_photos(conn: psycopg.Connection[dict[str, Any]], trail_id: int) -> int:
    row = conn.execute(
        """SELECT count(DISTINCT i.id) AS photos
           FROM images i WHERE i.site_id IN (SELECT site_id FROM trail_stops WHERE trail_id=%s)""",
        (trail_id,),
    ).fetchone()
    return int(row["photos"]) if row else 0


def verified_features_by_site(
    conn: psycopg.Connection[dict[str, Any]], trail_id: int
) -> dict[int, list[str]]:
    rows = conn.execute(
        """SELECT ts.site_id, t.label, count(*) AS count
           FROM trail_stops ts
           JOIN images i ON i.site_id=ts.site_id
           JOIN image_tags it ON it.image_id=i.id
           JOIN tags t ON t.id=it.tag_id
           WHERE ts.trail_id=%s AND it.status IN ('verified', 'added_by_human')
           GROUP BY ts.site_id, t.label
           ORDER BY ts.site_id, count DESC, t.label""",
        (trail_id,),
    ).fetchall()
    grouped: dict[int, list[str]] = {}
    for row in rows:
        grouped.setdefault(int(row["site_id"]), []).append(str(row["label"]))
    return grouped


def verified_feature_counts(
    conn: psycopg.Connection[dict[str, Any]], trail_id: int
) -> dict[str, int]:
    rows = conn.execute(
        """SELECT t.label, count(*) AS count
           FROM trail_stops ts
           JOIN images i ON i.site_id=ts.site_id
           JOIN image_tags it ON it.image_id=i.id
           JOIN tags t ON t.id=it.tag_id
           WHERE ts.trail_id=%s AND it.status IN ('verified', 'added_by_human')
           GROUP BY t.label""",
        (trail_id,),
    ).fetchall()
    return {str(row["label"]): int(row["count"]) for row in rows}
