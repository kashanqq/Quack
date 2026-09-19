"""Turning a program page into a `Program` — §6.4–§6.6.

The model reads the page; nothing it says is trusted on its own. Every
number and date must be backed by a quotation that really occurs in the
page *and* by the value itself occurring there too — otherwise the field is
dropped. A university name that cannot be confirmed rejects the whole
record: a card with the wrong university on it is worse than no card.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

import structlog

from app.config import KnowledgeParams
from app.llm.prompts import load_prompt
from app.schemas.common import ExamId
from app.schemas.llm import LLMMessage
from app.schemas.programs import (
    Deadline,
    ExtractedProgram,
    Program,
    Requirement,
)

_logger = structlog.get_logger(__name__)

CURRENCIES = frozenset(
    {
        "USD", "EUR", "GBP", "KZT", "RUB", "CHF", "CAD", "TRY", "PLN", "CZK",
        "HUF", "AED", "KRW", "JPY", "CNY", "SGD", "HKD", "MYR",
    }
)  # fmt: skip

VERIFIED_FIELDS = (
    "university",
    "tuition_per_year",
    "living_per_year",
    "duration_months",
)

_COUNTRIES: dict[str, str] = {
    "kazakhstan": "KZ", "казахстан": "KZ",
    "usa": "US", "united states": "US", "сша": "US",
    "united kingdom": "GB", "uk": "GB", "великобритания": "GB",
    "germany": "DE", "германия": "DE",
    "netherlands": "NL", "нидерланды": "NL",
    "turkey": "TR", "türkiye": "TR", "турция": "TR",
    "poland": "PL", "польша": "PL",
    "czechia": "CZ", "czech republic": "CZ", "чехия": "CZ",
    "hungary": "HU", "венгрия": "HU",
    "canada": "CA", "канада": "CA",
    "france": "FR", "франция": "FR",
    "italy": "IT", "италия": "IT",
    "spain": "ES", "испания": "ES",
    "switzerland": "CH", "швейцария": "CH",
    "uae": "AE", "united arab emirates": "AE", "оаэ": "AE",
    "south korea": "KR", "korea": "KR", "корея": "KR",
    "japan": "JP", "япония": "JP",
    "china": "CN", "китай": "CN",
    "singapore": "SG", "сингапур": "SG",
    "hong kong": "HK", "гонконг": "HK",
    "malaysia": "MY", "малайзия": "MY",
    "russia": "RU", "россия": "RU",
}  # fmt: skip

_RU_MONTHS = (
    "январ", "феврал", "март", "апрел", "мая", "июн",
    "июл", "август", "сентябр", "октябр", "ноябр", "декабр",
)  # fmt: skip
_EN_MONTHS = (
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
)  # fmt: skip

_TRANSLIT = str.maketrans(
    {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
        "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }
)  # fmt: skip

_CATALOGUE_WORDS = (
    "admission",
    "requirements",
    "tuition",
    "deadline",
    "поступ",
    "стоимост",
)
_MAX_LINKS_IN_CATALOGUE = 30


def slugify(text: str, limit: int = 30) -> str:
    """ASCII, lowercase, dash-separated — the stable half of a program id."""
    value = (text or "").lower().translate(_TRANSLIT)
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:limit].strip("-") or "unknown"


def program_id(university: str, direction: str) -> str:
    return f"{slugify(university, 30)}-{slugify(direction, 29)}"[:60].strip("-")


def country_code(value: str | None) -> str | None:
    """ISO-2 by dictionary; an unrecognized country rejects the record."""
    if not value:
        return None
    cleaned = value.strip()
    if len(cleaned) == 2 and cleaned.isalpha():
        return cleaned.upper()
    return _COUNTRIES.get(cleaned.casefold())


def map_exam(exam_name: str | None, description: str = "") -> ExamId | None:
    """Only exams we actually model; anything else keeps `exam_id=None`."""
    if not exam_name:
        return None
    haystack = f"{exam_name} {description}".casefold()
    if "sat" in haystack:
        return "SAT_MATH"
    if any(token in haystack for token in ("ент", "ent", "unt")):
        return "ENT_MATH"
    return None


def page_rejection(page_text: str, params: KnowledgeParams) -> str | None:
    """Reasons not to spend a model call on this page at all (§6.3)."""
    if len(page_text) < params.extract_min_page_chars:
        return "empty_page"
    lowered = page_text.casefold()
    if page_text.count("http") > _MAX_LINKS_IN_CATALOGUE and not any(
        word in lowered for word in _CATALOGUE_WORDS
    ):
        return "not_program_page"
    return None


# --- the model call ---


async def extract_program(llm: Any, html: str, url: str) -> ExtractedProgram:
    """`html` is already the page *text* from `fetch_page` (§0.5)."""
    prompt = load_prompt("extract_program")
    messages = [
        LLMMessage(role="system", content=prompt.render(page_text=html)),
        LLMMessage(role="user", content="Извлеки поля программы."),
    ]
    return await llm.structured(messages, ExtractedProgram, "bulk")


# --- verification against the page (§6.5) ---


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).casefold()


def quote_present(quote: str | None, page: str) -> bool:
    if not quote:
        return False
    return _normalized(quote)[:120] in _normalized(page)


def number_present(value: float | int, page: str) -> bool:
    """`1500`, `1 500`, `1,500` and `1.500` are all the same number here."""
    whole = int(value)
    if abs(value - whole) > 1e-9:
        candidates = {str(value), str(value).replace(".", ",")}
    else:
        plain = str(whole)
        grouped = f"{whole:,}"
        candidates = {
            plain,
            grouped,
            grouped.replace(",", " "),
            grouped.replace(",", "."),
            grouped.replace(",", " "),
        }
    haystack = _normalized(page)
    return any(_normalized(candidate) in haystack for candidate in candidates)


def date_present(value: date, page: str) -> bool:
    haystack = _normalized(page)
    variants = [
        value.isoformat(),
        value.strftime("%d.%m.%Y"),
        f"{value.day}.{value.month:02d}.{value.year}",
        f"{value.day} {_EN_MONTHS[value.month - 1]} {value.year}",
        f"{_EN_MONTHS[value.month - 1]} {value.day}, {value.year}",
        f"{value.day} {_RU_MONTHS[value.month - 1]}",
    ]
    return any(_normalized(variant) in haystack for variant in variants)


def verify_against_source(
    program: Program, extracted: ExtractedProgram, page_text: str
) -> tuple[Program, list[str]]:
    """Blank out every value the page does not actually support (§6.5).

    `environment_text` and free descriptions are not checked — they are an
    admitted retelling and carry the `extracted_auto` mark.
    """
    dropped: list[str] = []
    evidence = extracted.evidence or {}

    def confirmed(field: str, value: Any) -> bool:
        if value is None:
            return True
        if not quote_present(evidence.get(field), page_text):
            return False
        if isinstance(value, date):
            return date_present(value, page_text)
        return number_present(value, page_text)

    updates: dict[str, Any] = {}
    for field in ("tuition_per_year", "living_per_year", "duration_months"):
        value = getattr(program, field)
        if value is not None and not confirmed(field, value):
            updates[field] = None
            dropped.append(field)

    named = _normalized(program.university) in _normalized(page_text)
    quoted = quote_present(evidence.get("university"), page_text)
    if not (named and quoted):
        dropped.append("university")

    requirements: list[Requirement] = []
    for index, requirement in enumerate(program.requirements):
        if requirement.threshold is None:
            requirements.append(requirement)
            continue
        key = f"requirements[{index}].threshold"
        if confirmed(key, requirement.threshold) or number_present(
            requirement.threshold, page_text
        ):
            requirements.append(requirement)
            continue
        dropped.append(key)
        requirements.append(
            requirement.model_copy(update={"threshold": None, "comparator": "present"})
        )
    updates["requirements"] = requirements

    deadlines: list[Deadline] = []
    for index, deadline in enumerate(program.deadlines):
        key = f"deadlines[{index}].date"
        if confirmed(key, deadline.date) or date_present(deadline.date, page_text):
            deadlines.append(deadline)
        else:
            dropped.append(key)
    updates["deadlines"] = deadlines

    return program.model_copy(update=updates), dropped


# --- mapping and acceptance (§6.4, §6.6) ---


def to_program(extracted: ExtractedProgram, url: str, today: date) -> Program | str:
    """`ExtractedProgram` → `Program`, or a rejection reason."""
    if not extracted.university or not extracted.direction:
        return "insufficient_fields"
    country = country_code(extracted.country)
    if country is None:
        return "country_unknown"
    if not extracted.language:
        return "insufficient_fields"

    currency = (extracted.currency or "").strip().upper()
    if currency not in CURRENCIES:
        currency, tuition, living = "", None, None
    else:
        tuition, living = extracted.tuition_per_year, extracted.living_per_year

    requirements = [
        Requirement(
            type=item.type,
            exam_id=(
                map_exam(item.exam_name, item.description)
                if item.type == "exam_score"
                else None
            ),
            threshold=item.threshold,
            comparator=(
                item.comparator or ("present" if item.threshold is None else ">=")
            ),
            description=item.description,
            source=url,
        )
        for item in extracted.requirements
    ]
    deadlines = [
        Deadline(
            kind=item.kind,
            date=item.date,
            round=item.round,
            source=url,
            checked_at=today,
            is_demo=False,
        )
        for item in extracted.deadlines
        # Дедлайн без даты бесполезен: напомнить о нём нечем.
        if item.date is not None
    ]

    return Program(
        id=program_id(extracted.university, extracted.direction),
        university=extracted.university.strip(),
        country=country,
        # `city` обязателен; пустой заменяем страной и пишем это в notes.
        city=(extracted.city or "").strip() or country,
        direction=extracted.direction.strip(),
        language=extracted.language.strip(),
        duration_months=extracted.duration_months,
        tuition_per_year=tuition,
        living_per_year=living,
        currency=currency,
        requirements=requirements,
        deadlines=deadlines,
        scholarships_note=extracted.scholarships_note,
        environment_text=extracted.environment_text,
        source_url=url,
        checked_at=today,
        is_demo=False,
        extracted_auto=True,
        flagged=False,
    )


def acceptance_reason(program: Program, dropped: list[str]) -> str | None:
    """None when the record may be stored; a rejection reason otherwise."""
    if "university" in dropped:
        return "university_not_in_source"
    if not (program.university and program.country and program.direction):
        return "insufficient_fields"
    if not program.language:
        return "insufficient_fields"
    has_threshold = any(
        item.threshold is not None and item.type in ("exam_score", "language")
        for item in program.requirements
    )
    if has_threshold or program.deadlines or program.tuition_per_year is not None:
        return None
    return "insufficient_fields"


def parse_date(value: str) -> date | None:
    for pattern in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value.strip(), pattern).date()
        except ValueError:
            continue
    return None
