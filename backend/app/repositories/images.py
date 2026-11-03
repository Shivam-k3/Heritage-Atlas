"""Image and job queries."""

from typing import Any

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from ..config import upload_dir
from ..services.images import SavedImage, public_url

IMAGE_COLUMNS = """id, site_id, storage_path, original_filename, author, licence, licence_url,
                   source_url, sha256, width, height, mime_type, file_size, status, created_at"""

JOB_COLUMNS = "id, image_id, job_type, status, error, retry_count, created_at, updated_at"


def find_by_sha256(conn: psycopg.Connection[dict[str, Any]], sha256: str) -> dict[str, Any] | None:
    query = sql.SQL("SELECT {} FROM images WHERE sha256=%s").format(sql.SQL(IMAGE_COLUMNS))
    return conn.execute(query, (sha256,)).fetchone()


def create_image(
    conn: psycopg.Connection[dict[str, Any]],
    site_id: int,
    saved: SavedImage,
    author: str | None,
    licence: str | None,
    licence_url: str | None,
    source_url: str | None,
) -> dict[str, Any]:
    row = conn.execute(
        """INSERT INTO images (site_id, storage_path, original_filename, author, licence,
                               licence_url, source_url, sha256, width, height, mime_type, file_size,
                               captured_at, exif)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           RETURNING id, site_id, status, sha256""",
        (
            site_id,
            str(saved.path),
            saved.original_filename,
            author,
            licence,
            licence_url,
            source_url,
            saved.sha256,
            saved.width,
            saved.height,
            saved.mime_type,
            saved.file_size,
            saved.captured_at,
            Jsonb(saved.exif),
        ),
    ).fetchone()
    assert row is not None
    return row


def find_site_id(conn: psycopg.Connection[dict[str, Any]], image_id: int) -> int | None:
    row = conn.execute("SELECT site_id FROM images WHERE id=%s", (image_id,)).fetchone()
    return int(row["site_id"]) if row else None


def get_image(conn: psycopg.Connection[dict[str, Any]], image_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """SELECT i.id, i.site_id, s.name AS site_name, i.storage_path, i.original_filename,
                  i.author, i.licence, i.licence_url, i.source_url, i.sha256, i.width, i.height,
                  i.mime_type, i.file_size, i.status, i.captured_at, i.created_at
           FROM images i JOIN sites s ON s.id=i.site_id WHERE i.id=%s""",
        (image_id,),
    ).fetchone()
    if not row:
        return None
    row["url"] = public_url(row.pop("storage_path"), upload_dir())
    row["tags"] = list_tags(conn, image_id)
    return row


TAG_COLUMNS = """it.id, t.label, t.tag_type, it.score, it.status,
                  it.model_name, it.model_version, it.prompt_version"""


def list_tags(conn: psycopg.Connection[dict[str, Any]], image_id: int) -> list[dict[str, Any]]:
    query = sql.SQL(
        """SELECT {}
           FROM image_tags it JOIN tags t ON t.id=it.tag_id
           WHERE it.image_id=%s ORDER BY it.score DESC NULLS LAST, it.id"""
    ).format(sql.SQL(TAG_COLUMNS))
    return list(conn.execute(query, (image_id,)).fetchall())


def tags_for_images(
    conn: psycopg.Connection[dict[str, Any]], image_ids: list[int]
) -> dict[int, list[dict[str, Any]]]:
    """Active tags per image (rejected tags are not returned). One query for a result page."""
    if not image_ids:
        return {}
    query = sql.SQL(
        """SELECT it.image_id, {}
           FROM image_tags it JOIN tags t ON t.id=it.tag_id
           WHERE it.image_id = ANY(%s) AND it.status <> 'rejected'
           ORDER BY it.score DESC NULLS LAST, it.id"""
    ).format(sql.SQL(TAG_COLUMNS))
    rows = conn.execute(query, (image_ids,)).fetchall()
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        image_id = int(row.pop("image_id"))
        grouped.setdefault(image_id, []).append(row)
    return grouped


def create_job(
    conn: psycopg.Connection[dict[str, Any]], image_id: int, job_type: str = "process_image"
) -> dict[str, Any]:
    existing = conn.execute(
        """SELECT id, image_id, job_type, status, error, retry_count, created_at, updated_at
           FROM jobs WHERE image_id=%s AND status IN ('pending', 'running')
           ORDER BY id DESC LIMIT 1""",
        (image_id,),
    ).fetchone()
    if existing:
        return existing
    row = conn.execute(
        """INSERT INTO jobs (image_id, job_type) VALUES (%s, %s) RETURNING id""",
        (image_id, job_type),
    ).fetchone()
    assert row is not None
    created = get_job(conn, int(row["id"]))
    assert created is not None
    return created


def get_job(conn: psycopg.Connection[dict[str, Any]], job_id: int) -> dict[str, Any] | None:
    query = sql.SQL("SELECT {} FROM jobs WHERE id=%s").format(sql.SQL(JOB_COLUMNS))
    return conn.execute(query, (job_id,)).fetchone()


def prepare_reprocess(conn: psycopg.Connection[dict[str, Any]], image_id: int) -> None:
    conn.execute("UPDATE images SET status='uploaded', updated_at=now() WHERE id=%s", (image_id,))
