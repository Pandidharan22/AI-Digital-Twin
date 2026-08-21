"""Centralized configuration for the Token Service.

Scoped deliberately narrow -- LiveKit connection details only. Kept separate
from agent/config.py so this service can never accidentally import the
Gemini/Supabase secrets it has no business holding (see api/main.py's own
docstring: "Never holds a database or LLM credential").

Covers: NFR-6.1, NFR-6.2.
"""

import os

from dotenv import load_dotenv

load_dotenv()

LIVEKIT_URL = os.environ["LIVEKIT_URL"]
LIVEKIT_API_KEY = os.environ["LIVEKIT_API_KEY"]
LIVEKIT_API_SECRET = os.environ["LIVEKIT_API_SECRET"]

# Comma-separated list -- lets the deployed frontend's real origin and the
# local dev origin both work at once, rather than one replacing the other on
# every environment switch. Whitespace around entries is stripped.
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173").split(",")
    if origin.strip()
]
