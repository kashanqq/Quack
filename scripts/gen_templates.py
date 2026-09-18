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

from app.config import Settings  # noqa: E402
from app.errors import LLMUnavailable  # noqa: E402
from app.llm.client import LLMClient  # noqa: E402
from app.llm.prompts import load_prompt  # noqa: E402
from app.schemas.llm import LLMMessage  # noqa: E402
from app.schemas.tasks import TaskTemplateSpec  # noqa: E402
from app.tasks.generate import validate_template  # noqa: E402

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


def _skills_for_area(skills_doc: dict, area3: str) -> list[dict]:
    return [s for s in skills_doc["skills"] if s["id"].split(".")[1] == area3]


def _select_skills(
    skills_doc: dict, area3: str, explicit_ids: list[str] | None
) -> list[dict]:
    if explicit_ids:
        by_id = {s["id"]: s for s in skills_doc["skills"]}
        missing = [sid for sid in explicit_ids if sid not in by_id]
        if missing:
            raise SystemExit(f"unknown skill id(s): {', '.join(missing)}")
        return [by_id[sid] for sid in explicit_ids]
    found = _skills_for_area(skills_doc, area3)
    if not found:
        raise SystemExit(f"no skills found for area {area3!r}")
    return found


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


def _misconceptions_for_skill(
    all_misc: list[dict], skill_id: str, exam: str
) -> list[dict]:
    return [
        m
        for m in all_misc
        if skill_id in m.get("skill_ids", []) and m.get("exam_specific") in (None, exam)
    ]


def _example_templates(area_dir: Path, skill_id: str, limit: int = 2) -> list[dict]:
    if not area_dir.exists():
        return []
    files = sorted(area_dir.glob("*.json"))
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


def _format_misconceptions(entries: list[dict]) -> str:
    if not entries:
        return "нет заблуждений для этой области"
    return "\n".join(f"- {m['id']}: {m['name']} — {m['description']}" for m in entries)


def _format_examples(templates: list[dict]) -> str:
    if not templates:
        return "нет существующих шаблонов для примера"
    return "\n\n".join(json.dumps(t, ensure_ascii=False, indent=2) for t in templates)


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
        misconceptions=_format_misconceptions(misconceptions),
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
    skills = _select_skills(skills_doc, args.area, args.skill)
    exam_format_doc = _load_exam_format(data_dir, args.exam)
    all_misconceptions = _load_misconceptions(data_dir)

    print(f"Навыки для генерации: {[s['id'] for s in skills]}")

    per_skill_messages: list[tuple[dict, list[LLMMessage]]] = []
    for skill in skills:
        misconceptions = _misconceptions_for_skill(
            all_misconceptions, skill["id"], args.exam
        )
        examples = _example_templates(area_dir, skill["id"])
        messages = _build_messages(
            exam_format_doc, skill, misconceptions, examples, args.n
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
    client = LLMClient(settings, redis)

    generated = 0
    passed = 0
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
                errors = validate_template(spec, n_seeds=50)
                if errors:
                    dropped.append((spec.id, "; ".join(errors)))
                    continue
                out_path = out_dir / f"{spec.id}.json"
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
