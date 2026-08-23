# Post-evaluation backlog

Ideas raised during the evaluation build that are deliberately **not** being
acted on now — they're about making this a better tool for real interview
use afterward, not about meeting the current evaluation's bar. Captured here
so they aren't lost, and kept separate from `docs/TEST_PLAN.md`/`CLAUDE.md`'s
active to-do list on purpose.

---

## 1. Corpus depth — prepare for real interview use, not just the demo

Raised 2026-08-23: asking the twin to "rate your skills out of 10" got a
correct-per-spec refusal (`no_match` — nothing in the corpus documents a
self-rating), but that's the kind of question a real interviewer might
actually ask. The current corpus (resume + `context.md` + six curated
READMEs) was built for the evaluation's demo questions
(`CITATION_SPEC.md` §7), not for open-ended interview conversation depth.

Before this gets used in a real interview setting, worth revisiting:
- What real interview questions would hit gaps like this one, and whether
  `context.md` should grow to cover them (subjective self-assessments,
  strengths/weaknesses framed for an interview, "why should we hire you"
  style questions grounded in real, owner-approved content — not invented).
- Whether the refusal behavior itself should change for this category, or
  whether the right fix is always "add the missing content," keeping
  ADR-004's anti-hallucination guarantee intact either way.

## 2. Ingest whole GitHub repos, not just READMEs

Currently `ingestion/loaders/github_loader.py` only pulls each curated
repo's README (`DATA_INGESTION.md` Sec7's original scoping — see also
`ARCHITECTURE.md` ADR-002/ADR-003's "curated, not comprehensive" reasoning).
Raised 2026-08-23: for a technical interviewer asking something like "what's
the formula behind this guardrail," the README's high-level description
isn't enough — the real answer lives in the source code.

Would need real design work before building, not just widening the fetch:
- Which files matter (source, not lockfiles/assets/tests-as-noise) and how
  they'd chunk sensibly (READMEs already need boilerplate-stripping; source
  code needs a completely different chunking strategy — functions/classes,
  not `##` headers).
- Whether retrieval quality actually improves with much more corpus volume,
  or whether it dilutes it (this project's own `DATA_INGESTION.md` already
  chose curation over completeness once, for a documented reason).

## 3. More flexibility in the prompt for deep technical answers

Raised 2026-08-23: the current grounding contract (`CITATION_SPEC.md` §5)
is deliberately strict — "answer ONLY using text returned by the tool,"
"never embellish" — which is exactly what makes the anti-hallucination
guarantee (ADR-004) real. But it also means a genuinely technical follow-up
("walk me through the formula") can only ever restate what's literally in
a retrieved chunk, not reason a level deeper the way the owner could
in person.

Any change here is a real trade-off against the project's core premise, not
a tuning knob — worth a deliberate conversation about where the line is
(e.g., allowing more synthesis *across multiple retrieved chunks* in one
answer, vs. allowing the model to add anything not retrieved at all) rather
than loosening rule 2 wholesale.

---

**Status:** none of the above started. Revisit after the current evaluation
work (`CLAUDE.md`'s active to-do list) is done.
