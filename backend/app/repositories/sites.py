"""Site queries. All values are parameterised; dynamic columns come from a whitelist."""

from typing import Any

import psycopg
from psycopg import sql

from ..config import upload_dir
from ..services.images import public_url

SITE_COLUMNS = "id, name, region, district, category, lat, lon, status, merged_into_site_id"
DETAIL_COLUMNS = SITE_COLUMNS + ", description, description_source, created_at"

UPDATABLE = {
    "name": "name",
    "region": "region",
    "district": "district",
    "category": "category",
    "lat": "lat",
    "lon": "lon",
    "description": "description",
    "description_source": "description_source",
}


def list_sites(
    conn: psycopg.Connection[dict[str, Any]],
    region: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    verified_only: bool = False,
    status: str | None = "canonical",
    limit: int = 200,
    offset: int = 0,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    params: list[Any] = []
    if status:
        conditions.append("s.status = %s")
        params.append(status)
    if region:
        conditions.append("s.region = %s")
        params.append(region)
    if category:
        conditions.append("s.category = %s")
        params.append(category)
    if tag:
        conditions.append(
            """EXISTS (SELECT 1 FROM images i
                       JOIN image_tags it ON it.image_id = i.id
                       JOIN tags t ON t.id = it.tag_id
                       WHERE i.site_id = s.id AND t.label = %s AND it.status <> 'rejected')"""
        )
        params.append(tag)
    if verified_only:
        conditions.append(
            """EXISTS (SELECT 1 FROM images i
                       JOIN image_tags it ON it.image_id = i.id
                       WHERE i.site_id = s.id AND it.status IN ('verified', 'added_by_human'))"""
        )
    where = sql.SQL(" WHERE " + " AND ".join(conditions)) if conditions else sql.SQL("")
    params.extend([limit, offset])
    query = sql.SQL("SELECT {} FROM sites s{} ORDER BY s.id LIMIT %s OFFSET %s").format(
        sql.SQL(SITE_COLUMNS), where
    )
    return list(conn.execute(query, params).fetchall())


def get_site(conn: psycopg.Connection[dict[str, Any]], site_id: int) -> dict[str, Any] | None:
    query = sql.SQL("SELECT {} FROM sites WHERE id=%s").format(sql.SQL(DETAIL_COLUMNS))
    site = conn.execute(query, (site_id,)).fetchone()
    if not site:
        return None
    images = conn.execute(
        """SELECT id, site_id, storage_path, original_filename, author, licence, licence_url,
                  source_url, width, height, mime_type, file_size, status, created_at
           FROM images WHERE site_id=%s ORDER BY id""",
        (site_id,),
    ).fetchall()
    tags = conn.execute(
        """SELECT it.image_id, it.id, t.label, t.tag_type, it.score, it.status
           FROM image_tags it JOIN tags t ON t.id=it.tag_id
           WHERE it.image_id IN (SELECT id FROM images WHERE site_id=%s)
           ORDER BY it.score DESC NULLS LAST, it.id""",
        (site_id,),
    ).fetchall()
    by_image: dict[int, list[dict[str, Any]]] = {}
    for tag in tags:
        by_image.setdefault(int(tag["image_id"]), []).append(
            {
                "id": tag["id"],
                "label": tag["label"],
                "tag_type": tag["tag_type"],
                "score": tag["score"],
                "status": tag["status"],
            }
        )
    root = upload_dir()
    for image in images:
        image["url"] = public_url(image.pop("storage_path"), root)
        image["tags"] = by_image.get(int(image["id"]), [])
    site["images"] = images
    return site


def create_site(conn: psycopg.Connection[dict[str, Any]], data: dict[str, Any]) -> dict[str, Any]:
    query = sql.SQL(
        """INSERT INTO sites (name, region, district, category, lat, lon, description,
                              description_source)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING {}"""
    ).format(sql.SQL(DETAIL_COLUMNS))
    row = conn.execute(
        query,
        (
            data["name"],
            data.get("region"),
            data.get("district"),
            data.get("category"),
            data.get("lat"),
            data.get("lon"),
            data.get("description"),
            data.get("description_source"),
        ),
    ).fetchone()
    assert row is not None
    return row


def update_site(
    conn: psycopg.Connection[dict[str, Any]], site_id: int, fields: dict[str, Any]
) -> dict[str, Any] | None:
    assignments: list[sql.Composable] = [
        sql.SQL("{} = %s").format(sql.Identifier(UPDATABLE[key]))
        for key in fields
        if key in UPDATABLE
    ]
    if not assignments:
        return get_site(conn, site_id)
    values = [fields[key] for key in fields if key in UPDATABLE]
    if "description" in fields:
        assignments.append(sql.SQL("description_embedding = NULL"))
    assignments.append(sql.SQL("updated_at = now()"))
    query = sql.SQL("UPDATE sites SET {} WHERE id = %s RETURNING {}").format(
        sql.SQL(", ").join(assignments), sql.SQL(DETAIL_COLUMNS)
    )
    row = conn.execute(query, (*values, site_id)).fetchone()
    return row


def find_by_name(
    conn: psycopg.Connection[dict[str, Any]], name: str, region: str | None = None
) -> dict[str, Any] | None:
    if region:
        query = sql.SQL(
            "SELECT {} FROM sites WHERE lower(name)=lower(%s) AND region=%s LIMIT 1"
        ).format(sql.SQL(DETAIL_COLUMNS))
        return conn.execute(query, (name, region)).fetchone()
    query = sql.SQL("SELECT {} FROM sites WHERE lower(name)=lower(%s) ORDER BY id LIMIT 1").format(
        sql.SQL(DETAIL_COLUMNS)
    )
    return conn.execute(query, (name,)).fetchone()


def set_status(
    conn: psycopg.Connection[dict[str, Any]], site_id: int, status: str
) -> dict[str, Any] | None:
    row = conn.execute(
        "UPDATE sites SET status=%s, updated_at=now() WHERE id=%s RETURNING id",
        (status, site_id),
    ).fetchone()
    return get_site(conn, site_id) if row else None


def merge_sites(
    conn: psycopg.Connection[dict[str, Any]], site_id: int, target_site_id: int
) -> dict[str, Any] | None:
    """Move a draft cluster's images into a canonical site; never delete either record."""
    if site_id == target_site_id:
        raise ValueError("cannot merge a site into itself")
    source = conn.execute(
        "SELECT id, status FROM sites WHERE id=%s FOR UPDATE", (site_id,)
    ).fetchone()
    target = conn.execute(
        "SELECT id FROM sites WHERE id=%s AND status='canonical' FOR UPDATE", (target_site_id,)
    ).fetchone()
    if not source or source["status"] != "draft" or not target:
        return None
    conn.execute(
        "UPDATE images SET site_id=%s, updated_at=now() WHERE site_id=%s", (target_site_id, site_id)
    )
    conn.execute(
        """UPDATE sites SET status='merged', merged_into_site_id=%s, updated_at=now()
           WHERE id=%s""",
        (target_site_id, site_id),
    )
    return get_site(conn, target_site_id)


def create_draft_site(
    conn: psycopg.Connection[dict[str, Any]],
    name: str,
    lat: float | None,
    lon: float | None,
    source: str,
    description: str | None = None,
) -> dict[str, Any]:
    row = conn.execute(
        """INSERT INTO sites (name, lat, lon, status, source, description)
           VALUES (%s, %s, %s, 'draft', %s, %s) RETURNING id""",
        (name, lat, lon, source, description),
    ).fetchone()
    assert row is not None
    site = get_site(conn, int(row["id"]))
    assert site is not None
    return site


def site_vectors(
    conn: psycopg.Connection[dict[str, Any]], site_id: int | None = None
) -> list[dict[str, Any]]:
    if site_id is None:
        return list(
            conn.execute(
                "SELECT site_id, id, clip_embedding FROM images "
                "WHERE clip_embedding IS NOT NULL ORDER BY site_id, id"
            ).fetchall()
        )
    return list(
        conn.execute(
            "SELECT site_id, id, clip_embedding FROM images "
            "WHERE site_id=%s AND clip_embedding IS NOT NULL ORDER BY id",
            (site_id,),
        ).fetchall()
    )


def site_tag_sets(
    conn: psycopg.Connection[dict[str, Any]], site_id: int | None = None
) -> dict[int, set[str]]:
    """Per-site labels, preferring human-verified/added tags and falling back to auto."""
    if site_id is None:
        rows = conn.execute(
            """SELECT i.site_id, t.label, it.status
               FROM image_tags it
               JOIN tags t ON t.id = it.tag_id
               JOIN images i ON i.id = it.image_id
               WHERE it.status <> 'rejected'"""
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT i.site_id, t.label, it.status
               FROM image_tags it
               JOIN tags t ON t.id = it.tag_id
               JOIN images i ON i.id = it.image_id
               WHERE i.site_id=%s AND it.status <> 'rejected'""",
            (site_id,),
        ).fetchall()
    grouped: dict[int, dict[str, set[str]]] = {}
    for row in rows:
        statuses = grouped.setdefault(int(row["site_id"]), {"human": set(), "auto": set()})
        bucket = "human" if row["status"] in {"verified", "added_by_human"} else "auto"
        statuses[bucket].add(str(row["label"]))
    return {
        site: values["human"] if values["human"] else values["auto"]
        for site, values in grouped.items()
    }
