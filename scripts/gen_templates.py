"""Bulk task-template generator skeleton (30-B2-phase2.md §0.1 п.2, §3.1).

Reads a skill's data (id, name, description), the exam format, the area's
misconception library and up to two existing templates as a format example,
and asks ``MODEL_BULK`` via ``LLMClient.structured`` for a batch of new
``TaskTemplateSpec`` objects per skill. Each generated template is run
through ``validate_template`` on 50 seeds; only templates that pass are
written, one file per template named by ``template_id``, and ``seed.py
--validate`` is run over the data tree afterwards. ``--dry-run`` prints the
prompt(s) and the target skill list without calling the model or writing
anything.

This is the skeleton from the first phase-2 push: the full version (manual
review checklist, `--coverage` reporting) lands later in the same phase.

Usage (mirrors scripts/seed.py's own invocation convention):
    cd backend && uv run python ../scripts/gen_templates.py \
        --exam SAT_MATH --area alg --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

# Windows' default console/pipe encoding (e.g. cp1251) can't hold the
# Russian prompt text and math symbols (−, ×, √) this script prints —
# force UTF-8 regardless of host locale, same reasoning as PYTHONUTF8=1.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pydantic import BaseModel  # noqa: E402
from redis.asyncio import Redis  # noqa: E402
from redis.exceptions import RedisError  # noqa: E402

from app.config import Settings  # noqa: E402
from app.errors import LLMUnavailable  # noqa: E402
from app.llm.client import LLMClient  # noqa: E402
from app.llm.prompts import load_prompt  # noqa: E402
from app.schemas.llm import LLMMessage  # noqa: E402
from app.schemas.tasks import TaskTemplateSpec  # noqa: E402
from app.tasks.generate import generate_instance, validate_template  # noqa: E402

_EXAM_DIR = {"SAT_MATH": "sat", "ENT_MATH": "ent"}
_SKILLS_FILE = {"SAT_MATH": "sat_math.json", "ENT_MATH": "ent_math.json"}


class GeneratedTemplates(BaseModel):
    """Structured-output envelope: ``list[TaskTemplateSpec]`` per §3.1 isn't
    itself a ``BaseModel``, so ``client.structured`` needs it wrapped —
    same pattern as ``ObservationOut`` wrapping ``list[Observation]``."""

    templates: list[TaskTemplateSpec]


GeneratedTemplates.model_rebuild()


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_skills_doc(data_dir: Path, exam: str) -> dict:
    return _load_json(data_dir / "skills" / _SKILLS_FILE[exam])


def _load_all_skill_docs(data_dir: Path) -> list[dict]:
    return [_load_json(path) for path in sorted((data_dir / "skills").glob("*.json"))]


def _skill_descriptor_index(skill_docs: list[dict]) -> dict[str, dict]:
    """Full skill descriptors (name, description, effort_h, ...), pooled
    across every ``data/skills/*.json``. A skill shared by two exams
    (00-contracts.md §4.1: ``math.<area3>.<name>``) is described once, in
    whichever exam file owns it — ``ent_math.json``'s own ``areas[].skills``
    only carries ``{id, weight}`` refs to it, so the description has to be
    looked up here rather than assumed to live in the requested exam's file."""
    index: dict[str, dict] = {}
    for doc in skill_docs:
        for skill in doc["skills"]:
            index.setdefault(skill["id"], skill)
    return index


def _area_skill_ids(skills_doc: dict, area3: str) -> list[str]:
    """The area's full skill membership (own and shared) from ``areas[]``,
    not the exam file's flat ``skills`` list — that list is incomplete for
    shared ``math.*`` skills described only in the other exam's file."""
    for area in skills_doc.get("areas", []):
        ids = [ref["id"] for ref in area["skills"]]
        if any(skill_id.split(".")[1] == area3 for skill_id in ids):
            return ids
    return []


def _select_skills(
    skill_index: dict[str, dict],
    skills_doc: dict,
    area3: str,
    explicit_ids: list[str] | None,
) -> list[dict]:
    ids = explicit_ids if explicit_ids else _area_skill_ids(skills_doc, area3)
    if not ids:
        raise SystemExit(f"no skills found for area {area3!r}")
    missing = [sid for sid in ids if sid not in skill_index]
    if missing:
        raise SystemExit(
            "no description found in any data/skills/*.json for skill id(s): "
            + ", ".join(missing)
        )
    return [skill_index[sid] for sid in ids]


def _load_misconceptions(data_dir: Path) -> list[dict]:
    """Reads every ``*.json`` file in ``data/misconceptions/`` — today a
    single ``library.json``, later one file per area (delta §3.6) — and
    merges them by id, so this keeps working unchanged either way."""
    out: list[dict] = []
    seen: set[str] = set()
    directory = data_dir / "misconceptions"
    if not directory.exists():
        return out
    for path in sorted(directory.glob("*.json")):
        for entry in _load_json(path):
            if entry["id"] not in seen:
                seen.add(entry["id"])
                out.append(entry)
    return out


def _misconceptions_for_area(
    all_misc: list[dict], area_skill_ids: list[str], exam: str
) -> list[dict]:
    area_set = set(area_skill_ids)
    return [
        m
        for m in all_misc
        if area_set & set(m.get("skill_ids", []))
        and m.get("exam_specific") in (None, exam)
    ]


def _example_templates(
    area_dir: Path,
    skill_id: str,
    limit: int = 2,
    fallback_dir: Path | None = None,
) -> list[dict]:
    """Up to ``limit`` existing templates as a format sample (§3.1).

    An area generated for the first time has no files of its own, and the
    model still needs to see the shape of a real template — so fall back to
    the same exam's other areas rather than sending it none."""
    files = sorted(area_dir.glob("*.json")) if area_dir.exists() else []
    if not files and fallback_dir is not None and fallback_dir.exists():
        files = sorted(fallback_dir.glob("*/*.json"))
    matching = [f for f in files if _load_json(f).get("skill_id") == skill_id]
    rest = [f for f in files if f not in matching]
    return [_load_json(f) for f in (matching + rest)[:limit]]


