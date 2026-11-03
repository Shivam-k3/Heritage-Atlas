"""Text-to-text, text-to-image and image-to-image search."""

import hashlib
import io
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from .. import config, ml
from ..db import connect
from ..repositories import images as images_repo
from ..repositories import search as search_repo
from ..schemas import SearchImageOut, SearchSiteOut
from ..services.images import public_url

router = APIRouter(prefix="/search", tags=["search"])


def _query(q: str) -> str:
    value = q.strip()
    if not value:
        raise HTTPException(status_code=400, detail="query must not be empty")
    return value


def _prepare(rows: list[dict], conn) -> list[dict]:
    """Attach the public URL and active tags to each hit; never expose storage paths."""
    root = config.upload_dir()
    tags = images_repo.tags_for_images(conn, [int(row["image_id"]) for row in rows])
    for row in rows:
        row["url"] = public_url(row.pop("storage_path"), root)
        row["tags"] = tags.get(int(row["image_id"]), [])
    return rows


def _diversify(rows: list[dict], max_per_site: int | None, limit: int) -> list[dict]:
    if not max_per_site:
        return rows[:limit]
    seen: dict[int, int] = {}
    kept: list[dict] = []
    for row in rows:
        site_id = int(row["site_id"])
        if seen.get(site_id, 0) >= max_per_site:
            continue
        seen[site_id] = seen.get(site_id, 0) + 1
        kept.append(row)
        if len(kept) >= limit:
            break
    return kept


@router.get("/text", response_model=list[SearchSiteOut])
def search_text(
    q: Annotated[str, Query(min_length=1, max_length=500)],
    region: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    verified_only: bool = False,
    site_id: int | None = None,
    k: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    embedding = ml.embed_text(_query(q))
    with connect() as conn:
        return search_repo.search_sites(
            conn,
            embedding,
            region=region,
            category=category,
            tag=tag,
            verified_only=verified_only,
            site_id=site_id,
            limit=k,
            offset=offset,
        )


@router.get("/images", response_model=list[SearchImageOut])
def search_images(
    q: Annotated[str, Query(min_length=1, max_length=500)],
    region: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    verified_only: bool = False,
    site_id: int | None = None,
    k: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    embedding = ml.embed_clip_text(_query(q))
    with connect() as conn:
        rows = search_repo.search_images(
            conn,
            embedding,
            region=region,
            category=category,
            tag=tag,
            verified_only=verified_only,
            site_id=site_id,
            limit=k,
            offset=offset,
        )
        return _prepare(rows, conn)


@router.post("/by-image", response_model=list[SearchImageOut])
def search_by_image(
    file: Annotated[UploadFile, File()],
    region: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    verified_only: bool = False,
    site_id: int | None = None,
    cross_site: bool = False,
    exclude_image_id: int | None = None,
    max_per_site: Annotated[int | None, Query(ge=1, le=100)] = None,
    k: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    """CLIP image-to-image. The query image is always excluded when it can be identified.

    `cross_site=true` also excludes every image from the query image's site. If the upload
    matches no stored SHA-256 and no `exclude_image_id` is given, only content duplicates
    are impossible to identify, so nothing extra is excluded. `max_per_site` caps how many
    hits one other site may take on the returned page (best effort, applied after `offset`).
    """
    max_bytes = config.max_upload_bytes()
    payload = file.file.read(max_bytes + 1)
    if not payload:
        raise HTTPException(status_code=400, detail="file is empty")
    if len(payload) > max_bytes:
        raise HTTPException(status_code=413, detail="upload exceeds the size limit")
    try:
        embedding = ml.embed_image(io.BytesIO(payload))
    except ml.InvalidImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    sha256 = hashlib.sha256(payload).hexdigest()
    with connect() as conn:
        match = images_repo.find_by_sha256(conn, sha256)
        query_image_id = int(match["id"]) if match else exclude_image_id
        query_site_id = int(match["site_id"]) if match else None
        if query_site_id is None and query_image_id is not None:
            query_site_id = images_repo.find_site_id(conn, query_image_id)

        fetch = k * 5 if max_per_site else k
        rows = search_repo.search_images(
            conn,
            embedding,
            region=region,
            category=category,
            tag=tag,
            verified_only=verified_only,
            site_id=site_id,
            exclude_image_id=query_image_id,
            exclude_site_id=query_site_id if cross_site else None,
            limit=fetch,
            offset=offset,
        )
        return _prepare(_diversify(rows, max_per_site, k), conn)
