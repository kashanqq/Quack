"""Сжатая проекция результата подбора для контекста модели.

Полный `MatchingOut` — это карточки для фронта: со всей программой
целиком, всеми факторами и источниками, 3–4 КБ JSON на десять программ.
Модели из этого нужно ровно то, о чём она будет говорить: что за
программа, насколько реалистична и почему. Остальное она всё равно не
цитирует — числа и даты берутся из `get_program_facts` (постпроверка §5.2
отклоняет число без источника в результате инструмента).

Чистый модуль, без I/O.
"""

from __future__ import annotations

from app.schemas.matching import MatchingOut

_MAX_FACTORS = 3


def brief(matching: MatchingOut, max_items: int = 5) -> dict:
    """`MatchingOut` -> компактный dict для `ToolPayload.model_data`."""
    items = []
    for item in matching.items[:max_items]:
        program = item.program
        factors = sorted(item.factors, key=lambda f: -f.weight)[:_MAX_FACTORS]
        items.append(
            {
                "program_id": program.id,
                "university": program.university,
                "direction": program.direction,
                "country": program.country,
                "realism": item.realism,
                "why": [f"{f.status}: {f.text}" for f in factors],
                "soft_pending": item.soft_pending,
            }
        )
    return {
        "items": items,
        "shown": len(items),
        "total": matching.total,
        "profile_readiness": round(matching.profile_readiness, 2),
        "forecast_used": matching.forecast_used,
        "empty_reason": matching.empty_reason,
    }
