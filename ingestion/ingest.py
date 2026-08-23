"""Ingestion orchestrator.

Ties loaders -> chunker -> embedder -> Supabase upsert into one run. Idempotent:
re-running on unchanged input must not duplicate rows (upsert on content_hash),
and rows whose source was processed but whose content_hash wasn't seen this run
get deleted (removes content that no longer exists at the source).

Covers: FR-6.1, FR-6.4. See DATA_INGESTION.md Sec6.
"""

from pathlib import Path
from typing import List

import psycopg
from dotenv import load_dotenv
from supabase import Client, create_client

from ingestion.chunker import chunk
from ingestion.embedder import embed_documents
from ingestion.env import env_secret
from ingestion.loaders import github_loader, markdown_loader, pdf_loader
from ingestion.types import ChunkRecord

load_dotenv()

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
CORPUS_DIR = Path(__file__).parent.parent / "corpus"


def setup_db() -> None:
    """Apply schema.sql against Supabase Postgres.

    PostgREST (what supabase-py's table/rpc client speaks) can't run DDL --
    enabling the vector extension, creating the table, and defining the
    similarity function need a direct Postgres connection. Idempotent: every
    statement in schema.sql is IF NOT EXISTS / OR REPLACE, safe to re-run.
    """
    # env_secret(), not os.environ[...] directly -- see ingestion/env.py.
    # A GitHub Actions secret pasted with stray whitespace (confirmed live
    # 2026-08-23 against this exact workflow) reaches os.environ verbatim;
    # local dev never hits this, since python-dotenv already trims .env
    # values.
    database_url = env_secret("DATABASE_URL")
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()


def _supabase_client() -> Client:
    return create_client(env_secret("SUPABASE_URL"), env_secret("SUPABASE_SERVICE_KEY"))


def _load_all() -> List[ChunkRecord]:
    raw = []
    resume_path = CORPUS_DIR / "AI Engineer Resume.pdf"
    if resume_path.exists():
        raw += pdf_loader.load(resume_path)
    raw += markdown_loader.load_corpus_markdown(CORPUS_DIR)
    raw += github_loader.load()
    return chunk(raw)


def run() -> None:
    setup_db()
    client = _supabase_client()

    records = _load_all()
    if not records:
        print("No chunks produced -- aborting before touching the database.")
        return

    embeddings = embed_documents([r.embed_text for r in records])

    rows = [
        {
            "source": r.source,
            "source_type": r.source_type,
            "section": r.section,
            "text": r.text,
            "source_url": r.source_url,
            "content_hash": r.content_hash,
            "embedding": embeddings[i],
        }
        for i, r in enumerate(records)
    ]

    client.table("chunks").upsert(rows, on_conflict="content_hash").execute()

    # Idempotency step 4 (DATA_INGESTION.md Sec6): for every source touched this
    # run, delete rows with that source whose content_hash wasn't produced this
    # run -- removes content that was deleted/changed at the source.
    hashes_by_source = {}
    for r in records:
        hashes_by_source.setdefault(r.source, []).append(r.content_hash)

    total_deleted = 0
    for source, hashes in hashes_by_source.items():
        resp = (
            client.table("chunks")
            .delete()
            .eq("source", source)
            .not_.in_("content_hash", hashes)
            .execute()
        )
        total_deleted += len(resp.data)

    per_source = {}
    for r in records:
        per_source[r.source] = per_source.get(r.source, 0) + 1

    print(f"Upserted {len(rows)} chunks across {len(per_source)} sources.")
    for source, count in sorted(per_source.items()):
        print(f"  {source}: {count}")
    print(f"Deleted {total_deleted} stale rows.")


if __name__ == "__main__":
    run()
