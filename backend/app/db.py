import os

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

load_dotenv()

DSN = os.getenv("DATABASE_URL", "postgresql://atlas:atlas@localhost:5432/atlas")
UPLOAD_DIR = os.getenv(
    "UPLOAD_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
)


def connect():
    conn = psycopg.connect(DSN, row_factory=dict_row)
    register_vector(conn)
    return conn
