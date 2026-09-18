"""ARQ job registry: which queue each job runs on and how long it may take.

Очереди — tech-stack §2.5: `interactive` для того, чего ученик ждёт прямо
сейчас, `bulk` для фоновой подготовки. Таймаут очереди (`job_timeout`
воркера) — потолок для коротких задач; задача, которая ходит в LLM,
объявляет свой собственный через `arq.worker.func(timeout=...)`, иначе
наблюдатель на слоте `bulk` (LLM_TIMEOUT_BULK_S) не укладывался бы в 30 с
очереди `interactive`.

Задачи B2 (`app.agents.jobs`) регистрируются, только если слой B2 есть в
этой копии репозитория — воркер B3 поднимается и без него.
"""

from typing import Any

from arq.worker import Function, func

from app.config import settings
from app.loader import optional_layer as _optional_layer


async def ping(ctx: dict[str, Any], request_id: str) -> str:
    return "pong"


_jobs = _optional_layer("app.agents.jobs")

INTERACTIVE: list[Any] = [ping]
BULK: list[Any] = [ping]


def _registered(name: str, timeout: float) -> Function | None:
    """One B2 job with its own timeout, or None when the layer is absent."""
    if _jobs is None:
        return None
    coroutine = getattr(_jobs, name, None)
    if coroutine is None:
        return None
    return func(
        coroutine,
        name=name,
        timeout=min(timeout, settings.JOB_TIMEOUT_MAX_S),
        max_tries=3,
    )


# (job, queue, timeout) — таймауты из tech-stack §2.5, поднятые до реального
# таймаута соответствующего слота LLM плюс запас на I/O.
_JOB_TIMEOUTS: tuple[tuple[str, str, float], ...] = (
    ("observe_chat", "interactive", settings.job_timeout_llm_bulk_s),
    ("set_summary", "interactive", settings.job_timeout_llm_chat_s),
    ("propose_personal_nodes", "interactive", settings.job_timeout_llm_chat_s),
    ("pregenerate_set", "bulk", settings.job_timeout_llm_bulk_s),
    ("soft_match", "bulk", settings.JOB_TIMEOUT_MAX_S),
    ("extract_program", "bulk", settings.job_timeout_llm_bulk_s),
)

for _name, _queue, _timeout in _JOB_TIMEOUTS:
    _entry = _registered(_name, _timeout)
    if _entry is not None:
        (INTERACTIVE if _queue == "interactive" else BULK).append(_entry)

JOB_TIMEOUTS: dict[str, float] = {
    name: min(timeout, settings.JOB_TIMEOUT_MAX_S)
    for name, _queue, timeout in _JOB_TIMEOUTS
}
JOB_QUEUES: dict[str, str] = {name: queue for name, queue, _ in _JOB_TIMEOUTS}
