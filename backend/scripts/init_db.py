"""Apply db/schema.sql and pending db/migrations/*.sql to DATABASE_URL.

Every statement is idempotent, so this is safe to re-run and upgrades the original scaffold.

Usage:  python scripts/init_db.py          # create or upgrade
        python scripts/init_db.py --reset  # DROP everything and recreate (dev only)
"""

import argparse
import pathlib
import sys

import psycopg
from dotenv import load_dotenv

load_dotenv()

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import database_url  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = REPO_ROOT / "db" / "schema.sql"
MIGRATIONS = sorted((REPO_ROOT / "db" / "migrations").glob("*.sql"))

# Supabase exposes public tables through PostgREST; RLS makes them deny-by-default.
ENABLE_RLS = """
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE sites ENABLE ROW LEVEL SECURITY;
ALTER TABLE images ENABLE ROW LEVEL SECURITY;
ALTER TABLE tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE image_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE tag_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingest_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE trails ENABLE ROW LEVEL SECURITY;
ALTER TABLE trail_stops ENABLE ROW LEVEL SECURITY;
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="drop all tables first")
    args = parser.parse_args()

    with psycopg.connect(database_url(), autocommit=True) as conn:
        if args.reset:
            conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        conn.execute(SCHEMA.read_text(encoding="utf-8"))
        print("Schema applied.")
        for migration in MIGRATIONS:
            conn.execute(migration.read_text(encoding="utf-8"))
            print(f"Migration applied: {migration.name}")
        conn.execute(ENABLE_RLS)
    print("Row level security enabled on every table.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
