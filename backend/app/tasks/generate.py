"""Instance generation from templates — memory-architecture-quack.md §3.1–3.4.

generate_instance(spec, seed): deterministic per (spec.id, seed).
validate_template(spec, n_seeds=50): invariants from §3.4.

Source: 20-B1.md §4.3.
"""

from __future__ import annotations

import random
from uuid import NAMESPACE_URL, UUID, uuid5

from app.schemas.tasks import DistractorSpec, Option, TaskInstance, TaskTemplateSpec
from app.tasks.evaluate import (
    TemplateError,
    check_constraints,
    equal_values,
    eval_expr,
    to_canonical,
)
from app.tasks.generators import GENERATORS
from app.tasks.render import render_stem, render_value

_MCQ_NEEDED = {"mcq4": 3, "mcq5": 4}
_KEY_LETTERS = ["A", "B", "C", "D", "E"]
_MAX_SEED_ATTEMPTS = 200
_VALIDATE_FAILURE_RATE = 0.10
_EVAL_ERRORS = (TemplateError, TypeError, ValueError, AttributeError)


def _eval_or_literal(expr: str, params: dict):
    """Try sympy; on failure or non-scalar (Tuple/Rel/Boolean) → keep text as-is.

    Позволяет использовать в шаблонах текстовые варианты ответов
    (например, «y = 3x - 1», «Infinitely many», «(3, 2)»).
    """
    try:
        val = eval_expr(expr, params)
    except _EVAL_ERRORS:
        return expr
    if getattr(val, "is_Tuple", False):
        return expr
    if getattr(val, "rel_op", None) is not None:
        return expr
    if getattr(val, "is_Boolean", False):
        return expr
    return val


def sample_params(spec: TaskTemplateSpec, rng: random.Random) -> dict | None:
    """Sample params until constraints hold; up to _MAX_SEED_ATTEMPTS tries."""
    if not spec.params:
        return {} if check_constraints(spec.constraints, {}) else None
    for _ in range(_MAX_SEED_ATTEMPTS):
        params: dict[str, object] = {}
        for name, ps in spec.params.items():
            if ps.choices is not None:
                params[name] = rng.choice(ps.choices)
            elif ps.range is not None:
                params[name] = rng.randint(ps.range[0], ps.range[1])
            else:
                raise TemplateError(f"param {name!r} has neither range nor choices")
        if check_constraints(spec.constraints, params):
            return params
    return None


def generate_instance(
    spec: TaskTemplateSpec,
    seed: int,
    student_misc: set[str] | None = None,
    student_id: UUID | None = None,
) -> TaskInstance:
    """Build a concrete TaskInstance from a template and a seed."""
    if student_misc is None:
        student_misc = set()
    rng = random.Random(f"{spec.id}:{seed}")

    if spec.generator:
        fn = GENERATORS.get(spec.generator)
        if fn is None:
            raise TemplateError(f"unknown generator {spec.generator!r}")
        data = fn(rng)
        params = data["params"]
        correct_val = data["correct"]
        distractor_specs = data.get("distractors", spec.distractors)
    else:
        params = sample_params(spec, rng)
        if params is None:
            raise TemplateError(f"cannot satisfy constraints for {spec.id}")
        distractor_specs = spec.distractors
        if isinstance(spec.correct, list):
            correct_val = list(spec.correct)
        else:
            correct_val = _eval_or_literal(spec.correct, params)

    if spec.type in ("mcq4", "mcq5"):
        options, answer, trap_options = _build_mcq(
            rng, params, correct_val, distractor_specs, spec.type, student_misc
        )
    elif spec.type == "multi_select":
        options, answer, trap_options = _build_multi_select(
            rng, correct_val, distractor_specs, spec
        )
    elif spec.type == "numeric":
        options, answer, trap_options = _build_numeric(params, correct_val, spec)
    else:
        raise TemplateError(f"unsupported type {spec.type}")

    stem_rendered = render_stem(spec.stem, params)
    answer_text = answer if isinstance(answer, str) else ", ".join(answer)
    solution_rendered = [
        render_stem(line, params, answer=answer_text) for line in spec.solution
    ]

    uid = uuid5(NAMESPACE_URL, f"{spec.id}:{seed}:{student_id}")
    figure_url = spec.figure if spec.kind == "manual" else None

    return TaskInstance(
        id=uid,
        template_id=spec.id,
        seed=seed,
        exam_id=spec.exam_id,
        type=spec.type,
        skill_id=spec.skill_id,
        stem_rendered=stem_rendered,
        options=options,
        answer=answer,
        trap_answers=trap_options,
        solution_rendered=solution_rendered,
        figure_url=figure_url,
        time_reference_sec=spec.time_reference_sec,
        difficulty=spec.difficulty,
        tags=spec.tags,
    )


