"""Parses agent/main.py's structured "turn metrics" log lines and reports
median/p95 per stage, per TEST_PLAN.md Sec3 / NFR-1.

Reads whatever log source the worker's structured JSON logging landed in --
a captured `flyctl logs` stream, or a local worker.log file -- and pulls out
every line whose "message" field matches the turn-metrics format
agent/main.py's `_on_conversation_item` handler emits:

    [room=<name>] turn metrics: transcription_delay=<f> end_of_turn_delay=<f>
    llm_ttft=<f> tts_ttfb=<f> e2e_latency=<f>

Each field is None on turns where it doesn't apply (e.g. llm_ttft/tts_ttfb/
e2e_latency are only set on assistant turns; transcription_delay/
end_of_turn_delay only on user turns; e2e_latency is also None on the
greeting, which has no preceding user turn to measure from) -- those None
values are dropped per-field rather than treated as zero, so the median/p95
for each stage only reflects turns where that stage actually ran.

Usage:
    uv run python -m tests.parse_latency_log <logfile> [--room ROOM_NAME]

--room filters to one room's lines, which matters against a live capture
that may contain interleaved traffic from other concurrent visitors.
"""

import argparse
import json
import re
import statistics
import sys

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

LINE_RE = re.compile(
    r"\[room=(?P<room>[^\]]+)\] turn metrics: "
    r"transcription_delay=(?P<transcription_delay>\S+) "
    r"end_of_turn_delay=(?P<end_of_turn_delay>\S+) "
    r"llm_ttft=(?P<llm_ttft>\S+) "
    r"tts_ttfb=(?P<tts_ttfb>\S+) "
    r"e2e_latency=(?P<e2e_latency>\S+)"
)

FIELDS = ["transcription_delay", "end_of_turn_delay", "llm_ttft", "tts_ttfb", "e2e_latency"]


def _read_lines(path: str) -> list[str]:
    """flyctl logs and PowerShell redirection both land in this repo at
    different encodings depending on how they were captured -- try utf-8
    first (flyctl's own output) and fall back to utf-16 (seen from a
    PowerShell `>` redirect during local testing) rather than assuming one.
    """
    for encoding in ("utf-8", "utf-16"):
        try:
            with open(path, encoding=encoding) as f:
                return f.readlines()
        except UnicodeError:
            continue
    raise ValueError(f"could not decode {path} as utf-8 or utf-16")


def _percentile(values: list[float], pct: float) -> float:
    s = sorted(values)
    idx = min(len(s) - 1, max(0, round(pct / 100 * (len(s) - 1))))
    return s[idx]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("logfile")
    parser.add_argument("--room", default=None, help="filter to one room name")
    args = parser.parse_args()

    per_field: dict[str, list[float]] = {f: [] for f in FIELDS}
    matched_lines = 0

    for raw_line in _read_lines(args.logfile):
        line = ANSI_RE.sub("", raw_line).strip()
        if not line:
            continue
        # `flyctl logs` prefixes each JSON payload with a colored
        # "<timestamp> app[id] region [level]" header -- the JSON object
        # itself starts at the line's first "{". Local worker.log captures
        # (no flyctl header) are plain JSON and match the same way, since
        # their first "{" is index 0. Tolerate non-JSON noise (build
        # output, warnings) rather than aborting the whole parse.
        brace = line.find("{")
        try:
            message = json.loads(line[brace:]).get("message", "") if brace != -1 else ""
        except json.JSONDecodeError:
            message = line
        m = LINE_RE.search(message)
        if not m:
            continue
        if args.room and m.group("room") != args.room:
            continue
        matched_lines += 1
        for field in FIELDS:
            raw = m.group(field)
            if raw != "None":
                per_field[field].append(float(raw))

    if matched_lines == 0:
        print("No turn-metrics lines matched.", file=sys.stderr)
        sys.exit(1)

    print(f"Matched {matched_lines} turn-metrics log lines"
          f"{f' for room={args.room}' if args.room else ''}.\n")
    print(f"{'Stage':<22}{'n':>4}{'median':>10}{'p95':>10}")
    for field in FIELDS:
        values = per_field[field]
        if not values:
            print(f"{field:<22}{'0':>4}{'--':>10}{'--':>10}")
            continue
        median = statistics.median(values)
        p95 = _percentile(values, 95)
        print(f"{field:<22}{len(values):>4}{median * 1000:>9.0f}ms{p95 * 1000:>9.0f}ms")


if __name__ == "__main__":
    main()
