"""FastAPI token service.

Exposes POST /token (mints a short-lived LiveKit access token, unique room name
per visitor, expiry <=15 min) and GET /health (also the keep-warm ping target).
Never holds a database or LLM credential -- only the LiveKit API key/secret.

Covers: FR-1.1-1.3, NFR-3.4.
"""