def validate_template(spec: TaskTemplateSpec, n_seeds: int = 50) -> list[str]:
    """Return a list of errors (empty = template accepted). See §3.4."""
    errors: list[str] = []

    if spec.type in ("mcq4", "mcq5"):
        dummy = _dummy_params(spec)
        if dummy is not None:
            try:
                correct_expr = _eval_or_literal(spec.correct, dummy)
                seen: list[object] = []
                for d in spec.distractors:
                    d_expr = _eval_or_literal(d.expr, dummy)
                    if equal_values(d_expr, correct_expr):
                        errors.append(f"distractors collapse: {d.expr} == correct")
                        break
                    if any(equal_values(d_expr, s) for s in seen):
                        errors.append(
                            f"distractors collapse: {d.expr} duplicates another"
                        )
                        break
                    seen.append(d_expr)
            except _EVAL_ERRORS:
                pass

    failures = 0
    for s in range(n_seeds):
        try:
            generate_instance(spec, seed=s)
        except _EVAL_ERRORS:
            failures += 1
    if failures > int(n_seeds * _VALIDATE_FAILURE_RATE):
        errors.append(f"seed failure rate: {failures}/{n_seeds}")

    return errors


# --- helpers ---


def _dummy_params(spec: TaskTemplateSpec) -> dict[str, object] | None:
    """Middle of each range / first choice — for symbolic checks."""
    if not spec.params:
        return None
    out: dict[str, object] = {}
    for name, ps in spec.params.items():
        if ps.choices:
            out[name] = ps.choices[0]
        elif ps.range:
            lo, hi = ps.range
            out[name] = (lo + hi) // 2
        else:
            return None
    return out


def _build_mcq(
    rng: random.Random,
    params: dict,
    correct_val: object,
    distractor_specs: list[DistractorSpec],
    spec_type: str,
    student_misc: set[str],
) -> tuple[list[Option], str, list[Option]]:
    needed = _MCQ_NEEDED[spec_type]
    computed: list[tuple[DistractorSpec, object]] = []
    for d in distractor_specs:
        val = _eval_or_literal(d.expr, params)
        if equal_values(val, correct_val):
            continue
        if any(equal_values(val, c[1]) for c in computed):
            continue
        computed.append((d, val))

    preferred = [x for x in computed if x[0].misconception_id in student_misc]
    rest = [x for x in computed if x[0].misconception_id not in student_misc]
    selected = (preferred + rest)[:needed]
    if len(selected) < needed:
        raise TemplateError("distractors collapse")

    entries: list[tuple[str, bool, str | None]] = [
        (render_value(correct_val, "auto"), True, None)
    ]
    for d, val in selected:
        entries.append((render_value(val, "auto"), False, d.misconception_id))
    rng.shuffle(entries)

    options: list[Option] = []
    answer_key = ""
    for i, (text, is_correct, misc_id) in enumerate(entries):
        key = _KEY_LETTERS[i]
        options.append(
            Option(key=key, text=text, correct=is_correct, misconception_id=misc_id)
        )
        if is_correct:
            answer_key = key
    return options, answer_key, []


def _build_multi_select(
    rng: random.Random,
    correct_val: object,
    distractor_specs: list[DistractorSpec],
    spec: TaskTemplateSpec,
) -> tuple[list[Option], list[str], list[Option]]:
    correct_items = [
        str(x)
        for x in (correct_val if isinstance(correct_val, list) else [correct_val])
    ]
    entries: list[tuple[str, bool, str | None]] = [
        (s, True, None) for s in correct_items
    ]
    seen_texts = set(correct_items)
    for d in distractor_specs:
        text = str(d.expr)
        if text in seen_texts:
            continue
        seen_texts.add(text)
        entries.append((text, False, d.misconception_id))
    rng.shuffle(entries)
    entries = entries[:5]

    options: list[Option] = []
    answer_keys: list[str] = []
    for i, (text, is_correct, misc_id) in enumerate(entries):
        key = _KEY_LETTERS[i]
        options.append(
            Option(key=key, text=text, correct=is_correct, misconception_id=misc_id)
        )
        if is_correct:
            answer_keys.append(key)

    trap_options = _build_multi_select_traps(spec, options)
    return options, answer_keys, trap_options


def _build_multi_select_traps(
    spec: TaskTemplateSpec, options: list[Option]
) -> list[Option]:
    if not spec.omission_traps:
        return []
    text_to_key = {o.text: o.key for o in options}
    out: list[Option] = []
    for ot in spec.omission_traps:
        key = text_to_key.get(ot.omit, "")
        out.append(
            Option(
                key=key,
                text=ot.omit,
                correct=False,
                misconception_id=ot.misconception_id,
            )
        )
    return out


def _build_numeric(
    params: dict,
    correct_val: object,
    spec: TaskTemplateSpec,
) -> tuple[list[Option], str, list[Option]]:
    answer = (
        to_canonical(correct_val) if not isinstance(correct_val, str) else correct_val
    )
    trap_options: list[Option] = []
    for i, t in enumerate(spec.trap_answers or []):
        try:
            val = eval_expr(t.expr, params)
        except _EVAL_ERRORS:
            continue
        text = render_value(val, "auto")
        trap_options.append(
            Option(
                key=f"T{i + 1}",
                text=text,
                correct=False,
                misconception_id=t.misconception_id,
            )
        )
    return [], answer, trap_options
