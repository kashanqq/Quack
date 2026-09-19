"""B2 text generation: six prompts, six validators, one hash (§3, §4, §5, §7).

Every generator here takes facts that are already computed and returns
prose. None of them decides anything: the model never sets a realism level,
never ranks programs and never invents a number. The post-checks enforce
that last rule literally — a number that is not in the input facts fails the
text, and a failed text is never shown (product-logic §6.2).
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from pydantic import BaseModel

from app.config import settings
from app.errors import LLMUnavailable
from app.knowledge.text_inputs import canonical_json, inputs_hash, set_inputs_hash
from app.llm.prompts import Prompt, load_prompt
from app.schemas.llm import LLMMessage
from app.schemas.matching import MatchOut, SoftMatchOut
from app.schemas.sets import SetStats
from app.schemas.texts import (
    CompareTextOut,
    ExplanationInputs,
    ExplanationOut,
    GuidelineInputs,
    GuidelineOut,
    RealismTextOut,
    SetSummaryTextOut,
    SoftMatchInputs,
)

_logger = structlog.get_logger(__name__)

__all__ = [
    "PostcheckFailed",
    "generate_compare",
    "generate_explanation",
    "generate_guideline",
    "generate_realism",
    "generate_soft_match",
    "generate_summary",
    "inputs_hash",
    "prompt_for",
    "render_explanation",
    "render_guideline",
    "set_inputs_hash",
    "validate_soft_match",
]

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
# Идентификаторы и хэши — не факты: цифры внутри UUID разрешили бы модели
# назвать почти любое число, поэтому из фактов они вырезаются до разбора.
_OPAQUE_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
    r"|\b[0-9a-f]{16,}\b",
    re.IGNORECASE,
)
# Разделитель тысяч: «1 500» и «1500» — одно и то же число.
_THOUSANDS_RE = re.compile(r"(?<=\d)[\s ](?=\d{3}(?!\d))")
_SKILL_LEVEL_WORDS = {
    "low_data": "мало данных",
    "weak": "слабо",
    "shaky": "шатко",
    "solid": "уверенно",
    "closed": "закрыто",
}
_TEXT_PROMPTS = {
    "guideline": "guideline",
    "explanation": "explanation",
    "realism": "realism_text",
    "compare": "compare",
}


class PostcheckFailed(Exception):
    """A generated text failed its own check — it is never shown (§11)."""

    def __init__(self, reason: str = "postcheck") -> None:
        super().__init__(reason)
        self.reason = reason


def prompt_for(kind: str) -> Prompt:
    """The prompt behind one `TextKind`; its version goes into the hash."""
    return load_prompt(_TEXT_PROMPTS[kind])


def model_name() -> str:
    """Background generation never touches `MODEL_CHAT` (§2.1)."""
    return settings.MODEL_BULK


# --- numbers ---


def numbers_in(text: str) -> set[str]:
    """Every number in a text, normalized so `1 500` and `1500` match."""
    joined = _THOUSANDS_RE.sub("", text)
    return {_normalize(match.group(0)) for match in _NUMBER_RE.finditer(joined)}


def _normalize(value: str) -> str:
    value = value.replace(",", ".")
    if "." in value:
        value = value.rstrip("0").rstrip(".")
    return value or "0"


def _allowed_numbers(value: Any) -> set[str]:
    """Numbers that appear anywhere in a facts object, at any depth."""
    out: set[str] = set()
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    if isinstance(value, dict):
        for item in value.values():
            out |= _allowed_numbers(item)
    elif isinstance(value, list | tuple):
        for item in value:
            out |= _allowed_numbers(item)
    elif isinstance(value, bool):
        pass
    elif isinstance(value, int | float):
        out |= numbers_in(str(value))
    elif isinstance(value, str):
        out |= numbers_in(_OPAQUE_RE.sub(" ", value))
    return out


def check_numbers(text: str, facts: Any) -> None:
    """Raise unless every number in `text` also occurs in `facts` (§4.1)."""
    unknown = numbers_in(text) - _allowed_numbers(facts)
    if unknown:
        raise PostcheckFailed("postcheck")


# --- one generation with a single corrective retry ---


async def _structured[T: BaseModel](
    llm: Any,
    messages: list[LLMMessage],
    schema: type[T],
    validate: Any,
    *,
    slot: str = "bulk",
) -> T:
    """Generate, validate, and on failure retry once with the objection.

    Two failures mean the model cannot satisfy the constraint on this input;
    banging on the same wall a third time only spends the budget (§11).
    """
    current = list(messages)
    last_reason = "postcheck"
    for attempt in range(2):
        result = await llm.structured(current, schema, slot)
        try:
            validate(result)
        except PostcheckFailed as exc:
            last_reason = exc.reason
            if attempt == 1:
                break
            current = [
                *current,
                LLMMessage(
                    role="user",
                    content=(
                        "В прошлом ответе были числа или утверждения, которых нет "
                        "во входных фактах. Перепиши, пользуясь только "
                        "перечисленными фактами, без своих чисел и процентов."
                    ),
                ),
            ]
            continue
        return result
    raise PostcheckFailed(last_reason)


# --- guideline and explanation (§3) ---


def _levels(items: list[Any]) -> str:
    return (
        ", ".join(
            f"{item.name} — {_SKILL_LEVEL_WORDS.get(item.level, item.level)}"
            for item in items
        )
        or "нет"
    )


def _misconceptions(items: list[Any]) -> str:
    if not items:
        return "нет"
    return "; ".join(
        f"{item.name}: {item.description}"
        + (f" (проявляется: {item.trigger_words})" if item.trigger_words else "")
        for item in items
    )


def _guideline_variables(inputs: GuidelineInputs) -> dict[str, Any]:
    return {
        "skill_name": inputs.skill.name,
        "skill_description": inputs.skill.description,
        "exam_name": inputs.skill.exam_id,
        "area_name": inputs.skill.area_name or "не указан",
        "state_words": _SKILL_LEVEL_WORDS.get(inputs.state_words, inputs.state_words),
        "p_target_words": inputs.p_target_words,
        "prerequisites": _levels(inputs.prerequisites),
        "root_of": ", ".join(inputs.root_of) or "нет",
        "misconceptions": _misconceptions(inputs.active_misconceptions),
        "mode": inputs.mode,
        "position_in_set": inputs.set.position_in_set,
        "n_topics": inputs.set.n_topics,
        "deadline": inputs.set.deadline.isoformat() if inputs.set.deadline else "нет",
        "explanation_depth": inputs.profile.explanation_depth,
        "hint_level": inputs.profile.hint_level,
        "task_types": ", ".join(inputs.exam_format_hint.task_types) or "не указаны",
        "calculator": "да" if inputs.exam_format_hint.calculator else "нет",
        "template_tags": ", ".join(inputs.template_tags) or "не указаны",
    }


def render_guideline(out: GuidelineOut) -> str:
    """Markdown with fixed headings — the same structure for every topic."""
    lines = ["## Как готовиться", out.how_to_prepare.strip(), "", "## Что нужно уметь"]
    lines += [f"- {item.strip()}" for item in out.must_know]
    if out.traps:
        lines += ["", "## Ловушки"]
        lines += [f"- {item.strip()}" for item in out.traps]
    lines += ["", "## Что решать"]
    lines += [f"- {item.strip()}" for item in out.what_to_solve]
    lines += ["", "## Коротко", out.summary.strip()]
    return "\n".join(lines).strip()


def render_explanation(out: ExplanationOut) -> str:
    lines = [out.text.strip(), "", "## Главное"]
    lines += [f"- {item.strip()}" for item in out.key_points]
    return "\n".join(lines).strip()


def validate_guideline(out: GuidelineOut, inputs: GuidelineInputs) -> None:
    """Traps only from the misconceptions we passed in (§3.3)."""
    if not 3 <= len(out.must_know) <= 6:
        raise PostcheckFailed("invalid_output")
    if not 2 <= len(out.what_to_solve) <= 4:
        raise PostcheckFailed("invalid_output")
    if len(out.traps) > 4:
        raise PostcheckFailed("invalid_output")
    known = {item.name.casefold() for item in inputs.active_misconceptions}
    for trap in out.traps:
        text = trap.casefold()
        if not any(name and name in text or text in name for name in known):
            raise PostcheckFailed("invalid_trap")
    if len(render_guideline(out)) > 2000:
        raise PostcheckFailed("too_long")


async def generate_guideline(llm: Any, inputs: GuidelineInputs) -> str:
    prompt = load_prompt("guideline")
    messages = [
        LLMMessage(
            role="system", content=prompt.render(**_guideline_variables(inputs))
        ),
        LLMMessage(role="user", content="Составь гайдлайн по этой теме."),
    ]
    out = await _structured(
        llm,
        messages,
        GuidelineOut,
        lambda result: validate_guideline(result, inputs),
    )
    return render_guideline(out)


async def generate_explanation(llm: Any, inputs: ExplanationInputs) -> str:
    prompt = load_prompt("explanation")
    messages = [
        LLMMessage(
            role="system",
            content=prompt.render(
                skill_name=inputs.skill.name,
                skill_description=inputs.skill.description,
                exam_name=inputs.skill.exam_id,
                prerequisites=", ".join(inputs.prerequisites) or "нет",
                task_types=", ".join(inputs.exam_format_hint.task_types)
                or "не указаны",
                calculator="да" if inputs.exam_format_hint.calculator else "нет",
                explanation_depth=inputs.explanation_depth,
            ),
        ),
        LLMMessage(role="user", content="Объясни этот навык."),
    ]

    def validate(out: ExplanationOut) -> None:
        if not 2 <= len(out.key_points) <= 5 or not out.text.strip():
            raise PostcheckFailed("invalid_output")

    out = await _structured(llm, messages, ExplanationOut, validate)
    return render_explanation(out)


# --- set summary (§4) ---


async def generate_summary(llm: Any, stats: SetStats, stats_words: str) -> str:
    """One call, facts in, one paragraph out; numbers checked against facts."""
    prompt = load_prompt("set_summary")
    messages = [
        LLMMessage(role="system", content=prompt.render(stats_words=stats_words)),
        LLMMessage(role="user", content="Напиши отчёт по сету."),
    ]

    def validate(out: SetSummaryTextOut) -> None:
        if not out.text.strip() or len(out.text) > 600:
            raise PostcheckFailed("invalid_output")
        check_numbers(out.text, stats)

    out = await _structured(llm, messages, SetSummaryTextOut, validate)
    return out.text.strip()


# --- soft match (§5) ---


def validate_soft_match(out: SoftMatchOut) -> None:
    """No digits, no percent sign, no ranking — §5.3."""
    if not 0.0 <= out.score <= 1.0:
        raise PostcheckFailed("invalid_output")
    text = f"{out.fit_text or ''} {out.caveat or ''}"
    if any(character.isdigit() for character in text) or "%" in text:
        raise PostcheckFailed("digits_in_soft_text")
    if out.fit_text is not None and len(out.fit_text) > 240:
        raise PostcheckFailed("too_long")
    if out.caveat is not None and len(out.caveat) > 120:
        raise PostcheckFailed("too_long")
    if len(out.matched_traits) > 4:
        raise PostcheckFailed("invalid_output")


class _SoftMatchModelOut(BaseModel):
    """What the model returns — the row adds `program_id` and the version."""

    score: float
    fit_text: str
    caveat: str | None = None
    matched_traits: list[str] = []
    confidence: str = "medium"


async def generate_soft_match(llm: Any, inputs: SoftMatchInputs) -> SoftMatchOut:
    prompt = load_prompt("soft_match")
    messages = [
        LLMMessage(
            role="system",
            content=prompt.render(
                traits_summary=inputs.traits_summary,
                traits_verbatim="; ".join(inputs.traits_verbatim) or "нет",
                university=inputs.program.university,
                country=inputs.program.country,
                city=inputs.program.city,
                language=inputs.program.language,
                direction=inputs.program.direction,
                environment_text=inputs.program.environment_text or "нет описания",
                scholarships_note=inputs.program.scholarships_note or "не указано",
            ),
        ),
        LLMMessage(role="user", content="Оцени соответствие."),
    ]

    def validate(out: _SoftMatchModelOut) -> None:
        validate_soft_match(_as_row(out, inputs, prompt.extractor_version))

    out = await _structured(llm, messages, _SoftMatchModelOut, validate)
    return _as_row(out, inputs, prompt.extractor_version)


def _as_row(
    out: _SoftMatchModelOut, inputs: SoftMatchInputs, prompt_version: str
) -> SoftMatchOut:
    confidence = (
        out.confidence if out.confidence in ("low", "medium", "high") else "medium"
    )
    return SoftMatchOut(
        program_id="",
        score=out.score,
        fit_text=out.fit_text,
        caveat=out.caveat,
        matched_traits=list(out.matched_traits)[:4],
        confidence=confidence,  # type: ignore[arg-type]
        prompt_version=prompt_version,
        stale=False,
    )


# --- comparison and realism (§7) ---


async def generate_compare(
    llm: Any, rows: list[Any], priorities: list[str], summary: str
) -> str:
    prompt = load_prompt("compare")
    rendered = "\n".join(
        f"- {row.param}: "
        + ", ".join(f"{name} — {value}" for name, value in sorted(row.values.items()))
        for row in rows
    )
    messages = [
        LLMMessage(
            role="system",
            content=prompt.render(
                rows=rendered or "нет различий",
                priorities=", ".join(priorities) or "не заданы",
                traits_summary=summary or "не заполнено",
            ),
        ),
        LLMMessage(role="user", content="Сформулируй вывод."),
    ]

    def validate(out: CompareTextOut) -> None:
        if not out.conclusion.strip() or len(out.conclusion) > 400:
            raise PostcheckFailed("invalid_output")
        check_numbers(out.conclusion, [row.values for row in rows])

    out = await _structured(llm, messages, CompareTextOut, validate)
    return out.conclusion.strip()


_REALISM_WORDS = {
    "possible": "реально",
    "try": "стоит попробовать",
    "impossible": "пока нереально",
}


async def generate_realism(llm: Any, match: MatchOut) -> str:
    prompt = load_prompt("realism_text")
    factors = "\n".join(
        f"- {factor.id} ({factor.status}): {factor.text}"
        + (f" — источник: {factor.source.label}" if factor.source else "")
        for factor in match.factors
    )
    messages = [
        LLMMessage(
            role="system",
            content=prompt.render(
                program=f"{match.program.university}, {match.program.direction}",
                realism_words=_REALISM_WORDS.get(match.realism, match.realism),
                factors=factors or "факторов нет",
                assumptions="; ".join(match.assumptions) or "нет",
            ),
        ),
        LLMMessage(role="user", content="Объясни, почему шансы такие."),
    ]

    def validate(out: RealismTextOut) -> None:
        if not out.text.strip() or len(out.text) > 400:
            raise PostcheckFailed("invalid_output")
        check_numbers(out.text, [factor.text for factor in match.factors])

    out = await _structured(llm, messages, RealismTextOut, validate)
    return out.text.strip()


def raise_if_invalid_output(exc: Exception) -> None:
    """`structured output failed` is not a retryable condition (§11)."""
    if isinstance(exc, LLMUnavailable) and "structured output failed" in str(exc):
        raise PostcheckFailed("invalid_output") from exc


def facts_json(value: Any) -> str:
    """Deterministic rendering used by the tests and the debug logs."""
    return canonical_json(
        value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    )
