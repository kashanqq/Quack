"""The extraction pipeline on fakes — §13.2 `test_extract_job.py`."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from arq import Retry

from app.agents import jobs_phase4 as jobs
from app.errors import ValidationFailed
from app.schemas.programs import (
    ExtractedDeadline,
    ExtractedProgram,
    ExtractedRequirement,
    SearchHit,
    SearchStatusOut,
)
from app.search import client as search_client
from app.search import extract as extractor
from tests.quack.conftest import make_program
from tests.search.test_extract_phase4 import PAGE

pytestmark = pytest.mark.phase4

STUDENT = UUID("11111111-1111-4111-8111-111111111111")
URL = "https://mit.edu/cs"
SEARCH_ID = "search:abc"
LONG_PAGE = PAGE + " " * 1200


class _Session:
    async def commit(self):
        pass

    async def flush(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None


class _Redis:
    def __init__(self) -> None:
        self.values: dict = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, nx=False, ex=None, **_kwargs):
        if nx and key in self.values:
            return None
        self.values[key] = value
        return True

    async def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)

    async def incr(self, key):
        self.values[key] = int(self.values.get(key, 0)) + 1
        return self.values[key]

    async def expire(self, *_args, **_kwargs):
        return True


def _ctx(llm=None, redis=None, job_try=1):
    return {
        "sessionmaker": _Session,
        "redis": redis or _Redis(),
        "llm": llm,
        "job_id": "job-1",
        "job_try": job_try,
    }


def _extracted() -> ExtractedProgram:
    return ExtractedProgram(
        university="Massachusetts Institute of Technology",
        country="USA",
        city="Cambridge",
        direction="Computer Science",
        language="English",
        tuition_per_year=1500,
        currency="USD",
        requirements=[
            ExtractedRequirement(
                type="exam_score",
                exam_name="SAT Math",
                threshold=1400,
                comparator=">=",
                description="SAT Math 1400",
            )
        ],
        deadlines=[
            ExtractedDeadline(
                kind="application", date=date(2026, 12, 15), raw="15 December 2026"
            )
        ],
        evidence={
            "university": "Massachusetts Institute of Technology",
            "tuition_per_year": "Tuition is 1 500 USD per year",
            "requirements[0].threshold": "SAT Math score of 1400 required",
            "deadlines[0].date": "Application deadline: 15 December 2026",
        },
    )


@pytest.fixture
def pipeline(monkeypatch):
    """Fetch, the model and the repository, all replaced by recorders."""
    state = SimpleNamespace(
        page=LONG_PAGE,
        fetch_error=None,
        extracted=_extracted(),
        known=None,
        upserts=[],
        outcome="created",
        model_calls=0,
        deleted_soft=[],
        enqueued=[],
    )

    async def fetch_page(_url, max_chars=40000):
        if state.fetch_error is not None:
            raise state.fetch_error
        return state.page

    async def extract(_llm, _page, _url):
        state.model_calls += 1
        return state.extracted

    async def get_by_normalized_url(*_args):
        return state.known

    async def get_program(*_args):
        return None

    async def upsert_extracted(_session, program, meta, **kwargs):
        state.upserts.append((program, meta, kwargs))
        return state.outcome

    async def delete_for_program(_session, program_id):
        state.deleted_soft.append(program_id)
        return 0

    async def enqueue(_ctx, fn_name, job_id, **kwargs):
        state.enqueued.append((fn_name, job_id, kwargs))

    monkeypatch.setattr(search_client, "fetch_page", fetch_page)
    monkeypatch.setattr(extractor, "extract_program", extract)
    monkeypatch.setattr(
        jobs.programs_repo, "get_by_normalized_url", get_by_normalized_url
    )
    monkeypatch.setattr(jobs.programs_repo, "get_program", get_program)
    monkeypatch.setattr(jobs.programs_repo, "upsert_extracted", upsert_extracted)
    monkeypatch.setattr(jobs.soft_repo, "delete_for_program", delete_for_program)
    monkeypatch.setattr(jobs, "_enqueue", enqueue)
    return state


async def _status(ctx) -> SearchStatusOut:
    from app import keys

    raw = await ctx["redis"].get(keys.search_status(SEARCH_ID))
    return SearchStatusOut.model_validate_json(raw)


# --- the happy path ---


async def test_a_valid_page_becomes_a_program(pipeline):
    ctx = _ctx()
    await jobs.extract_program(ctx, "req", URL, None, "query", SEARCH_ID)
    [(program, meta, kwargs)] = pipeline.upserts
    assert program.university.startswith("Massachusetts")
    assert program.extracted_auto is True and program.is_demo is False
    assert program.flagged is False
    assert program.source_url == URL
    assert program.checked_at == datetime.now(UTC).date()
    assert meta.search_query == "query"
    assert meta.dropped_fields == []
    assert kwargs["normalized_url"] == search_client.normalize_url(URL)
    # Найденная программа попадает в статус поиска (§6.1).
    assert (await _status(ctx)).found == [program.id]


async def test_a_number_the_page_does_not_contain_is_dropped(pipeline):
    pipeline.extracted = pipeline.extracted.model_copy(
        update={"tuition_per_year": 2000}
    )
    await jobs.extract_program(_ctx(), "req", URL, None, None, SEARCH_ID)
    [(program, meta, _kwargs)] = pipeline.upserts
    assert program.tuition_per_year is None
    assert meta.dropped_fields == ["tuition_per_year"]


async def test_a_student_with_a_summary_gets_a_soft_match_job(pipeline, monkeypatch):
    from app.schemas.profile import Profile

    profile = Profile(student_id=STUDENT)
    profile.traits.summary = "тёплый климат"

    async def get_profile(*_args):
        return profile

    monkeypatch.setattr(jobs.profiles_repo, "get_profile", get_profile)
    await jobs.extract_program(_ctx(), "req", URL, str(STUDENT), None, SEARCH_ID)
    assert [fn for fn, _job_id, _kwargs in pipeline.enqueued] == ["soft_match"]


async def test_no_summary_means_no_soft_match_job(pipeline, monkeypatch):
    from app.schemas.profile import Profile

    async def get_profile(*_args):
        return Profile(student_id=STUDENT)

    monkeypatch.setattr(jobs.profiles_repo, "get_profile", get_profile)
    await jobs.extract_program(_ctx(), "req", URL, str(STUDENT), None, SEARCH_ID)
    assert pipeline.enqueued == []


# --- pages the model never sees ---


async def test_a_short_page_costs_no_model_call(pipeline):
    pipeline.page = "коротко"
    ctx = _ctx()
    await jobs.extract_program(ctx, "req", URL, None, None, SEARCH_ID)
    assert pipeline.model_calls == 0 and pipeline.upserts == []
    assert (await _status(ctx)).rejected == 1


async def test_a_catalogue_page_costs_no_model_call(pipeline):
    pipeline.page = " ".join(f"http://x{i}.test" for i in range(40)) + " " * 900
    await jobs.extract_program(_ctx(), "req", URL, None, None, SEARCH_ID)
    assert pipeline.model_calls == 0 and pipeline.upserts == []


async def test_a_404_is_final_and_not_retried(pipeline):
    pipeline.fetch_error = search_client.FetchFailed("gone", status=404)
    await jobs.extract_program(_ctx(), "req", URL, None, None, SEARCH_ID)
    assert pipeline.upserts == []


async def test_a_timeout_is_retried_then_given_up(pipeline):
    pipeline.fetch_error = search_client.FetchFailed("timeout")
    with pytest.raises(Retry):
        await jobs.extract_program(_ctx(), "req", URL, None, None, SEARCH_ID)
    # Вторая попытка уже последняя — задача завершается отбраковкой.
    await jobs.extract_program(_ctx(job_try=2), "req", URL, None, None, SEARCH_ID)
    assert pipeline.upserts == []


async def test_an_invalid_url_is_rejected_without_a_retry(pipeline):
    pipeline.fetch_error = ValidationFailed("http(s) URL required")
    await jobs.extract_program(_ctx(), "req", URL, None, None, SEARCH_ID)
    assert pipeline.upserts == []


# --- duplicates (§6.7) ---


async def test_a_fresh_record_for_the_same_url_is_skipped(pipeline):
    pipeline.known = make_program(1, extracted_auto=True).model_copy(
        update={"checked_at": datetime.now(UTC).date()}
    )
    await jobs.extract_program(_ctx(), "req", URL, None, None, SEARCH_ID)
    assert pipeline.model_calls == 0 and pipeline.upserts == []


async def test_a_stale_record_for_the_same_url_is_re_extracted(pipeline):
    pipeline.known = make_program(1, extracted_auto=True).model_copy(
        update={"checked_at": datetime.now(UTC).date() - timedelta(days=30)}
    )
    await jobs.extract_program(_ctx(), "req", URL, None, None, SEARCH_ID)
    assert pipeline.model_calls == 1 and len(pipeline.upserts) == 1


async def test_the_curated_floor_is_never_overwritten(pipeline):
    pipeline.known = make_program(1).model_copy(
        update={
            "extracted_auto": False,
            "checked_at": datetime.now(UTC).date() - timedelta(days=30),
        }
    )
    await jobs.extract_program(_ctx(), "req", URL, None, None, SEARCH_ID)
    assert pipeline.model_calls == 0 and pipeline.upserts == []


async def test_losing_a_duplicate_counts_as_rejected(pipeline):
    pipeline.outcome = "lost"
    ctx = _ctx()
    await jobs.extract_program(ctx, "req", URL, None, None, SEARCH_ID)
    status = await _status(ctx)
    assert status.found == [] and status.rejected == 1


async def test_a_locked_url_is_left_to_the_other_worker(pipeline):
    from app import keys

    redis = _Redis()
    redis.values[
        keys.lock(f"extract:{jobs._short(search_client.normalize_url(URL))}")
    ] = "1"
    await jobs.extract_program(_ctx(redis=redis), "req", URL, None, None, SEARCH_ID)
    assert pipeline.upserts == []


# --- search_programs (§6.2) ---


@pytest.fixture
def search(monkeypatch, pipeline):
    hits = [
        SearchHit(title="MIT", url="https://mit.edu/cs", snippet=""),
        SearchHit(title="Reddit", url="https://reddit.com/r/sat", snippet=""),
        SearchHit(title="PDF", url="https://mit.edu/handbook.pdf", snippet=""),
    ]
    state = SimpleNamespace(hits=hits, error=None, queries=[])

    async def search_programs_limited(_redis, query, n=5):
        state.queries.append((query, n))
        if state.error is not None:
            raise state.error
        return state.hits

    monkeypatch.setattr(
        search_client, "search_programs_limited", search_programs_limited
    )
    return state


async def test_the_denylist_and_binary_urls_never_reach_extraction(search, pipeline):
    ctx = _ctx()
    await jobs.search_programs(ctx, "req", "math in the US", str(STUDENT))
    queued = [job for job in pipeline.enqueued if job[0] == "extract_program"]
    assert len(queued) == 1
    assert queued[0][2]["url"] == "https://mit.edu/cs"
    assert queued[0][2]["search_id"] == ctx["job_id"]
    # Две отброшенные ссылки посчитаны в статусе (§6.1).
    from app import keys

    raw = await ctx["redis"].get(keys.search_status(ctx["job_id"]))
    status = SearchStatusOut.model_validate_json(raw)
    assert status.status == "done" and status.rejected == 2


async def test_a_search_outage_is_retried_then_reported(search, pipeline):
    from app.errors import SearchUnavailable

    search.error = SearchUnavailable("search unavailable")
    with pytest.raises(Retry):
        await jobs.search_programs(_ctx(), "req", "math", None)

    ctx = _ctx(job_try=2)
    await jobs.search_programs(ctx, "req", "math", None)
    from app import keys

    raw = await ctx["redis"].get(keys.search_status(ctx["job_id"]))
    assert SearchStatusOut.model_validate_json(raw).status == "unavailable"
    assert pipeline.enqueued == []


async def test_a_known_fresh_url_is_not_queued_again(search, pipeline, monkeypatch):
    async def get_by_normalized_url(*_args):
        return make_program(1, extracted_auto=True).model_copy(
            update={"checked_at": datetime.now(UTC).date()}
        )

    monkeypatch.setattr(
        jobs.programs_repo, "get_by_normalized_url", get_by_normalized_url
    )
    await jobs.search_programs(_ctx(), "req", "math", None)
    assert [job for job in pipeline.enqueued if job[0] == "extract_program"] == []
