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
    results: List[RawSection] = []
    category: str = ""
    items: List[str] = []

    def flush():
        if category:
            text = _clean(f"{category}: {' '.join(items)}")
            results.append(
                RawSection(source, "resume", f"Technical Skills — {category}", text)
            )

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
    return results


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
    results: List[RawSection] = []
    entry_lines: List[str] = []

    def flush():
        if entry_lines:
            text = _clean(" ".join(entry_lines))
            label = re.split(r"CGPA|Marks", text)[0].strip().rstrip(",")
            results.append(RawSection(source, "resume", f"Education — {label}", text))

    for line in lines:
        if not line.strip():
            continue
        if line.startswith("•"):
            flush()
            entry_lines = [line.lstrip("•")]
        else:
            entry_lines.append(line)
    flush()
    return results


def load(pdf_path: Path) -> List[RawSection]:
    reader = PdfReader(pdf_path)
    raw_text = "\n".join(page.extract_text() for page in reader.pages)
    lines = raw_text.split("\n")
    sections = _split_into_sections(lines)
    source = pdf_path.name

    results: List[RawSection] = []

    preamble = _clean(" ".join(sections.get("__preamble__", [])))
    if preamble:
        results.append(RawSection(source, "resume", "Contact Info", preamble))

    if sections.get("Objective"):
        text = _clean(" ".join(sections["Objective"]))
        results.append(RawSection(source, "resume", "Objective", text))

    if sections.get("Technical Skills"):
        results.extend(_split_technical_skills(sections["Technical Skills"], source))

    if sections.get("Projects"):
        results.extend(_split_projects(sections["Projects"], source))

    if sections.get("Experience / Freelance"):
        text = _clean(" ".join(sections["Experience / Freelance"]))
        results.append(
            RawSection(source, "resume", "Experience — Freelance Software Developer", text)
        )

    if sections.get("Core Engineering Strengths"):
        text = _clean(" ".join(sections["Core Engineering Strengths"]))
        results.append(RawSection(source, "resume", "Core Engineering Strengths", text))

    if sections.get("Education"):
        results.extend(_split_education(sections["Education"], source))

    return results
