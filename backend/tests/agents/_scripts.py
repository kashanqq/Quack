"""Shared helpers for phase-3 agent tests: FakeLLMClient scripts and
repository fakes (docs/tz/phase3-agents.md §6.1–§6.2)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

from app.llm.fake import text_turn, tool_call_turn
from app.schemas.chat import StreamEvent, ToolCall
from app.schemas.common import FactorStatus, Source
from app.schemas.matching import FactorOut, MatchingOut, MatchOut
from app.schemas.programs import Program

TC = tool_call_turn
TXT = text_turn


def calls_turn(*calls: tuple[str, dict]) -> list[StreamEvent]:
    """One stream turn with several tool calls (ids c1, c2, …)."""
    return [
        ToolCall(tool=name, args=args, call_id=f"c{index + 1}")
        for index, (name, args) in enumerate(calls)
    ]


async def collect(stream) -> list[Any]:
    return [event async for event in stream]


def program(program_id: str, **overrides: Any) -> Program:
    values: dict[str, Any] = dict(
        id=program_id,
        university=f"Uni {program_id}",
        country="DE",
        city="Berlin",
        direction="Computer Science",
        language="English",
        tuition_per_year=1500,
        living_per_year=9000,
        currency="EUR",
        requirements=[],
        deadlines=[],
        source_url=f"https://example.com/{program_id}",
        checked_at=date(2026, 9, 1),
        is_demo=True,
        extracted_auto=False,
        flagged=False,
    )
    values.update(overrides)
    return Program(**values)


def matching_out(*items: tuple[str, str], factor_status: FactorStatus = "above"):
    """`matching_out(("A", "possible"), ("B", "try"))`."""
    source = Source(label="x", url=None, checked_at=None, is_demo=True)
    return MatchingOut(
        items=[
            MatchOut(
                program=program(pid),
                realism=realism,
                factors=[
                    FactorOut(
                        id="budget",
                        kind="hard",
                        status=factor_status,
                        text="budget",
                        source=source,
                        weight=1.0,
                    )
                ],
                assumptions=[],
                score=1.0 - index * 0.1,
                fits_text=None,
                soft_pending=True,
            )
            for index, (pid, realism) in enumerate(items)
        ],
        total=len(items),
        profile_readiness=0.5,
        forecast_used=False,
        empty_reason=None,
    )


def patch_selection_io(monkeypatch, *, profile, saved=None, forecasts=None):
    """Fake every repository `selection.run` touches outside the tools."""
    from app.agents import selection

    monkeypatch.setattr(
        selection.programs_repo,
        "list_saved_programs",
        AsyncMock(return_value=saved or []),
    )
    monkeypatch.setattr(
        selection.forecast_repo,
        "get",
        AsyncMock(side_effect=lambda _s, _sid, exam: (forecasts or {}).get(exam)),
    )
    monkeypatch.setattr(
        selection.profiles_repo, "get_profile", AsyncMock(return_value=profile)
    )


NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


def new_id() -> str:
    return str(uuid4())
