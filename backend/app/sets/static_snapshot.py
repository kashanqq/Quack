"""The canonical skill map read from seed data, without Neo4j (§11 A3, D05).

When the graph is down the *canonical* layer is still knowable: it is the
versioned `data/skills/*.json` the graph was seeded from, and it changes only
when someone edits and re-seeds it. This module reads it, validates it, and
produces the same deterministic prerequisite ordering the graph would.

What it deliberately does **not** do is invent a student. There is no
`KnowledgeState` here, no mastery, no forecast: a plan assembled from a
snapshot would be a guess about the person, while an ordering of the subject
is a fact about the subject. So the outage behaviour is "keep the plan you
already have, ordered by this, and say the forecast is unavailable" — never
"here is a fresh plan we made up".

The order is a topological sort by `requires`, with ties broken by the order
the skills appear in the file. That is the stable answer D05 asks for: the
same input always gives the same sequence, on any machine, in any process.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import structlog

_logger = structlog.get_logger(__name__)

#: `backend/app/sets/static_snapshot.py` → repository root → `data/skills`.
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data"


class SnapshotUnavailable(RuntimeError):
    """The seed data is missing or malformed — say so, do not fake a map."""


@dataclass(frozen=True)
class StaticSkill:
    skill_id: str
    name: str
    area_id: str | None
    weight: float
    effort_h: float | None
    requires: tuple[str, ...]


@dataclass(frozen=True)
class StaticExam:
    exam_id: str
    name: str
    #: Canonical skills in dependency order.
    skills: tuple[StaticSkill, ...]

    @property
    def order(self) -> tuple[str, ...]:
        return tuple(skill.skill_id for skill in self.skills)


def load(data_dir: Path | None = None) -> dict[str, StaticExam]:
    """{exam_id: snapshot} from every `data/skills/*.json`.

    Raises `SnapshotUnavailable` rather than returning half a map: an
    incomplete ordering is worse than an explicit "cannot answer".
    """
    directory = (data_dir or DEFAULT_DATA_DIR) / "skills"
    if not directory.is_dir():
        raise SnapshotUnavailable(f"no canonical snapshot at {directory}")
    exams: dict[str, StaticExam] = {}
    for path in sorted(directory.glob("*.json")):
        exam = _read_exam(path)
        exams[exam.exam_id] = exam
    if not exams:
        raise SnapshotUnavailable(f"no exam files in {directory}")
    return exams


@lru_cache(maxsize=1)
def cached() -> dict[str, StaticExam]:
    """The snapshot for the running process; seed data does not change under it."""
    return load()


def available() -> bool:
    """Is there a usable snapshot? Used by `/health` and `seed --demo-check`."""
    try:
        cached()
    except SnapshotUnavailable:
        return False
    except Exception:  # noqa: BLE001 — a broken file reads as "not available"
        _logger.warning("static_snapshot_unreadable", exc_info=True)
        return False
    return True


def order_for(exam_id: str) -> tuple[str, ...]:
    """Canonical skill ids of one exam in dependency order; `()` if unknown."""
    try:
        exam = cached().get(exam_id)
    except Exception:  # noqa: BLE001
        return ()
    return exam.order if exam is not None else ()


def sort_topics[T](exam_id: str, items: list[T], key) -> list[T]:
    """Order existing topics by the snapshot; unknown skills keep their place.

    Used to keep a persisted set readable while the graph is down. It only
    reorders what the student already has — it never adds or removes a topic.
    """
    order = order_for(exam_id)
    if not order:
        return list(items)
    rank = {skill_id: index for index, skill_id in enumerate(order)}
    fallback = len(rank)
    return sorted(
        items, key=lambda item: (rank.get(key(item), fallback), key(item) or "")
    )


def _read_exam(path: Path) -> StaticExam:
    try:
        # The seed files are checked in with a BOM on some editors; the graph
        # loader tolerates it, so this must too, or the two disagree offline.
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotUnavailable(f"{path.name}: {exc}") from exc

    exam = payload.get("exam") or {}
    exam_id = exam.get("id")
    if not exam_id:
        raise SnapshotUnavailable(f"{path.name}: no exam id")

    area_of: dict[str, str] = {}
    weight_of: dict[str, float] = {}
    for area in payload.get("areas", []):
        for entry in area.get("skills", []):
            area_of[entry["id"]] = area.get("id")
            weight_of[entry["id"]] = float(entry.get("weight", 1.0))

    declared = payload.get("skills", [])
    if not declared:
        raise SnapshotUnavailable(f"{path.name}: no skills")
    by_id = {skill["id"]: skill for skill in declared}
    ordered_ids = _topological(
        [skill["id"] for skill in declared],
        {
            skill["id"]: [
                requirement["skill_id"]
                for requirement in skill.get("requires", [])
                if requirement.get("skill_id") in by_id
            ]
            for skill in declared
        },
        path.name,
    )
    skills = tuple(
        StaticSkill(
            skill_id=skill_id,
            name=by_id[skill_id].get("name", skill_id),
            area_id=area_of.get(skill_id),
            weight=weight_of.get(skill_id, 1.0),
            effort_h=by_id[skill_id].get("effort_h"),
            requires=tuple(
                requirement["skill_id"]
                for requirement in by_id[skill_id].get("requires", [])
            ),
        )
        for skill_id in ordered_ids
    )
    return StaticExam(exam_id=exam_id, name=exam.get("name", exam_id), skills=skills)


def _topological(
    ids: list[str], requires: dict[str, list[str]], label: str
) -> list[str]:
    """Kahn's algorithm with the file order as the tie-break.

    A cycle is a data error, not something to work around silently: the seed
    files are validated in CI, and a cycle here would otherwise turn into an
    arbitrary — but stable-looking — ordering.
    """
    position = {skill_id: index for index, skill_id in enumerate(ids)}
    pending = {skill_id: set(requires.get(skill_id, ())) for skill_id in ids}
    ordered: list[str] = []
    while pending:
        ready = sorted(
            (skill_id for skill_id, needs in pending.items() if not needs),
            key=lambda skill_id: position[skill_id],
        )
        if not ready:
            raise SnapshotUnavailable(f"{label}: prerequisite cycle")
        for skill_id in ready:
            ordered.append(skill_id)
            del pending[skill_id]
        for needs in pending.values():
            needs.difference_update(ready)
    return ordered
