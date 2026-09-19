"""T01–T03, T05: what a read returns when the model is not there (§11 A1)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app import fallbacks
from app.schemas.texts import GeneratedText

pytestmark = pytest.mark.phase5

NOW = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
STUDENT = uuid4()
SET_ID = uuid4()


def _text(
    input_hash: str, *, status: str = "ready", text: str | None = "тело"
) -> GeneratedText:
    return GeneratedText(
        id=uuid4(),
        kind="guideline",
        input_hash=input_hash,
        text=text,
        model="m",
        prompt_version="guideline_v1",
        created_at=NOW,
        student_id=STUDENT,
        subject="math.alg.linear_eq",
        set_id=SET_ID,
        status=status,  # type: ignore[arg-type]
    )


def _select(**overrides):
    kwargs = {
        "kind": "guideline",
        "subject": "math.alg.linear_eq",
        "set_id": SET_ID,
        "current_hash": "h1",
        "current": None,
        "last_ready": None,
        "llm_status": "ok",
    }
    kwargs.update(overrides)
    return fallbacks.select_text(**kwargs)


def test_t01_a_current_text_survives_the_outage_and_says_it_is_saved():
    """T01: тот же текст, но с пометкой saved_version — не «сгенерировано сейчас»."""
    live = _select(current=_text("h1"))
    assert (live.status, live.mark, live.text) == ("ready", "generated", "тело")

    down = _select(current=_text("h1"), llm_status="down")
    assert down.status == "ready"
    assert down.mark == "saved_version"
    assert down.text == "тело"
    assert down.reason == "llm_unavailable"


def test_t03_a_changed_hash_is_stale_not_current():
    """T03: поздняя генерация под старым хэшем не становится текущей."""
    out = _select(current=None, last_ready=_text("h0"))
    assert out.status == "stale"
    assert out.mark == "saved_version"
    assert out.input_hash == "h1"


def test_a_missing_text_is_never_dressed_up_as_ready():
    empty = _select()
    assert (empty.status, empty.text, empty.reason) == (
        "generating",
        None,
        "not_generated",
    )
    down = _select(llm_status="down")
    assert down.text is None and down.reason == "llm_unavailable"


def test_a_failed_row_reports_its_own_reason():
    out = _select(current=_text("h1", status="failed", text=None))
    assert out.status == "failed"
    assert out.reason == "llm_unavailable"


def test_without_inputs_there_is_no_hash_to_file_a_text_under():
    """Граф лежит: показать текст под чужим ключом было бы враньём."""
    out = _select(current_hash=None, current=_text("h1"))
    assert out.status == "generating"
    assert out.input_hash == ""
    assert out.reason == "graph_unavailable"
    assert out.text is None


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"graph_ok": True}, ("live", None)),
        ({"graph_ok": False}, ("static", "graph_unavailable")),
        (
            {"graph_ok": True, "projection_pending": True},
            ("live", "projection_pending"),
        ),
        ({"graph_ok": True, "search_ok": False}, ("cached", "search_unavailable")),
        ({"graph_ok": True, "cached": True}, ("cached", None)),
    ],
)
def test_availability_ranks_the_reasons_in_one_place(kwargs, expected):
    out = fallbacks.availability(**kwargs)
    assert (out.mode, out.reason) == expected


def test_availability_never_guesses_a_version():
    assert fallbacks.availability(graph_ok=True).as_of_event_id is None
    assert fallbacks.availability(graph_ok=True, as_of_event_id=7).as_of_event_id == 7
