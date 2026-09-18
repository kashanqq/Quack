"""ARQ job stubs (docs/tz/30-B2.md §5.5).

Signatures only: an ARQ worker context first, then ``request_id``, then the
task's own named parameters. B3 wires these into ``app/workers/registry.py``
on sync day; nothing here talks to Postgres, Neo4j or Redis yet.
"""

from __future__ import annotations

from uuid import UUID


async def observe_chat(
    ctx: dict, request_id: str, chat_id: UUID, student_id: UUID
) -> None:
    """Extract observations from a chat window and reconcile them into the
    knowledge model (memory-architecture §8.1).

    Queue: `interactive` (tech-stack §2.5). Trigger: every N chat messages,
    a topic switch, or an explicit button. Timeout: 30 s.
    """
    raise NotImplementedError("phase 2")


async def pregenerate_set(
    ctx: dict, request_id: str, set_id: UUID, student_id: UUID
) -> None:
    """Pre-generate guidelines and explanations for every topic in a set so
    they're ready before the student opens them.

    Queue: `bulk` (tech-stack §2.5). Trigger: `set.opened`. Timeout: 90 s.
    """
    raise NotImplementedError("phase 2")


async def set_summary(
    ctx: dict, request_id: str, set_id: UUID, student_id: UUID
) -> None:
    """Build the short end-of-set report — what's closed, which skills
    firmed up, which misconceptions resolved (product-logic §4.1).

    Queue: `interactive` (tech-stack §2.5). Trigger: `set.completed`.
    Timeout: 30 s.
    """
    raise NotImplementedError("phase 2")


async def propose_personal_nodes(
    ctx: dict, request_id: str, set_id: UUID, student_id: UUID
) -> None:
    """Decide whether any canonical skill entering a new set needs a
    personal node under it (product-logic §5.2).

    Queue: `interactive` (tech-stack §2.5). Trigger: `set.opened`.
    Timeout: 30 s.
    """
    raise NotImplementedError("phase 2")


async def soft_match(
    ctx: dict, request_id: str, student_id: UUID, program_ids: list[str]
) -> None:
    """Score soft fit between the student's trait summary and each given
    program's environment text (product-logic §3.3).

    Queue: `bulk` (tech-stack §2.5). Trigger: a change to the trait summary
    or new candidate programs. Timeout: 20 s per program.
    """
    raise NotImplementedError("phase 2")


async def extract_program(ctx: dict, request_id: str, url: str) -> None:
    """Fetch the program page at `url` and extract `Program` fields via
    `MODEL_BULK` structured output (tech-stack §4.6, product-logic §5.1).

    Queue: `bulk` (tech-stack §2.5). Trigger: a new program surfaces in
    search. Timeout: 60 s.
    """
    raise NotImplementedError("phase 2")