def _load_exam_format(data_dir: Path, exam: str) -> dict:
    return _load_json(data_dir / "exam_formats" / _SKILLS_FILE[exam])


def _format_exam_format(doc: dict) -> str:
    lines = [
        f"- {section['name']}: item_types={section['item_types']}, "
        f"difficulty_shares={section['difficulty_shares']}"
        for section in doc.get("sections", [])
    ]
    return "\n".join(lines) if lines else "нет данных о формате"


def _format_misconceptions(entries: list[dict], skill_id: str) -> str:
    """Own-skill misconceptions first, then the rest of the area's, each
    marked with the neighbouring skill they actually belong to — the model
    still needs to know the area's misconceptions even when the target
    skill has none of its own (30-B2-phase2.md §3.1)."""
    if not entries:
        return "нет заблуждений для этой области"
    own = [m for m in entries if skill_id in m.get("skill_ids", [])]
    other = [m for m in entries if skill_id not in m.get("skill_ids", [])]
    lines = [f"- {m['id']}: {m['name']} — {m['description']}" for m in own]
    for m in other:
        related = next(
            (sid for sid in m.get("skill_ids", []) if sid != skill_id), skill_id
        )
        lines.append(
            f"- {m['id']}: {m['name']} — {m['description']} (смежный навык {related})"
        )
    return "\n".join(lines)


def _format_examples(templates: list[dict]) -> str:
    if not templates:
        return "нет существующих шаблонов для примера"
    return "\n\n".join(json.dumps(t, ensure_ascii=False, indent=2) for t in templates)


