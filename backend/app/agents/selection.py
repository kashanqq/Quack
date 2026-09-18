"""Selection assistant — stub run() and its tool registry (docs/tz/30-B2.md §5.2).

The assistant never decides matching, cost thresholds or requirement status
itself (product-logic §3.3: "not letting the language model into hard
factors") — it only talks, and reaches for one of these tools whenever a
turn needs a fact, a write, or a computation it isn't allowed to invent.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.agents.router import AgentDeps
from app.llm.tools import ToolCtx, ToolRegistry, tool
from app.schemas.chat import ChatCtx, ChatMessageIn, MessageOut, StreamEvent
from app.schemas.common import ExamId
from app.schemas.profile import Profile


async def run(
    ctx: ChatCtx,
    message: ChatMessageIn,
    history: list[MessageOut],
    profile: Profile,
    deps: AgentDeps,
) -> AsyncIterator[StreamEvent]:
    """Drive one turn of the selection chat (product-logic §3.2).

    Stub for phase 1: the real implementation is the tool-calling loop over
    ``SELECTION_TOOLS`` (via ``app.llm.loop.run_tool_loop``) plus postcheck,
    landing in phase 2. ``history`` is the persisted read-model for this
    chat (``MessageOut``, chronological, oldest first) and ``profile`` is
    the student's current questionnaire and traits (``app.schemas.profile``)
    — both already have real contracts, so they're typed concretely rather
    than left as placeholders.
    """
    raise NotImplementedError("phase 2")


class UpdateProfileArgs(BaseModel):
    path: str = Field(
        description=(
            "Dotted path into the student's profile, using the exact field "
            "names from product-logic §3.1's questionnaire (e.g. "
            "'preferences.countries', 'academics.sat_target', "
            "'preferences.grant_need') or 'traits.summary' / "
            "'traits.verbatim' for the free-text trait layer. A path "
            "outside these two trees is rejected."
        )
    )
    value: Any = Field(
        description=(
            "The new value, in that field's own shape (string, number, "
            "list, or an ISO 8601 date for date fields). For "
            "'traits.verbatim' this is the one quote to append, not the "
            "whole list; for 'traits.summary' it is the full replacement "
            "text of the running preference summary."
        )
    )
    by: Literal["assistant", "user"] = Field(
        default="assistant",
        description=(
            "Who is recorded as the source of this change. Leave at the "
            "default — the assistant tool call always attributes to "
            "itself, not to the student directly."
        ),
    )


@tool(
    name="update_profile",
    description=(
        "Writes one field of the student's profile — a questionnaire "
        "answer or the free-text trait summary/quote — so it persists and "
        "feeds matching, comparison and the prep side. Call it as soon as "
        "a message states a concrete fact about the student (a number, a "
        "country, a preference), not for facts that only matter within "
        "this reply."
    ),
    read_only=False,
)
async def update_profile(args: UpdateProfileArgs, ctx: ToolCtx) -> Any:
    raise NotImplementedError("phase 2")


class RunMatchingArgs(BaseModel):
    limit: int = Field(
        default=5,
        description=(
            "How many ranked programs to return. Keep this small (the "
            "default is meant for normal use) — results are read out to "
            "the student one by one, not browsed as a list."
        ),
    )


@tool(
    name="run_matching",
    description=(
        "Runs the deterministic ranking algorithm (product-logic §3.3) "
        "over the program dataset using the student's current "
        "questionnaire, trait summary and, when available, a predicted "
        "exam score, and returns the top programs with their realism "
        "level and the hard/soft factors behind it. Call this to produce "
        "or refresh the actual recommendation list — never estimate or "
        "guess a ranking yourself."
    ),
    read_only=True,
)
async def run_matching(args: RunMatchingArgs, ctx: ToolCtx) -> Any:
    raise NotImplementedError("phase 2")


class CompareArgs(BaseModel):
    program_ids: list[str] = Field(
        description=(
            "Two to four program ids to place side by side — ids the "
            "student named or that a prior run_matching/get_program_facts "
            "call already surfaced, e.g. ['eth-cs', 'nu-cs']."
        )
    )


@tool(
    name="compare",
    description=(
        "Builds a side-by-side comparison of two to four specific "
        "programs (product-logic §3.4): where their requirement status "
        "differs, how they stack up on the student's own top priorities, "
        "and standard quality metrics (mobility, research, ranking, cost, "
        "duration, language, scholarships). Call it only once specific "
        "programs are on the table — it is not a way to discover new ones "
        "(use run_matching or query_dataset for that)."
    ),
    read_only=True,
)
async def compare(args: CompareArgs, ctx: ToolCtx) -> Any:
    raise NotImplementedError("phase 2")


class SaveProgramArgs(BaseModel):
    program_id: str = Field(
        description="Id of the single program to add to the student's saved list."
    )


@tool(
    name="save_program",
    description=(
        "Adds one program to the student's saved list (product-logic §3.5), "
        "which is what unlocks a preparation plan for its exams and its own "
        "deadlines and requirements view. Call it only right after the "
        "student has explicitly confirmed they want to save that specific "
        "program — never as a side effect of matching or comparing, and "
        "never to save more than one program at a time."
    ),
    read_only=False,
)
async def save_program(args: SaveProgramArgs, ctx: ToolCtx) -> Any:
    raise NotImplementedError("phase 2")


class ProgramFactsArgs(BaseModel):
    program_id: str = Field(description="Id of the program to fetch stored facts for.")


@tool(
    name="get_program_facts",
    description=(
        "Returns everything stored about one program: university, country, "
        "city, direction, language, duration, tuition and living cost, "
        "admission requirements with their thresholds, deadlines, "
        "scholarship notes and the free-text environment description, each "
        "with its source and check date. This is the only way to state a "
        "program's numbers, dates or requirements — anything stated "
        "without it fails the assistant's postcheck against tool results."
    ),
    read_only=True,
)
async def get_program_facts(args: ProgramFactsArgs, ctx: ToolCtx) -> Any:
    raise NotImplementedError("phase 2")


class AdmissionRouteArgs(BaseModel):
    country_id: str = Field(
        description=(
            "ISO alpha-2 country code (00-contracts.md §4.1), e.g. 'KZ' or 'US'."
        )
    )


@tool(
    name="get_admission_route",
    description=(
        "Looks up how admission works in a country in general — "
        "application rounds, what programs there typically require, "
        "country-specific mechanics such as grant thresholds — from the "
        "shared admissions knowledge base (product-logic §5.0), "
        "independent of any single program. Use it for 'how does "
        "admission work in X' questions; use get_program_facts instead "
        "for one program's own requirements."
    ),
    read_only=True,
)
async def get_admission_route(args: AdmissionRouteArgs, ctx: ToolCtx) -> Any:
    raise NotImplementedError("phase 2")


class ExamFormatArgs(BaseModel):
    exam_id: ExamId = Field(description="Which exam's format to look up.")


@tool(
    name="get_exam_format",
    description=(
        "Returns the official structure of one exam from the knowledge "
        "base: sections, number and type of items, timing, scoring and "
        "partial-credit rules, calculator policy, adaptivity, and the "
        "area/difficulty distribution used to build mocks. Call it "
        "whenever a reply needs a specific exam fact (section count, "
        "points, whether a calculator is allowed) instead of relying on "
        "memory — exam facts stated without it fail postcheck."
    ),
    read_only=True,
)
async def get_exam_format(args: ExamFormatArgs, ctx: ToolCtx) -> Any:
    raise NotImplementedError("phase 2")


class QueryDatasetArgs(BaseModel):
    question: str = Field(
        description=(
            "The student's question about the program dataset, close to "
            "their own words, e.g. 'where can I study my major' or 'how "
            "much does it cost in Germany'."
        )
    )
    country: str | None = Field(
        default=None,
        description=(
            "ISO alpha-2 country code to narrow the search, if the "
            "question names one country. Leave unset otherwise."
        ),
    )
    direction: str | None = Field(
        default=None,
        description=(
            "Field of study to narrow the search, if the question names "
            "one. Leave unset otherwise."
        ),
    )


@tool(
    name="query_dataset",
    description=(
        "Answers an aggregate or exploratory question over the whole "
        "program dataset — availability by field of study, typical cost "
        "in a country, how many options exist for a direction — without "
        "pinning to one program (product-logic §3.2's 'вопрос по "
        "данным'). Use it for 'what's out there' questions; use "
        "get_program_facts for a program the student has already named, "
        "and run_matching to actually produce the ranked recommendation "
        "list."
    ),
    read_only=True,
)
async def query_dataset(args: QueryDatasetArgs, ctx: ToolCtx) -> Any:
    raise NotImplementedError("phase 2")


SELECTION_TOOLS = ToolRegistry()
for _spec in (
    update_profile,
    run_matching,
    compare,
    save_program,
    get_program_facts,
    get_admission_route,
    get_exam_format,
    query_dataset,
):
    SELECTION_TOOLS.register(_spec)
del _spec
