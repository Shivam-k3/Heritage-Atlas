"""Heritage Atlas FastAPI application. Route handlers stay thin; SQL lives in repositories."""

import asyncio
import logging
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config, db, ml
from .routers import ai, images, ingestion, jobs, review, search, sites, trails, users
from .schemas import HealthOut, ReadinessOut

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("heritage_atlas")


@asynccontextmanager
async def lifespan(_: FastAPI):
    readiness = await asyncio.to_thread(ml.warm_up)
    for name, state in readiness.items():
        if state["loaded"]:
            logger.info(
                "%s model ready in %.3fs",
                name,
                state["initialization_seconds"],
            )
        else:
            logger.error("%s model unavailable: %s", name, state["error"])
    yield


app = FastAPI(
    title=config.API_TITLE,
    version=config.API_VERSION,
    lifespan=lifespan,
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
    ai.router,
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


@app.get("/readiness", response_model=ReadinessOut, tags=["health"])
def readiness() -> dict:
    try:
        database_ok = db.ping()
    except psycopg.Error as exc:
        logger.warning("readiness database error: %s", exc)
        database_ok = False
    models = ml.model_readiness()
    models_ready = all(state["loaded"] for state in models.values())
    return {
        "status": "ready" if database_ok and models_ready else "not_ready",
        "database": "ok" if database_ok else "unavailable",
        "models": models,
    }


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
