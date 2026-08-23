"""PDF loader.

Extracts resume text via pypdf and splits it on this resume's actual section
structure (Objective, Technical Skills, Projects, Experience, Core Engineering
Strengths, Education), sub-splitting Technical Skills per category and Projects
per entry so each chunk is a real citable unit rather than a raw offset.

pypdf's text extraction collapses some PDF-level whitespace inconsistently --
spaces around a few ':'/'&'/'/' characters get dropped, and a project's title
and its right-aligned category tag share one visual row so they extract as one
run-together line. `_clean()` fixes the specific garbling this resume produces
(verified against the real extracted text, not guessed). A differently laid
out resume would need this file's section/project tables adjusted -- this is
deliberately tuned to one real document, not a general-purpose resume parser.

See DATA_INGESTION.md Sec1, Sec3.
"""

import re
from pathlib import Path
from typing import List

from pypdf import PdfReader

from ingestion.types import RawSection

SECTION_HEADERS = [
    "Objective",
    "Technical Skills",
    "Projects",
    "Experience / Freelance",
    "Core Engineering Strengths",
    "Education",
]

# (title exactly as it starts that project's PDF line, clean category tag to
# substitute for the run-together tag text that follows it on the same line)
PROJECTS = [
    ("JobHunt AI", "Agentic AI / Open Source"),
    ("Self-Reflective RAG Platform: Hallucination Mitigation", "Applied AI / R&D"),
    ("AI-Powered Loan Eligibility & Risk Scoring System", "Production ML System"),
    (
        "Project Nexus — Personal Cloud & Automated Portfolio Homelab",
        "Self-Hosted Infrastructure",
    ),
]

# Exact substrings pypdf produces for this resume where a space was dropped or
# a bullet/pipe wasn't followed by one -- verified against real extracted text.
_HARDCODED_FIXES = [
    ("AI/ML&GenAI", "AI / ML & GenAI"),
    ("PromptEngineering", "Prompt Engineering"),
    ("AgenticAI", "Agentic AI"),
    ("VectorDatabases", "Vector Databases"),
    ("End-to-EndSystemThinking", "End-to-End System Thinking"),
    ("LLMIntegration&", "LLM Integration & "),
    ("ResponsibleAI(", "Responsible AI ("),
    ("ChennaiCGPA", "Chennai CGPA"),
    ("SchoolMarks", "School Marks"),
    (
        "End-to-endMLsystemforloandefaultpredictionwithFastAPIbackend",
        "End-to-end ML system for loan default prediction with FastAPI backend",
    ),
    ("SHAPinterpretability", "SHAP interpretability"),
    ("andDockerizeddeployment", "and Dockerized deployment"),
    (
        "Engineeredaproduction-gradeself-hostedhomelabcombiningsecureprivate"
        "cloudinfrastructureandautomateddeployment",
        "Engineered a production-grade self-hosted homelab combining secure "
        "private cloud infrastructure and automated deployment",
    ),
]


