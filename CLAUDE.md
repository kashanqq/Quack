## Repository layout

- `frontend/` — Next.js app (see `frontend/README.md`). Run npm commands there.
- `backend/` — FastAPI app (see `backend/README.md`). Run uv commands there; unit tests: `uv run --frozen pytest -m "not integration"`.
- `deploy/` — local infrastructure. Root `Makefile` wraps common development commands.
- Keep frontend and backend changes in their own folders; shared docs live at the repository root and in `docs/`:
  - Cross-cutting (both frontend and backend should read): product-logic.md, arch-logic.md, DESIGN.md, tech-stack.md.
  - Backend-only implementation detail (do not load for frontend work — it's internal to the AI/memory layer, not part of the API contract): memory-architecture-quack.md.

## backend/ssot

`backend/ssot/` contains copies of root documents and the only checked-in `memory-architecture-quack.md`; do not assume the copies are hardlinks or that a root memory document exists.

## Phase 2 backend coordination

- Source contracts: `backend/docs/tz/00-contracts.md` and `docs/tz/phase2/00-contracts-phase2.md` (§2, §6–§7, §9.3). The Phase 2 contract is currently supplied separately and must be added at that path for the team.
- Ownership: `backend/app/apply/*`, `knowledge/*`, `sets/*`, `matching/*`, `tasks/*`, and graph internals belong to B1; `backend/app/roadmap/*`, LLM and agents belong to B2; `backend/app/api/*`, `db/*`, `events/*`, and platform infrastructure belong to B3, as detailed in the Phase 2 ownership table. B3 creates only the agreed `apply/*` and `roadmap/*` skeleton stubs.
- Frozen shared contracts: `backend/app/schemas/*`, `backend/app/events/dispatch.py`, `backend/app/events/handlers.py`, and `backend/app/keys.py`.
- To change a frozen contract, record the need in `docs/sync-log.md`, sync with the team, have the owner change it, then rebase the other branches.
- Keep the contract's `tz-executor` subtask workflow when the skill is available; do not assume its file is present in this checkout.
