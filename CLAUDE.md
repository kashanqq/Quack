## Repository layout

- `frontend/` — Next.js app (see `frontend/README.md`). Run npm commands there.
- `backend/` — FastAPI app (see `backend/README.md`). Run uv commands there; unit tests: `uv run --frozen pytest -m "not integration"`.
- `deploy/` — local infrastructure. Root `Makefile` wraps common development commands.
- Keep frontend and backend changes in their own folders; shared docs live at the repository root and in `docs/`:
  - Cross-cutting (both frontend and backend should read): product-logic.md, arch-logic.md, DESIGN.md, tech-stack.md.
  - Backend-only implementation detail (do not load for frontend work — it's internal to the AI/memory layer, not part of the API contract): memory-architecture-quack.md.