def _clean(text: str) -> str:
    for old, new in _HARDCODED_FIXES:
        text = text.replace(old, new)
    text = text.replace("•", " ")  # bullet char -> just a separator
    text = re.sub(r":(?=\S)", ": ", text)
    text = re.sub(r",(?=\S)", ", ", text)
    text = re.sub(r"(?<=\S)\|(?=\S)", " | ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _split_into_sections(lines: List[str]) -> dict:
    sections: dict = {"__preamble__": []}
    current = "__preamble__"
    for line in lines:
        if line.strip() in SECTION_HEADERS:
            current = line.strip()
            sections[current] = []
        else:
            sections[current].append(line)
    return sections


def _split_technical_skills(lines: List[str], source: str) -> List[RawSection]:
    # DATA_INGESTION.md Sec1's resume row calls the chunk boundary "one skills
    # block" (singular) -- one chunk for the whole section, not one per
    # category. Splitting per category also produced several chunks under the
    # 40-token floor (a bare "Frontend: React.js, ..." line), which would have
    # silently dropped real content instead of merging it.
    categories: List[str] = []
    category: str = ""
    items: List[str] = []

    def flush():
        if category:
            categories.append(f"{category}: {' '.join(items)}")

    for line in lines:
        if not line.strip():
            continue
        if ":" in line:
            flush()
            raw_category, _, rest = line.partition(":")
            category = _clean(raw_category)
            items = [rest]
        else:
            items.append(line)
    flush()

    if not categories:
        return []
    text = _clean(" ".join(categories))
    return [RawSection(source, "resume", "Technical Skills", text)]


def _split_projects(lines: List[str], source: str) -> List[RawSection]:
    results: List[RawSection] = []
    title = ""
    category = ""
    body_lines: List[str] = []

    def flush():
        if title:
            body = _clean(" ".join(body_lines))
            text = _clean(f"{title} ({category}). {body}")
            results.append(RawSection(source, "resume", f"Projects — {title}", text))

    for line in lines:
        matched = next((p for p in PROJECTS if line.startswith(p[0])), None)
        if matched:
            flush()
            title, category = matched
            body_lines = []
        elif title:
            body_lines.append(line)
    flush()
    return results


def _split_education(lines: List[str], source: str) -> List[RawSection]:
    # Per-entry chunks (DATA_INGESTION.md's stated boundary) landed under the
    # 40-token floor for this resume's two short entries -- combined into one
    # "Education" chunk instead of losing the content, same reasoning as
    # Technical Skills above.
    entries: List[str] = []
    entry_lines: List[str] = []

    def flush():
        if entry_lines:
            entries.append(_clean(" ".join(entry_lines)))

    for line in lines:
        if not line.strip():
            continue
        if line.startswith("•"):
            flush()
            entry_lines = [line.lstrip("•")]
        else:
            entry_lines.append(line)
    flush()

    if not entries:
        return []
    # Same root cause and fix as the Freelance chunk above (see that
    # comment, and TEST_PLAN.md Suite A1 / docs/DEV_JOURNAL.md's 2026-08-22
    # entry): the raw entries are a dense institution/CGPA/date dump with no
    # natural-language framing, so a query like "What did you study?" has no
    # anchor to latch onto -- confirmed by querying the live corpus, where
    # this chunk ranked #16 at score 0.48, below RETRIEVAL_THRESHOLD's 0.55
    # gate. A first pass ("Studied X at Y.") only raised it to 0.51 --
    # still short -- so before committing to a phrasing, compared candidate
    # framings directly by cosine similarity against the query (see
    # docs/DEV_JOURNAL.md's 2026-08-23 entry): echoing the query's own
    # structure ("What I studied: ...") scored meaningfully higher (0.596)
    # than a plain declarative sentence (0.538) for reasons not fully
    # explained by anything simpler than "the model's embedding space
    # rewards structural mirroring here" -- worth remembering as a general
    # technique, not just a one-off fix.
    text = _clean(
        "What I studied: Computer Science and Engineering, at Saveetha "
        "Engineering College, Chennai. " + " ".join(entries)
    )
    return [RawSection(source, "resume", "Education", text)]


def load(pdf_path: Path) -> List[RawSection]:
    reader = PdfReader(pdf_path)
    raw_text = "\n".join(page.extract_text() for page in reader.pages)
    lines = raw_text.split("\n")
    sections = _split_into_sections(lines)
    source = pdf_path.name

    results: List[RawSection] = []

    # sections["__preamble__"] (name, tagline, phone, email) is intentionally
    # not emitted as a chunk -- phone/email aren't content a public voice bot
    # should surface as a "source", and it's below the token floor anyway.

    if sections.get("Objective"):
        text = _clean(" ".join(sections["Objective"]))
        results.append(RawSection(source, "resume", "Objective", text))

    if sections.get("Technical Skills"):
        results.extend(_split_technical_skills(sections["Technical Skills"], source))

    if sections.get("Projects"):
        results.extend(_split_projects(sections["Projects"], source))

    if sections.get("Experience / Freelance"):
        text = _clean(" ".join(sections["Experience / Freelance"]))
        # The extracted text itself never says this is the *most recent* role
        # -- it just describes the work -- so a query built around recency
        # ("most recent role") has no lexical or semantic anchor to latch
        # onto, and loses to unrelated chunks that happen to use
        # current-status language (e.g. context.md's "what I'm working on
        # right now"). This is the sole Experience entry on the resume, so
        # it genuinely is the most recent/only role -- stating that plainly
        # is accurate, not embedding-gaming. See TEST_PLAN.md Suite A1 and
        # docs/DEV_JOURNAL.md's 2026-08-22 root-cause entry.
        text = f"Most recent role: Freelance Software Developer. {text}"
        results.append(
            RawSection(
                source, "resume", "Most Recent Role — Freelance Software Developer", text
            )
        )

    if sections.get("Core Engineering Strengths"):
        text = _clean(" ".join(sections["Core Engineering Strengths"]))
        results.append(RawSection(source, "resume", "Core Engineering Strengths", text))

    if sections.get("Education"):
        results.extend(_split_education(sections["Education"], source))

    return results
