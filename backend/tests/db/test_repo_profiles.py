"""Profile defaults, path validation and readiness without a live database."""

from uuid import uuid4

import pytest

from app.db.repo.profiles import (
    apply_profile_update,
    get_profile,
    profile_readiness,
)
from app.errors import ValidationFailed
from app.schemas.profile import ProfileUpdateIn, Questionnaire


class ProfileSession:
    def __init__(self):
        self.row = None
        self.commits = 0

    async def get(self, model, student_id):
        return self.row

    def add(self, row):
        self.row = row

    async def flush(self):
        pass


@pytest.mark.asyncio
async def test_empty_profile_has_default_leaves_and_zero_readiness():
    profile = await get_profile(ProfileSession(), uuid4())
    assert profile.readiness == 0.0
    assert profile.traits.verbatim == []
    assert profile.traits.summary == ""
    for section in profile.questionnaire:
        for _, field in section[1]:
            assert field.value is None
            assert field.mark == "default"


def test_readiness_exact_weights():
    questionnaire = Questionnaire()
    assert profile_readiness(questionnaire) == 0.0
    questionnaire.direction.field.value = "IT"
    assert profile_readiness(questionnaire) == 0.2
    questionnaire.preferences.budget_per_year.value = 100
    questionnaire.preferences.grant_need.value = "preferred"
    questionnaire.preferences.countries.value = []
    questionnaire.level.grade.value = 11
    questionnaire.academics.ent_trial_score.value = 30
    questionnaire.academics.ielts_score.value = 6.5
    questionnaire.preferences.language.value = "en"
    questionnaire.pace.hours_per_week.value = 5
    assert profile_readiness(questionnaire) == 1.0


@pytest.mark.asyncio
async def test_profile_path_and_value_validation_and_trait_append():
    session = ProfileSession()
    student_id = uuid4()
    with pytest.raises(ValidationFailed):
        await apply_profile_update(
            session,
            student_id,
            ProfileUpdateIn(path="unknown.path", value="x", by="user"),
        )
    with pytest.raises(ValidationFailed):
        await apply_profile_update(
            session,
            student_id,
            ProfileUpdateIn(path="level.grade", value="not a number", by="user"),
        )
    assert session.row is None

    profile = await apply_profile_update(
        session,
        student_id,
        ProfileUpdateIn(path="level.grade", value=11, by="assistant"),
    )
    assert profile.questionnaire.level.grade.value == 11
    assert profile.questionnaire.level.grade.mark == "assumed"
    for value in ("люблю бананы", "хочу тепло"):
        profile = await apply_profile_update(
            session,
            student_id,
            ProfileUpdateIn(path="traits.verbatim", value=value, by="user"),
        )
    assert profile.traits.verbatim == ["люблю бананы", "хочу тепло"]
    assert session.commits == 0
