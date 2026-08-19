-- Chunks table and hybrid (dense + keyword) search function for the Voice
-- Twin vector store. Idempotent: safe to re-run. See docs/DATA_INGESTION.md
-- Sec4/6 and docs/ARCHITECTURE.md Sec2.4, ADR-004.

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

-- Hybrid search support: a generated full-text column alongside the vector
-- index. Postgres maintains this automatically from `text` on every
-- insert/upsert -- no ingestion-side code needed to populate it.
alter table chunks add column if not exists text_search tsvector
    generated always as (to_tsvector('english', text)) stored;

create index if not exists chunks_text_search_idx
    on chunks using gin (text_search);

-- Hybrid retrieval. Dense cosine similarity decides *eligibility* -- this is
-- the anti-hallucination threshold gate (ADR-004): a chunk must clear
-- match_threshold on real semantic similarity to be considered at all, full
-- stop, no exceptions for a keyword hit alone. Reciprocal Rank Fusion between
-- the dense rank and a full-text keyword rank then decides *order* among
-- already-eligible candidates, so a chunk with a strong literal match (an
-- acronym, a name, a number -- exactly what a single dense embedding vector
-- is bad at anchoring on) can still surface in the top match_count even when
-- pure dense-similarity ranking would have pushed it out.
create or replace function match_chunks (
    query_embedding vector(384),
    query_text text,
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
    with eligible as (
        select
            chunks.id,
            chunks.source,
            chunks.source_type,
            chunks.section,
            chunks.text,
            chunks.source_url,
            1 - (chunks.embedding <=> query_embedding) as similarity,
            row_number() over (order by chunks.embedding <=> query_embedding) as dense_rank,
            ts_rank_cd(chunks.text_search, plainto_tsquery('english', query_text)) as keyword_score
        from chunks
        where 1 - (chunks.embedding <=> query_embedding) > match_threshold
    ),
    ranked as (
        select
            eligible.*,
            row_number() over (order by keyword_score desc) as keyword_rank
        from eligible
    )
    select
        ranked.id, ranked.source, ranked.source_type, ranked.section,
        ranked.text, ranked.source_url, ranked.similarity
    from ranked
    order by
        (1.0 / (60 + dense_rank))
        + case when keyword_score > 0 then 1.0 / (60 + keyword_rank) else 0 end
        desc
    limit match_count;
$$;
