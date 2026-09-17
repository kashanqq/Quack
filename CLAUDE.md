## Repository layout

- `frontend/` — Next.js app (see frontend/README.md). Run npm commands from this folder.
- `backend/` — server side, not started yet (see backend/README.md).
- Keep frontend and backend changes in their own folders; shared docs live in the root:
  - Cross-cutting (both frontend and backend should read): product-logic.md, arch-logic.md, DESIGN.md, tech-stack.md.
  - Backend-only implementation detail (do not load for frontend work — it's internal to the AI/memory layer, not part of the API contract): memory-architecture-quack.md.

## graphify

The frontend has a knowledge graph at frontend/graphify-out/ with god nodes, community structure, and cross-file relationships. Run graphify commands from `frontend/`.

Once backend/ development starts, it must get its own separate graph at backend/graphify-out/, built and run from `backend/`. Never run graphify from the repo root, and never merge the frontend and backend graphs — they are unrelated layers (React UI vs. server code) and mixing them would pollute community detection and query results on both sides.

The backend graph also includes the root SSoT docs (arch-logic.md, product-logic.md, DESIGN.md, tech-stack.md, memory-architecture-quack.md) for richer prompting context, via `backend/ssot/` — a folder of Windows hardlinks (not copies) to the root files, so there is no drift and no second source of truth.

**Every SSoT doc lives in the repo root first.** Never create a file directly inside `backend/ssot/` — it's gitignored, so anything placed there only (not hardlinked from root) is untracked and will silently vanish. Always add new SSoT docs to the root, then hardlink them into `backend/ssot/`.

**`backend/ssot/` only ever hardlinks the 5 root SSoT docs backend actually needs** (the 4 cross-cutting docs + memory-architecture-quack.md) — never frontend-only files. `frontend/` gets no `ssot/` folder and no hardlink to `memory-architecture-quack.md`: it isn't part of the API contract and must never be exposed to frontend, hardlinked or otherwise. Frontend reads the 4 cross-cutting root docs directly via relative links (e.g. `../arch-logic.md`) when needed — it doesn't build an ssot-style ingestion folder because its graphify graph only indexes `frontend/` itself, unlike backend's graph which pulls in root docs for prompting context.

Hardlinks don't survive `git clone`/checkout, so on a fresh clone (or after adding a new root SSoT doc) recreate them:
```powershell
New-Item -ItemType Directory -Force -Path backend/ssot | Out-Null
New-Item -ItemType HardLink -Path backend/ssot/arch-logic.md -Target arch-logic.md -Force
New-Item -ItemType HardLink -Path backend/ssot/product-logic.md -Target product-logic.md -Force
New-Item -ItemType HardLink -Path backend/ssot/DESIGN.md -Target DESIGN.md -Force
New-Item -ItemType HardLink -Path backend/ssot/tech-stack.md -Target tech-stack.md -Force
New-Item -ItemType HardLink -Path backend/ssot/memory-architecture-quack.md -Target memory-architecture-quack.md -Force
```

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists, from within the relevant folder (`frontend/` or `backend/`). Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` from the same folder (`frontend/` or `backend/`) to keep that folder's graph current (AST-only, no API cost).
