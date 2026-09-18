[18.09.2026 04:28] [B2 → B3] app/schemas/llm.py отсутствует в скелете —
модели ModelSlot/LLMMessage/ToolCallOut/LLMUsage/LLMResult/LLMStatus временно
объявлены в app/llm/_schemas_shim.py по 00-contracts.md §6. После добавления
файла — замени импорты в app/llm/ на app.schemas.llm и удали shim.
ЗАКРЫТО 18.09.2026: app/schemas/llm.py создан по 00-contracts §6, импорты в
client.py переключены, shim удалён.

[18.09.2026 06:05] [B2 → B3] app/schemas/chat.py не содержит StreamEvent-варианты
(TextDelta/ToolCall/ToolResult/Done/StreamError, 00-contracts.md §6) — нужны
client.py для стриминга. Временно объявлены там же, в app/llm/_schemas_shim.py.
После добавления в schemas/chat.py — замени импорты в app/llm/ на
app.schemas.chat и удали эти классы из shim.
ЗАКРЫТО 18.09.2026: schemas/chat.py дополнен StreamEvent-вариантами (union с
дискриминатором "type"), импорты в client.py переключены, shim удалён.

[18.09.2026 08:00] [B2 → B3] создал schemas/llm.py, дополнил chat.py/common.py/config.py
по 00-contracts §6 — блокировало весь слой ИИ. Строго по контракту, отдельный коммит
136383d, ревью на синке.

[18.09.2026 09:15] [B2 → B3] добавил в keys.py две функции: llm_errors() → "quack:llm:errors"
и llm_probe() → "quack:llm:probe". llm_errors — счётчик ошибок circuit breaker, ключ назван
дословно в ТЗ §3.4 п.2, в таблице 00-contracts §4.5 его нет. llm_probe — маркер "идёт пробный
вызов после down", нужен потому что после истечения TTL статуса down (120с) счётчик ошибок
(TTL 60с) уже пуст и не может отличить "всё хорошо" от "ждём исхода пробного вызова" — статус()
должен отдавать degraded, а не ok, до исхода пробы (ТЗ §3.4 п.5). Тоже нет в 00-contracts §4.5.
Обе функции в стиле остальных (без аргументов или с slot-подобным строковым параметром), ничего
в keys.py не переименовано.

[18.09.2026] [B2] Расхождение ТЗ §4.1 (`@tool(name, description)`) с ТЗ §5.2 (`save_program`
требует `read_only=False`): добавил декоратору `tool()` параметр `read_only: bool = True`,
прокидывается в `ToolSpec.read_only`. Разрешено в пользу §5.2 — без параметра объявить пишущий
инструмент через декоратор невозможно.

[18.09.2026] [B2] Расхождение внутри ТЗ §4.3 п.3: внутренний объект конца цикла назван
`LoopDone` в одном предложении и `LoopEnd` в следующем. Разрешено в пользу `LoopEnd` (так его
ждут тесты команды §6) с полями `LoopDone` (`text_full`, `tool_results`, `steps`); объявлен
в `app/llm/loop.py`, не в `app/schemas/`.

[18.09.2026] [B2] Расхождение ТЗ §5.2 (`get_program_facts`) с product-logic §5.0 (там же
факт называется `get_program_requirements` в списке инструментов, читающих базу знаний о
поступлении). Разрешено в пользу буквального имени из исполняемого ТЗ 30-B2 §5.2 —
`get_program_facts` в `app/agents/selection.py`; по смыслу инструмент шире одних требований
(возвращает весь `Program`, включая стоимость и дедлайны), так что более широкое имя не
противоречит product-logic. Не переименовывал.

[18.09.2026] [B2] Расхождение ТЗ §5.3 (`explain_belief(ExplainBeliefArgs(skill_id))`,
`get_task(GetTaskArgs(skill_id, difficulty=None))`) с memory-architecture §9.5
(`explain_belief(node_id)`, `get_task(skill_id, with_trap?: misconception_id,
exclude_seen: true)`). Разрешено в пользу буквальных сигнатур из исполняемого ТЗ 30-B2
§5.3 — `app/agents/tutor.py` объявляет `ExplainBeliefArgs(skill_id: str)` и
`GetTaskArgs(skill_id: str, difficulty: int | None = None)`; поле названо `skill_id`, а не
`node_id`, но докстринг инструмента явно допускает id заблуждения (по §9.5). `with_trap` и
`exclude_seen` из §9.5 в аргументы не вынесены — в Ф1 тела всё равно стабы, деталь
реализации (какой инструмент пула выбрать) не блокирует каркас; учесть в Ф2 при реальной
реализации `get_task`.

[18.09.2026] [B2] Расхождение ТЗ §5.4 (`Observation.confidence: float = Field(ge=0, le=1)`,
без значения по умолчанию — обязательное поле) с примером выхода наблюдателя в
memory-architecture §8.1: последнее наблюдение примера, `{"kind": "pace_signal", "signal":
"asked_to_slow_down", "event_ids": [4423]}`, не содержит поле `confidence` вовсе. Пример
должен валидироваться схемой целиком без правок (явное требование шага) — буквальная
сигнатура ТЗ этого не допускает.

