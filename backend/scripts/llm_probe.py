"""One-shot live-provider probe for the B2 provider decision (docs/tz/30-B2.md §2).

Runs the three checks §2 asks for, against the real ``LLMClient`` and the
real ``Settings`` (no mocks, no fakes): ``structured()`` with
``ObservationOut`` on three prepared Russian chat fragments, ``stream()``
with a single ``get_time`` tool, and a reminder to check provider rate
limits by hand.

Not part of the test suite (tests/ is out of scope for this phase, see
docs/tz/30-B2.md's header) and not imported by application code — a
throwaway script attached to docs/decisions/llm-provider.md so the probe
can be re-run. Costs real provider credits each run; see that document for
the order-of-magnitude estimate.

Usage:
    uv run python scripts/llm_probe.py
    LLM_STRUCTURED_MODE=tool uv run python scripts/llm_probe.py   # §6 checklist item 3
"""

from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import dataclass, field

import app.llm.client as llm_client_module
from app.agents.observer import ObservationOut
from app.config import Settings
from app.errors import LLMUnavailable
from app.llm.client import LLMClient
from app.llm.prompts import load_prompt
from app.schemas.chat import TextDelta, ToolCall
from app.schemas.llm import LLMMessage, ToolCallOut

try:
    from redis.asyncio import Redis
except ImportError:  # pragma: no cover - redis is a project dependency
    Redis = None  # type: ignore[assignment, misc]

# --- §2 item 1: three prepared Russian chat fragments -----------------------
# Each is a short prep-chat window (4-6 turns), containing exactly one
# submitted solution with an error the tutor catches and the student fixes
# mid-fragment - written for this probe, not pulled from real chat data.

FRAGMENTS: list[tuple[str, str]] = [
    (
        "sat.alg.abs_value_eq",
        """Ученик: Помоги решить |2x-6|=4
Репетитор: Раскрой модуль как два случая: 2x-6=4 и 2x-6=-4. Попробуй сам.
Ученик: Хорошо: 2x-6=4 -> 2x=10 -> x=5. Всё, ответ x=5.
Репетитор: Ты нашёл только один случай. А что со вторым уравнением, 2x-6=-4?
Ученик: Ой, точно забыл про минус. Тогда 2x=2, x=1. Значит оба корня: x=5 и x=1.
Репетитор: Верно, теперь оба решения найдены.""",
    ),
    (
        "sat.alg.quadratic_roots",
        """Ученик: Реши x^2 - 4x + 3 = 0 через дискриминант.
Репетитор: Найди D = b^2 - 4ac. Какие тут a, b, c?
Ученик: a=1, b=-4, c=3. D = (-4)^2 - 4*1*3 = 16-4=12. Корни x=(4+-sqrt(12))/2.
Репетитор: Проверь вычитание: 4*1*3 это сколько?
Ученик: Ой, 4*1*3=12, значит D=16-12=4, sqrt(4)=2. x=(4+-2)/2 -> x=3 или x=1.
Репетитор: Теперь верно.""",
    ),
    (
        "sat.arith.percent_change",
        """Ученик: Цена товара была 8000, стала 10000. На сколько процентов выросла
цена?
Репетитор: Как ты посчитаешь процент изменения?
Ученик: Разница 2000, я разделил 2000 на 10000 и получил 20%.
Репетитор: На что нужно делить изменение — на старую цену или новую?
Ученик: А, точно, нужно делить на старую, 8000. 2000/8000=0.25, то есть рост на 25%.
Репетитор: Верно, 25%.""",
    ),
]

ALLOWED_SKILL_IDS: list[str] = [
    "sat.alg.abs_value_eq",
    "sat.alg.linear_eq",
    "sat.alg.linear_ineq",
    "sat.alg.quadratic_roots",
    "sat.alg.systems_of_eq",
    "sat.arith.percent_change",
    "sat.geom.circle_chord",
    "sat.stat.mean_median",
]

