"""GitHub loader via the official GitHub MCP server.

Pulls repo list metadata (name, description, topics, language, stars, updated
date) and README content per repo. Filters out forks, archived repos, and repos
with no README. Auth via GITHUB_TOKEN (fine-grained PAT, public-repo read-only).

No LinkedIn scraping happens anywhere in this codebase -- LinkedIn content, if
used, enters only via the owner's official data export as local files (ADR-003,
FR-6.7).

Covers: FR-6.5, FR-6.7. See DATA_INGESTION.md Sec7.
"""
