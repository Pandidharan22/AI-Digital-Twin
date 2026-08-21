// FR-5.4: suggested opening questions for a first-time visitor. This is a
// voice agent with no text-input path, so these are read-and-ask-aloud
// prompts, not click-to-send chips -- CITATION_SPEC.md Sec7's demo sequence,
// with question 1 swapped for a phrasing that actually retrieves correctly
// (see docs/TEST_PLAN.md's A1 known-gap note: "What's your most recent
// role?" fails to rank the Freelance chunk in the top-4 at every tuned
// threshold; "What did you work on at your freelance role?" -- TEST_PLAN's
// own A2 -- targets the identical source and verified as a top-1 hit).
const QUESTIONS = [
  "What did you work on at your freelance role?",
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
