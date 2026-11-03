"""Database connection helpers. SQL lives in app/repositories; this module owns connections."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from .config import database_url


def open_connection() -> psycopg.Connection[dict[str, Any]]:
    """Open a connection for long-lived callers such as the worker."""
    conn = psycopg.connect(database_url(), row_factory=dict_row)
    register_vector(conn)
    return conn


@contextmanager
def connect() -> Iterator[psycopg.Connection[dict[str, Any]]]:
    """Open a short-lived connection. Commits on success, rolls back on error."""
    conn = open_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ping() -> bool:
    with connect() as conn:
        return conn.execute("SELECT 1").fetchone() is not None
