"""The cache key of a generated text — §3.4.

Pure, and shared on purpose: the route computes the hash to decide whether
what it has is current, and the job computes it to decide whether it has
anything to do. If the two ever disagreed, every read would look stale and
the queue would never empty.

What the hash contains is a product decision, not an implementation detail:
skill state in *words* (`SkillLevel`), not `p_recall` — otherwise answering
one task would invalidate a guideline that is still perfectly true.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from pydantic import BaseModel


def canonical_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    )


def inputs_hash(
    kind: str,
    student_id: UUID | None,
    subject: str,
    inputs: BaseModel | dict[str, Any],
    prompt_version: str,
    model: str,
) -> str:
    """sha256 over kind, owner, subject, inputs, prompt version and model."""
    payload = (
        inputs.model_dump(mode="json") if isinstance(inputs, BaseModel) else inputs
    )
    return hashlib.sha256(
        canonical_json(
            {
                "kind": kind,
                "student_id": str(student_id) if student_id is not None else None,
                "subject": subject,
                "inputs": payload,
                "prompt_version": prompt_version,
                "model": model,
            }
        ).encode("utf-8")
    ).hexdigest()


def set_inputs_hash(hashes: list[str]) -> str:
    """The `_job_id` of `pregenerate_set` — one run per version of the set."""
    return hashlib.sha256("|".join(sorted(hashes)).encode("utf-8")).hexdigest()
