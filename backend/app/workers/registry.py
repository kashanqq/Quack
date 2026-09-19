"""ARQ job registry: which queue each job runs on and how long it may take.

Очереди — tech-stack §2.5: `interactive` для того, чего ученик ждёт прямо
сейчас, `bulk` для фоновой подготовки. Таймаут очереди (`job_timeout`
воркера) — потолок для коротких задач (`ping`); задача, которая ходит в LLM,
объявляет свой собственный через `arq.worker.func(timeout=...)`.

Фаза 3 (docs/tz/phase3-agents.md §3.12, F19): в `interactive` —
`observe_chat` (`OBSERVER_JOB_TIMEOUT_S`) и `canonize_misconception`
(`CANON_JOB_TIMEOUT_S`); задачи фаз 4–6 ещё стабы и не регистрируются.

`observe_chat` ставится с `job_id=observe:{chat_id}`: ARQ отвергает дубль,
пока job стоит или идёт. `keep_result=0`, иначе хранимый результат держал бы
этот id занятым ещё час после завершения и следующий триггер чата молча
пропадал бы. У канонизации результат хранится: `canon:{event}:{ordinal}` и
должен оставаться занятым.

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

# (job, queue, timeout, keep_result)
_JOBS: tuple[tuple[str, str, float, float | None], ...] = (
    ("observe_chat", "interactive", settings.OBSERVER_JOB_TIMEOUT_S, 0),
    ("canonize_misconception", "interactive", settings.CANON_JOB_TIMEOUT_S, None),
)


def _registered(
    name: str, timeout: float, keep_result: float | None
) -> Function | None:
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
        keep_result=keep_result,
        max_tries=3,
    )


for _name, _queue, _timeout, _keep in _JOBS:
    _entry = _registered(_name, _timeout, _keep)
    if _entry is not None:
        (INTERACTIVE if _queue == "interactive" else BULK).append(_entry)

JOB_TIMEOUTS: dict[str, float] = {
    name: min(timeout, settings.JOB_TIMEOUT_MAX_S) for name, _q, timeout, _k in _JOBS
}
JOB_QUEUES: dict[str, str] = {name: queue for name, queue, _t, _k in _JOBS}
