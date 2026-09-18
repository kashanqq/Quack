"""Grade a student's answer to a TaskInstance — memory-architecture-quack.md §8.2.

Pure function: grade(instance, answer) -> Grade.

Source: 20-B1.md §4.4.
"""

from __future__ import annotations

from typing import Any

from sympy import Float, Integer, Rational, sympify

from app.schemas.tasks import Grade, TaskInstance


def grade(instance: TaskInstance, answer: Any) -> Grade:
    """Grade an answer against an instance.

    - mcq4/mcq5: answer is a key; correct → True; distractor → matched_misconception_id.
    - numeric: answer is a string; matches instance.answer as sympy value,
      or trap_answers → matched_misconception_id.
    - multi_select: answer is a list of keys; partial credit; omitted traps.
    """
    if instance.type in ("mcq4", "mcq5"):
        return _grade_mcq(instance, answer)
    if instance.type == "numeric":
        return _grade_numeric(instance, answer)
    if instance.type == "multi_select":
        return _grade_multi_select(instance, answer)
    return Grade(correct=False)


def _grade_mcq(instance: TaskInstance, answer: Any) -> Grade:
    key = str(answer)
    for opt in instance.options:
        if opt.key == key:
            if opt.correct:
                return Grade(correct=True)
            return Grade(correct=False, matched_misconception_id=opt.misconception_id)
    return Grade(correct=False)


def _grade_numeric(instance: TaskInstance, answer: Any) -> Grade:
    try:
        student_val = sympify(str(answer))
    except Exception:  # noqa: BLE001
        return Grade(correct=False)
    try:
        correct_val = sympify(instance.answer)
    except Exception:  # noqa: BLE001
        return Grade(correct=False)

    if _num_equal(student_val, correct_val):
        return Grade(correct=True)

    for trap in instance.trap_answers:
        try:
            trap_val = sympify(trap.text)
        except Exception:  # noqa: BLE001
            continue
        if _num_equal(student_val, trap_val):
            return Grade(correct=False, matched_misconception_id=trap.misconception_id)
    return Grade(correct=False)


def _num_equal(a, b) -> bool:
    try:
        if isinstance(a, Float) or isinstance(b, Float):
            return abs(float(a) - float(b)) < 1e-6
        return (a - b) == 0
    except Exception:  # noqa: BLE001
        return False


def _grade_multi_select(instance: TaskInstance, answer: Any) -> Grade:
    if not isinstance(answer, list):
        answer = [answer]
    selected = {str(k) for k in answer}
    correct_keys = {o.key for o in instance.options if o.correct}
    all_options = {o.key: o for o in instance.options}

    correct_chosen = selected & correct_keys
    wrong_chosen = selected - correct_keys

    if not correct_keys:
        return Grade(correct=False)

    if not wrong_chosen:
        partial = len(correct_chosen) / len(correct_keys)
    else:
        partial = max(0.0, (len(correct_chosen) - len(wrong_chosen)) / len(correct_keys))

    correct = partial == 1.0 and not wrong_chosen

    matched: str | None = None
    for key in wrong_chosen:
        opt = all_options.get(key)
        if opt and opt.misconception_id:
            matched = opt.misconception_id
            break

    omitted: list[str] = []
    missing = correct_keys - correct_chosen
    for trap in instance.trap_answers:
        if trap.key in missing and trap.misconception_id:
            omitted.append(trap.misconception_id)

    return Grade(
        correct=correct,
        matched_misconception_id=matched,
        partial=partial,
        omitted_misconception_ids=omitted,
    )