# Agent worker image. Built from repo root: docker build -f agent/Dockerfile .
# Not a web service -- this process connects outbound to LiveKit Cloud and
# waits for dispatch (see docs/DEPLOYMENT.md Sec2). No inbound port needs to
# be publicly reachable; AgentServer's own :8081 is job-coordination/health
# only, exposed for Fly's internal checks, not the public internet.

FROM python:3.11-slim

# Astral's official pattern for pulling the uv binary into another image
# without a separate install step.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Dependencies first, source after -- so an app-code-only change doesn't
# invalidate the (slow) dependency-install layer.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# The default PyPI Linux torch wheel bundles CUDA libraries and is 3-4x
# larger than needed -- this project only ever runs the embedding model on
# CPU (bge-small-en-v1.5, 384 dims; see CLAUDE.md's stack table). Swap in
# the CPU-only build after the locked sync so uv.lock itself stays
# untouched (and the local Windows dev environment, which already resolves
# a CPU-only wheel on its own platform, is unaffected).
RUN uv pip install torch --index-url https://download.pytorch.org/whl/cpu

# Only the worker's actual runtime code -- not ingestion/'s loaders,
# chunker, or offline scripts, which this process never imports (confirmed
# by reading agent/retrieval.py's own import: just ingestion.embedder).
COPY agent/ ./agent/
COPY ingestion/__init__.py ./ingestion/__init__.py
COPY ingestion/embedder.py ./ingestion/embedder.py

ENV PATH="/app/.venv/bin:$PATH"

# Bakes Silero VAD's model file into the image at build time instead of
# fetching it on first run -- keeps cold start off the network dependency
# DEPLOYMENT.md Sec4's <15s target would otherwise be exposed to.
RUN python -m livekit.agents download-files

# Same reasoning, for bge-small-en-v1.5: SentenceTransformer's constructor
# hits Hugging Face Hub over the network by default (unauthenticated, so
# slow/rate-limited -- confirmed live on Fly.io, 2026-08-21: this alone
# added ~19s to every cold job-runner start, the actual cause of repeated
# initialize_process_timeout failures that looked like a CPU problem but
# weren't -- weight loading itself is near-instant once the files are
# local). Baking the model into the image and forcing offline mode at
# runtime (HF_HUB_OFFLINE below) removes the network round-trip entirely.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"
ENV HF_HUB_OFFLINE=1

CMD ["python", "-m", "livekit.agents", "start", "agent/main.py"]
