"""Minimal reviewer identity storage."""

from typing import Any

import psycopg

USER_COLUMNS = "id, name, email, role, created_at"


def create_user(
    conn: psycopg.Connection[dict[str, Any]],
    name: str,
    email: str | None,
    role: str,
) -> dict[str, Any]:
    row = conn.execute(
        """INSERT INTO users (name, email, role) VALUES (%s, %s, %s)
           ON CONFLICT (email) DO NOTHING RETURNING id, name, email, role, created_at""",
        (name, email, role),
    ).fetchone()
    if row:
        return row
    existing = conn.execute(
        "SELECT id, name, email, role, created_at FROM users WHERE email=%s", (email,)
    ).fetchone()
    assert existing is not None
    return existing


def list_users(
    conn: psycopg.Connection[dict[str, Any]], limit: int = 100, offset: int = 0
) -> list[dict[str, Any]]:
    return list(
        conn.execute(
            "SELECT id, name, email, role, created_at FROM users ORDER BY id LIMIT %s OFFSET %s",
            (limit, offset),
        ).fetchall()
    )


def get_user(conn: psycopg.Connection[dict[str, Any]], user_id: int) -> dict[str, Any] | None:
    return conn.execute(
        "SELECT id, name, email, role, created_at FROM users WHERE id=%s", (user_id,)
    ).fetchone()
