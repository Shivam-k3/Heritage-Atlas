"""Human verification queue and append-only audit history."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from .. import config
from ..db import connect
from ..repositories import review as review_repo
from ..schemas import (
    HumanTagCreate,
    ReviewAction,
    ReviewHistoryOut,
    ReviewQueueOut,
    ReviewResult,
)

router = APIRouter(prefix="/review", tags=["review"])


def _reviewer(name: str) -> str:
    """Fixed demo reviewer list. This is an audit label, not authentication."""
    allowed = config.reviewers()
    match = next((value for value in allowed if value == name.strip().lower()), None)
    if match is None:
        raise HTTPException(
            status_code=400,
            detail=f"unknown reviewer; allowed: {', '.join(allowed)}",
        )
    return match


@router.get("/reviewers", response_model=list[str])
def list_reviewers() -> list[str]:
    return config.reviewers()


@router.get("/queue", response_model=list[ReviewQueueOut])
def review_queue(
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: str = "auto",
) -> list[dict]:
    if status not in {"auto", "verified", "rejected", "added_by_human"}:
        raise HTTPException(status_code=400, detail="invalid status")
    with connect() as conn:
        return review_repo.queue(conn, limit=limit, offset=offset, status=status)


@router.post("/tags/add", response_model=ReviewResult)
def add_human_tag(body: HumanTagCreate) -> dict:
    with connect() as conn:
        result = review_repo.add_human_tag(
            conn,
            body.image_id,
            body.label,
            body.tag_type,
            _reviewer(body.reviewer),
            body.reviewer_id,
        )
    if not result:
        raise HTTPException(status_code=404, detail="image not found")
    return result


@router.post("/tags/{image_tag_id}", response_model=ReviewResult)
def review_tag(image_tag_id: int, body: ReviewAction) -> dict:
    with connect() as conn:
        result = review_repo.apply_review(
            conn, image_tag_id, body.action, _reviewer(body.reviewer), body.reviewer_id
        )
    if not result:
        raise HTTPException(status_code=404, detail="tag not found")
    return result


@router.get("/history/{image_tag_id}", response_model=list[ReviewHistoryOut])
def review_history(image_tag_id: int) -> list[dict]:
    with connect() as conn:
        if not review_repo.get_image_tag(conn, image_tag_id):
            raise HTTPException(status_code=404, detail="tag not found")
        return review_repo.history(conn, image_tag_id)
