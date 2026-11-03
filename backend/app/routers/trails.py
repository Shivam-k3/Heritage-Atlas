"""Explorer Trails: ordered stops, haversine distances and generated journals."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from ..db import connect
from ..repositories import trails as trails_repo
from ..schemas import (
    JournalOut,
    TrailCreate,
    TrailFromImages,
    TrailFromImagesOut,
    TrailOut,
    TrailReorder,
    TrailStopCreate,
    TrailStopOut,
    TrailSummaryOut,
    TrailUpdate,
)
from ..services.geo import missing_coordinate_sites, trail_legs
from ..services.journal import generated_summary, top_features
from ..services.trails import group_visits

router = APIRouter(prefix="/trails", tags=["trails"])


@router.post("", response_model=TrailOut, status_code=201)
def create_trail(body: TrailCreate) -> dict:
    with connect() as conn:
        return trails_repo.create_trail(conn, body.model_dump())


@router.post("/from-images", response_model=TrailFromImagesOut, status_code=201)
def trail_from_images(body: TrailFromImages) -> dict:
    """Build an ordered trail from images that have a capture time and site coordinates.

    Images missing either are skipped and counted, never guessed.
    """
    with connect() as conn:
        rows = trails_repo.images_with_visit_data(conn, body.image_ids)
        visits = group_visits(rows)
        if not visits:
            raise HTTPException(
                status_code=400,
                detail="no images with a capture time and site coordinates",
            )
        trail = trails_repo.create_trail(conn, body.model_dump(exclude={"image_ids"}))
        for visit in visits:
            trails_repo.add_stop(
                conn,
                int(trail["id"]),
                int(visit["site_id"]),
                visit["visit_date"],
                None,
            )
        created = trails_repo.get_trail(conn, int(trail["id"]))
    assert created is not None
    used = sum(1 for row in rows if row["usable"])
    return {"trail": created, "images_used": used, "images_skipped": len(rows) - used}


@router.get("", response_model=list[TrailOut])
def list_trails(
    created_by: str | None = None,
    is_public: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    with connect() as conn:
        return trails_repo.list_trails(
            conn, created_by=created_by, is_public=is_public, limit=limit, offset=offset
        )


@router.get("/{trail_id}", response_model=TrailOut)
def get_trail(trail_id: int) -> dict:
    with connect() as conn:
        trail = trails_repo.get_trail(conn, trail_id)
    if not trail:
        raise HTTPException(status_code=404, detail="trail not found")
    return trail


@router.patch("/{trail_id}", response_model=TrailOut)
def update_trail(trail_id: int, body: TrailUpdate) -> dict:
    with connect() as conn:
        trail = trails_repo.update_trail(conn, trail_id, body.model_dump(exclude_unset=True))
    if not trail:
        raise HTTPException(status_code=404, detail="trail not found")
    return trail


@router.post("/{trail_id}/stops", response_model=TrailStopOut, status_code=201)
def add_stop(trail_id: int, body: TrailStopCreate) -> dict:
    with connect() as conn:
        if not trails_repo.get_trail(conn, trail_id):
            raise HTTPException(status_code=404, detail="trail not found")
        stop = trails_repo.add_stop(conn, trail_id, body.site_id, body.visit_date, body.note)
    if not stop:
        raise HTTPException(status_code=404, detail="site not found")
    return stop


@router.patch("/{trail_id}/stops/reorder", response_model=list[TrailStopOut])
def reorder_stops(trail_id: int, body: TrailReorder) -> list[dict]:
    with connect() as conn:
        if not trails_repo.get_trail(conn, trail_id):
            raise HTTPException(status_code=404, detail="trail not found")
        try:
            return trails_repo.reorder(conn, trail_id, body.stop_ids)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{trail_id}/stops/{stop_id}", response_model=list[TrailStopOut])
def remove_stop(trail_id: int, stop_id: int) -> list[dict]:
    with connect() as conn:
        if not trails_repo.get_trail(conn, trail_id):
            raise HTTPException(status_code=404, detail="trail not found")
        if not trails_repo.remove_stop(conn, trail_id, stop_id):
            raise HTTPException(status_code=404, detail="stop not found")
        return trails_repo.stops(conn, trail_id)


@router.get("/{trail_id}/journal", response_model=JournalOut)
def trail_journal(trail_id: int) -> dict:
    with connect() as conn:
        trail = trails_repo.get_trail(conn, trail_id)
        if not trail:
            raise HTTPException(status_code=404, detail="trail not found")
        counts = trails_repo.photo_counts(conn, trail_id)
        features = trails_repo.verified_features_by_site(conn, trail_id)
    entries = [
        {
            "stop_order": stop["stop_order"],
            "site_id": stop["site_id"],
            "site_name": stop["site_name"],
            "visit_date": stop["visit_date"],
            "original_note": stop["note"],
            "generated_summary": generated_summary(
                stop["stop_order"],
                stop["site_name"],
                stop["category"],
                stop["region"],
                stop["visit_date"],
                counts.get(int(stop["site_id"]), 0),
                features.get(int(stop["site_id"]), []),
            ),
            "generated": True,
            "photos": counts.get(int(stop["site_id"]), 0),
            "verified_features": features.get(int(stop["site_id"]), []),
        }
        for stop in trail["stops"]
    ]
    return {"trail_id": trail_id, "title": trail["title"], "generated": True, "entries": entries}


@router.get("/{trail_id}/summary", response_model=TrailSummaryOut)
def trail_summary(trail_id: int) -> dict:
    with connect() as conn:
        trail = trails_repo.get_trail(conn, trail_id)
        if not trail:
            raise HTTPException(status_code=404, detail="trail not found")
        photos = trails_repo.total_photos(conn, trail_id)
        feature_counts = trails_repo.verified_feature_counts(conn, trail_id)
    legs = trail_legs(trail["stops"])
    return {
        "trail_id": trail_id,
        "title": trail["title"],
        "sites": len(trail["stops"]),
        "photos": photos,
        "total_km": round(sum(float(leg["km"]) for leg in legs), 2),
        "distance_mode": "straight_line",
        "missing_coordinates": missing_coordinate_sites(trail["stops"]),
        "top_features": top_features(feature_counts),
        "legs": legs,
    }
