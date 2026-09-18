"""B2 roadmap conflict interface."""

from collections import defaultdict
from datetime import date
from itertools import combinations

from app.roadmap.milestones import exam_label, format_date_ru, milestone_key
from app.schemas.common import ExamId
from app.schemas.programs import Program
from app.schemas.roadmap import ConflictOut, MilestoneOut

_BINDING_WORDS = ("binding", "обязательство")


def _has_document_requirement(program: Program) -> bool:
    return any(requirement.type == "document" for requirement in program.requirements)


def _is_binding(description: str) -> bool:
    lowered = description.lower()
    return any(word in lowered for word in _BINDING_WORDS)


def _requires_exam(program: Program, exam_id: ExamId) -> bool:
    return any(
        requirement.type == "exam_score" and requirement.exam_id == exam_id
        for requirement in program.requirements
    )


def _same_day_applications(
    milestones: list[MilestoneOut], saved: list[Program]
) -> list[ConflictOut]:
    document_programs = {
        program.id for program in saved if _has_document_requirement(program)
    }
    universities = {program.id: program.university for program in saved}

    by_date: dict[date, list[MilestoneOut]] = defaultdict(list)
    for milestone in milestones:
        if (
            milestone.kind == "application"
            and milestone.program_id in document_programs
        ):
            by_date[milestone.date].append(milestone)

    conflicts: list[ConflictOut] = []
    for on, group in by_date.items():
        distinct = {m.program_id: m for m in group}
        if len(distinct) < 2:
            continue
        names = [universities.get(pid, pid) for pid in distinct]
        conflicts.append(
            ConflictOut(
                kind="same_day_applications",
                milestone_keys=[m.key for m in distinct.values()],
                text=(
                    f"Конфликт: подача документов {', '.join(names)} "
                    f"в один день, {format_date_ru(on)}."
                ),
                options=[
                    "подать документы заранее по одной из программ",
                    "попросить продление у одной из программ",
                ],
            )
        )
    return conflicts


def _exclusive_rounds(saved: list[Program]) -> list[ConflictOut]:
    conflicts: list[ConflictOut] = []
    for program_a, program_b in combinations(saved, 2):
        for deadline_a in program_a.deadlines:
            if not deadline_a.round or "early" not in deadline_a.round.lower():
                continue
            if not any(
                requirement.type == "other" and _is_binding(requirement.description)
                for requirement in program_a.requirements
            ):
                continue
            for deadline_b in program_b.deadlines:
                if deadline_b.date != deadline_a.date:
                    continue
                if not deadline_b.round or "early" not in deadline_b.round.lower():
                    continue
                if not any(
                    requirement.type == "other" and _is_binding(requirement.description)
                    for requirement in program_b.requirements
                ):
                    continue
                conflicts.append(
                    ConflictOut(
                        kind="exclusive_rounds",
                        milestone_keys=[
                            milestone_key("application", program_a.id, deadline_a.date),
                            milestone_key("application", program_b.id, deadline_b.date),
                        ],
                        text=(
                            "Конфликт: обязательные early-раунды "
                            f"{program_a.university} и {program_b.university} "
                            "нельзя совместить — оба требуют обязательства до "
                            f"{format_date_ru(deadline_a.date)}."
                        ),
                        options=[
                            "выбрать одну программу из двух early-раундов",
                            "перевести одну программу в обычный раунд",
                        ],
                    )
                )
    return conflicts


def _exam_after_deadline(
    saved: list[Program], planned_test_dates: dict[ExamId, date | None]
) -> list[ConflictOut]:
    conflicts: list[ConflictOut] = []
    for exam_id, planned_date in planned_test_dates.items():
        if planned_date is None:
            continue
        for program in saved:
            if not _requires_exam(program, exam_id):
                continue
            for deadline in program.deadlines:
                if deadline.kind != "application" or planned_date <= deadline.date:
                    continue
                round_word = (
                    "early-подаче"
                    if deadline.round and "early" in deadline.round.lower()
                    else "подаче"
                )
                conflicts.append(
                    ConflictOut(
                        kind="exam_after_deadline",
                        milestone_keys=[
                            milestone_key("test", exam_id, planned_date),
                            milestone_key("application", program.id, deadline.date),
                        ],
                        text=(
                            f"Конфликт: {exam_label(exam_id)} "
                            f"{format_date_ru(planned_date)} не успевает к "
                            f"{round_word} {program.university} "
                            f"{format_date_ru(deadline.date)}"
                        ),
                        options=[
                            "перенести дату экзамена раньше",
                            "договориться об исключении из этой подачи",
                        ],
                    )
                )
    return conflicts


def find_conflicts(
    milestones: list[MilestoneOut],
    saved: list[Program],
    planned_test_dates: dict[ExamId, date | None],
) -> list[ConflictOut]:
    """Contract: 00-contracts-phase2.md §7.3."""
    return [
        *_same_day_applications(milestones, saved),
        *_exclusive_rounds(saved),
        *_exam_after_deadline(saved, planned_test_dates),
    ]