GET_TIME_TOOL = {
    "type": "function",
    "function": {
        "name": "get_time",
        "description": "Возвращает текущее серверное время в формате ISO 8601 UTC.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
}


@dataclass
class StructuredProbeResult:
    skill_id: str
    valid_first_try: bool | None = None
    n_observations: int | None = None
    skill_ids_seen: list[str] = field(default_factory=list)
    skill_ids_in_list: bool | None = None
    error: str | None = None


def _observer_messages(window: str) -> list[LLMMessage]:
    prompt = load_prompt("observer")
    system_text = prompt.render(
        window=window,
        skills="Допустимые skill_id для этого прогона (другие использовать нельзя): "
        + ", ".join(ALLOWED_SKILL_IDS),
        misconceptions="Библиотека заблуждений для этого прогона пуста — подходящих "
        "существующих заблуждений нет, но заводить proposed_misconception нужно, "
        "только если наблюдение действительно на это указывает.",
        task_instance="В этом окне репетитор не выдавал отдельной задачи с "
        "экземпляром — task_in_chat в этом фрагменте не применим.",
        previous_summary="Резюме предыдущего сета нет — это первый сет ученика.",
    )
    return [
        LLMMessage(role="system", content=system_text),
        LLMMessage(
            role="user",
            content="Вот окно сообщений для разбора:\n\n" + window,
        ),
    ]


async def run_structured_probe(
    client: LLMClient, settings: Settings
) -> list[StructuredProbeResult]:
    results: list[StructuredProbeResult] = []
    original_parse = llm_client_module.parse_structured_output

    for skill_id, window in FRAGMENTS:
        result = StructuredProbeResult(skill_id=skill_id)
        call_count = 0

        def instrumented_parse(raw_text, schema, _result=result):  # noqa: ANN001
            nonlocal call_count
            call_count += 1
            parsed, error = original_parse(raw_text, schema)
            if call_count == 1:
                _result.valid_first_try = parsed is not None
            return parsed, error

        llm_client_module.parse_structured_output = instrumented_parse
        try:
            messages = _observer_messages(window)
            out = await client.structured(messages, ObservationOut, "bulk")
            result.n_observations = len(out.observations)
            result.skill_ids_seen = sorted(
                {o.skill_id for o in out.observations if o.skill_id is not None}
                | {
                    o.root_skill_id
                    for o in out.observations
                    if o.root_skill_id is not None
                }
            )
            result.skill_ids_in_list = all(
                sid in ALLOWED_SKILL_IDS for sid in result.skill_ids_seen
            )
        except LLMUnavailable as exc:
            result.error = str(exc)
        finally:
            llm_client_module.parse_structured_output = original_parse

        results.append(result)

    return results


@dataclass
class StreamProbeResult:
    tool_called: bool = False
    text_before_call: bool = False
    text_after_call: bool = False
    time_to_first_text_delta_s: float | None = None
    error: str | None = None


async def run_stream_probe(client: LLMClient) -> StreamProbeResult:
    result = StreamProbeResult()
    messages = [
        LLMMessage(
            role="system",
            content="Ты ассистент. Если доступен инструмент get_time, используй его, "
            "чтобы ответить точно.",
        ),
        LLMMessage(
            role="user",
            content="Сколько сейчас времени? Вызови get_time, а затем одним "
            "коротким предложением скажи, какой сейчас, по-твоему, час суток.",
        ),
    ]
    start = time.monotonic()
    saw_tool_call = False
    tool_call_event: ToolCall | None = None
    try:
        async for event in client.stream(messages, "chat", tools=[GET_TIME_TOOL]):
            if isinstance(event, TextDelta):
                if result.time_to_first_text_delta_s is None:
                    result.time_to_first_text_delta_s = time.monotonic() - start
                if saw_tool_call:
                    result.text_after_call = True
                else:
                    result.text_before_call = True
            elif isinstance(event, ToolCall) and event.tool == "get_time":
                result.tool_called = True
                saw_tool_call = True
                tool_call_event = event
    except LLMUnavailable as exc:
        result.error = str(exc)
        return result

    got_tool_call = result.tool_called and tool_call_event is not None
    need_follow_up = got_tool_call and not result.text_after_call
    if need_follow_up:
        # Standard OpenAI-compatible tool-call protocol: a turn that calls a
        # tool ends there and waits for a role="tool" result before the
        # model continues - so a second stream() call, replying with a
        # synthetic get_time result, is the natural way to observe "text
        # after the call" rather than an extra unrelated request.
        synthetic_result = "2026-09-18T12:00:00Z"
        follow_up = [
            *messages,
            LLMMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCallOut(
                        call_id=tool_call_event.call_id,
                        name=tool_call_event.tool,
                        args=tool_call_event.args,
                    )
                ],
            ),
            LLMMessage(
                role="tool",
                content=f'{{"time": "{synthetic_result}"}}',
                tool_call_id=tool_call_event.call_id,
                name="get_time",
            ),
        ]
        try:
            async for event in client.stream(follow_up, "chat"):
                if isinstance(event, TextDelta):
                    result.text_after_call = True
                    if result.time_to_first_text_delta_s is None:
                        result.time_to_first_text_delta_s = time.monotonic() - start
        except LLMUnavailable as exc:
            result.error = (result.error or "") + f" | follow-up: {exc}"

    return result


