"""Apply db/schema.sql to the database in DATABASE_URL. Safe to re-run with --reset.

Usage:  python scripts/init_db.py          # create tables if the DB is empty
        python scripts/init_db.py --reset  # DROP everything and recreate (dev only)
"""

import argparse
import pathlib
import sys

import psycopg
from dotenv import load_dotenv

load_dotenv()

from app.db import DSN  # noqa: E402

SCHEMA = pathlib.Path(__file__).resolve().parents[2] / "db" / "schema.sql"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="drop all tables first")
    args = parser.parse_args()

    with psycopg.connect(DSN, autocommit=True) as conn:
        if args.reset:
            conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        exists = conn.execute("SELECT to_regclass('public.sites')").fetchone()[0]
        if exists:
            print("Schema already present. Use --reset to recreate.")
            return 0
        conn.execute(SCHEMA.read_text())
    print("Schema applied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
