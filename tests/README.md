# Tests

Run everything: `uv run pytest`. Fast, infra-free subset only:
`uv run pytest -m "not integration"`.

- **`test_citations.py`** -- unit tests for `agent/citations.py`'s data-channel
  payload contract (`CITATION_SPEC.md` Sec4). `get_job_context()` is
  monkeypatched, so these never touch a real LiveKit room; sub-second.
- **`test_retrieval_suite.py`** -- integration tests for `agent/retrieval.py`'s
  Suite A / Suite B contract (`docs/TEST_PLAN.md` Sec1), run against the real,
  live Supabase corpus through the actual production `retrieve()` function.
  Needs `DATABASE_URL`/`SUPABASE_*` in `.env`; takes ~30s (local embedding +
  real network calls per question). Three cases are `xfail(strict=True)` --
  real, understood, currently-accepted retrieval gaps, not oversights; see
  the file's own docstring and `docs/DEV_JOURNAL.md`'s 2026-08-23 entry for
  what each one is and why it's not fixed.
- **`measure_latency.py`** / **`parse_latency_log.py`** -- not pytest tests;
  a load-generation + log-analysis pair for `TEST_PLAN.md` Sec3's latency
  measurement. Run directly: `uv run python -m tests.measure_latency`.

Broader acceptance-test automation (the full `TEST_PLAN.md` suite, UX tests,
the silent-observation test) is manual, per Phase 6 (P6.1) -- not everything
in that document is realistically pytest-automatable (e.g. "hand the link to
someone who's never seen it and watch").
