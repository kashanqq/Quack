"""Reject tracked environment files and recognizable provider credentials."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATTERNS = (
    re.compile(rb"sk-[A-Za-z0-9]{20,}"),
    re.compile(rb"AIza[0-9A-Za-z_-]{30,}"),
    re.compile(rb"tvly-[0-9A-Za-z_-]{20,}"),
)


def _tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return [ROOT / path.decode("utf-8") for path in result.stdout.split(b"\0") if path]


def test_no_tracked_dot_env_file():
    offenders = [
        path.relative_to(ROOT) for path in _tracked_files() if path.name == ".env"
    ]
    assert not offenders, f"tracked .env files: {offenders}"


def test_no_recognizable_secrets_in_tracked_files():
    offenders = []
    for path in _tracked_files():
        if not path.is_file():
            continue
        content = path.read_bytes()
        if any(pattern.search(content) for pattern in PATTERNS):
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, f"possible secrets in tracked files: {offenders}"
