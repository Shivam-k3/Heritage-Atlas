"""Vector search queries. CLIP and MiniLM embeddings are never mixed in one ranking."""

from typing import Any

import psycopg
from psycopg import sql


def _filters(
    region: str | None,
    category: str | None,
    tag: str | None,
    verified_only: bool,
    site_id: int | None,
    site_alias: str,
    image_alias: str | None,
) -> tuple[list[sql.Composable], list[Any]]:
    site = sql.Identifier(site_alias)
    conditions: list[sql.Composable] = []
    params: list[Any] = []
    if region:
        conditions.append(sql.SQL("{} = %s").format(sql.Identifier(site_alias, "region")))
        params.append(region)
    if category:
        conditions.append(sql.SQL("{} = %s").format(sql.Identifier(site_alias, "category")))
        params.append(category)
    if site_id is not None:
        conditions.append(sql.SQL("{}.id = %s").format(site))
        params.append(site_id)
    if image_alias:
        image = sql.Identifier(image_alias)
        if tag:
            conditions.append(
                sql.SQL(
                    """EXISTS (SELECT 1 FROM image_tags it JOIN tags t ON t.id=it.tag_id
                               WHERE it.image_id={}.id AND t.label=%s
                                 AND it.status <> 'rejected')"""
                ).format(image)
            )
            params.append(tag)
        if verified_only:
            conditions.append(
                sql.SQL(
                    """EXISTS (SELECT 1 FROM image_tags it WHERE it.image_id={}.id
                               AND it.status IN ('verified', 'added_by_human'))"""
                ).format(image)
            )
    else:
        if tag:
            conditions.append(
                sql.SQL(
                    """EXISTS (SELECT 1 FROM images i2 JOIN image_tags it ON it.image_id=i2.id
                               JOIN tags t ON t.id=it.tag_id
                               WHERE i2.site_id=s.id AND t.label=%s AND it.status <> 'rejected')"""
                )
            )
            params.append(tag)
        if verified_only:
            conditions.append(
                sql.SQL(
                    """EXISTS (SELECT 1 FROM images i2 JOIN image_tags it ON it.image_id=i2.id
                               WHERE i2.site_id=s.id AND it.status IN ('verified', 'added_by_human'))"""
                )
            )
    return conditions, params


def search_images(
    conn: psycopg.Connection[dict[str, Any]],
    embedding: Any,
    region: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    verified_only: bool = False,
    site_id: int | None = None,
    exclude_image_id: int | None = None,
    exclude_site_id: int | None = None,
    limit: int = 10,
    offset: int = 0,
) -> list[dict[str, Any]]:
    conditions, params = _filters(region, category, tag, verified_only, site_id, "s", "i")
    conditions.insert(0, sql.SQL("i.clip_embedding IS NOT NULL"))
    if exclude_image_id is not None:
        conditions.append(sql.SQL("i.id <> %s"))
        params.append(exclude_image_id)
    if exclude_site_id is not None:
        conditions.append(sql.SQL("i.site_id <> %s"))
        params.append(exclude_site_id)
    where = sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conditions)
    query = sql.SQL(
        """SELECT i.id AS image_id, i.site_id, s.name, s.region, s.category, i.storage_path,
                  i.author, i.licence, i.licence_url, i.source_url,
                  1 - (i.clip_embedding <=> %s) AS score
           FROM images i JOIN sites s ON s.id=i.site_id{}
           ORDER BY i.clip_embedding <=> %s LIMIT %s OFFSET %s"""
    ).format(where)
    rows = conn.execute(query, [embedding, *params, embedding, limit, offset]).fetchall()
    return list(rows)


def search_sites(
    conn: psycopg.Connection[dict[str, Any]],
    embedding: Any,
    region: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    verified_only: bool = False,
    site_id: int | None = None,
    limit: int = 10,
    offset: int = 0,
) -> list[dict[str, Any]]:
    conditions, params = _filters(region, category, tag, verified_only, site_id, "s", None)
    conditions.insert(0, sql.SQL("s.description_embedding IS NOT NULL"))
    where = sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conditions)
    query = sql.SQL(
        """SELECT s.id, s.name, s.region, s.category, s.description,
                  1 - (s.description_embedding <=> %s) AS score
           FROM sites s{}
           ORDER BY s.description_embedding <=> %s LIMIT %s OFFSET %s"""
    ).format(where)
    rows = conn.execute(query, [embedding, *params, embedding, limit, offset]).fetchall()
    return list(rows)
