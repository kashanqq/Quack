"""The single event-to-B1-apply registration table."""

from app.apply.aggregates import run as _aggregates_run  # noqa: F401 (jobs_infra)
from app.apply.dispute import apply_dispute
from app.apply.observation import (
    apply_misconception_canonized,
    apply_misconception_personal_created,
    apply_observation_extracted,
)
from app.apply.profile_updated import apply_profile_updated
from app.apply.quack import (
    apply_accept,
    enqueue_recs_urgent,
    log_decline,
    on_profile_updated_enqueue,
)
from app.apply.sets import (
    on_program_change,
    on_run_completed,
    on_set_change,
    on_set_opened_enqueue,
)
from app.apply.summary_stats import on_set_completed
from app.apply.task_answered import apply_task_answered, apply_task_skipped
from app.apply.texts import on_topic_opened
from app.events.dispatch import on
from app.schemas.events import EventType

on(EventType.task_answered)(apply_task_answered)
on(EventType.task_skipped)(apply_task_skipped)
on(EventType.task_timed_out)(apply_task_skipped)
on(EventType.profile_updated)(apply_profile_updated)
on(EventType.program_saved)(on_program_change)
on(EventType.program_removed)(on_program_change)
on(EventType.set_switched_by_user)(on_set_change)
on(EventType.set_deadline_changed)(on_set_change)
on(EventType.misconception_disputed)(apply_dispute)
on(EventType.misconception_undisputed)(apply_dispute)
on(EventType.diagnostic_completed)(on_run_completed)
on(EventType.mock_completed)(on_run_completed)
# Phase 3 — the observer and the canonization of proposed misconceptions.
on(EventType.observation_extracted)(apply_observation_extracted)
on(EventType.misconception_canonized)(apply_misconception_canonized)
on(EventType.misconception_personal_created)(apply_misconception_personal_created)

# --- Phase 4 (docs/tz/40-phase4-background-quack.md §2.2) ---
# Обработчики фазы 4 только считают уже известные факты и кладут задачи в
# outbox: ни один из них не пишет в граф и не ходит в модель.
on(EventType.set_opened)(on_set_opened_enqueue)
on(EventType.set_completed)(on_set_completed)
on(EventType.topic_opened)(on_topic_opened)
on(EventType.profile_updated)(on_profile_updated_enqueue)
on(EventType.recommendation_accepted)(apply_accept)
on(EventType.recommendation_declined)(log_decline)
# Всё, из-за чего план мог устареть прямо сейчас (§0.2).
on(EventType.program_saved)(enqueue_recs_urgent)
on(EventType.program_removed)(enqueue_recs_urgent)
on(EventType.set_completed)(enqueue_recs_urgent)
on(EventType.set_deadline_changed)(enqueue_recs_urgent)
on(EventType.set_switched_by_user)(enqueue_recs_urgent)
on(EventType.diagnostic_completed)(enqueue_recs_urgent)
on(EventType.mock_completed)(enqueue_recs_urgent)
on(EventType.milestone_done)(enqueue_recs_urgent)
