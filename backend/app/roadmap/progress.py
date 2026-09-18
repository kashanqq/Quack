"""B2 roadmap progress interface."""

from app.schemas.knowledge import ForecastOut, SkillStateView
from app.schemas.roadmap import ExamProgress, ExamRequirementOut, MilestoneOut


def exam_progress(
    requirement: ExamRequirementOut,
    states: list[SkillStateView],
    forecast: ForecastOut | None,
    milestones: list[MilestoneOut],
) -> ExamProgress:
    """Contract: 00-contracts-phase2.md §7.3."""
    total_need = sum(state.weight * state.p_target for state in states)
    if total_need > 0:
        closed_need = sum(
            state.weight * min(state.p_recall, state.p_target) for state in states
        )
        readiness = closed_need / total_need
    else:
        readiness = 0.0

    exam_milestones = [
        milestone
        for milestone in milestones
        if milestone.exam_id == requirement.exam_id
    ]

    return ExamProgress(
        exam_id=requirement.exam_id,
        readiness=readiness,
        forecast=forecast,
        milestones_done=sum(1 for milestone in exam_milestones if milestone.done),
        milestones_total=len(exam_milestones),
    )
