"""Environment variable access for ingestion secrets.

Centralizes a lesson learned the hard way against the real GitHub Actions
ingestion cron (docs/DEV_JOURNAL.md's 2026-08-23 entries): secrets pasted
into GitHub's repo-secrets UI can carry whitespace -- not just trailing,
but embedded in the *middle* of the value, from a long token or URL that
visually wrapped across lines wherever it was copied from. This never
shows up in local dev, since python-dotenv already strips .env values on
parse; GitHub injects a secret into os.environ byte-for-byte as stored,
with no such trimming. A plain .strip() only fixed the first failure
(a trailing newline in DATABASE_URL) -- the second (an illegal header
value from GITHUB_TOKEN) proved the whitespace wasn't always just at the
ends.

A real credential -- a token, a URL, a Postgres connection string -- never
legitimately contains whitespace anywhere in it, so removing all of it,
wherever it is, is always safe and never lossy for a well-formed value.
"""

import os


def env_secret(name: str) -> str:
    """os.environ[name] with every whitespace character stripped out,
    wherever it appears -- not just leading/trailing. See module docstring."""
    return "".join(os.environ[name].split())
