"""Site CRUD and explainable related-site recommendations."""

from typing import Annotated

import numpy as np
from fastapi import APIRouter, HTTPException, Query

from .. import config
from ..db import connect
from ..repositories import ingestion as ingestion_repo
from ..repositories import sites as sites_repo
from ..schemas import (
    DraftSiteOut,
    RelatedSiteOut,
    SiteCreate,
    SiteDetailOut,
    SiteMerge,
    SiteSummaryOut,
    SiteUpdate,
)
from ..services.ranking import rank_related

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("", response_model=list[SiteSummaryOut])
def list_sites(
    region: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    verified_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    with connect() as conn:
        return sites_repo.list_sites(
            conn,
            region=region,
            category=category,
            tag=tag,
            verified_only=verified_only,
            limit=limit,
            offset=offset,
        )


@router.post("", response_model=SiteDetailOut, status_code=201)
def create_site(body: SiteCreate) -> dict:
    with connect() as conn:
        return sites_repo.create_site(conn, body.model_dump())


@router.get("/drafts", response_model=list[DraftSiteOut])
def list_drafts(
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    """Unverified location clusters produced by folder ingestion."""
    with connect() as conn:
        return ingestion_repo.draft_sites(conn, limit=limit, offset=offset)


def _require_draft(conn, site_id: int) -> dict:
    site = sites_repo.get_site(conn, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="site not found")
    if site["status"] != "draft":
        raise HTTPException(status_code=400, detail="only draft sites can be reviewed")
    return site


@router.post("/{site_id}/confirm", response_model=SiteDetailOut)
def confirm_draft(site_id: int) -> dict:
    """Promote a draft cluster to a canonical site. The reviewer renames it with PATCH."""
    with connect() as conn:
        _require_draft(conn, site_id)
        site = sites_repo.set_status(conn, site_id, "canonical")
    assert site is not None
    return site


@router.post("/{site_id}/reject", response_model=SiteDetailOut)
def reject_draft(site_id: int) -> dict:
    """Mark a draft cluster as rejected. Images are kept for audit, never deleted."""
    with connect() as conn:
        _require_draft(conn, site_id)
        site = sites_repo.set_status(conn, site_id, "rejected")
    assert site is not None
    return site


@router.post("/{site_id}/merge", response_model=SiteDetailOut)
def merge_draft(site_id: int, body: SiteMerge) -> dict:
    """Move a draft cluster's images into an existing canonical site."""
    with connect() as conn:
        _require_draft(conn, site_id)
        try:
            target = sites_repo.merge_sites(conn, site_id, body.target_site_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not target:
        raise HTTPException(status_code=404, detail="target canonical site not found")
    return target


@router.get("/{site_id}", response_model=SiteDetailOut)
def get_site(site_id: int) -> dict:
    with connect() as conn:
        site = sites_repo.get_site(conn, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="site not found")
    return site


@router.patch("/{site_id}", response_model=SiteDetailOut)
def update_site(site_id: int, body: SiteUpdate) -> dict:
    fields = body.model_dump(exclude_unset=True)
    with connect() as conn:
        site = sites_repo.update_site(conn, site_id, fields)
    if not site:
        raise HTTPException(status_code=404, detail="site not found")
    return site


@router.get("/{site_id}/related", response_model=list[RelatedSiteOut])
def related_sites(
    site_id: int,
    k: Annotated[int, Query(ge=1, le=20)] = 5,
    alpha: Annotated[float | None, Query(ge=0, le=1)] = None,
) -> list[dict]:
    with connect() as conn:
        if not sites_repo.get_site(conn, site_id):
            raise HTTPException(status_code=404, detail="site not found")
        all_vectors = sites_repo.site_vectors(conn)
        tag_sets = sites_repo.site_tag_sets(conn)
        all_sites = sites_repo.list_sites(conn, limit=1000)

    images_by_site: dict[int, list[tuple[int, np.ndarray]]] = {}
    for row in all_vectors:
        images_by_site.setdefault(int(row["site_id"]), []).append(
            (int(row["id"]), row["clip_embedding"].to_numpy())
        )
    target_images = images_by_site.get(site_id, [])
    target_tags = tag_sets.get(site_id, set())
    candidates = [
        {
            "site_id": int(site["id"]),
            "name": site["name"],
            "images": images_by_site.get(int(site["id"]), []),
            "tags": tag_sets.get(int(site["id"]), set()),
        }
        for site in all_sites
    ]
    weight = config.related_clip_weight() if alpha is None else alpha
    return rank_related(site_id, target_images, target_tags, candidates, weight, k)