def _leftover_placeholder(spec: TaskTemplateSpec, n_seeds: int = 3) -> str | None:
    """Render a few instances and check that no ``{`` survived substitution.

    ``render_stem`` only substitutes a bare ``{name}`` (a single param or
    ``{answer}``); anything else in braces — a composite expression, or any
    ``{...}`` at all in ``multi_select`` option text, which the engine never
    renders — is left in the string as-is and reaches the student literally.
    ``validate_template`` doesn't catch this (it checks symbolic/seed
    invariants, not rendered text), so this is a separate, string-level check.
    """
    for seed in range(n_seeds):
        try:
            instance = generate_instance(spec, seed=seed)
        except Exception as exc:
            return f"seed {seed} crashed: {exc!r}"
        texts = [instance.stem_rendered, *instance.solution_rendered]
        texts += [option.text for option in instance.options]
        texts += [trap.text for trap in instance.trap_answers]
        for text in texts:
            if "{" in text:
                return f"leftover placeholder in seed {seed}: {text!r}"
    return None


# render_stem (app/tasks/render.py, B1's file) only wraps a substituted
# negative value in parentheses when the character right before its `{name}`
# is an ASCII operator (+-*/) — the typographic operators our own solutions
# use (−, ·, ×, ÷) aren't recognised, so e.g. "4·{q}" with q=-2 renders as
# the unparenthesised, ambiguous "4·-2" instead of "4·(-2)" (sync-log
# 2026-09-18, B2 -> B1). This is a string-level check on the rendered text,
# same reasoning as `_leftover_placeholder`.
_UNPARENTHESIZED_NEGATIVE = re.compile(r"[+\-*/−·×÷]\s*-\d")


def _unparenthesized_negative(spec: TaskTemplateSpec, n_seeds: int = 40) -> str | None:
    """Render several instances and check for an operator directly followed
    by an unwrapped negative value (no parentheses in between)."""
    for seed in range(n_seeds):
        try:
            instance = generate_instance(spec, seed=seed)
        except Exception:
            continue  # validate_template already accounts for seed failures
        texts = [instance.stem_rendered, *instance.solution_rendered]
        texts += [option.text for option in instance.options]
        texts += [trap.text for trap in instance.trap_answers]
        for text in texts:
            match = _UNPARENTHESIZED_NEGATIVE.search(text)
            if match:
                return (
                    f"unparenthesized negative in seed {seed}: "
                    f"{match.group(0)!r} in {text!r}"
                )
    return None


def _build_messages(
    exam_format_doc: dict,
    skill: dict,
    misconceptions: list[dict],
    examples: list[dict],
    n: int,
) -> list[LLMMessage]:
    prompt = load_prompt("gen_template")
    system_text = prompt.render(
        exam_name=exam_format_doc.get("name", exam_format_doc.get("exam_id", "")),
        skill_id=skill["id"],
        skill_name=skill["name"],
        skill_description=skill["description"],
        exam_format=_format_exam_format(exam_format_doc),
        misconceptions=_format_misconceptions(misconceptions, skill["id"]),
        examples=_format_examples(examples),
        n=str(n),
    )
    user_text = (
        f"Составь {n} шаблонов для навыка {skill['id']} ({skill['name']}) "
        "по инструкции выше."
    )
    return [
        LLMMessage(role="system", content=system_text),
        LLMMessage(role="user", content=user_text),
    ]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exam", required=True, choices=sorted(_EXAM_DIR))
    parser.add_argument("--area", required=True, help="area3 code, e.g. 'alg'")
    parser.add_argument(
        "--skill", action="append", default=None, help="skill_id, repeatable"
    )
    parser.add_argument("--n", type=int, default=3, help="templates per skill")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--no-seed-validate",
        action="store_true",
        help="skip running scripts/seed.py --validate after writing templates",
    )
    return parser.parse_args(argv)


