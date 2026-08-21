"""FastAPI token service.

Exposes POST /token (mints a short-lived LiveKit access token, unique room name
per visitor, expiry <=15 min) and GET /health (also the keep-warm ping target).
Never holds a database or LLM credential -- only the LiveKit API key/secret,
loaded from api/config.py, deliberately kept separate from agent/config.py.

Covers: FR-1.1-1.3, NFR-3.4.
"""

import uuid
from datetime import timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from livekit import api as lk_api
from pydantic import BaseModel

from . import config

app = FastAPI(title="Voice Twin Token Service")

# Dev-only origin by default (api/config.py); must be tightened to the real
# deployed frontend origin before Phase 5 -- flagged there, not silently left
# permissive.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class TokenResponse(BaseModel):
    token: str
    url: str
    room: str


@app.post("/token", response_model=TokenResponse)
def create_token() -> TokenResponse:
    """Mint a token for a brand-new visitor session.

    Every call gets its own room and participant identity (FR-1.2) -- no
    visitor ever joins another's room. can_publish_data=True is required for
    nothing on the token-issuing side itself, but the agent worker publishes
    citations over the data channel into this room, so the grant needs to
    already be broad enough to receive them.
    """
    room_name = f"twin-{uuid.uuid4().hex[:8]}"
    identity = f"visitor-{uuid.uuid4().hex[:8]}"

    grants = lk_api.VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True,
    )
    token = (
        lk_api.AccessToken(config.LIVEKIT_API_KEY, config.LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(grants)
        .with_ttl(timedelta(minutes=15))  # FR-1.3
        .to_jwt()
    )

    return TokenResponse(token=token, url=config.LIVEKIT_URL, room=room_name)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
