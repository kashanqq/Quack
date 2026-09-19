"""The two demo accounts for the defence run (§11 A5, D06).

Everything here is an *input*. The prepared account gets a filled-in profile
and three saved programs; the requirements list, the deadline conflict, the
plan and the forecast are then whatever `app/roadmap` and `app/apply` derive
from those inputs. Nothing writes a conflict, a knowledge state or a grade
directly — a hand-written conflict would prove nothing about the product, and
a hand-written knowledge state would be a lie about a student.

Idempotency comes from comparing against real state rather than from a ledger
table: a profile field that already holds the value is skipped, a program that
is already saved is skipped. So a second run adds no second answer and resets
nothing the jury has done since the first (T22). The clean account is only
ever *created*; wiping it is a separate, explicit command.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import structlog
from pydantic import BaseModel, EmailStr, Field, TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import hash_password
from app.db.repo import profiles as profiles_repo
from app.db.repo import programs as programs_repo
from app.db.repo.users import get_user_by_email, upsert_user
from app.errors import AppError
from app.events import handlers as _handlers  # noqa: F401 — registers B1 rules
from app.events import store as events_store
from app.events.dispatch import RuleDeps
from app.schemas.events import EventIn, EventType, ProfileUpdatedPayload
from app.schemas.profile import ProfileUpdateIn

_logger = structlog.get_logger(__name__)

MANIFEST = Path("demo") / "manifest.json"


class DemoUser(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: str = ""


class DemoUsers(BaseModel):
    prepared: DemoUser
    clean: DemoUser


class ProfileStep(BaseModel):
    path: str
    value: Any
    by: str = "user"


class Expected(BaseModel):
    conflict_kind: str
    conflict_date: str
    why: str = ""
    min_requirements: int = 0
    min_milestones: int = 0


class Warm(BaseModel):
    exams: list[str] = Field(default_factory=list)
    compare_program_ids: list[str] = Field(default_factory=list)
    why: str = ""


class Prepared(BaseModel):
    profile: list[ProfileStep]
    traits: list[str] = Field(default_factory=list)
    saved_programs: list[str]
    expected: Expected
    warm: Warm = Field(default_factory=Warm)


class CleanDiagnostic(BaseModel):
    exam_id: str
    n_tasks: int = Field(ge=1)
    why: str = ""


class Clean(BaseModel):
    diagnostic: CleanDiagnostic


class Manifest(BaseModel):
    version: str
    note: str = ""
    users: DemoUsers
    prepared: Prepared
    clean: Clean


def student_id_of(email: str) -> UUID:
    """The same derivation the ordinary user seed uses — one id per email."""
    return uuid5(NAMESPACE_URL, email.lower())


def load_manifest(data_dir: Path) -> Manifest:
    path = data_dir / MANIFEST
    return Manifest.model_validate(json.loads(path.read_text(encoding="utf-8")))


def validate_manifest(data_dir: Path) -> Manifest:
    """Structure plus the two cross-file facts that make the demo meaningful.

    The conflict the walkthrough shows has to follow from the checked-in
    programs. If someone edits a deadline, this fails at `seed --validate`
    rather than at the defence.
    """
    manifest = load_manifest(data_dir)
    if manifest.users.prepared.email.lower() == manifest.users.clean.email.lower():
        raise ValueError("the two demo accounts must be different users")

    programs = {
        item["id"]: item
        for item in json.loads(
            (data_dir / "programs_floor" / "programs.json").read_text(encoding="utf-8")
        )
    }
    missing = [pid for pid in manifest.prepared.saved_programs if pid not in programs]
    if missing:
        raise ValueError(f"demo saves unknown programs: {', '.join(missing)}")

    expected = manifest.prepared.expected
    if expected.conflict_kind == "same_day_applications":
        same_day = [
            pid
            for pid in manifest.prepared.saved_programs
            if any(
                deadline["kind"] == "application"
                and deadline["date"] == expected.conflict_date
                for deadline in programs[pid].get("deadlines", [])
            )
            and any(
                requirement["type"] == "document"
                for requirement in programs[pid].get("requirements", [])
            )
        ]
        if len(same_day) < 2:
            raise ValueError(
                "the demo conflict is not derivable: fewer than two saved programs "
                f"have a document requirement due on {expected.conflict_date}"
            )
    return manifest


@dataclass
class DemoReport:
    """What `--demo` did and what `--demo-check` sees. Never a password."""

    created_users: list[str] = field(default_factory=list)
    profile_applied: int = 0
    profile_skipped: int = 0
    traits_applied: int = 0
    programs_saved: int = 0
    programs_skipped: int = 0
    warmed: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def lines(self) -> list[str]:
        out = [
            f"users created: {', '.join(self.created_users) or 'none (already there)'}",
            f"profile: {self.profile_applied} applied, {self.profile_skipped} skipped",
            f"traits: {self.traits_applied} applied",
            f"programs: {self.programs_saved} saved, {self.programs_skipped} skipped",
        ]
        if self.warmed:
            out.append(f"warm-up queued: {', '.join(self.warmed)}")
        out.extend(self.notes)
        return out


async def ensure_users(session: AsyncSession, manifest: Manifest) -> list[str]:
    """Create whichever demo account is missing; never reset an existing one."""
    created: list[str] = []
    for user in (manifest.users.prepared, manifest.users.clean):
        email = str(user.email).lower()
        if await get_user_by_email(session, email) is not None:
            continue
        await upsert_user(
            session, student_id_of(email), email, hash_password(user.password)
        )
        created.append(email)
    return created


async def seed_demo(
    session: AsyncSession,
    deps: RuleDeps,
    data_dir: Path,
    *,
    warm: bool = True,
) -> DemoReport:
    """Bring both accounts to the documented starting state, idempotently."""
    manifest = validate_manifest(data_dir)
    report = DemoReport()
    report.created_users = await ensure_users(session, manifest)
    await session.commit()

    student = student_id_of(str(manifest.users.prepared.email))
    await _ensure_graph_student(deps, student)

    await _apply_profile(session, deps, student, manifest.prepared, report)
    await _save_programs(session, deps, student, manifest.prepared, report)
    await session.commit()

    # The plan itself is rebuilt by the ordinary B1 rule, not written here.
    # It is idempotent, and running it explicitly means a re-seed after a
    # graph wipe brings the account back without needing a profile edit.
    report.notes.append(await _rebuild_plan(session, deps, student, manifest))
    await session.commit()

    if warm:
        report.warmed = await _warm(session, deps, student, manifest.prepared)
        # The warm-up intents are durable like any other: written here, handed
        # to ARQ by the caller once this transaction has committed (§9.2).
        await deps.jobs.persist(session)
        await session.commit()
    else:
        report.notes.append("warm-up skipped (--no-warm)")

    clean = student_id_of(str(manifest.users.clean.email))
    report.notes.append(
        f"clean account {manifest.users.clean.email} is registered only: "
        f"the {manifest.clean.diagnostic.n_tasks}-task check is started from the UI "
        "with n_tasks, diag_max is not lowered"
    )
    _logger.info(
        "seed_demo",
        prepared=str(student),
        clean=str(clean),
        applied=report.profile_applied,
        saved=report.programs_saved,
    )
    return report


async def _ensure_graph_student(deps: RuleDeps, student_id: UUID) -> None:
    if deps.graph is None:
        return
    from app.graph.queries import personal as personal_q

    await personal_q.ensure_student(deps.graph, student_id)


async def _apply_profile(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    prepared: Prepared,
    report: DemoReport,
) -> None:
    """Every field goes through the ordinary event + apply path (§11 A5)."""
    for step in prepared.profile:
        current = _current_value(
            await profiles_repo.get_profile(session, student_id), step.path
        )
        if current == _normalized(step.value):
            report.profile_skipped += 1
            continue
        await profiles_repo.apply_profile_update(
            session,
            student_id,
            ProfileUpdateIn(path=step.path, value=step.value, by=step.by),
        )
        await events_store.append(
            session,
            deps.redis,
            EventIn(
                type=EventType.profile_updated,
                payload=ProfileUpdatedPayload(
                    field=step.path, value=step.value, by=step.by
                ).model_dump(mode="json"),
                student_id=student_id,
            ),
            deps,
        )
        report.profile_applied += 1

    profile = await profiles_repo.get_profile(session, student_id)
    for line in prepared.traits:
        if line in profile.traits.verbatim:
            continue
        await profiles_repo.apply_profile_update(
            session,
            student_id,
            ProfileUpdateIn(path="traits.verbatim", value=line, by="user"),
        )
        report.traits_applied += 1


async def _save_programs(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    prepared: Prepared,
    report: DemoReport,
) -> None:
    saved = {
        item.program_id for item in await programs_repo.list_saved(session, student_id)
    }
    for program_id in prepared.saved_programs:
        if program_id in saved:
            report.programs_skipped += 1
            continue
        try:
            await programs_repo.save_program(session, student_id, program_id)
        except AppError as exc:
            report.notes.append(f"{program_id}: {exc.message}")
            continue
        await events_store.append(
            session,
            deps.redis,
            EventIn(
                type=EventType.program_saved,
                payload={"program_id": program_id},
                student_id=student_id,
            ),
            deps,
        )
        report.programs_saved += 1


async def _rebuild_plan(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, manifest: Manifest
) -> str:
    """Ask B1 to assemble the plan from the profile that was just written."""
    if deps.graph is None:
        return "plan not rebuilt: Neo4j unavailable"
    from app.apply.sets import rebuild_sets

    built: list[str] = []
    for exam_id in manifest.prepared.warm.exams or ["SAT_MATH"]:
        result = await rebuild_sets(session, deps, student_id, exam_id)  # type: ignore[arg-type]
        total = len(result.upcoming) + len(result.done) + (1 if result.current else 0)
        built.append(f"{exam_id}:{total}")
    return f"plan rebuilt ({', '.join(built)} sets)"


async def _warm(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, prepared: Prepared
) -> list[str]:
    """Queue the existing phase-4 jobs for what the walkthrough opens.

    No new generator and no waiting: the intents go through the durable
    outbox like any other, and `--demo-check` reports whether they finished.
    """
    from app.db.repo import sets as sets_repo

    queued: list[str] = []
    for exam_id in prepared.warm.exams:
        for item in await sets_repo.list_sets(session, student_id, exam_id):  # type: ignore[arg-type]
            if item.status not in ("current", "upcoming"):
                continue
            deps.jobs.enqueue(
                "bulk",
                "pregenerate_set",
                job_id=f"pregen:{item.id}:demo",
                set_id=str(item.id),
                student_id=str(student_id),
            )
            queued.append(f"pregenerate_set:{item.id}")
            break  # только текущий сет: прогрев не должен съесть бюджет
    ids = prepared.warm.compare_program_ids
    if len(ids) >= 2:
        deps.jobs.enqueue(
            "bulk",
            "realism_texts",
            job_id=f"realism:{student_id}:demo",
            student_id=str(student_id),
            program_ids=list(ids),
        )
        deps.jobs.enqueue(
            "bulk",
            "compare_text",
            job_id=f"compare:{student_id}:demo",
            student_id=str(student_id),
            program_ids=list(ids),
        )
        queued.extend(["realism_texts", "compare_text"])
    return queued


def _current_value(profile: Any, path: str) -> Any:
    section_name, _, leaf_name = path.partition(".")
    section = getattr(profile.questionnaire, section_name, None)
    if section is None:
        return None
    field_ = getattr(section, leaf_name, None)
    return _normalized(getattr(field_, "value", None))


def _normalized(value: Any) -> Any:
    """Compare what the manifest says with what the profile stores.

    Dates and enums come back as typed objects, so both sides are reduced to
    their JSON form before comparison — otherwise every run would rewrite
    every date field and log a second `profile.updated` event.
    """
    return TypeAdapter(Any).dump_python(value, mode="json")


@dataclass
class DemoStatus:
    """`--demo-check`: is the demo ready, and what is still in flight?"""

    lines: list[str] = field(default_factory=list)
    ready: bool = True

    def add(self, ok: bool, text: str) -> None:
        self.lines.append(f"[{'ok' if ok else '!!'}] {text}")
        self.ready = self.ready and ok


async def check_demo(
    session: AsyncSession, deps: RuleDeps, data_dir: Path
) -> DemoStatus:
    """State of both accounts, the derived conflict, the caches and the queue.

    Read-only, and it prints no password: the credentials live in the
    manifest and in the operator's notes, not in a command's output (§17).
    """
    from sqlalchemy import func, select

    from app.db.models import GeneratedText, JobOutbox
    from app.db.repo import outbox as outbox_repo
    from app.db.repo import sets as sets_repo
    from app.events import recovery
    from app.roadmap import conflicts as roadmap_conflicts
    from app.roadmap import milestones as roadmap_milestones
    from app.roadmap import requirements as roadmap_requirements
    from app.sets import static_snapshot

    status = DemoStatus()
    manifest = validate_manifest(data_dir)
    status.add(True, f"manifest v{manifest.version} validated")

    prepared = student_id_of(str(manifest.users.prepared.email))
    clean = student_id_of(str(manifest.users.clean.email))
    for label, email in (
        ("prepared", str(manifest.users.prepared.email)),
        ("clean", str(manifest.users.clean.email)),
    ):
        user = await get_user_by_email(session, email.lower())
        status.add(user is not None, f"{label} account {email}")

    profile = await profiles_repo.get_profile(session, prepared)
    filled = sum(
        1
        for step in manifest.prepared.profile
        if _current_value(profile, step.path) == _normalized(step.value)
    )
    status.add(
        filled == len(manifest.prepared.profile),
        f"profile fields {filled}/{len(manifest.prepared.profile)}",
    )

    saved = await programs_repo.list_saved_programs(session, prepared)
    status.add(
        len(saved) >= len(manifest.prepared.saved_programs),
        f"saved programs {len(saved)}/{len(manifest.prepared.saved_programs)}",
    )

    # The conflict is recomputed here exactly the way `/overview` does it,
    # from the saved programs — never read from a stored "expected" answer.
    required = roadmap_requirements.build_requirements(
        saved, profile, {}, {}, {}, deps.params
    )
    today = deps.now().date()
    marks = roadmap_milestones.build_milestones(saved, required, {}, [], {}, today)
    found = roadmap_conflicts.find_conflicts(marks, saved, {})
    expected = manifest.prepared.expected
    status.add(
        len(required) >= expected.min_requirements,
        f"derived requirements: {len(required)}",
    )
    status.add(
        len(marks) >= expected.min_milestones, f"derived milestones: {len(marks)}"
    )
    status.add(
        any(item.kind == expected.conflict_kind for item in found),
        f"derived conflict {expected.conflict_kind} on {expected.conflict_date} "
        f"({len(found)} conflicts total)",
    )

    texts = int(
        await session.scalar(
            select(func.count())
            .select_from(GeneratedText)
            .where(
                GeneratedText.student_id == prepared, GeneratedText.status == "ready"
            )
        )
        or 0
    )
    status.add(texts > 0, f"ready generated texts for the prepared account: {texts}")

    for label, student in (("prepared", prepared), ("clean", clean)):
        for exam_id in ("SAT_MATH", "ENT_MATH"):
            items = await sets_repo.list_sets(session, student, exam_id)  # type: ignore[arg-type]
            if items:
                status.lines.append(f"[..] {label} {exam_id}: {len(items)} sets")

    active = int(
        await session.scalar(
            select(func.count())
            .select_from(JobOutbox)
            .where(JobOutbox.status.in_(outbox_repo.ACTIVE))
        )
        or 0
    )
    status.lines.append(f"[..] job intents still active: {active}")
    failed = int(
        await session.scalar(
            select(func.count())
            .select_from(JobOutbox)
            .where(JobOutbox.status == "failed")
        )
        or 0
    )
    status.add(failed == 0, f"failed job intents: {failed}")
    status.add(
        await recovery.pending_count(session) == 0,
        "graph backlog is empty",
    )
    status.add(static_snapshot.available(), "canonical snapshot readable without Neo4j")
    status.add(deps.graph is not None, "Neo4j reachable")
    return status


async def reset_clean(session: AsyncSession, data_dir: Path) -> int:
    """Wipe the clean account so the live path can be shown again.

    Deliberately not part of `--demo`: a seed that resets an account would
    throw away whatever the jury just did on it. The allowlist is the
    manifest — this command cannot touch any other user (§17).
    """
    from sqlalchemy import delete

    from app.db.models import (
        DiagnosticRun,
        Event,
        MockRun,
        Set,
        TaskInstance,
    )

    manifest = validate_manifest(data_dir)
    clean = student_id_of(str(manifest.users.clean.email))
    removed = 0
    for model in (TaskInstance, DiagnosticRun, MockRun, Set, Event):
        result = await session.execute(
            delete(model).where(model.student_id == clean)  # type: ignore[attr-defined]
        )
        removed += int(result.rowcount or 0)
    await session.commit()
    _logger.info("demo_clean_reset", student_id=str(clean), rows=removed)
    return removed
