-- Chunks table and similarity search function for the Voice Twin vector store.
-- Idempotent: safe to re-run. See docs/DATA_INGESTION.md Sec4/6 and
-- docs/ARCHITECTURE.md Sec2.4.

create extension if not exists vector;

create table if not exists chunks (
    id bigserial primary key,
    source text not null,
    source_type text not null,
    section text not null,
    text text not null,
    source_url text,
    content_hash text not null unique,
    embedding vector(384) not null,
    ingested_at timestamptz not null default now()
);

create index if not exists chunks_embedding_idx
    on chunks using hnsw (embedding vector_cosine_ops);

-- PostgREST (what supabase-py's table/rpc client speaks) can't evaluate the
-- pgvector <=> distance operator directly, so similarity search is wrapped in
-- a function and called via .rpc("match_chunks", ...) instead.
create or replace function match_chunks (
    query_embedding vector(384),
    match_threshold float,
    match_count int
) returns table (
    id bigint,
    source text,
    source_type text,
    section text,
    text text,
    source_url text,
    similarity float
) language sql stable as $$
    select
        chunks.id,
        chunks.source,
        chunks.source_type,
        chunks.section,
        chunks.text,
        chunks.source_url,
        1 - (chunks.embedding <=> query_embedding) as similarity
    from chunks
    where 1 - (chunks.embedding <=> query_embedding) > match_threshold
    order by chunks.embedding <=> query_embedding
    limit match_count;
$$;
