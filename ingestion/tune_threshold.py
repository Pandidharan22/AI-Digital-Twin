"""Threshold tuning sweep.

Runs TEST_PLAN.md's Suite A (in-corpus, must match) and Suite B (out-of-corpus,
must refuse) against the live corpus at several RETRIEVAL_THRESHOLD candidates,
independent of whatever threshold is currently configured in .env -- so the full
sweep runs in one pass without editing environment state between runs. Reuses
validate.py's own _match() helper (the same embed+RPC path agent/retrieval.py
uses in production, just parameterized by threshold) rather than duplicating
retrieval logic.

Per TEST_PLAN.md Sec2's own rule: pick the LOWEST threshold with zero Suite B
false accepts -- a false accept (an out-of-scope query returning results) is
worse than a false refusal, since a refusal is honest and an accepted-but-weak
match risks the LLM stretching it into a fabricated claim.

Covers: BUILD_PLAN.md Phase 3 Day 4 item 9.
"""

import os
import sys

from dotenv import load_dotenv
from supabase import create_client

from ingestion.validate import _match

load_dotenv()

# Same display-robustness fix validate.py applies -- corpus text can contain
# real em-dashes this terminal's cp1252 codepage can't print.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOP_K = 4
THRESHOLDS = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]

# Suite A -- in-corpus, must all MATCH. Extends validate.py's 5 SPOT_CHECKS to
# TEST_PLAN.md's full ~12-question suite, grounded in this project's real
# corpus (resume + corpus/context.md) rather than TEST_PLAN.md's original
# generic [company]/[your main project] placeholders.
SUITE_A = [
    ("What's your most recent role?", ["freelance", "software developer"]),
    ("What did you work on at your freelance role?", ["client-facing", "stakeholders", "applied ai"]),
    ("What programming languages and frameworks do you know?", ["python", "fastapi"]),
    ("Tell me about the Self-Reflective RAG platform", ["hallucination", "retrieval confidence", "heuristic"]),
    ("What did you study?", ["saveetha", "computer science"]),
    ("Have you worked with Docker?", ["docker"]),
    ("What was the hardest technical problem you've solved?", ["context expansion", "hallucination", "risk"]),
    ("What are you looking for in your next role?", ["remote", "agents", "hybrid"]),
    ("Do you have experience with vector databases?", ["faiss", "chromadb", "qdrant"]),
    ("Tell me about the loan eligibility project", ["roc-auc", "shap", "loan"]),
    ("What are you working on right now?", ["jobhunt"]),
    ("What happened with the Mockbuilder project?", ["mockbuilder", "scrap"]),
    ("What's your CGPA?", ["cgpa", "7.6"]),
]

# Suite B -- out-of-corpus, must all NO_MATCH. Generic by design (TEST_PLAN.md
# Sec1 Suite B) -- these are personal-boundary/off-topic questions regardless
# of whose twin this is, no corpus-specific tailoring needed.
SUITE_B = [
    "What's your favourite pizza topping?",
    "What's your opinion on the latest election?",
    "Do you have any siblings?",
    "What car do you drive?",
    "What's your salary expectation?",
    "Where do you live exactly?",
    "What did you do last weekend?",
]


def sweep() -> None:
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    print(f"{'threshold':>10} | {'Suite A correct':>16} | {'Suite B false accepts':>22}")
    print("-" * 55)

    results = []
    for threshold in THRESHOLDS:
        a_correct = 0
        for query, keywords in SUITE_A:
            rows = _match(client, query, threshold, TOP_K)
            found = any(
                any(kw.lower() in f"{row['source']} {row['section']} {row['text']}".lower() for kw in keywords)
                for row in rows
            )
            if found:
                a_correct += 1

        b_false_accepts = sum(1 for query in SUITE_B if _match(client, query, threshold, TOP_K))

        results.append((threshold, a_correct, b_false_accepts))
        print(
            f"{threshold:>10.2f} | {a_correct:>3}/{len(SUITE_A):<12} | "
            f"{b_false_accepts:>3}/{len(SUITE_B)}"
        )

    print()
    zero_false_accept = [t for t, _a, b in results if b == 0]
    if not zero_false_accept:
        print("No threshold in the sweep achieved zero Suite B false accepts -- widen THRESHOLDS.")
        return

    chosen = min(zero_false_accept)
    chosen_a = next(a for t, a, _b in results if t == chosen)
    print(
        f"Recommended RETRIEVAL_THRESHOLD = {chosen} "
        f"(zero Suite B false accepts, {chosen_a}/{len(SUITE_A)} Suite A correct)"
    )


if __name__ == "__main__":
    sweep()
