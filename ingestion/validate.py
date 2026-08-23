"""Post-ingestion validation.

Run after every ingest: structural assertions (chunk count in range, no
floor/ceiling violations, no nulls, no duplicate hashes, embedding dims match)
plus 5 spot-check queries against the real, live corpus -- verifying retrieval
actually surfaces the right chunk for a known question, and that a genuinely
out-of-scope question gets refused at the data layer (no_match) rather than
reaching the LLM at all. Per DATA_INGESTION.md Sec9: "debugging bad retrieval
through a voice interface is miserable -- validate at the data layer."
"""

import os
import sys
from collections import Counter

import psycopg
from dotenv import load_dotenv
from supabase import create_client

from ingestion.chunker import CEILING_TOKENS, FLOOR_TOKENS, _token_count
from ingestion.embedder import embed_query
from ingestion.env import env_secret

load_dotenv()

# Chunk text can contain real emoji/em-dash from GitHub READMEs; this
# terminal's cp1252 codepage can't print them. UTF-8 output with replacement
# is a display-robustness fix only -- the underlying stored data is untouched.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MIN_CHUNKS = 40
MAX_CHUNKS = 150
EXPECTED_DIM = 384

# (query, keywords -- pass if any appear in the top result's section+text)
SPOT_CHECKS = [
    ("What are you working on right now?", ["jobhunt"]),
    ("What was hard about your RAG project?", ["hallucination", "risk", "context expansion"]),
    ("What are you looking for in your next role?", ["remote", "agents", "hybrid"]),
    ("What happened with the Mockbuilder project?", ["mockbuilder", "scrap"]),
    ("What's your CGPA?", ["cgpa", "7.6"]),
]

OUT_OF_SCOPE_QUERY = "What's your favorite pizza topping?"


def validate_structure() -> bool:
    ok = True
    with psycopg.connect(env_secret("DATABASE_URL")) as conn:
        with conn.cursor() as cur:
            cur.execute("select count(*) from chunks")
            total = cur.fetchone()[0]
            print(f"Total chunks: {total}")
            if not (MIN_CHUNKS <= total <= MAX_CHUNKS):
                print(f"  FAIL: expected {MIN_CHUNKS}-{MAX_CHUNKS}")
                ok = False

            cur.execute(
                "select source, section, text, content_hash, vector_dims(embedding) from chunks"
            )
            rows = cur.fetchall()

    for source, section, text, content_hash, dim in rows:
        if not source or not section:
            print(f"  FAIL: null source/section on hash {content_hash}")
            ok = False
        if dim != EXPECTED_DIM:
            print(f"  FAIL: embedding dim {dim} != {EXPECTED_DIM} on hash {content_hash}")
            ok = False
        tc = _token_count(text)
        if tc < FLOOR_TOKENS:
            print(f"  FAIL: chunk under floor ({tc} tokens): {section}")
            ok = False
        if tc > CEILING_TOKENS:
            print(f"  FAIL: chunk over ceiling ({tc} tokens): {section}")
            ok = False

    dupes = [h for h, c in Counter(r[3] for r in rows).items() if c > 1]
    if dupes:
        print(f"  FAIL: {len(dupes)} duplicate content_hash values")
        ok = False

    print("Structural validation: " + ("PASS" if ok else "FAIL"))
    return ok


def _match(client, query: str, threshold: float, top_k: int):
    embedding = embed_query(query)
    resp = client.rpc(
        "match_chunks",
        {
            "query_embedding": embedding,
            "query_text": query,
            "match_threshold": threshold,
            "match_count": top_k,
        },
    ).execute()
    return resp.data


def validate_retrieval() -> bool:
    client = create_client(env_secret("SUPABASE_URL"), env_secret("SUPABASE_SERVICE_KEY"))
    threshold = float(os.environ.get("RETRIEVAL_THRESHOLD", 0.35))
    top_k = int(os.environ.get("RETRIEVAL_TOP_K", 4))

    ok = True
    print(f"\nSpot-check queries (threshold={threshold}, top_k={top_k}):")
    for query, keywords in SPOT_CHECKS:
        results = _match(client, query, threshold, top_k)
        print(f'\n  Q: "{query}"')
        if not results:
            print("    FAIL: no results returned")
            ok = False
            continue
        for r in results:
            print(f"    {r['similarity']:.3f}  [{r['source']} | {r['section']}]")

        # Checked against the full top-k, not just rank 0 -- FR-3.2 hands the
        # LLM all top-k chunks, so a match anywhere in that set is what the
        # agent will actually see, not just whichever ranked highest.
        found_at = next(
            (
                i
                for i, r in enumerate(results)
                if any(kw.lower() in f"{r['source']} {r['section']} {r['text']}".lower() for kw in keywords)
            ),
            None,
        )
        if found_at is None:
            print(f"    FAIL: none of {keywords} found in top-{top_k}")
            ok = False
        else:
            print(f"    PASS (matched at rank {found_at})")

    print(f'\n  Q (out-of-scope): "{OUT_OF_SCOPE_QUERY}"')
    results = _match(client, OUT_OF_SCOPE_QUERY, threshold, top_k)
    if results:
        print(f"    FAIL: expected no_match, got {len(results)} results "
              f"(top sim={results[0]['similarity']:.3f})")
        ok = False
    else:
        print("    PASS: correctly refused (no_match)")

    print("\nRetrieval validation: " + ("PASS" if ok else "FAIL"))
    return ok


def main() -> None:
    struct_ok = validate_structure()
    retrieval_ok = validate_retrieval()
    if struct_ok and retrieval_ok:
        print("\nAll validations passed.")
    else:
        print("\nSome validations FAILED.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
