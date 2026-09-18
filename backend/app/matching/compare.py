"""Comparison — product-logic §3.4, 20-B1-phase2.md §5.4.

Pure function: build a table of parameters where the programs differ, plus
collapsed-same list and the student's relevant priorities.
conclusion=None — text lives in phase 4.

Source: 00-contracts-phase2.md §7.1.
"""

from __future__ import annotations

from app.matching.hard import HardResult
from app.schemas.common import Source
from app.schemas.matching import CompareOut, CompareRow
from app.schemas.profile import Profile
from app.schemas.programs import Program

_STANDARD_PARAMS = (
    ("cost", "стоимость / год"),
    ("living", "проживание / год"),
    ("duration", "длительность"),
    ("language", "язык"),
    ("scholarships", "стипендии"),
)


def compare(
    profile: Profile,
    programs: list[Program],
    hard_results: list[HardResult],
) -> CompareOut:
    """Side-by-side table across student-relevant and standard factors."""
    by_id = {p.id: p for p in programs}
    ids = [p.id for p in programs]

    rows: list[CompareRow] = []
    collapsed: list[str] = []

    # 1. Различающиеся требования
    hr_by_id = {h.program_id: h for h in hard_results}
    differing_factors = _differing_factors(hr_by_id, ids)
    for factor_id in sorted(differing_factors):
        row = _factor_row(factor_id, ids, hr_by_id)
        rows.append(row)

    # 2. Топ-3 приоритета ученика (не только hard — сюда попадают research/mobility)
    priorities = profile.questionnaire.priorities.ranking.value or []
    for key in priorities[:3]:
        row = _priority_row(key, ids, by_id, hr_by_id)
        if row is None:
            continue
        rows.append(row)

    # 3. Стандартные параметры
    for key, label in _STANDARD_PARAMS:
        row = _standard_row(key, label, ids, by_id)
        if row is None:
            continue
        if row.differs:
            rows.append(row)
        else:
            collapsed.append(label)

    return CompareOut(
        program_ids=ids,
        rows=rows,
        collapsed_same=collapsed,
        conclusion=None,
    )


# --- rows ---


def _factor_row(
    factor_id: str, ids: list[str], hr_by_id: dict[str, HardResult]
) -> CompareRow:
    values: dict[str, str] = {}
    source: Source | None = None
    for pid in ids:
        h = hr_by_id.get(pid)
        if h is None:
            values[pid] = "—"
            continue
        for f in h.factors:
            if f.id == factor_id:
                values[pid] = f.status
                if source is None:
                    source = f.source
                break
        else:
            values[pid] = "—"
    return CompareRow(
        param=factor_id,
        values=values,
        differs=True,
        relevant_to_student=True,
        source=source,
    )


def _priority_row(
    key: str,
    ids: list[str],
    by_id: dict[str, Program],
    hr_by_id: dict[str, HardResult],
) -> CompareRow | None:
    # стандартные: ranking / research / mobility — берём из environment_text
    if key in ("ranking", "research", "mobility"):
        values: dict[str, str] = {}
        for pid in ids:
            p = by_id.get(pid)
            if p is None:
                values[pid] = "—"
                continue
            text = (p.environment_text or "").lower()
            values[pid] = _keyword_phrase(text, key)
        return CompareRow(
            param=key,
            values=values,
            differs=len(set(values.values())) > 1,
            relevant_to_student=True,
            source=None,
        )
    # realism / cost / location / program — уже покрыты другими строками
    return None


def _standard_row(
    key: str, label: str, ids: list[str], by_id: dict[str, Program]
) -> CompareRow | None:
    values: dict[str, str] = {}
    for pid in ids:
        p = by_id.get(pid)
        if p is None:
            values[pid] = "—"
            continue
        if key == "cost":
            values[pid] = (
                f"{p.tuition_per_year} {p.currency}"
                if p.tuition_per_year is not None
                else "—"
            )
        elif key == "living":
            values[pid] = (
                f"{p.living_per_year} {p.currency}"
                if p.living_per_year is not None
                else "—"
            )
        elif key == "duration":
            values[pid] = (
                f"{p.duration_months} мес" if p.duration_months is not None else "—"
            )
        elif key == "language":
            values[pid] = p.language
        elif key == "scholarships":
            values[pid] = p.scholarships_note or "—"
        else:
            values[pid] = "—"
    return CompareRow(
        param=label,
        values=values,
        differs=len(set(values.values())) > 1,
        relevant_to_student=False,
        source=None,
    )


def _differing_factors(hr_by_id: dict[str, HardResult], ids: list[str]) -> set[str]:
    """Factor ids whose status differs across the compared programs."""
    if len(ids) < 2:
        return set()
    statuses: dict[str, set[str]] = {}
    for pid in ids:
        h = hr_by_id.get(pid)
        if h is None:
            continue
        for f in h.factors:
            statuses.setdefault(f.id, set()).add(f.status)
    return {fid for fid, s in statuses.items() if len(s) > 1}


def _keyword_phrase(text: str, key: str) -> str:
    if key == "research":
        if "research" in text or "лаборат" in text or "наук" in text:
            return "сильно"
        return "обычно"
    if key == "mobility":
        if "exchange" in text or "обмен" in text or "мобильн" in text:
            return "да"
        return "нет"
    if key == "ranking":
        if "top" in text or "рейтинг" in text:
            return "высокий"
        return "средний"
    return "—"
