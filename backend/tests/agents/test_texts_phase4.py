"""Text generation, hashing and post-checks — §13.2."""

from datetime import date
from uuid import uuid4

import pytest

from app.agents import texts as agent_texts
from app.errors import LLMUnavailable
from app.knowledge.text_inputs import inputs_hash, set_inputs_hash
from app.llm.fake import FakeLLMClient
from app.schemas.matching import MatchOut
from app.schemas.texts import (
    ExplanationInputs,
    ExplanationOut,
    GuidelineInputs,
    GuidelineOut,
    MisconceptionBrief,
    PrerequisiteBrief,
    ProfileBrief,
    ProgramBrief,
    SetBrief,
    SetSummaryTextOut,
    SkillBrief,
    SoftMatchInputs,
)
from tests.quack.conftest import make_program

pytestmark = pytest.mark.phase4

STUDENT = uuid4()


def _guideline_inputs(**overrides) -> GuidelineInputs:
    base = {
        "skill": SkillBrief(
            id="alg.linear",
            name="Линейные уравнения",
            description="Решение уравнений первой степени",
            exam_id="SAT_MATH",
            area_name="Алгебра",
        ),
        "state_words": "shaky",
        "p_target_words": "держать на уровне около 90 процентов",
        "prerequisites": [
            PrerequisiteBrief(id="alg.basic", name="Арифметика", level="solid")
        ],
        "active_misconceptions": [
            MisconceptionBrief(
                id="m1",
                name="знак при переносе",
                description="теряет минус при переносе через равенство",
                trigger_words="минус",
            )
        ],
        "root_of": [],
        "set": SetBrief(deadline=date(2026, 10, 1), position_in_set=0, n_topics=3),
        "profile": ProfileBrief(),
        "template_tags": ["linear", "word_problem"],
        "mode": "topic",
    }
    return GuidelineInputs(**{**base, **overrides})


def _guideline_out(**overrides) -> GuidelineOut:
    base = {
        "how_to_prepare": "Начни с переноса слагаемых, потом переходи к дробям.",
        "must_know": ["переносить слагаемые", "приводить подобные", "проверять корень"],
        "traps": ["знак при переносе"],
        "what_to_solve": ["простые линейные", "текстовые задачи"],
        "summary": "Коротко: следи за знаком.",
    }
    return GuidelineOut(**{**base, **overrides})


# --- the hash (§3.4) ---


def test_inputs_hash_is_deterministic_and_version_sensitive():
    inputs = _guideline_inputs()
    first = inputs_hash("guideline", STUDENT, "alg.linear", inputs, "guideline_v1", "m")
    again = inputs_hash("guideline", STUDENT, "alg.linear", inputs, "guideline_v1", "m")
    assert first == again
    assert first != inputs_hash(
        "guideline", STUDENT, "alg.linear", inputs, "guideline_v2", "m"
    )
    assert first != inputs_hash(
        "guideline", STUDENT, "alg.linear", inputs, "guideline_v1", "other-model"
    )
    assert first != inputs_hash(
        "guideline", None, "alg.linear", inputs, "guideline_v1", "m"
    )


def test_hash_changes_with_the_state_word_and_the_misconceptions():
    base = _guideline_inputs()
    digest = inputs_hash("guideline", STUDENT, "s", base, "v", "m")
    assert digest != inputs_hash(
        "guideline", STUDENT, "s", _guideline_inputs(state_words="solid"), "v", "m"
    )
    assert digest != inputs_hash(
        "guideline",
        STUDENT,
        "s",
        _guideline_inputs(active_misconceptions=[]),
        "v",
        "m",
    )


def test_inputs_carry_no_probabilities_at_all():
    """Состояние словами, а не числами: иначе каждый ответ на задачу
    инвалидировал бы текст (§3.4)."""
    payload = _guideline_inputs().model_dump(mode="json")
    assert "p_recall" not in str(payload)
    assert "conf" not in str(payload)


def test_set_inputs_hash_does_not_depend_on_order():
    assert set_inputs_hash(["a", "b"]) == set_inputs_hash(["b", "a"])
    assert set_inputs_hash(["a", "b"]) != set_inputs_hash(["a", "c"])


# --- number post-check (§4.1) ---


def test_numbers_must_come_from_the_facts():
    facts = {"tasks_answered": 5, "note": "цена 1 500"}
    agent_texts.check_numbers("решено 5 задач за 1500", facts)
    with pytest.raises(agent_texts.PostcheckFailed):
        agent_texts.check_numbers("решено 7 задач", facts)


def test_thousand_separators_are_the_same_number():
    agent_texts.check_numbers("стоит 1 500", {"tuition": 1500})
    agent_texts.check_numbers("стоит 1500", {"note": "1 500"})


# --- guideline ---


async def test_guideline_renders_markdown_with_fixed_headings():
    llm = FakeLLMClient([_guideline_out()])
    text = await agent_texts.generate_guideline(llm, _guideline_inputs())
    assert text.startswith("## Как готовиться")
    assert "## Что нужно уметь" in text
    assert "## Ловушки" in text
    assert "## Что решать" in text


async def test_a_trap_outside_the_inputs_is_rejected_then_retried():
    invented = _guideline_out(traps=["путает косинус с синусом"])
    llm = FakeLLMClient([invented, _guideline_out()])
    text = await agent_texts.generate_guideline(llm, _guideline_inputs())
    assert "косинус" not in text
    assert len(llm.calls) == 2


