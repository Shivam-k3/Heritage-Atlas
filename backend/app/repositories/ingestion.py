"""Bulk ingestion batch records and draft location clusters."""

from typing import Any

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

BATCH_COLUMNS = """id, source_path, status, total_files, accepted, duplicates, rejected,
                   gps_images, clusters, report, created_at, updated_at"""

DRAFT_COLUMNS = """s.id, s.name, s.region, s.district, s.category, s.lat, s.lon,
                   s.status, s.merged_into_site_id, s.source,
                   count(i.id) AS images,
                   coalesce(array_agg(i.id ORDER BY i.id) FILTER (WHERE i.id IS NOT NULL),
                            '{}') AS image_ids"""


def create_batch(conn: psycopg.Connection[dict[str, Any]], source_path: str) -> dict[str, Any]:
    row = conn.execute(
        sql.SQL("INSERT INTO ingest_batches (source_path) VALUES (%s) RETURNING {}").format(
            sql.SQL(BATCH_COLUMNS)
        ),
        (source_path,),
    ).fetchone()
    assert row is not None
    return row


def get_batch(conn: psycopg.Connection[dict[str, Any]], batch_id: int) -> dict[str, Any] | None:
    query = sql.SQL("SELECT {} FROM ingest_batches WHERE id=%s").format(sql.SQL(BATCH_COLUMNS))
    return conn.execute(query, (batch_id,)).fetchone()


def list_batches(
    conn: psycopg.Connection[dict[str, Any]], limit: int = 50, offset: int = 0
) -> list[dict[str, Any]]:
    query = sql.SQL("SELECT {} FROM ingest_batches ORDER BY id DESC LIMIT %s OFFSET %s").format(
        sql.SQL(BATCH_COLUMNS)
    )
    return list(conn.execute(query, (limit, offset)).fetchall())


def update_progress(
    conn: psycopg.Connection[dict[str, Any]],
    batch_id: int,
    *,
    total_files: int,
    accepted: int,
    duplicates: int,
    rejected: int,
    gps_images: int,
    clusters: int,
) -> None:
    conn.execute(
        """UPDATE ingest_batches SET total_files=%s, accepted=%s, duplicates=%s, rejected=%s,
                                    gps_images=%s, clusters=%s, updated_at=now()
           WHERE id=%s""",
        (total_files, accepted, duplicates, rejected, gps_images, clusters, batch_id),
    )


def finish_batch(
    conn: psycopg.Connection[dict[str, Any]],
    batch_id: int,
    *,
    status: str,
    report: dict[str, Any],
) -> dict[str, Any]:
    row = conn.execute(
        sql.SQL(
            """UPDATE ingest_batches SET status=%s, report=%s, updated_at=now()
               WHERE id=%s RETURNING {}"""
        ).format(sql.SQL(BATCH_COLUMNS)),
        (status, Jsonb(report), batch_id),
    ).fetchone()
    assert row is not None
    return row


def draft_sites(
    conn: psycopg.Connection[dict[str, Any]], limit: int = 200, offset: int = 0
) -> list[dict[str, Any]]:
    query = sql.SQL(
        """SELECT {}
           FROM sites s LEFT JOIN images i ON i.site_id = s.id
           WHERE s.status = 'draft'
           GROUP BY s.id
           ORDER BY s.id
           LIMIT %s OFFSET %s"""
    ).format(sql.SQL(DRAFT_COLUMNS))
    return list(conn.execute(query, (limit, offset)).fetchall())
