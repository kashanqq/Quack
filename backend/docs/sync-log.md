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

---

# Фаза 2: закрытие замечаний ревью (19.09.2026)

[19.09.2026] [B1] **Замороженный контракт `app/schemas/knowledge.py` изменён.**
`EvidenceIn.ordinal: int = 0`, `EvidenceContext.instance_id/message_id`,
`EvidenceOut.ordinal`. Причина: `merge_evidence` делал MERGE по
(event_id, skill_id) и не писал контекст — второе свидетельство одного
события (попадание в заблуждение) затирало первое, а `list_evidence` всегда
отдавал `instance_id=None, message_id=None`, из-за чего `explain_belief` и
раскрытие «до сообщения» были невозможны. Поля добавлены со значениями по
умолчанию, совместимость сохранена. Идентификатор свидетельства теперь
`{event_id}:{skill_id}:{ordinal}` (`personal.evidence_id` /
`parse_evidence_id`; двухчастная форма фазы 1 читается как ordinal = 0).

[19.09.2026] [B1] **Идемпотентность `apply_task_answered`.** `upsert_state`
больше не создаёт узел безусловно: если состояние по (skill, exam) уже
записано этим же `source_event_id` — вызов пустой. Сам обработчик выходит
раньше, если экземпляр уже отвечен (`tasks_repo.get_answered_at`), потому
что `bump_seen` и `mark_answered` не идемпотентны. Проверка сквозная:
`tests/apply/test_e2e_task.py::test_repeated_dispatch_keeps_the_same_counters`.

[19.09.2026] [B3] **Окно наблюдателя — явный флаг, а не побочный эффект.**
`message.user`, `message.assistant` (`api/chat.py`) и `task.issued`
(`apply/tasks.py`) пишутся с `dispatch_event=False`: они намеренно остаются
без `processed_at`, это окно наблюдателя (§8.1), которое он сам и закрывает.
Раньше это держалось на том, что транспорт передавал `deps=None`, и любой
рефакторинг транспорта съел бы окно. `events.store.append` теперь пишет
предупреждение `dispatch_without_deps`, если правила диспетчеризуются без
`RuleDeps`.

[19.09.2026] [B1] **Задача репетитора видна наблюдателю.** `apply.tasks.issue`
принимает `chat_id` и пишет `task.issued` с ним; событие пишется раньше
экземпляра, и экземпляр сохраняется с `mode` и `issued_event_id`. `via`
считается по режиму (`mock_*` → `mock`, `chat` → `chat`, иначе `topic`).

[19.09.2026] [B1] **Вес задачи из чата.** Пара `("task", "chat")` внесена в
таблицу §4.3 со значением 0.8; `reconcile_task_answer` для режима `chat`
ставит `source="task"`, `kind="task_in_chat"`. Раньше выходило
`source="chat"`, `kind=None` — такой комбинации в таблице нет, вес был 0,
то есть ответ на задачу из чата не двигал модель знаний вовсе.

[19.09.2026] [B3] **Очередь задач в API.** `app.state.arq` (`ArqRedis`,
создаётся лениво через `from_url`, чтобы недоступный Redis не задерживал
старт) и зависимость `api.deps.get_arq`. `enqueue` переехал в
`app/workers/queue.py`, чтобы маршруты не импортировали воркер (кольцо
`api → workers.main → main`); загрузка необязательных слоёв — в `app/loader.py`.

[19.09.2026] [B3] **Пер-функциональные таймауты задач.** `job_timeout` очереди
остаётся потолком коротких задач (interactive 30 с, bulk 90 с), а задачи,
которые ходят в LLM, объявляют свой собственный через `arq.worker.func`:
`observe_chat` — `LLM_TIMEOUT_BULK_S + 15` и так далее (`app/workers/registry.py`,
таблицы `JOB_TIMEOUTS` / `JOB_QUEUES`). Наблюдатель на слоте bulk в 30 с
очереди не укладывался.

## Ответы на уточнения ревью

[19.09.2026] [B1] `TaskRequestIn.difficulty: int | None` добавлено (замороженный
контракт `schemas/tasks.py`) — иначе `GetTaskArgs.difficulty` репетитора было
некуда передать. `tasks.select.pick_template(difficulty=...)` заменяет расчёт
по последним ответам. Заодно `apply.tasks.issue` наконец передаёт реальные
последние оценки навыка (`tasks_repo.last_grades_for_skill`), а не пустой список.

[19.09.2026] [B1] `p_target` закрыт в этой фазе. `app/apply/targets.py` берёт
цель из `roadmap.requirements.build_requirements` (максимальный порог
сохранённых программ либо ручная цель анкеты) и считает
`min(p_target_max, target / max_raw)`; порог в шкалированных баллах переводится
в сырые по таблице экзамена. Используют `apply.sets.rebuild_sets`,
`apply.knowledge.states_view` и `apply.task_answered` (через новый аргумент
`reconcile_task_answer(p_target=...)`). TODO в `apply/sets.py` и
`apply/knowledge.py` сняты.

