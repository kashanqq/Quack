"""Матчинг направления обучения: «информатика» и «Computer Science» — одно.

Чистый модуль, без I/O. Направление в анкете ученик пишет своими словами
и по-русски, а `Program.direction` в датасете — как его назвал вуз, обычно
по-английски. Сравнение подстрокой («информатика» in «Computer Science»)
давало пустой результат на каждом непереведённом направлении, поэтому обе
стороны сперва приводятся к канону по словарю синонимов.

Словарь покрывает направления демо-датасета (product-logic §5.1). Слова,
которых в нём нет, сравниваются по-старому — подстрокой в обе стороны, так
что новое направление не ломает подбор, а лишь не получает синонимов.
"""

from __future__ import annotations

import re

# канон -> варианты написания (нижний регистр, без пунктуации)
_SYNONYMS: dict[str, tuple[str, ...]] = {
    "computer_science": (
        "computer science",
        "cs",
        "computing",
        "information technology",
        "it",
        "software engineering",
        "информатика",
        "компьютерные науки",
        "программирование",
        "разработка по",
        "информационные технологии",
        "ит",
    ),
    "data_science": (
        "data science",
        "data analytics",
        "machine learning",
        "artificial intelligence",
        "ai",
        "анализ данных",
        "наука о данных",
        "машинное обучение",
        "искусственный интеллект",
    ),
    "mathematics": (
        "mathematics",
        "maths",
        "math",
        "applied mathematics",
        "математика",
        "прикладная математика",
    ),
    "physics": ("physics", "applied physics", "физика"),
    "engineering": (
        "engineering",
        "mechanical engineering",
        "electrical engineering",
        "инженерия",
        "инженерное дело",
        "машиностроение",
        "электротехника",
    ),
    "economics": (
        "economics",
        "finance",
        "экономика",
        "финансы",
    ),
    "business": (
        "business",
        "business administration",
        "management",
        "бизнес",
        "менеджмент",
        "управление",
    ),
    "medicine": ("medicine", "medical", "медицина", "лечебное дело"),
    "biology": ("biology", "life sciences", "биология"),
    "chemistry": ("chemistry", "химия"),
    "law": ("law", "jurisprudence", "право", "юриспруденция"),
    "psychology": ("psychology", "психология"),
    "architecture": ("architecture", "архитектура"),
    "design": ("design", "graphic design", "дизайн"),
    "linguistics": (
        "linguistics",
        "languages",
        "лингвистика",
        "языки",
        "филология",
    ),
}

_BY_VARIANT: dict[str, str] = {
    variant: canon for canon, variants in _SYNONYMS.items() for variant in variants
}


def _normalize(text: str) -> str:
    return re.sub(r"[^\w\s]+", " ", text.strip().lower(), flags=re.UNICODE)


def canonical_direction(text: str | None) -> str | None:
    """Канон направления, или None — слова нет в словаре."""
    if not text:
        return None
    normalized = _normalize(text)
    if not normalized:
        return None
    if normalized in _BY_VARIANT:
        return _BY_VARIANT[normalized]
    # Направление вуза часто длиннее («BSc Computer Science and Engineering»):
    # ищем самый длинный вариант, который в нём встречается целым словом.
    best: tuple[int, str] | None = None
    for variant, canon in _BY_VARIANT.items():
        if re.search(rf"(?<!\w){re.escape(variant)}(?!\w)", normalized):
            if best is None or len(variant) > best[0]:
                best = (len(variant), canon)
    return best[1] if best else None


def direction_matches(wanted: str | None, program_direction: str) -> bool:
    """Совпадает ли направление программы с тем, что ученик назвал в анкете."""
    if not wanted:
        return True
    wanted_canon = canonical_direction(wanted)
    program_canon = canonical_direction(program_direction)
    if wanted_canon is not None and program_canon is not None:
        return wanted_canon == program_canon
    left = _normalize(wanted)
    right = _normalize(program_direction)
    return bool(left) and (left in right or right in left)
