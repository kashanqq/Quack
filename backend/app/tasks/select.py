"""Template selection for one skill — memory-architecture §10.2.

Pure function: pick a template from the pool based on what the student has
seen and how their last grades went.

Source: 20-B1-phase2.md §4.1.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.tasks import TaskTemplateSpec


def pick_template(
    templates: list[TaskTemplateSpec],
    seen: dict[str, int],
    last_grades: list[bool],
    with_trap: str | None,
    other_structure_than: str | None,
    rng: random.Random,
    difficulty: int | None = None,
) -> TaskTemplateSpec | None:
    """Choose one template from the pool.

    Rules (§10.2):
      - prefer templates with n_seen == 0
      - difficulty: one step up from last correct, one step down after two
        consecutive incorrect; start at the median difficulty of the pool
      - with_trap: only templates whose distractors reference this
        misconception id
      - other_structure_than: exclude templates with the same stem skeleton
        (compare template_id without the suffix after the last '_')
      - pool exhausted → minimum n_seen (repeat with a different seed)
      - difficulty: явно запрошенная сложность (репетитор через `get_task`)
        заменяет расчёт по последним ответам
    """
    if not templates:
        return None

    pool = list(templates)

    # 1. with_trap: только шаблоны, у которых есть дистрактор с этим заблуждением
    if with_trap is not None:
        pool = [
            t
            for t in pool
            if any(d.misconception_id == with_trap for d in t.distractors)
            or any((o.misconception_id == with_trap) for o in (t.omission_traps or []))
        ]
        if not pool:
            return None

    # 2. other_structure_than: исключить одинаковые структуры
    if other_structure_than is not None:
        excluded_skeleton = _skeleton(other_structure_than)
        pool = [t for t in pool if _skeleton(t.id) != excluded_skeleton]
        if not pool:
            return None

    # 3. Целевая сложность
    target_difficulty = (
        max(1, min(5, int(difficulty)))
        if difficulty is not None
        else _target_difficulty(pool, last_grades)
    )

    # 4. Группировка по n_seen
    unseen = [t for t in pool if seen.get(t.id, 0) == 0]
    candidates = unseen if unseen else pool

    # 5. Сортировка по близости к целевой сложности
    candidates.sort(key=lambda t: abs(t.difficulty - target_difficulty))

    # 6. Взять лучших и выбрать случайно среди равных
    best_diff = abs(candidates[0].difficulty - target_difficulty)
    top = [t for t in candidates if abs(t.difficulty - target_difficulty) == best_diff]
    return rng.choice(top)


# --- helpers ---


def _skeleton(template_id: str) -> str:
    """Убираем суффикс после последнего '_' — структура без параметров."""
    if "_" not in template_id:
        return template_id
    return template_id.rsplit("_", 1)[0]


def _target_difficulty(pool: list[TaskTemplateSpec], last_grades: list[bool]) -> int:
    """1 — шаг вверх, -1 — шаг вниз, 0 — стартовая (медиана)."""
    difficulties = sorted(t.difficulty for t in pool)
    median = difficulties[len(difficulties) // 2]

    if len(last_grades) >= 2 and not last_grades[-1] and not last_grades[-2]:
        return max(1, median - 1)
    if last_grades and last_grades[-1]:
        return min(5, median + 1)
    return median