def print_limits_reminder(settings: Settings) -> None:
    print()
    print("=== §2 item 3: лимиты аккаунта ===")
    print(
        "Лимиты запросов/мин и токенов/день смотрятся руками в дашборде "
        "Together (https://api.together.ai/settings/billing или "
        "аналогичная страница rate limits в личном кабинете) — этот скрипт "
        "их не запрашивает (нет API для этого через openai-совместимый "
        "эндпоинт)."
    )
    print(
        "Запишите проверенные значения с датой проверки в "
        "docs/decisions/llm-provider.md, раздел «Результаты пробы» -> "
        "«3. Лимиты аккаунта», и при необходимости пересчитайте "
        f"LLM_RPM_CHAT (сейчас {settings.LLM_RPM_CHAT}) / "
        f"LLM_RPM_BULK (сейчас {settings.LLM_RPM_BULK}) как запас 20% "
        "от подтверждённого лимита."
    )


async def _main() -> int:
    settings = Settings()
    if not settings.LLM_API_KEY.get_secret_value():
        print(
            "LLM_API_KEY пуст — нечем звонить провайдеру. Заполните "
            "backend/.env (LLM_API_KEY=...) и запустите снова.",
            file=sys.stderr,
        )
        return 1

    redis = Redis.from_url(settings.REDIS_URL) if Redis is not None else None
    client = LLMClient(settings, redis)

    print(f"LLM_BASE_URL: {settings.LLM_BASE_URL}")
    print(f"MODEL_BULK (structured): {settings.MODEL_BULK}")
    print(f"MODEL_CHAT (stream): {settings.MODEL_CHAT}")
    print(f"LLM_STRUCTURED_MODE: {settings.LLM_STRUCTURED_MODE}")
    print()

    print("=== §2 item 1: structured(ObservationOut) на трёх фрагментах ===")
    structured_results = await run_structured_probe(client, settings)
    valid_count = 0
    for res in structured_results:
        print(f"- фрагмент {res.skill_id}:")
        if res.error is not None:
            print(f"    ОШИБКА: {res.error}")
            continue
        print(f"    валиден с первого раза: {res.valid_first_try}")
        print(f"    наблюдений: {res.n_observations}")
        print(f"    skill_id в наблюдениях: {res.skill_ids_seen}")
        print(f"    все skill_id из списка: {res.skill_ids_in_list}")
        if res.valid_first_try:
            valid_count += 1
    print(f"Итого валидны с первого раза: {valid_count} из {len(structured_results)}")

    print()
    print("=== §2 item 2: stream() с инструментом get_time ===")
    stream_result = await run_stream_probe(client)
    if stream_result.error is not None:
        print(f"ОШИБКА: {stream_result.error}")
    else:
        print(f"инструмент вызван: {stream_result.tool_called}")
        print(f"текст до вызова: {stream_result.text_before_call}")
        print(f"текст после вызова: {stream_result.text_after_call}")
        print(
            f"время до первого text_delta: {stream_result.time_to_first_text_delta_s}"
        )

    print_limits_reminder(settings)

    if redis is not None:
        await redis.aclose()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
