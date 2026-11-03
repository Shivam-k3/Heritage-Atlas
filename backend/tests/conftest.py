"""Shared fixtures.

Database tests need TEST_DATABASE_URL pointing at a database whose name ends in `_test`.
Pure unit tests run without a database.
"""

import os
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = REPO_ROOT / "db" / "schema.sql"
MIGRATIONS = sorted((REPO_ROOT / "db" / "migrations").glob("*.sql"))
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "").strip()

# app.config reads DATABASE_URL at call time, so set it before importing the app.
if TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("UPLOAD_DIR", str(Path(__file__).resolve().parent / ".uploads"))

TABLES = (
    "tag_reviews",
    "image_tags",
    "tags",
    "jobs",
    "ingest_batches",
    "trail_stops",
    "trails",
    "images",
    "sites",
    "users",
)


def _guard(url: str) -> None:
    name = str(psycopg.conninfo.conninfo_to_dict(url).get("dbname", ""))
    if not name.endswith("_test"):
        raise RuntimeError("refusing to run destructive tests outside a *_test database")


@pytest.fixture(scope="session")
def database() -> str:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not set")
    _guard(TEST_DATABASE_URL)
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
        conn.execute(SCHEMA.read_text(encoding="utf-8"))
        for migration in MIGRATIONS:
            conn.execute(migration.read_text(encoding="utf-8"))
    return TEST_DATABASE_URL


@pytest.fixture
def db(database: str):
    with psycopg.connect(database, row_factory=dict_row) as conn:
        register_vector(conn)
        yield conn
        conn.rollback()


@pytest.fixture
def clean_db(database: str):
    with psycopg.connect(database, autocommit=True) as conn:
        conn.execute("TRUNCATE " + ", ".join(TABLES) + " RESTART IDENTITY CASCADE")
    yield


@pytest.fixture
def client(clean_db) -> TestClient:
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def png_bytes(color: str = "red", size: tuple[int, int] = (32, 32)) -> bytes:
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()
