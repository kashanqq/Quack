"""Turning an exam target score into the recall every skill aims at.

Pure, and shared: `apply.targets` needs it with I/O around it, and the pace
variants of phase 4 need it inside a loop with no I/O at all (§8.3).
"""

from __future__ import annotations

from app.config import KnowledgeParams
from app.schemas.knowledge import ExamFormat


def raw_from_scaled(scaled: float, exam_format: ExamFormat) -> float | None:
    """Inverse of `sets.forecast._scale` — a scaled score back to raw points."""
    table = exam_format.scale_table
    if not table:
        return None
    points: list[tuple[float, float]] = []
    for raw_key, scaled_value in table.items():
        try:
            points.append((float(raw_key), float(scaled_value)))
        except (ValueError, TypeError):
            continue
    if len(points) < 2:
        return None
    points.sort(key=lambda point: point[1])

    if scaled <= points[0][1]:
        return points[0][0]
    if scaled >= points[-1][1]:
        return points[-1][0]
    for (raw0, scaled0), (raw1, scaled1) in zip(points, points[1:], strict=False):
        if scaled0 <= scaled <= scaled1:
            if scaled1 == scaled0:
                return raw0
            share = (scaled - scaled0) / (scaled1 - scaled0)
            return raw0 + share * (raw1 - raw0)
    return None


def p_target_from(
    target_score: float, exam_format: ExamFormat | None, params: KnowledgeParams
) -> float:
    """`min(p_target_max, target / max_raw)`, converting scaled targets first."""
    if exam_format is None or exam_format.max_raw_score <= 0:
        return params.p_target_max
    raw_target = target_score
    if target_score > exam_format.max_raw_score:
        converted = raw_from_scaled(target_score, exam_format)
        if converted is None:
            return params.p_target_max
        raw_target = converted
    share = raw_target / exam_format.max_raw_score
    return max(0.0, min(params.p_target_max, share))
