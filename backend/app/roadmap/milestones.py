"""B2 roadmap milestone interface."""

from datetime import date, datetime

from app.schemas.common import ExamId, Source
from app.schemas.knowledge import TestDate
from app.schemas.programs import Deadline, Program
from app.schemas.roadmap import ExamRequirementOut, MilestoneOut

EXAM_LABELS: dict[ExamId, str] = {
    "SAT_MATH": "SAT",
    "ENT_MATH": "ЕНТ математика",
}

_RU_MONTHS_GENITIVE = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)

_DEADLINE_KIND_MAP: dict[str, str] = {
    "application": "application",
    "scholarship": "scholarship",
    "exam_registration": "registration",
    "other": "document",
}


def milestone_key(kind: str, ref_id: str, on: date) -> str:
    return f"{kind}:{ref_id}:{on.isoformat()}"


def format_date_ru(on: date) -> str:
    return f"{on.day} {_RU_MONTHS_GENITIVE[on.month - 1]}"


def exam_label(exam_id: ExamId) -> str:
    return EXAM_LABELS.get(exam_id, exam_id)


def _source(entry: TestDate | Deadline) -> Source:
    return Source(
        label=entry.source, url=None, checked_at=entry.checked_at, is_demo=entry.is_demo
    )


def _deadline_title(kind: str, program: Program) -> str:
    titles = {
        "application": f"подача — {program.university}",
        "scholarship": f"стипендия — {program.university}",
        "registration": f"регистрация — {program.university}",
        "document": f"документ — {program.university}",
    }
    return titles.get(kind, program.university)


def build_milestones(
    saved,
    requirements: list[ExamRequirementOut],
    test_dates,
    calendars: list[TestDate],
    marks: dict[str, datetime],
    today,
) -> list[MilestoneOut]:
    """Contract: 00-contracts-phase2.md §7.3."""
    milestones: list[MilestoneOut] = []

    for requirement in requirements:
        exam_id = requirement.exam_id
        candidates = sorted(requirement.test_dates, key=lambda td: td.date)[:2]
        for candidate in candidates:
            reg_key = milestone_key(
                "registration", exam_id, candidate.registration_deadline
            )
            milestones.append(
                MilestoneOut(
                    key=reg_key,
                    kind="registration",
                    date=candidate.registration_deadline,
                    title=f"регистрация {exam_label(exam_id)}",
                    exam_id=exam_id,
                    program_id=None,
                    source=_source(candidate),
                    done=reg_key in marks,
                    done_at=marks.get(reg_key),
                )
            )
            test_key = milestone_key("test", exam_id, candidate.date)
            milestones.append(
                MilestoneOut(
                    key=test_key,
                    kind="test",
                    date=candidate.date,
                    title=f"{exam_label(exam_id)} {format_date_ru(candidate.date)}",
                    exam_id=exam_id,
                    program_id=None,
                    source=_source(candidate),
                    done=test_key in marks,
                    done_at=marks.get(test_key),
                )
            )
            if candidate.late_deadline is not None:
                late_key = milestone_key(
                    "registration", exam_id, candidate.late_deadline
                )
                milestones.append(
                    MilestoneOut(
                        key=late_key,
                        kind="registration",
                        date=candidate.late_deadline,
                        title="поздняя регистрация",
                        exam_id=exam_id,
                        program_id=None,
                        source=_source(candidate),
                        done=late_key in marks,
                        done_at=marks.get(late_key),
                    )
                )
        if not requirement.has_knowledge_model and candidates:
            window_key = milestone_key("window", exam_id, candidates[0].date)
            milestones.append(
                MilestoneOut(
                    key=window_key,
                    kind="window",
                    date=candidates[0].date,
                    title=f"окно подготовки — {exam_label(exam_id)}",
                    exam_id=exam_id,
                    program_id=None,
                    source=_source(candidates[0]),
                    done=window_key in marks,
                    done_at=marks.get(window_key),
                )
            )

    for program in saved:
        for deadline in program.deadlines:
            kind = _DEADLINE_KIND_MAP[deadline.kind]
            key = milestone_key(kind, program.id, deadline.date)
            milestones.append(
                MilestoneOut(
                    key=key,
                    kind=kind,
                    date=deadline.date,
                    title=_deadline_title(kind, program),
                    exam_id=None,
                    program_id=program.id,
                    source=_source(deadline),
                    done=key in marks,
                    done_at=marks.get(key),
                )
            )

    def sort_key(milestone: MilestoneOut) -> tuple[int, date]:
        is_past_done = milestone.date < today and milestone.done
        return (1 if is_past_done else 0, milestone.date)

    return sorted(milestones, key=sort_key)
