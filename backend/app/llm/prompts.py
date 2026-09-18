"""Prompt loader with file-based versioning (docs/tz/30-B2.md §4.2).

Prompts live as markdown files ``app/agents/prompts/<name>_v<N>.md``; the
highest ``N`` present for a given ``name`` wins. The prompts directory is
resolved from this module's own location, not from the process's current
working directory, so the loader behaves the same from a worker, a test
runner, or any other entry point.

``Prompt.render`` does plain ``{{var}}`` substitution and raises ``KeyError``
naming the offending placeholder if anything is left unresolved — sending a
half-filled template to the model is worse than crashing before the call.
Keyword arguments that don't match any placeholder in the text are accepted
and simply unused: a caller may pass a superset of variables shared across
several prompts, and a given prompt version is free to not need all of them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "agents" / "prompts"
_FILENAME_RE = re.compile(r"^(?P<name>.+)_v(?P<version>\d+)\.md$")
_PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")


@dataclass
class Prompt:
    name: str
    version: int
    text: str

    @property
    def extractor_version(self) -> str:
        return f"{self.name}_v{self.version}"

    def render(self, **variables: object) -> str:
        def substitute(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in variables:
                raise KeyError(
                    f"prompt {self.extractor_version!r} has unresolved "
                    f"placeholder {{{{{key}}}}}"
                )
            return str(variables[key])

        return _PLACEHOLDER_RE.sub(substitute, self.text)


def load_prompt(name: str) -> Prompt:
    best_version: int | None = None
    best_path: Path | None = None
    for path in _PROMPTS_DIR.glob(f"{name}_v*.md"):
        match = _FILENAME_RE.match(path.name)
        if match is None or match.group("name") != name:
            continue
        version = int(match.group("version"))
        if best_version is None or version > best_version:
            best_version = version
            best_path = path

    if best_path is None or best_version is None:
        raise FileNotFoundError(
            f"no prompt files found for name {name!r} in {_PROMPTS_DIR}"
        )

    return Prompt(
        name=name,
        version=best_version,
        text=best_path.read_text(encoding="utf-8"),
    )
