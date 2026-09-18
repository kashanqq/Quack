"""B2 roadmap requirement interface."""

from typing import Literal

from app.config import KnowledgeParams
from app.schemas.common import ExamId
from app.schemas.knowledge import ExamFormat, ForecastOut, TestDate
from app.schemas.profile import Academics, Profile
from app.schemas.programs import Program
from app.schemas.roadmap import ExamRequirementOut

_MANUAL_TARGET_FIELDS: dict[ExamId, str] = {
    "SAT_MATH": "sat_target",
}
_SELF_ESTIMATE_FIELDS: dict[ExamId, str] = {
    "SAT_MATH": "sat_score",
    "ENT_MATH": "ent_trial_score",
}


def build_requirements(
    saved: list[Program],
    profile: Profile,
    exam_formats: dict[ExamId, ExamFormat],
    test_dates: dict[ExamId, list[TestDate]],
    forecasts: dict[ExamId, ForecastOut | None],
    params: KnowledgeParams,
) -> list[ExamRequirementOut]:
    """Contract: 00-contracts-phase2.md §7.3."""
    needs: dict[ExamId, list[tuple[float, str]]] = {}
    for program in saved:
        for requirement in program.requirements:
            if requirement.type != "exam_score" or requirement.exam_id is None:
                continue
            if requirement.threshold is None:
                continue
            needs.setdefault(requirement.exam_id, []).append(
                (requirement.threshold, program.id)
            )

    academics = profile.questionnaire.academics
    out: list[ExamRequirementOut] = []
    for exam_id, thresholds in needs.items():
        ranked = sorted(thresholds, key=lambda item: item[0], reverse=True)
        program_ids = [program_id for _, program_id in ranked]

        target_score = ranked[0][0]
        target_source: Literal["programs", "manual"] = "programs"
        manual_field_name = _MANUAL_TARGET_FIELDS.get(exam_id)
        if manual_field_name is not None:
            manual_field = getattr(academics, manual_field_name)
            if manual_field.mark == "stated" and manual_field.value is not None:
                target_score = float(manual_field.value)
                target_source = "manual"

        exam_format = exam_formats.get(exam_id)
        has_knowledge_model = exam_format is not None
        max_raw_score = exam_format.max_raw_score if exam_format else 0.0

        current_estimate, estimate_note = _current_estimate(
            exam_id, forecasts.get(exam_id), academics, params
        )

        out.append(
            ExamRequirementOut(
                exam_id=exam_id,
                target_score=target_score,
                target_source=target_source,
                max_raw_score=max_raw_score,
                program_ids=program_ids,
                test_dates=sorted(test_dates.get(exam_id, []), key=lambda td: td.date)[
                    :3
                ],
                has_knowledge_model=has_knowledge_model,
                current_estimate=current_estimate,
                estimate_note=estimate_note,
            )
        )
    return out


def _current_estimate(
    exam_id: ExamId,
    forecast: ForecastOut | None,
    academics: Academics,
    params: KnowledgeParams,
) -> tuple[float | None, str]:
    if (
        forecast is not None
        and forecast.coverage >= params.c_cov
        and forecast.predicted_scaled is not None
    ):
        return forecast.predicted_scaled, "по модели знаний"

    field_name = _SELF_ESTIMATE_FIELDS.get(exam_id)
    if field_name is not None:
        field = getattr(academics, field_name)
        if field.value is not None:
            return float(field.value), "по твоей оценке"

    return None, "нет данных"
