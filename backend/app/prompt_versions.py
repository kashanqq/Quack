"""Which prompt version a cached text was written with (§3.4).

The version belongs in the hash: a new prompt must make every old text
stale. But `app/apply` may not import the B2 layer (`tests/test_layers.py`)
and must keep working in a checkout that has no prompts at all — so the
lookup goes through the optional loader and falls back to the `_v1` names.
"""

from __future__ import annotations

from app.config import settings
from app.loader import optional_layer

# Промпт на каждый вид текста; имя файла — `<name>_v<N>.md`.
PROMPT_NAMES: dict[str, str] = {
    "guideline": "guideline",
    "explanation": "explanation",
    "realism": "realism_text",
    "compare": "compare",
    "summary": "set_summary",
    "soft_match": "soft_match",
    "extract_program": "extract_program",
}


def version_of(kind: str) -> str:
    """`guideline_v1` — the highest version present, or the `_v1` default."""
    name = PROMPT_NAMES.get(kind, kind)
    prompts = optional_layer("app.llm.prompts")
    if prompts is None:
        return f"{name}_v1"
    try:
        return prompts.load_prompt(name).extractor_version
    except FileNotFoundError:
        return f"{name}_v1"


def text_versions() -> tuple[dict[str, str], str]:
    """({kind: prompt_version}, model) for the four cached text kinds."""
    return (
        {
            kind: version_of(kind)
            for kind in ("guideline", "explanation", "realism", "compare")
        },
        settings.MODEL_BULK,
    )
