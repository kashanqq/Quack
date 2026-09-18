"""Static checks for the Phase 2 frontend contract and CI gates."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.phase2

ROOT = Path(__file__).resolve().parents[2]


def test_generated_schema_uses_the_existing_frontend_root():
    schema = ROOT / "frontend" / "src" / "api" / "schema.d.ts"
    text = schema.read_text(encoding="utf-8")
    assert '"/matching"' in text
    assert '"/overview"' in text
    assert '"/diagnostic"' in text
    assert '"/mocks"' in text
    generator = (ROOT / "scripts" / "gen_types.sh").read_text(encoding="utf-8")
    assert "frontend/src/api/schema.d.ts" in generator


def test_ci_requires_phase2_seed_catalog_and_clean_types():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "pytest -m phase2" in workflow
    assert "python ../scripts/seed.py --validate" in workflow
    assert "npm ci --ignore-scripts" in workflow
    assert "make types" in workflow
    assert "git diff --exit-code -- frontend/src/api/schema.d.ts" in workflow
    assert "skipping type check" not in workflow
