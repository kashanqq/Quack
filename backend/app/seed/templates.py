"""Load task templates into Neo4j and Postgres cache — memory-architecture §3.1.

Each template lives in its own JSON file under data/templates/<exam>/<area>/<name>.json.
Writes:
  - Neo4j: TaskTemplate node, TESTS → Skill, TRAPS → Misconception edges
  - Postgres: templates cache via repo.tasks.upsert_template (B3)

Validates every template with validate_template before writing.

Source: 20-B1.md §6.3.
"""

from __future__ import annotations

import json
from pathlib import Path

from neo4j import AsyncDriver
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repo import tasks as tasks_repo
from app.graph import labels as L
from app.schemas.tasks import TaskTemplateSpec
from app.seed.skills import SeedError, SeedReport
from app.tasks.generate import validate_template


async def seed_templates(
    driver: AsyncDriver,
    path: Path,
    session: AsyncSession | None = None,
) -> SeedReport:
    """Walk data/templates/**/*.json and load each template.

    If session is given, also cache the spec in Postgres (repo.tasks.upsert_template).
    If session is None, only Neo4j is written (useful for --validate).
    """
    report = SeedReport()
    files = sorted(path.rglob("*.json"))
    if not files:
        raise SeedError(str(path), "no template files found")

    specs: list[TaskTemplateSpec] = []
    for path in files:
        raw = json.loads(path.read_text(encoding="utf-8"))
        try:
            spec = TaskTemplateSpec.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            raise SeedError(str(path), str(exc)) from exc

        errors = validate_template(spec)
        if errors:
            raise SeedError(str(path), "; ".join(errors))

        specs.append(spec)

    # ---- Neo4j ----
    async with driver.session() as session_neo:
        for spec in specs:
            # check skill exists
            rec = await (
                await session_neo.run(
                    f"MATCH (s:{L.SKILL} {{id: $id}}) RETURN s.id AS id",
                    id=spec.skill_id,
                )
            ).single()
            if rec is None:
                raise SeedError(
                    spec.id, f"skill {spec.skill_id} not found"
                )

            await session_neo.run(
                f"""
                MERGE (t:{L.TASK_TEMPLATE} {{id: $id}})
                SET t.exam_id = $exam_id, t.type = $type,
                    t.difficulty = $difficulty,
                    t.tags = $tags,
                    t.time_reference_sec = $time_reference_sec,
                    t.kind = $kind
                """,
                id=spec.id,
                exam_id=spec.exam_id,
                type=spec.type,
                difficulty=spec.difficulty,
                tags=spec.tags,
                time_reference_sec=spec.time_reference_sec,
                kind=spec.kind,
            )
            report.nodes += 1

            await session_neo.run(
                f"""
                MATCH (t:{L.TASK_TEMPLATE} {{id: $id}})
                MATCH (s:{L.SKILL} {{id: $skill_id}})
                MERGE (t)-[:{L.TESTS} {{weight: 1.0}}]->(s)
                """,
                id=spec.id,
                skill_id=spec.skill_id,
            )
            report.rels += 1

            # TRAPS edges (distractor → misconception), one per (template, key, misc)
            trap_pairs = _collect_trap_pairs(spec)
            for distractor_key, misc_id in trap_pairs:
                if misc_id is None:
                    continue
                # check misconception exists
                rec = await (
                    await session_neo.run(
                        f"MATCH (m:{L.MISCONCEPTION} {{id: $id}}) RETURN m.id AS id",
                        id=misc_id,
                    )
                ).single()
                if rec is None:
                    raise SeedError(
                        spec.id, f"misconception {misc_id} not found"
                    )
                await session_neo.run(
                    f"""
                    MATCH (t:{L.TASK_TEMPLATE} {{id: $id}})
                    MATCH (m:{L.MISCONCEPTION} {{id: $misc}})
                    MERGE (t)-[r:{L.TRAPS} {{distractor_key: $key}}]->(m)
                    """,
                    id=spec.id,
                    misc=misc_id,
                    key=distractor_key,
                )
                report.rels += 1

    # ---- Postgres cache ----
    if session is not None:
        for spec in specs:
            await tasks_repo.upsert_template(session, spec)

    return report


def _collect_trap_pairs(spec: TaskTemplateSpec) -> list[tuple[str, str | None]]:
    """Return [(distractor_key, misconception_id)] from all distractor sources."""
    pairs: list[tuple[str, str | None]] = []
    for d in spec.distractors:
        pairs.append((d.expr, d.misconception_id))
    for t in spec.trap_answers or []:
        pairs.append((t.expr, t.misconception_id))
    for o in spec.omission_traps or []:
        pairs.append((o.omit, o.misconception_id))
    return pairs




def validate_templates(path: Path) -> None:
    """Validate all template files under path. Raises SeedError on first bad one.

    Called by scripts/seed.py --validate.
    """
    if path.is_dir():
        files = sorted(path.rglob("*.json"))
    else:
        files = [path]
    if not files:
        raise SeedError(str(path), "no template files found")
    for f in files:
        raw = json.loads(f.read_text(encoding="utf-8"))
        try:
            spec = TaskTemplateSpec.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            raise SeedError(str(f), str(exc)) from exc
        errors = validate_template(spec)
        if errors:
            raise SeedError(str(f), "; ".join(errors))
