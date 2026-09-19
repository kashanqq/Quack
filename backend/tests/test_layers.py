"""Shared imports and Phase 2 layer boundaries."""

import ast
import importlib
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
PURE_PACKAGES = ("knowledge", "tasks", "sets", "matching", "roadmap", "quack")
PURE_FORBIDDEN = (
    "app.db",
    "app.graph",
    "app.llm",
    "app.agents",
    "fastapi",
    "sqlalchemy",
    "neo4j",
    "redis",
    "openai",
)
APPLY_FORBIDDEN = ("app.llm", "app.agents", "fastapi")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                relative = path.parent.relative_to(APP_ROOT).as_posix()
                package = f"app.{relative.replace('/', '.')}"
                module = importlib.util.resolve_name(
                    "." * node.level + (node.module or ""), package
                )
            else:
                module = node.module or ""
            imports.add(module)
            imports.update(f"{module}.{alias.name}" for alias in node.names)
    return imports


def _check_imports(package: str, forbidden: tuple[str, ...]) -> None:
    for path in (APP_ROOT / package).rglob("*.py"):
        for imported in _imports(path):
            for prefix in forbidden:
                assert imported != prefix and not imported.startswith(f"{prefix}."), (
                    f"{path.relative_to(APP_ROOT)} imports forbidden {imported}"
                )


def test_b3_shared_modules_import_without_b1_or_b2():
    for module in (
        "app.config",
        "app.keys",
        "app.errors",
        "app.api.deps",
        "app.api.auth",
        "app.main",
    ):
        importlib.import_module(module)


@pytest.mark.parametrize("package", PURE_PACKAGES)
def test_phase2_pure_packages_do_not_import_io_layers(package):
    _check_imports(package, PURE_FORBIDDEN)


def test_apply_does_not_import_llm_agents_or_fastapi():
    _check_imports("apply", APPLY_FORBIDDEN)
