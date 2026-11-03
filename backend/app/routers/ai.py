"""Grounded, optional Gemini assistant endpoints."""

from fastapi import APIRouter, HTTPException

from .. import ai, config
from ..db import connect
from ..schemas import (
    AIChatOut,
    AIChatRequest,
    AIExplainOut,
    AIStatusOut,
    AITrailSuggestOut,
    AITrailSuggestRequest,
)
from ..services import ai as ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/status", response_model=AIStatusOut)
def ai_status() -> dict[str, object]:
    return ai.status()


@router.post("/chat", response_model=AIChatOut)
def ai_chat(body: AIChatRequest) -> dict:
    if len(body.history) > config.ai_max_history_messages():
        raise HTTPException(
            status_code=422,
            detail=f"history may contain at most {config.ai_max_history_messages()} messages",
        )
    with connect() as conn:
        if body.site_id is not None:
            from ..repositories import sites as sites_repo

            if not sites_repo.get_site(conn, body.site_id):
                raise HTTPException(status_code=404, detail="site not found")
        if body.image_id is not None:
            from ..repositories import images as images_repo

            if not images_repo.get_image(conn, body.image_id):
                raise HTTPException(status_code=404, detail="image not found")
        return ai_service.chat(
            conn,
            body.question,
            [message.model_dump() for message in body.history],
            body.site_id,
            body.image_id,
        )


@router.post("/explain/{site_id}", response_model=AIExplainOut)
def ai_explain(site_id: int) -> dict:
    with connect() as conn:
        result = ai_service.explain(conn, site_id)
    if result is None:
        raise HTTPException(status_code=404, detail="site not found")
    return result


@router.post("/trails/suggest", response_model=AITrailSuggestOut)
def ai_trail_suggest(body: AITrailSuggestRequest) -> dict:
    with connect() as conn:
        try:
            return ai_service.suggest_trail(
                conn,
                body.site_ids,
                body.title,
                body.description,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"site {exc.args[0]} not found") from exc
