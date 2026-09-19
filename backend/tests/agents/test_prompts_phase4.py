"""The six phase-4 prompts load and render — §13.2 `test_prompts_phase4.py`."""

import pytest

from app.llm.prompts import load_prompt
from app.prompt_versions import PROMPT_NAMES, version_of

pytestmark = pytest.mark.phase4

_VARIABLES = {
    "guideline": {
        "skill_name": "Линейные уравнения",
        "skill_description": "описание",
        "exam_name": "SAT_MATH",
        "area_name": "Алгебра",
        "state_words": "шатко",
        "p_target_words": "около 90 процентов",
        "prerequisites": "Арифметика — уверенно",
        "root_of": "нет",
        "misconceptions": "знак при переносе",
        "mode": "topic",
        "position_in_set": 1,
        "n_topics": 3,
        "deadline": "2026-10-01",
        "explanation_depth": "normal",
        "hint_level": "normal",
        "task_types": "mcq4",
        "calculator": "да",
        "template_tags": "linear",
    },
    "explanation": {
        "skill_name": "Линейные уравнения",
        "skill_description": "описание",
        "exam_name": "SAT_MATH",
        "prerequisites": "Арифметика",
        "task_types": "mcq4",
        "calculator": "да",
        "explanation_depth": "short",
    },
    "set_summary": {"stats_words": "закрыто тем: 2 из 3"},
    "soft_match": {
        "traits_summary": "тёплый климат",
        "traits_verbatim": "не люблю холод",
        "university": "University 1",
        "country": "ES",
        "city": "Valencia",
        "language": "en",
        "direction": "math",
        "environment_text": "приморский город",
        "scholarships_note": "нет",
    },
    "compare": {
        "rows": "- стоимость: a — 12000, b — 9000",
        "priorities": "cost",
        "traits_summary": "бюджет важен",
    },
    "realism_text": {
        "program": "University 1, math",
        "realism_words": "стоит попробовать",
        "factors": "- exam_score (below): нужно 1400",
        "assumptions": "нет",
    },
    "extract_program": {"page_text": "Tuition is 1 500 USD"},
}


@pytest.mark.parametrize("name", sorted(_VARIABLES))
def test_prompt_loads_and_renders_without_leftovers(name):
    prompt = load_prompt(name)
    assert prompt.extractor_version == f"{name}_v{prompt.version}"
    rendered = prompt.render(**_VARIABLES[name])
    assert "{{" not in rendered
    assert rendered.strip()


def test_every_phase4_kind_resolves_to_a_real_prompt_version():
    for kind, name in PROMPT_NAMES.items():
        assert version_of(kind) == load_prompt(name).extractor_version


def test_extra_variables_are_accepted():
    """Промпты делят набор переменных: лишние просто не используются."""
    load_prompt("explanation").render(**_VARIABLES["guideline"])
