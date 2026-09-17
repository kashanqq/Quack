## Repository layout

- `frontend/` — Next.js application (see `frontend/README.md`). Run npm commands there.
- `backend/` — Python/FastAPI backend (see `backend/README.md`). Run uv commands there.
- `deploy/` — local infrastructure. Root `Makefile` wraps common development commands.
- Shared product and architecture documents live at the repository root and in `docs/`.

## graphify

Frontend graph data is in `frontend/graphify-out/`; backend graph data is in `backend/graphify-out/`. Query or update each graph only from its own application folder. Do not merge the two graphs.

The backend graph contains stale absolute paths from an earlier checkout. Rebuild it from `backend/` before relying on queries. If graphify is available, run `graphify update .` after backend code changes.

`backend/ssot/` contains copies of root documents and the only checked-in `memory-architecture-quack.md`; do not assume the copies are hardlinks or that a root memory document exists.
