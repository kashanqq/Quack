"""The single Phase 2 event-to-B1-apply registration table."""

from app.apply.dispute import apply_dispute
from app.apply.profile_updated import apply_profile_updated
from app.apply.sets import on_program_change, on_run_completed, on_set_change
from app.apply.task_answered import apply_task_answered, apply_task_skipped
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
