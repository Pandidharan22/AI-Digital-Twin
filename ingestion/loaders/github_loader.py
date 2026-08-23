"""GitHub loader via the plain REST API.

Pulls repo list metadata (name, description, topics, language, stars, updated
date) and README content per repo, using GITHUB_TOKEN (fine-grained PAT,
public-repo read-only) against api.github.com directly.

Deliberately not an MCP client. DATA_INGESTION.md originally framed this as
"the official GitHub MCP server," but that server is a separate process
(Docker/binary) that itself just calls this same REST API underneath -- using
it directly here means one fewer moving part and no Docker dependency to keep
alive through the Phase 5 deployment and GitHub Actions cron, for identical
data. See ARCHITECTURE.md ADR-002/ADR-003 amendment notes for the full
trade-off discussion; this was a deliberate choice, walked through with the
owner, not an oversight.

No LinkedIn scraping happens anywhere in this codebase -- LinkedIn content, if
used, enters only via the owner's official data export as local files (ADR-003,
FR-6.7).

Covers: FR-6.5. See DATA_INGESTION.md Sec7.
"""

import os
import re
from typing import List, Optional

import httpx

from ingestion.types import RawSection

SOURCE_TYPE = "github_repo"

# Curated, not "all public repos" -- DATA_INGESTION.md Sec7: "a bot that cites
# test-repo-3 looks careless." This account has 22 non-fork repos; most are
# coursework/practice projects never mentioned in the resume or context.md.
# These six are the ones the owner's own narrative actually references: the
# four resume projects, the Mockbuilder failure story from context.md, and
# this project itself. Update by hand as the real narrative changes -- not
# meant to silently grow as new repos get created.
CURATED_REPOS = {
    "Heuristic-Self-Reflective-RAG",
    "Job-Hunt-AI",
    "AI-Powered-Loan-Eligibility-Risk-Scoring-System-API",
    "Nexus---Personal-Cloud-and-Automated-Portfolio-Homelab",
    "Mock-Builder",
    "AI-Digital-Twin",
}

# DATA_INGESTION.md Sec3: "strip README boilerplate ... these match many
# queries weakly and crowd out real content."
_SKIP_HEADERS = {
    "installation",
    "install",
    "license",
    "contributing",
    "table of contents",
    "toc",
    "requirements",
}

_BADGE_LINE = re.compile(
    r"^(\[!\[.*?\]\(.*?\)\]\(.*?\)|!\[.*?\]\(.*?\))"
    r"(\s+(\[!\[.*?\]\(.*?\)\]\(.*?\)|!\[.*?\]\(.*?\)))*\s*$"
)


_HR_LINE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")


def _strip_badges(text: str) -> str:
    lines = [
        line
        for line in text.split("\n")
        if not _BADGE_LINE.match(line.strip()) and not _HR_LINE.match(line.strip())
    ]
    return "\n".join(lines)


def _list_repos(username: str, headers: dict) -> List[dict]:
    repos: List[dict] = []
    page = 1
    while True:
        resp = httpx.get(
            f"https://api.github.com/users/{username}/repos",
            params={"per_page": 100, "page": page, "type": "owner"},
            headers=headers,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos


def _fetch_readme(owner: str, repo: str, headers: dict) -> Optional[str]:
    resp = httpx.get(
        f"https://api.github.com/repos/{owner}/{repo}/readme",
        headers={**headers, "Accept": "application/vnd.github.raw"},
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.text


def _split_readme(readme: str) -> List[tuple]:
    """Return [(header_or_None, body), ...]; header is None for the preamble."""
    cleaned = _strip_badges(readme)
    parts = re.split(r"^#{1,2} +", cleaned, flags=re.MULTILINE)
    result = []
    preamble = parts[0].strip()
    if preamble:
        result.append((None, preamble))
    for part in parts[1:]:
        header, _, body = part.partition("\n")
        header = header.strip()
        body = body.strip()
        if header.lower() in _SKIP_HEADERS or not body:
            continue
        result.append((header, body))
    return result


def load() -> List[RawSection]:
    # .strip(): same CI secret-paste hazard as ingest.py's setup_db() -- a
    # trailing newline here would land inside the Authorization header
    # value itself, which httpx/the server would reject outright rather
    # than silently misparse the way psycopg's URL parsing did.
    username = os.environ["GITHUB_USERNAME"].strip()
    token = os.environ["GITHUB_TOKEN"].strip()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    results: List[RawSection] = []
    for repo in _list_repos(username, headers):
        if repo["fork"] or repo["archived"]:
            continue
        if repo["name"] not in CURATED_REPOS:
            continue

        name = repo["name"]
        readme = _fetch_readme(username, name, headers)
        if readme is None:
            continue

        url = repo["html_url"]
        sections = _split_readme(readme)
        if not sections:
            continue

        meta_bits = []
        if repo.get("description"):
            meta_bits.append(repo["description"])
        if repo.get("language"):
            meta_bits.append(f"Written primarily in {repo['language']}.")
        if repo.get("topics"):
            meta_bits.append("Topics: " + ", ".join(repo["topics"]) + ".")
        meta_text = " ".join(meta_bits)

        for i, (header, body) in enumerate(sections):
            if header is None:
                text = f"{meta_text} {body}".strip() if meta_text else body
                section = f"{name} — Overview"
            else:
                text = body
                section = f"{name} — {header}"
            results.append(RawSection(name, SOURCE_TYPE, section, text, url))

    return results
