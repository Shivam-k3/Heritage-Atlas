"""Heritage Atlas FastAPI application. Route handlers stay thin; SQL lives in repositories."""

import logging

import psycopg
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config, db, ml
from .routers import images, ingestion, jobs, review, search, sites, trails, users
from .schemas import HealthOut

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("heritage_atlas")

app = FastAPI(
    title=config.API_TITLE,
    version=config.API_VERSION,
    description=(
        "AI-assisted heritage archive. CLIP (512-d) and MiniLM (384-d) are separate "
        "embedding spaces; scores are raw cosine similarities, not probabilities."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

upload_root = config.upload_dir()
upload_root.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=upload_root), name="files")

for router in (
    sites.router,
    images.router,
    jobs.router,
    search.router,
    review.router,
    ingestion.router,
    trails.router,
    users.router,
):
    app.include_router(router)


@app.get("/health", response_model=HealthOut, tags=["health"])
def health() -> dict:
    try:
        db.ping()
    except psycopg.Error as exc:
        logger.warning("health check database error: %s", exc)
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ok", "database": "ok", "models": ml.model_info()}


@app.exception_handler(psycopg.errors.IntegrityError)
async def integrity_error(_: Request, exc: psycopg.errors.IntegrityError) -> JSONResponse:
    logger.warning("database constraint violation: %s", exc)
    return JSONResponse(status_code=409, content={"detail": "database constraint violation"})


@app.exception_handler(psycopg.Error)
async def database_error(_: Request, exc: psycopg.Error) -> JSONResponse:
    logger.exception("database error", exc_info=exc)
    return JSONResponse(status_code=503, content={"detail": "database unavailable"})


@app.exception_handler(Exception)
async def unhandled_error(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "internal server error"})
