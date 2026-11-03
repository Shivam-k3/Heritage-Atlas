"""Read-only bulk ingestion batch progress.

Folder scanning is a CLI capability (scripts/ingest_folder.py): the browser cannot address
an arbitrary server filesystem path. Browser uploads use POST /images/upload-batch.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from ..db import connect
from ..repositories import ingestion as ingestion_repo
from ..schemas import IngestBatchOut

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.get("/batches", response_model=list[IngestBatchOut])
def list_batches(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    with connect() as conn:
        return ingestion_repo.list_batches(conn, limit=limit, offset=offset)


@router.get("/batches/{batch_id}", response_model=IngestBatchOut)
def get_batch(batch_id: int) -> dict:
    with connect() as conn:
        batch = ingestion_repo.get_batch(conn, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="ingest batch not found")
    return batch