async def test_two_bad_generations_fail_the_text():
    invented = _guideline_out(traps=["выдуманная ловушка"])
    llm = FakeLLMClient([invented, invented])
    with pytest.raises(agent_texts.PostcheckFailed):
        await agent_texts.generate_guideline(llm, _guideline_inputs())


async def test_empty_misconceptions_mean_an_empty_traps_section():
    llm = FakeLLMClient([_guideline_out(traps=[])])
    text = await agent_texts.generate_guideline(
        llm, _guideline_inputs(active_misconceptions=[])
    )
    assert "## Ловушки" not in text


async def test_llm_down_propagates_untouched():
    llm = FakeLLMClient([LLMUnavailable("llm unavailable")])
    with pytest.raises(LLMUnavailable):
        await agent_texts.generate_guideline(llm, _guideline_inputs())


# --- explanation ---


async def test_explanation_is_shared_and_needs_key_points():
    inputs = ExplanationInputs(
        skill=SkillBrief(
            id="alg.linear",
            name="Линейные уравнения",
            description="",
            exam_id="SAT_MATH",
        ),
        prerequisites=["Арифметика"],
    )
    llm = FakeLLMClient(
        [
            ExplanationOut(text="Это уравнение первой степени.", key_points=["одно"]),
            ExplanationOut(
                text="Это уравнение первой степени.",
                key_points=["перенос", "проверка"],
            ),
        ]
    )
    text = await agent_texts.generate_explanation(llm, inputs)
    assert "## Главное" in text
    assert len(llm.calls) == 2


# --- summary ---


async def test_summary_rejects_a_number_that_is_not_in_the_stats():
    from app.config import KnowledgeParams
    from app.sets.report import set_stats, stats_words
    from tests.sets.test_report import _inputs as report_inputs

    stats = set_stats(report_inputs(), KnowledgeParams(), report_inputs().completed_at)
    bad = SetSummaryTextOut(text="Ты решил 7 задач — отлично!")
    llm = FakeLLMClient([bad, bad])
    with pytest.raises(agent_texts.PostcheckFailed):
        await agent_texts.generate_summary(llm, stats, stats_words(stats))

    good = SetSummaryTextOut(text="Ты решил 5 задач, 4 верно — хороший темп.")
    llm = FakeLLMClient([good])
    assert "5" in await agent_texts.generate_summary(llm, stats, stats_words(stats))


# --- soft match ---


def _soft_inputs() -> SoftMatchInputs:
    return SoftMatchInputs(
        traits_summary="тёплый климат, небольшой город",
        traits_verbatim=["не люблю холод"],
        program=ProgramBrief(
            university="University 1",
            country="ES",
            city="Valencia",
            language="en",
            direction="math",
            environment_text="Тёплый приморский город, компактный кампус.",
        ),
    )


async def test_soft_match_rejects_digits_in_the_text():
    from app.agents.texts import _SoftMatchModelOut

    bad = _SoftMatchModelOut(score=0.8, fit_text="подходит: 20 градусов зимой")
    good = _SoftMatchModelOut(
        score=0.8, fit_text="подходит: тёплый приморский город", confidence="high"
    )
    llm = FakeLLMClient([bad, good])
    result = await agent_texts.generate_soft_match(llm, _soft_inputs())
    assert result.score == 0.8
    assert not any(character.isdigit() for character in result.fit_text)
    assert len(llm.calls) == 2


async def test_soft_match_gives_up_after_two_bad_answers():
    from app.agents.texts import _SoftMatchModelOut

    bad = _SoftMatchModelOut(score=0.5, fit_text="стоит 5000 евро")
    llm = FakeLLMClient([bad, bad])
    with pytest.raises(agent_texts.PostcheckFailed):
        await agent_texts.generate_soft_match(llm, _soft_inputs())


# --- realism and compare ---


async def test_realism_text_may_only_repeat_the_factor_numbers():
    from app.schemas.matching import FactorOut
    from app.schemas.texts import RealismTextOut

    match = MatchOut(
        program=make_program(1, threshold=1400),
        realism="try",
        factors=[
            FactorOut(
                id="exam_score",
                kind="hard",
                status="below",
                text="нужно 1400, прогноз 1300",
                source=None,
                weight=3.0,
            )
        ],
        assumptions=["бюджет не указан"],
        score=1.0,
        fits_text=None,
        soft_pending=False,
    )
    invented = RealismTextOut(text="не хватает 250 баллов")
    fine = RealismTextOut(text="до 1400 пока не хватает, сейчас 1300")
    llm = FakeLLMClient([invented, fine])
    text = await agent_texts.generate_realism(llm, match)
    assert "1400" in text and "250" not in text


async def test_compare_conclusion_uses_only_the_differing_rows():
    from types import SimpleNamespace

    from app.schemas.texts import CompareTextOut

    rows = [
        SimpleNamespace(param="стоимость", values={"a": "12000 USD", "b": "9000 USD"})
    ]
    conclusion = CompareTextOut(conclusion="разница в цене: 12000 против 9000")
    llm = FakeLLMClient([conclusion])
    text = await agent_texts.generate_compare(llm, rows, ["cost"], "бюджет важен")
    assert "12000" in text
    messages = llm.calls[0].messages
    assert "стоимость" in messages[0].content
