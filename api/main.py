"""FastAPI token service.

Exposes POST /token (mints a short-lived LiveKit access token, unique room name
per visitor, expiry <=15 min) and GET /health (also the keep-warm ping target).
Never holds a database or LLM credential -- only the LiveKit API key/secret,
loaded from api/config.py, deliberately kept separate from agent/config.py.

POST /token is rate-limited (TEST_PLAN.md Sec6) -- it's unauthenticated by
design (any visitor needs a token before they can do anything else), and each
call provisions a real LiveKit room plus dispatches a real agent job (Fly.io
compute, Gemini/Deepgram API calls). Without a limit, that's an open door to
running up real usage costs and burning through Gemini's free-tier RPM budget
with no login or CAPTCHA in the way.

Covers: FR-1.1-1.3, NFR-3.4.
"""

import uuid
from datetime import timedelta

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from livekit import api as lk_api
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from . import config

app = FastAPI(title="Voice Twin Token Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.FRONTEND_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# get_remote_address reads request.client.host, which is only the real
# visitor IP -- rather than the address of whatever reverse proxy the
# platform (Render) sits behind -- because uvicorn's own
# ProxyHeadersMiddleware rewrites it from X-Forwarded-For. That middleware
# only trusts a proxy in FORWARDED_ALLOW_IPS (default "127.0.0.1", confirmed
# against the installed uvicorn's actual source, not assumed); render.yaml
# sets it to "*" for this deployment specifically because Render's load
# balancer is the *only* path a public request can take to reach this
# service -- there's no direct route that would let an outside caller spoof
# X-Forwarded-For past it. Without that env var, every visitor would appear
# to share one IP (the proxy's), and the limit below would apply site-wide
# instead of per-visitor.
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class TokenResponse(BaseModel):
    token: str
    url: str
    room: str


@app.post("/token", response_model=TokenResponse)
@limiter.limit("5/minute;30/hour")
def create_token(request: Request) -> TokenResponse:
    """Mint a token for a brand-new visitor session.

    Every call gets its own room and participant identity (FR-1.2) -- no
    visitor ever joins another's room. can_publish_data=True is required for
    nothing on the token-issuing side itself, but the agent worker publishes
    citations over the data channel into this room, so the grant needs to
    already be broad enough to receive them.

    Rate-limited to 5/minute and 30/hour per client IP -- generous for a real
    visitor reloading a flaky connection a few times, tight against a script
    minting rooms in a loop. `request` is otherwise unused here; slowapi's
    `@limiter.limit` decorator requires it as a named parameter to find the
    request it's rate-limiting (confirmed from the installed package's own
    source, not assumed from its README).
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
