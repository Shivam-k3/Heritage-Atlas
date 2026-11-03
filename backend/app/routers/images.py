"""Upload, batch upload, image detail and reprocess endpoints."""

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from .. import config
from ..db import connect
from ..ml import InvalidImageError
from ..repositories import images as images_repo
from ..repositories import sites as sites_repo
from ..schemas import ImageOut, JobOut, TagOut, UploadBatchOut, UploadOut
from ..services.images import (
    SavedImage,
    UploadTooLargeError,
    public_url,
    save_image,
)

router = APIRouter(tags=["images"])


def _resolve_site(
    conn,
    *,
    site_id: int | None,
    site_name: str | None,
    region: str | None,
    district: str | None,
    category: str | None,
    site_type: str | None,
    lat: float | None,
    lon: float | None,
    description: str | None,
    fallback_lat: float | None = None,
    fallback_lon: float | None = None,
) -> int:
    if site_id is not None:
        if not sites_repo.get_site(conn, site_id):
            raise HTTPException(status_code=404, detail="site not found")
        return site_id
    if not site_name:
        raise HTTPException(status_code=400, detail="site_id or site_name is required")
    site = sites_repo.find_by_name(conn, site_name, region)
    if site:
        return int(site["id"])
    created = sites_repo.create_site(
        conn,
        {
            "name": site_name,
            "region": region,
            "district": district,
            "category": category or site_type,
            "lat": lat if lat is not None else fallback_lat,
            "lon": lon if lon is not None else fallback_lon,
            "description": description,
            "description_source": "upload",
        },
    )
    return int(created["id"])


def _duplicate_result(conn, existing: dict, root) -> dict:
    """Reuse the stored image; queue a job only when the image still needs processing."""
    job = None
    if existing["status"] in {"uploaded", "processing"}:
        job = images_repo.create_job(conn, int(existing["id"]))
    elif existing["status"] == "failed":
        images_repo.prepare_reprocess(conn, int(existing["id"]))
        job = images_repo.create_job(conn, int(existing["id"]))
    return {
        "site_id": int(existing["site_id"]),
        "image_id": int(existing["id"]),
        "job_id": int(job["id"]) if job else None,
        "status": "queued" if job else str(existing["status"]),
        "duplicate": True,
        "url": public_url(existing["storage_path"], root),
    }


def _new_image_result(
    conn,
    saved: SavedImage,
    site_id: int,
    root,
    author: str | None,
    licence: str | None,
    licence_url: str | None,
    source_url: str | None,
) -> dict:
    image = images_repo.create_image(
        conn,
        site_id,
        saved,
        author=author,
        licence=licence,
        licence_url=licence_url,
        source_url=source_url,
    )
    job = images_repo.create_job(conn, int(image["id"]))
    return {
        "site_id": site_id,
        "image_id": int(image["id"]),
        "job_id": int(job["id"]),
        "status": "queued",
        "duplicate": False,
        "url": public_url(saved.path, root),
    }


@router.post("/images/upload", response_model=UploadOut, status_code=202)
def upload_image(
    file: Annotated[UploadFile, File()],
    site_id: Annotated[int | None, Form()] = None,
    site_name: Annotated[str | None, Form()] = None,
    region: Annotated[str | None, Form()] = None,
    district: Annotated[str | None, Form()] = None,
    category: Annotated[str | None, Form()] = None,
    site_type: Annotated[str | None, Form()] = None,
    lat: Annotated[float | None, Form()] = None,
    lon: Annotated[float | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    author: Annotated[str | None, Form()] = None,
    licence: Annotated[str | None, Form()] = None,
    licence_url: Annotated[str | None, Form()] = None,
    source_url: Annotated[str | None, Form()] = None,
) -> dict:
    root = config.upload_dir()
    try:
        saved = save_image(file.file, file.filename or "upload", root, config.max_upload_bytes())
    except UploadTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except InvalidImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    with connect() as conn:
        existing = images_repo.find_by_sha256(conn, saved.sha256)
        if existing:
            return _duplicate_result(conn, existing, root)
        resolved_site_id = _resolve_site(
            conn,
            site_id=site_id,
            site_name=site_name,
            region=region,
            district=district,
            category=category,
            site_type=site_type,
            lat=lat,
            lon=lon,
            description=description,
            fallback_lat=saved.lat,
            fallback_lon=saved.lon,
        )
        return _new_image_result(
            conn, saved, resolved_site_id, root, author, licence, licence_url, source_url
        )


@router.post("/images/upload-batch", response_model=UploadBatchOut, status_code=202)
def upload_batch(
    files: Annotated[list[UploadFile], File()],
    site_id: Annotated[int | None, Form()] = None,
    site_name: Annotated[str | None, Form()] = None,
    region: Annotated[str | None, Form()] = None,
    district: Annotated[str | None, Form()] = None,
    category: Annotated[str | None, Form()] = None,
    site_type: Annotated[str | None, Form()] = None,
    lat: Annotated[float | None, Form()] = None,
    lon: Annotated[float | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    author: Annotated[str | None, Form()] = None,
    licence: Annotated[str | None, Form()] = None,
    licence_url: Annotated[str | None, Form()] = None,
    source_url: Annotated[str | None, Form()] = None,
) -> dict:
    """Upload several files to one site. A corrupt file is reported, not fatal for the batch."""
    if not files:
        raise HTTPException(status_code=400, detail="at least one file is required")
    root = config.upload_dir()
    results: list[dict] = []
    errors: list[dict[str, str]] = []
    with connect() as conn:
        resolved_site_id = _resolve_site(
            conn,
            site_id=site_id,
            site_name=site_name,
            region=region,
            district=district,
            category=category,
            site_type=site_type,
            lat=lat,
            lon=lon,
            description=description,
        )
        for upload in files:
            filename = upload.filename or "upload"
            try:
                saved = save_image(upload.file, filename, root, config.max_upload_bytes())
            except (UploadTooLargeError, InvalidImageError) as exc:
                errors.append({"filename": filename, "error": str(exc)})
                continue
            existing = images_repo.find_by_sha256(conn, saved.sha256)
            if existing:
                results.append(_duplicate_result(conn, existing, root))
                continue
            results.append(
                _new_image_result(
                    conn,
                    saved,
                    resolved_site_id,
                    root,
                    author,
                    licence,
                    licence_url,
                    source_url,
                )
            )
    duplicates = sum(1 for result in results if result["duplicate"])
    return {
        "results": results,
        "errors": errors,
        "accepted": len(results) - duplicates,
        "duplicates": duplicates,
        "rejected": len(errors),
    }


@router.get("/images/{image_id}", response_model=ImageOut)
def get_image(image_id: int) -> dict:
    with connect() as conn:
        image = images_repo.get_image(conn, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="image not found")
    return image


@router.get("/images/{image_id}/tags", response_model=list[TagOut])
def get_image_tags(image_id: int) -> list[dict]:
    with connect() as conn:
        if not images_repo.get_image(conn, image_id):
            raise HTTPException(status_code=404, detail="image not found")
        return images_repo.list_tags(conn, image_id)


@router.post("/images/{image_id}/reprocess", response_model=JobOut, status_code=202)
def reprocess_image(image_id: int) -> dict:
    with connect() as conn:
        if not images_repo.get_image(conn, image_id):
            raise HTTPException(status_code=404, detail="image not found")
        images_repo.prepare_reprocess(conn, image_id)
        return images_repo.create_job(conn, image_id)
