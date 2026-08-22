// FR-5.4: suggested opening questions for a first-time visitor. This is a
// voice agent with no text-input path, so these are read-and-ask-aloud
// prompts, not click-to-send chips -- CITATION_SPEC.md Sec7's demo sequence,
// verbatim. Question 1 was swapped out from 2026-08-21 to 2026-08-22 for a
// workaround phrasing, after the Freelance chunk's own text turned out to
// lack any recency framing for a "most recent role" query to latch onto
// (docs/TEST_PLAN.md Suite A1, docs/DEV_JOURNAL.md's 2026-08-22 entry) --
// restored to the spec's literal wording now that the underlying chunk is
// fixed and reverified at rank 0.
const QUESTIONS = [
  "Tell me about your most recent role.",
  "What did you build with WebRTC?",
  "What's your favourite pizza topping?",
  "You worked at Google, didn't you?",
];

export function SuggestedQuestions() {
  return (
    <div className="suggested-questions">
      <h2>Try asking</h2>
      <ul>
        {QUESTIONS.map((q) => (
          <li key={q}>&ldquo;{q}&rdquo;</li>
        ))}
      </ul>
    </div>
  );
}
