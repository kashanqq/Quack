"""Registry of non-parametric task generators — memory-architecture-quack.md §3.5.

A generator is a callable(rng) -> {"params": dict, "correct": value, "distractors": list[DistractorSpec]}.
Used only when TaskTemplateSpec.generator is set (usually for tasks with figures
or non-trivial param logic).
"""

from __future__ import annotations

import random
from typing import Callable

from sympy import Integer

from app.schemas.tasks import DistractorSpec


GENERATORS: dict[str, Callable[[random.Random], dict]] = {}


def generator(name: str):
    """Decorator to register a generator function under a name."""

    def deco(fn: Callable[[random.Random], dict]) -> Callable[[random.Random], dict]:
        GENERATORS[name] = fn
        return fn

    return deco


@generator("sat.geom.circle_chord")
def _circle_chord(rng: random.Random) -> dict:
    """Pick a Pythagorean triple (r, d, half); return chord length = 2*half.

    Distance from center to chord = d, radius = r, half-chord = sqrt(r² - d²).
    Triples keep the answer integral and the numbers digestible.
    """
    triples = [
        (5, 3, 4),
        (5, 4, 3),
        (10, 6, 8),
        (13, 5, 12),
        (13, 12, 5),
    ]
    r, d, half = rng.choice(triples)
    correct = 2 * half
    return {
        "params": {"r": r, "d": d},
        "correct": Integer(correct),
        "distractors": [
            DistractorSpec(expr=str(half), misconception_id=None),
            DistractorSpec(expr=str(d), misconception_id=None),
            DistractorSpec(expr=str(r), misconception_id=None),
        ],
    }
