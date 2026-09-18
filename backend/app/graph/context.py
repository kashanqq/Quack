"""Context assembler for the tutor agent (phase 2).

Source: memory-architecture-quack.md §9.2 (slots), 20-B1.md §2.6.
Phase 1: only the TopicContext shape is declared, build_topic_context raises.
"""

from __future__ import annotations

from uuid import UUID

from neo4j import AsyncDriver
from pydantic import BaseModel


class TopicContext(BaseModel):
    """Slots for the tutor's context block (memory-architecture §9.2).

    Each slot is a list of short strings, already formatted for injection.
    Order in the injected block: topic, strengths, prerequisite_gaps,
    active_misconceptions, under_watch, low_data, deadline, profile, previous_set.
    """

    topic: list[str] = []
    strengths: list[str] = []
    prerequisite_gaps: list[str] = []
    active_misconceptions: list[str] = []
    under_watch: list[str] = []
    low_data: list[str] = []
    deadline: list[str] = []
    profile: list[str] = []
    previous_set: list[str] = []


async def build_topic_context(
    driver: AsyncDriver, student_id: UUID, skill_id: str, set_id: UUID
) -> TopicContext:
    """Phase 2: assemble the tutor context from 4 parallel Cypher queries.

    See memory-architecture-quack.md §9.2 for slot limits and sources.
    """
    raise NotImplementedError("phase 2")
