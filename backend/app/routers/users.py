"""Minimal reviewer identity endpoints. No authentication in the hackathon build."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from ..db import connect
from ..repositories import users as users_repo
from ..schemas import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=201)
def create_user(body: UserCreate) -> dict:
    with connect() as conn:
        return users_repo.create_user(conn, body.name, body.email, body.role)


@router.get("", response_model=list[UserOut])
def list_users(
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    with connect() as conn:
        return users_repo.list_users(conn, limit=limit, offset=offset)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int) -> dict:
    with connect() as conn:
        user = users_repo.get_user(conn, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return user