**Пересмотрено 18.09.2026** (после ревью): блок `confidence: float = Field(default=1.0, ...)`
делал дефолт общим для всех девяти `kind`, из-за чего забытый моделью `confidence` у
любого вида (включая `solution_step`) молча становился максимальным (1.0) и проходил
фильтр `observer_min_confidence` — прямо против правила §8.1 «при сомнении низкий
confidence, а не пропуск» (в промпте `observer_v1.md` то же самое буквально). Новое
решение: `confidence: float | None = Field(default=None, ge=0, le=1)`, и
`model_validator` требует его явно для всех `kind`, кроме `pace_signal` (`ValueError`
с именем поля в списке отсутствующих). Пропуск допустим только для `pace_signal` — по
таблице §8.1 у него вес/ярус "—" (в `Evidence` не превращается, идёт напрямую в
агрегаты профиля), так что отсутствующее значение (`None`) ни на что нижестоящее не
влияет; остальные восемь видов примера содержат `confidence` явно и продолжают
валидироваться как раньше. Пример §8.1 целиком по-прежнему валидируется без правок —
проверено смоуком (10/10 наблюдений).

[18.09.2026] [B2 → B3] `app/config.py` — чужой файл (00-contracts §2: `main.py config.py
keys.py errors.py logging.py` — B3), правка по прямому поручению в рамках шага ТЗ §2/§7:
`SettingsConfigDict` не читал `.env` вовсе (`env_file` не был задан) — `Settings()` рядом с
заполненным `backend/.env` отдавала пустые `LLM_BASE_URL`/`LLM_API_KEY`/`MODEL_CHAT`.
Добавлены `env_file=".env"`, `env_file_encoding="utf-8"`, `extra="ignore"` (без последнего
лишние переменные в `.env`, которых нет среди полей `Settings`, роняли бы валидацию —
`pydantic-settings` по умолчанию `extra="forbid"`, проверено явно). Приоритет переменных
окружения над файлом — поведение библиотеки по умолчанию, проверено явно (`LLM_STRUCTURED_MODE`
из env перекрывает значение из `.env`). Больше в файле ничего не менялось. B3 — ревью на
синке.

[18.09.2026] [B2 → B3] `backend/.gitignore` целиком игнорирует `docs/` (строка `docs/`), и
`backend/docs/` никогда не был закоммичен (`git log -- docs` пуст, `git ls-files docs`
пуст) — включая уже существующие там `docs/tz/30-B2.md`, `docs/sync-log.md` и этот шаг:
`docs/decisions/llm-provider.md`, `docs/tz/checklists/phase1-B2.md`. Не трогал `.gitignore`
(не мой файл, вне поручения этого шага) — фиксирую, чтобы не потерялось перед коммитом:
приёмка §7 требует `docs/decisions/llm-provider.md` в репозитории, а сейчас он не попадёт
в git ни при каком `git add .`. B3 — нужно решение: снять `docs/` из `.gitignore` (возможно
точечно, если под ним не должно быть чего-то ещё) до коммита результатов этого шага.

[18.09.2026] [B2 → B3] `deploy/.env.example` (корень репозитория, не `backend/`) — чужой
файл (00-contracts §2: `deploy/` целиком B3), правка по прямому поручению этого шага и по
`tech-stack.md` §2.1 (`LLM_*`/`MODEL_*` — B2, tech-stack §4.1). Файл уже существовал (с
блоком Postgres/Neo4j/Redis от B3) — дописан только блок языковой модели
(`LLM_BASE_URL, LLM_API_KEY=<пусто>, MODEL_CHAT, MODEL_BULK, LLM_STRUCTURED_MODE,
LLM_STRICT_SCHEMA, LLM_REASONING_CHAT, LLM_REASONING_BULK, LLM_TIMEOUT_CHAT_S,
LLM_TIMEOUT_BULK_S, LLM_RPM_CHAT, LLM_RPM_BULK, LLM_FORCE_DOWN`) со значениями из
`docs/decisions/llm-provider.md`, с комментарием, что остальное дополняет B3. Остальные
переменные 00-contracts §5 не добавлял.

[18.09.2026] [B2] `docs/tz/checklists/phase1-B2.md`, пункты 5–7 (сеть выключена/включена
→ `/health`, `LLM_FORCE_DOWN=1` → `/health` + `POST /chat/selection/messages` → 503,
эхо-чат через `curl -N`) отмечены как заблокированные: `app/api/`, `app/main.py` в этой
фазе — пустые однострочные заглушки B3 (`docs/tz/30-B2.md` §8 отдаёт SSE-транспорт и
роутеры B3), проверить эти пункты нечем до появления рабочих `/health` и
`POST /chat/{kind}/messages`. Со стороны B2 всё, что нужно этим пунктам, готово:
`agents.router.run_chat` (эхо) и `llm_client.status()` реализованы и проверены фейком
(`docs/tz/notes/b2-progress.md`), ждут только проводки B3 (00-contracts §7: B3 ждёт
`run_chat` и `status()` к 19:00, ориентир уже был).
