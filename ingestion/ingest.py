"""Ingestion orchestrator.

Ties loaders -> chunker -> embedder -> Supabase upsert into one run. Idempotent:
re-running on unchanged input must not duplicate rows, and rows whose source was
processed but whose content_hash wasn't seen this run get deleted (removes content
that no longer exists at the source).

Covers: FR-6.1, FR-6.4. See DATA_INGESTION.md Sec6.
"""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv()

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def setup_db() -> None:
    """Apply schema.sql against Supabase Postgres.

    PostgREST (what supabase-py's table/rpc client speaks) can't run DDL --
    enabling the vector extension, creating the table, and defining the
    similarity function need a direct Postgres connection. Idempotent: every
    statement in schema.sql is IF NOT EXISTS / OR REPLACE, safe to re-run.
    """
    database_url = os.environ["DATABASE_URL"]
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()


if __name__ == "__main__":
    setup_db()
    print("Schema applied.")