async def run(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    data_dir = ROOT / "data"
    exam_dir_name = _EXAM_DIR[args.exam]
    area_dir = data_dir / "templates" / exam_dir_name / args.area
    out_dir = args.out if args.out is not None else area_dir

    skills_doc = _load_skills_doc(data_dir, args.exam)
    skill_index = _skill_descriptor_index(_load_all_skill_docs(data_dir))
    skills = _select_skills(skill_index, skills_doc, args.area, args.skill)
    exam_format_doc = _load_exam_format(data_dir, args.exam)
    all_misconceptions = _load_misconceptions(data_dir)
    area_skill_ids = _area_skill_ids(skills_doc, args.area)
    area_misconceptions = _misconceptions_for_area(
        all_misconceptions, area_skill_ids, args.exam
    )

    print(f"Навыки для генерации: {[s['id'] for s in skills]}")

    per_skill_messages: list[tuple[dict, list[LLMMessage]]] = []
    for skill in skills:
        examples = _example_templates(
            area_dir,
            skill["id"],
            fallback_dir=data_dir / "templates" / exam_dir_name,
        )
        messages = _build_messages(
            exam_format_doc, skill, area_misconceptions, examples, args.n
        )
        per_skill_messages.append((skill, messages))

    if args.dry_run:
        for skill, messages in per_skill_messages:
            print(f"\n=== навык {skill['id']} ===")
            for message in messages:
                print(f"--- {message.role} ---")
                print(message.content)
        return 0

    settings = Settings()
    redis = Redis.from_url(settings.REDIS_URL)
    try:
        await redis.ping()
    except RedisError as exc:
        print(
            f"Redis недоступен ({settings.REDIS_URL}): {exc}. "
            "Скрипт делит общий rate-limit бакет 'bulk' с рантаймом (delta §3.1) "
            "и не может безопасно работать без него — подними Redis (make up) и повтори."
        )
        await redis.aclose()
        return 1
    client = LLMClient(settings, redis)

    generated = 0
    passed = 0
    skipped_existing: list[str] = []
    dropped: list[tuple[str, str]] = []

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        for skill, messages in per_skill_messages:
            try:
                result = await client.structured(messages, GeneratedTemplates, "bulk")
            except LLMUnavailable as exc:
                dropped.append((f"<{skill['id']}>", f"llm_unavailable: {exc}"))
                continue
            for spec in result.templates:
                generated += 1
                out_path = out_dir / f"{spec.id}.json"
                if out_path.exists():
                    skipped_existing.append(spec.id)
                    print(f"пропущен (уже существует): {spec.id}")
                    continue
                try:
                    errors = validate_template(spec, n_seeds=50)
                except Exception as exc:
                    # a crash on one adversarial spec must not abort the
                    # whole batch (and the templates already written for
                    # other skills)
                    dropped.append((spec.id, f"validation crashed: {exc!r}"))
                    continue
                if errors:
                    dropped.append((spec.id, "; ".join(errors)))
                    continue
                placeholder_issue = _leftover_placeholder(spec)
                if placeholder_issue is not None:
                    dropped.append((spec.id, placeholder_issue))
                    continue
                unparenthesized_issue = _unparenthesized_negative(spec)
                if unparenthesized_issue is not None:
                    dropped.append((spec.id, unparenthesized_issue))
                    continue
                out_path.write_text(
                    json.dumps(
                        spec.model_dump(mode="json"), ensure_ascii=False, indent=2
                    )
                    + "\n",
                    encoding="utf-8",
                )
                passed += 1
    finally:
        await redis.aclose()

    print(f"сгенерировано: {generated}")
    print(f"прошло инварианты: {passed}")
    print(f"{len(skipped_existing)} пропущено (template_id уже существует)")
    print(f"{len(dropped)} отброшено")
    for template_id, reason in dropped:
        print(f"  - {template_id}: {reason}")

    if not args.no_seed_validate:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "seed.py"), "--validate"],
            capture_output=True,
            text=True,
            check=False,
        )
        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            return 1

    return 0


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(run(argv))


if __name__ == "__main__":
    sys.exit(main())