[19.09.2026] [B1] Формат `obs.answer` подтверждён и расширен: `tasks.answer.grade`
принимает букву для mcq, число или строку для numeric, список букв, а теперь и
одну строку «A, B» / «A B» / «AB» для multi_select — наблюдатель кладёт в
`obs.answer` то, что написал ученик.

[19.09.2026] [B1] Синонимы направлений: `app/matching/directions.py`
(`direction_matches`) вместо сравнения подстрокой в `matching/hard.py`.
Словарь покрывает направления демо-датасета в русском и английском написании;
незнакомое направление по-прежнему сравнивается подстрокой в обе стороны.

[19.09.2026] [B3] Кнопка «обновить модель знаний»: `POST /knowledge/refresh`
пишет `observer.requested` и ставит `observe_chat` на очередь `interactive`.
Ответ `RefreshOut{status: queued|empty|failed, job_id, window_size,
failed_reason}`. `failed_reason` добавлен: `llm_unavailable`,
`queue_unavailable`, `job_not_enqueued` — «модель недоступна» и «очередь
недоступна» это разные сообщения ученику, а пустое окно вообще не ошибка
(`empty`).

[19.09.2026] [B2] Чат сета: поддержка контекстом и наблюдателем остаётся,
фронт его не запрашивает — в фазу не включаем, отдельного маршрута не заводим.
`chat_id_for(student_id, kind, set_id, topic_skill_id)` вынесен из `api/chat.py`
в общую функцию, так что подключение — один вызов, когда фронт будет готов.

[19.09.2026] [B2] `tool_result.data`: `ToolResult` получил `model_data`
(в поток SSE не сериализуется). Инструмент, у которого представление для фронта
и для модели различаются, возвращает `ToolPayload(data=..., model_data=...)`;
`run_tool_loop` кладёт в контекст модели именно `model_data`. Сжатая проекция
подбора — `app/matching/brief.py` (id, вуз, направление, реализм, три главных
фактора) вместо 3–4 КБ карточек на каждый ход.

[19.09.2026] [B2] Расход токенов: `LLMClient.last_usage()` (тот же метод у
`FakeLLMClient` и в протоколе `LLMLike`) — `complete`, `structured` и `stream`
пишут туда usage последнего вызова, так что расход наблюдателя измерим, а не
оценивается по прайсу.

[19.09.2026] [B1] Новые параметры в `KnowledgeParams` (и в §12
`memory-architecture-quack.md`): `observer_window_max=30`,
`assistant_max_questions=3`, `assistant_readiness_threshold=0.6`,
`context_set_multiplier=2.0`, `tutor_escalate_after_failures=2`. Таймауты задач —
в `Settings`: `JOB_TIMEOUT_DEFAULT_S`, `JOB_TIMEOUT_MAX_S` и свойства
`job_timeout_llm_chat_s` / `job_timeout_llm_bulk_s`.

## Попутно найденное и починенное

[19.09.2026] [B1] `personal.upsert_misc_state` не работал вовсе: Cypher падал с
`42N24 A WITH clause is required between 'MERGE' and 'MATCH'`. Добавлен
`WITH ms, m`. Раньше это не ловилось, потому что интеграционные тесты графа не
запускались (см. ниже).

[19.09.2026] [B1] `graph.queries.kb`: `list_test_dates` / `list_facts_about`
отдавали `neo4j.time.Date`, а контракты объявлены на `datetime.date` — падала
валидация. Добавлен `_as_date`.

[19.09.2026] [B1] `merge_evidence` не писал `e.student_id`, хотя индекс
`evidence_recent` объявлен на `(student_id, observed_at)`. Теперь пишет. Индекс
`evidence_key` расширен до `(event_id, skill_id, ordinal)`, добавлены индексы по
`ctx_instance_id` и `ctx_message_id`.

[19.09.2026] [B1] `apply.profile_updated` теперь действительно вызывает
`reconcile_prior` (§4.8) и пишет приоры анкеты в граф; раньше это был TODO в
докстринге, а приоры никуда не попадали.

[19.09.2026] [B3] Интеграционные тесты графа: `tests/graph/test_personal_phase2.py`
не объявлял `pytest.mark.asyncio(loop_scope="module")` и падал целиком
(«attached to a different loop»), а модули сидировали разные наборы навыков в
одну базу, из-за чего `test_sat_weights_sum_to_max_raw_score` зависел от порядка
запуска. Добавлены `loop_scope` и общая очистка графа
(`tests.conftest.wipe_graph`) перед сидированием.

[19.09.2026] [B1] `apply.diagnostic._persist_indirect` писал косвенные
свидетельства с `event_id=0`, то есть все они за всё время сводились в один
узел на навык. Теперь свидетельства привязаны к событию `diagnostic.progress`
(и разведены по `ordinal`), а само событие пишется с `dispatch_event=False` —
правил у него нет.

[19.09.2026] [B1] `apply.sets` клал прогноз в кэш с `as_of_event_id=0`, так что
по нему нельзя было понять, на каком состоянии журнала он посчитан. Добавлен
`events.store.last_event_id(session, student_id)`.
