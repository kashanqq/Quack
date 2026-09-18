"""Mock assembly and scoring — memory-architecture §8.3, §10.2.

Pure functions: assemble a mock from templates, score a finished mock by the
rules of its exam section.

Source: 20-B1-phase2.md §4.2.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Literal

from app.config import KnowledgeParams

if TYPE_CHECKING:
    from app.schemas.knowledge import ExamFormat, Section
    from app.schemas.tasks import Grade, TaskTemplateSpec

MockKind = Literal["mock_set", "mock_topic", "mock_misconception"]


def assemble_mock(
    kind: MockKind,
    section: Section,
    templates_by_skill: dict[str, list[TaskTemplateSpec]],
    seen: dict[str, int],
    rng: random.Random,
    params: KnowledgeParams,
) -> list[tuple[str, TaskTemplateSpec]]:
    """Pick templates for a mock of one kind.

    Returns:
        list of (skill_id, TaskTemplateSpec) — one per task, in order.
    """
    if not templates_by_skill:
        return []

    if kind == "mock_topic":
        n = rng.randint(params.mock_topic_min, params.mock_topic_max)
        return _pick_generic(templates_by_skill, seen, n, rng)

    if kind == "mock_set":
        n = rng.randint(params.mock_set_min, params.mock_set_max)
        return _pick_by_section(templates_by_skill, section, n, seen, rng)

    if kind == "mock_misconception":
        return _pick_misconception(templates_by_skill, seen, rng, params)

    return []


def score(
    section: Section,
    grades: list[Grade],
    exam_format: ExamFormat,
) -> tuple[float, float | None]:
    """Score a finished mock by the section's scoring_rule.

    Returns:
        (raw_score, scaled_score or None) — scaled uses the exam's ScaleTable.
    """
    raw = _score_raw(section, grades, exam_format)
    scaled = _scale(raw, exam_format)
    return raw, scaled


# --- assembly ---


def _pick_generic(
    templates_by_skill: dict[str, list[TaskTemplateSpec]],
    seen: dict[str, int],
    n: int,
    rng: random.Random,
) -> list[tuple[str, TaskTemplateSpec]]:
    """Pick n distinct templates from the pool, preferring unseen, mixed skills."""
    pool: list[tuple[str, TaskTemplateSpec]] = []
    for skill_id, templates in templates_by_skill.items():
        for t in templates:
            pool.append((skill_id, t))

    if not pool:
        return []

    # Сортировка: сначала непройденные
    pool.sort(key=lambda st: seen.get(st[1].id, 0))
    rng.shuffle(pool)  # перемешать в пределах равных n_seen

    # Повторная сортировка для стабильного «сначала невиданные»
    pool.sort(key=lambda st: seen.get(st[1].id, 0))

    # Взять n разных структур
    chosen: list[tuple[str, TaskTemplateSpec]] = []
    used_skeletons: set[str] = set()
    for skill_id, t in pool:
        if len(chosen) >= n:
            break
        skeleton = _skeleton(t.id)
        if skeleton in used_skeletons:
            continue
        used_skeletons.add(skeleton)
        chosen.append((skill_id, t))

    # Добрать, если не хватило
    if len(chosen) < n:
        for skill_id, t in pool:
            if len(chosen) >= n:
                break
            if (skill_id, t) in chosen:
                continue
            chosen.append((skill_id, t))

    return chosen[:n]


def _pick_by_section(
    templates_by_skill: dict[str, list[TaskTemplateSpec]],
    section: Section,
    n: int,
    seen: dict[str, int],
    rng: random.Random,
) -> list[tuple[str, TaskTemplateSpec]]:
    """mock_set: cover item_types proportional to shares."""
    total_items = sum(section.item_types.values()) or 1
    # сколько каждого типа
    type_budget: dict[str, int] = {}
    for t_type, count in section.item_types.items():
        type_budget[t_type] = round(n * count / total_items)
    # Докрутить до n
    diff = n - sum(type_budget.values())
    if diff > 0:
        # добавим по одному самому частому
        for t_type in sorted(type_budget, key=lambda k: -section.item_types[k]):
            if diff <= 0:
                break
            type_budget[t_type] += 1
            diff -= 1

    chosen: list[tuple[str, TaskTemplateSpec]] = []
    used_skeletons: set[str] = set()

    for t_type, budget in type_budget.items():
        pool: list[tuple[str, TaskTemplateSpec]] = []
        for skill_id, templates in templates_by_skill.items():
            for t in templates:
                if t.type == t_type and t.id not in {c[1].id for c in chosen}:
                    pool.append((skill_id, t))
        # предпочтение непройденным
        pool.sort(key=lambda st: seen.get(st[1].id, 0))
        rng.shuffle(pool)
        pool.sort(key=lambda st: seen.get(st[1].id, 0))

        added = 0
        for skill_id, t in pool:
            if added >= budget:
                break
            if _skeleton(t.id) in used_skeletons:
                continue
            used_skeletons.add(_skeleton(t.id))
            chosen.append((skill_id, t))
            added += 1

    # Добрать, если не хватило
    if len(chosen) < n:
        extras = _pick_generic(
            templates_by_skill,
            seen,
            n - len(chosen),
            rng,
        )
        for skill_id, t in extras:
            if (skill_id, t) not in chosen:
                chosen.append((skill_id, t))

    return chosen[:n]


def _pick_misconception(
    templates_by_skill: dict[str, list[TaskTemplateSpec]],
    seen: dict[str, int],
    rng: random.Random,
    params: KnowledgeParams,
) -> list[tuple[str, TaskTemplateSpec]]:
    """mock_misconception: n шаблонов с TRAPS, по разным навыкам если возможно."""
    by_skill: dict[str, list[TaskTemplateSpec]] = {}
    for skill_id, templates in templates_by_skill.items():
        with_traps = [
            t
            for t in templates
            if t.distractors and any(d.misconception_id for d in t.distractors)
        ]
        if with_traps:
            by_skill[skill_id] = with_traps

    if not by_skill:
        return []

    # По одному шаблону с каждого навыка, пока не наберём n
    chosen: list[tuple[str, TaskTemplateSpec]] = []
    skill_ids = list(by_skill.keys())
    rng.shuffle(skill_ids)

    idx = 0
    while len(chosen) < params.mock_misc_n and idx < len(skill_ids):
        sid = skill_ids[idx]
        pool = by_skill[sid]
        pool.sort(key=lambda t: seen.get(t.id, 0))
        chosen.append((sid, pool[0]))
        idx += 1

    # Если всё ещё мало — второй проход по кругу
    while len(chosen) < params.mock_misc_n:
        progressed = False
        for sid in skill_ids:
            if len(chosen) >= params.mock_misc_n:
                break
            pool = by_skill[sid]
            for t in pool:
                if all(t.id != c[1].id for c in chosen):
                    chosen.append((sid, t))
                    progressed = True
                    break
        if not progressed:
            break

    return chosen


def _skeleton(template_id: str) -> str:
    if "_" not in template_id:
        return template_id
    return template_id.rsplit("_", 1)[0]


# --- scoring ---


def _score_raw(section: Section, grades: list[Grade], exam_format: ExamFormat) -> float:
    """Sum raw points by rules of section/exam_format."""
    rule = section.scoring_rule.lower()
    points = 0.0

    if "multi_select" in rule and "partial" in rule:
        # ЕНТ-стиль: mcq5 → 1, multi_select → 2 за полное, 1 за частичное
        for g in grades:
            if g.correct:
                points += 1.0
            elif g.partial is not None and g.partial > 0:
                # 1 балл за частично верный
                points += 1.0
        return points

    # дефолт: 1 балл за верный
    for g in grades:
        if g.correct:
            points += 1.0
    return points


def _scale(raw: float, exam_format: ExamFormat) -> float | None:
    """Линейная интерполяция по ScaleTable. None если нет таблицы."""
    table = exam_format.scale_table
    if not table:
        return None
    points: list[tuple[float, float]] = []
    for k, v in table.items():
        try:
            points.append((float(k), float(v)))
        except (ValueError, TypeError):
            continue
    if not points:
        return None
    points.sort()

    if raw <= points[0][0]:
        return points[0][1]
    if raw >= points[-1][0]:
        return points[-1][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:], strict=False):
        if x0 <= raw <= x1:
            if x1 == x0:
                return y0
            t = (raw - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return None
