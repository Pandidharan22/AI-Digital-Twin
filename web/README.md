# Frontend

React (Vite + TypeScript), built on `@livekit/components-react`. Fetches a
token from the Token Service (`api/main.py`), connects to the LiveKit room,
renders agent audio, and listens on the `citations` data-channel topic to
render source cards keyed by `turn_id` — see `src/components/CitationsPanel.tsx`
and `docs/CITATION_SPEC.md` Sec4 for the wire contract.

Scoped deliberately minimal (Phase 3 Day 4, per `docs/BUILD_PLAN.md`): room
connection, mic toggle, and the citations panel only. Connection-state UI
(FR-5.2), a mic-permission explainer (FR-1.5), a transcript panel (FR-5.1),
suggested-question chips (FR-5.4), mobile layout, and visual polish are all
explicit Phase 4 scope, not built here.

## Run locally

```bash
cp .env.example .env.local   # only needed if the Token Service isn't on :8000
npm install
npm run dev
```

Requires the Token Service (`uv run uvicorn api.main:app --port 8000`) and
the agent worker (`uv run python -m livekit.agents start agent/main.py`)
both running.
