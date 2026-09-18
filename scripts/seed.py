"""Validate seed data or run the B3/B1 seed pipeline in contract order."""

import argparse
import asyncio
import importlib
import inspect
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings  # noqa: E402
from app.db.engine import close_engine, create_engine, create_sessionmaker  # noqa: E402
from app.seed.calendars import seed_calendars, validate_calendars  # noqa: E402
from app.seed.programs import seed_programs_floor, validate_programs_floor  # noqa: E402
from app.seed.users import seed_users, validate_users  # noqa: E402

ORDER = (
    "users",
    "skills",
    "exam_formats",
    "misconceptions",
    "templates",
    "knowledge_base",
    "calendars",
    "programs",
)
B1_STEPS = set(ORDER[1:6])
PATHS = {
    "users": Path("users.json"),
    "calendars": Path("knowledge_base/calendars.json"),
    "programs": Path("programs_floor/programs.json"),
}

COVERAGE_MIN = 2


def _b1_module(name: str) -> Any | None:
    module_name = f"app.seed.{name}"
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            return None
        raise


def validate_data(data_dir: Path) -> None:
    for path in sorted(data_dir.rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"{path}: {exc}") from exc
    for name, validator in (
        ("users", validate_users),
        ("calendars", validate_calendars),
        ("programs", validate_programs_floor),
    ):
        path = data_dir / PATHS[name]
        try:
            validator(path)
        except Exception as exc:
            raise ValueError(f"{path}: {exc}") from exc
    misconceptions = _b1_module("misconceptions")
    if misconceptions is not None:
        validator = getattr(misconceptions, "_load_catalog", None)
        if validator is not None:
            path = data_dir / "misconceptions"
            try:
                validator(path)
            except Exception as exc:
                raise ValueError(f"{path}: {exc}") from exc
    templates = _b1_module("templates")
    if templates is not None:
        validator = getattr(templates, "validate_templates", None)
        if validator is not None:
            path = data_dir / "templates"
            try:
                validator(path)
            except Exception as exc:
                raise ValueError(f"{path}: {exc}") from exc


def _load_skill_ids(data_dir: Path) -> list[str]:
    """Все skill_id, объявленные в data/skills/*.json (включая ссылки в areas)."""
    ids: set[str] = set()
    for path in sorted((data_dir / "skills").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for area in payload.get("areas", []):
            for s in area.get("skills", []):
                ids.add(s["id"])
        for s in payload.get("skills", []):
            ids.add(s["id"])
    return sorted(ids)


def _count_templates_by_skill(data_dir: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in sorted((data_dir / "templates").rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        skill_id = payload.get("skill_id")
        if skill_id:
            counts[skill_id] = counts.get(skill_id, 0) + 1
    return counts


def run_coverage(data_dir: Path) -> int:
    """Печатает таблицу «навык → число шаблонов», помечает < COVERAGE_MIN.

    Exit-code 1, если есть навыки с покрытием меньше COVERAGE_MIN.
    Не требует БД.
    """
    skills = _load_skill_ids(data_dir)
    counts = _count_templates_by_skill(data_dir)

    print(f"templates coverage (min={COVERAGE_MIN})")
    print(f"{'count':>6}  skill_id")
    print("-" * 60)
    missing: list[str] = []
    for skill_id in skills:
        n = counts.get(skill_id, 0)
        flag = "  <" if n < COVERAGE_MIN else "   "
        print(f"{n:>6}{flag}  {skill_id}")
        if n < COVERAGE_MIN:
            missing.append(skill_id)

    total_templates = sum(counts.values())
    print("-" * 60)
    print(f"skills: {len(skills)}, templates: {total_templates}")
    if missing:
        print(
            f"\n{len(missing)} skill(s) below {COVERAGE_MIN} templates:",
            file=sys.stderr,
        )
        for s in missing:
            print(f"  - {s}", file=sys.stderr)
        return 1
    print("all skills covered.")
    return 0


async def _call_b1_loader(
    name: str, module: Any, session: Any, driver: Any, data_dir: Path
) -> Any:
    loader = getattr(module, f"seed_{name}")
    available = {
        "session": session,
        "driver": driver,
        "path": data_dir / name,
        "data_dir": data_dir,
        "settings": settings,
    }
    parameters = inspect.signature(loader).parameters
    unknown = [
        key
        for key, param in parameters.items()
        if key not in available and param.default is inspect.Parameter.empty
    ]
    if unknown:
        raise RuntimeError(f"{name}: B1 loader interface needs sync: {unknown}")
    kwargs = {key: available[key] for key in parameters if key in available}
    result = loader(**kwargs)
    return await result if inspect.isawaitable(result) else result


async def run_seed(data_dir: Path, selected: set[str]) -> None:
    from app.main import _optional_layer

    engine = create_engine(settings)
    driver = None
    graph_client = None
    try:
        graph_client = _optional_layer("app.graph.client")
        if graph_client is not None:
            driver = graph_client.create_driver(settings)
            if inspect.isawaitable(driver):
                driver = await driver
        sessionmaker = create_sessionmaker(engine)
        async with sessionmaker() as session:
            for name in ORDER:
                if name not in selected:
                    continue
                if name in B1_STEPS:
                    module = _b1_module(name)
                    if module is None:
                        print(f"{name}: waiting: B1 loader")
                        continue
                    count = await _call_b1_loader(
                        name, module, session, driver, data_dir
                    )
                elif name == "users":
                    count = await seed_users(session, data_dir / PATHS[name])
                elif name == "calendars":
                    count = await seed_calendars(driver, data_dir / PATHS[name])
                else:
                    count = await seed_programs_floor(session, data_dir / PATHS[name])
                await session.commit()
                print(f"{name}: {count}")
    finally:
        if driver is not None and graph_client is not None:
            result = graph_client.close_driver(driver)
            if inspect.isawaitable(result):
                await result
        await close_engine(engine)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate or seed Quack data")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="print template coverage per skill and exit non-zero on gaps",
    )
    parser.add_argument("--only", help="comma-separated seed step names")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    args = parser.parse_args(argv)

    if args.coverage:
        try:
            return run_coverage(args.data_dir)
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return 1

    selected = set(args.only.split(",")) if args.only else set(ORDER)
    unknown = selected.difference(ORDER)
    if unknown:
        parser.error(f"unknown seed steps: {', '.join(sorted(unknown))}")
    try:
        validate_data(args.data_dir)
        if not args.validate:
            asyncio.run(run_seed(args.data_dir, selected))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())