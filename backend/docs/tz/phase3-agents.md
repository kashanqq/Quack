# ТЗ фазы 3 — агенты: ассистент подбора, репетитор, наблюдатель

Quack! · фаза 3 «агенты» · v0.1 · 19.09.2026. Один документ на фазу (дельта контрактов — §5, задания по владельцам — внутри компонентов §3, тесты — §6, приёмка — §7). Источники: `backend-phases.md` §3, `product-logic.md` §3.2, §4.5, §6.2–6.3, §9; `memory-architecture-quack.md` §4.3, §5.4, §8.1, §9, §10.3, §10.6, §11, §12; `tech-stack.md` §2.4, §2.5, §4; `00-contracts.md`, `00-contracts-phase2.md`; состояние ветки после фазы 2 (файлы `app/**` на 19.09).

Правило чтения: всё, что не названо в §5 «Контракты», остаётся как в фазах 1–2. Модель никогда не пишет в граф и в Postgres напрямую: единственный путь записи — инструмент → `events.store.append` → `events.dispatch` → обработчик `apply/*`.

---

## 1. Исходное состояние

### 1.1 Что уже существует к началу фазы 3

| Слой | Готово (используется фазой 3 как есть) |
| :---- | :---- |
| **B2 `app/llm/`** | `LLMClient` (`complete`/`stream`/`structured`/`status`; два слота `chat`/`bulk`; таймауты `LLM_TIMEOUT_*`; rate-limit `INCR+EXPIRE` на `keys.llm_ratelimit(slot)`; circuit breaker `keys.llm_status/llm_errors/llm_probe`; `reasoning_effort` по слоту; `structured` с одним встроенным повтором на невалидный JSON и `LLMUnavailable("structured output failed")` после него; `LLM_FORCE_DOWN`). Протокол `LLMLike`. `FakeLLMClient` со скриптом `FakeTurn` и помощниками `tool_call_turn`/`text_turn`, `calls`, `tool_messages()`. `ToolRegistry`/`@tool`/`ToolCtx(student_id, deps, request_id)`. `run_tool_loop(client, registry, messages, slot, ctx, max_steps=6) -> AsyncIterator[StreamEvent \| LoopEnd]`. `load_prompt(name) -> Prompt(name, version, text)`, `Prompt.render`, `Prompt.extractor_version`. |
| **B2 `app/agents/`** | `router.run_chat` (эхо, без истории и инструментов), `AgentDeps(llm, pg, graph, redis)`. `selection.py`: стаб `run`, реестр `SELECTION_TOOLS` из 8 инструментов с моделями аргументов и описаниями, тела `NotImplementedError("phase 2")`. `tutor.py`: стаб `run`, `TUTOR_TOOLS = ToolRegistry(read_only=True)` из 3 инструментов. `observer.py`: `ObservationKind`, `Observation` с `model_validator` по `kind`, `ObservationOut`; стаб `observe`. `postcheck.check_facts(text, tool_results) -> PostcheckResult(ok, mismatches)` — чистая функция, **не в цепочке**. `jobs.py`: 6 стабов ARQ (`observe_chat`, `pregenerate_set`, `set_summary`, `propose_personal_nodes`, `soft_match`, `extract_program`); **`canonize_misconception` отсутствует**. Промпты `selection_v1..v3`, `tutor_v1..v2` (`{{learner_model}}`), `observer_v1` (`{{window}} {{skills}} {{misconceptions}} {{task_instance}} {{previous_summary}}`), `extract_program_v1`, `gen_template_v1`. Провайдер: Together, `MODEL_CHAT=DeepSeek-V4-Flash`, `MODEL_BULK=DeepSeek-V4-Pro`, `LLM_STRUCTURED_MODE=response_format` (`docs/decisions/llm-provider.md`). |
| **B1 правила** | `knowledge.reconcile.reconcile_task_answer(...)`, `reconcile_prior`; `knowledge.hlr.apply_evidence` (потолок `p_chat_cap` для яруса 3 уже реализован); `knowledge.weights` (таблица §4.3 включая чатовые `kind`: `task_in_chat 0.8`, `solution_step 0.7`, `avoided_trap 0.7`, `confusion 0.6`, `applied 0.5`, `question 0.2`; `tier_for`, `is_strong`); `knowledge.misconceptions.next_status(event=hit\|avoided\|dispute\|undispute)`, `update_triggers`, `visible_label`, `visible_to`, `trigger_words`; `knowledge.roots`; `knowledge.words.skill_level/trend/state_words`; `sets/*`, `matching/*` (`hard_filter`, `realism`, `rank`, `compare`, `shift.diff`, `explain_empty`), `tasks/*`, `roadmap/*`. |
| **B1 граф** | `graph.queries.personal`: `ensure_student`, `get_state(s)`, `upsert_state` (новый узел + `PREVIOUS`, `source_event_id`), `merge_evidence` (MERGE по `(event_id, skill_id)`, контекст **не пишется**), `get_misc_states`, `upsert_misc_state` (MERGE по `(student_id, misconception_id)`), `add_root_cause` (MERGE по `(evidence_id, root_skill_id)`), `list_evidence` (читает `e.ctx_instance_id`, `e.ctx_message_id` — всегда `None`, см. §5), `list_root_causes`, `get_state_history`. `canonical`: `get_skill`, `list_exam_skills`, `list_areas`, `get_prerequisites(depth)`, `get_dependents`, `get_exam_format`, `list_misconceptions_for_skill`, `list_templates_for_skill`. `kb`: `get_admission_route`, `list_test_dates`, `list_facts_about`. Vector index `misc_emb` (384, cosine). `graph.context.TopicContext` (9 слотов `list[str]`), стаб `build_topic_context(driver, student_id, skill_id, set_id)`. `embeddings.Embedder(model_name, dim).embed(texts)` — ленивая загрузка. |
| **B1 `app/apply/`** | `task_answered.apply_task_answered` (11 шагов §8.2, `AnswerResult`), `apply_task_skipped`, `profile_updated`, `dispute`, `sets.rebuild_sets` (лок `quack:lock:rebuild:{sid}` 10 с, `bump` версии), `open_set`, `on_program_change`, `on_set_change`, `on_run_completed`, `diagnostic.*`, `mocks.*`, `tasks.issue` (шаблон → экземпляр → `insert_instance` → событие `task.issued` с `chat_id=None`), `knowledge.states_view/misconceptions_view/explain`. |
| **B3 платформа** | `events.store.append(session, redis, ev, deps=None, *, dispatch_event=True)` (при `deps=None` диспетчер строится с `graph=None` → событие остаётся `processed_at=NULL`), `list_unprocessed(session, chat_id, limit)`, `mark_processed`, `list_events`, `list_by_type`; `events.dispatch.dispatch(session, event, deps) -> dict[str, Any]`, `RuleDeps(graph, redis, params, now)`, маркер `GraphUnavailable`, `on(EventType)`; `events.handlers` — единственный реестр; `events.version.bump/get`; `events.session.current_session_id`. `api/chat.py`: `POST /chat/{kind}/messages` (пишет `message.user` **до** вызова агента, оборачивает поток `_wrap_agent`, на `Done` пишет `message.assistant` + `messages`, подставляет `event_id`; `ToolCall`/`ToolResult` пропускает наружу как есть; на `StreamError` завершает поток без записи ответа), `GET /chat/{kind}/messages`, `_chat_id` (`uuid5(student,"selection")`, `uuid5(student, f"prep:{set_id}:{topic_skill_id}")`, prep без `set_id`/`topic_skill_id` → 400). `api/sse.py` (keepalive 15 с, поток закрывается на `done`/`error`). `api/deps.get_rule_deps`. Роутеры фазы 2 (`tasks`, `sets`, `diagnostic`, `mocks`, `matching`, `overview`, `knowledge`, `profile`, `saved`, `prep/knowledge/version`, `health`). `db.repo.*` (`messages.append_message/list_messages`, `profiles.get_profile/apply_profile_update`, `programs.*`, `tasks.*`, `sets.*`, `forecast.*`, `texts.*`). Таблицы `0001`+`0002` (включая `set_summaries`, `daily_aggregates`, `messages`). `workers/main.py` (`startup` кладёт в `ctx` `sessionmaker`, `neo4j`, `redis`, `llm`; `enqueue(redis, queue, fn_name, **kwargs)` прокидывает `request_id`; `WorkerInteractive` `job_timeout=30`, `max_tries=3`), `workers/registry.py` (только `ping`). `keys.py` (`session`, `llm_*`, `knowledge_version`, `forecast`, `ctx_topic(sid, skill)`, `lock(name)`). `conftest`: `redis` (fakeredis), `fake_llm`, `frozen_now`, `rule_deps`, `db_session`, `seeded_graph`, `student_with_saved`, `templates_db`, `fake_apply`. |

### 1.2 Стабы фаз 1/2, которые закрывает фаза 3

| Стаб / отсутствующая часть | Где | Владелец |
| :---- | :---- | :---- |
| `agents.router.run_chat` — эхо → ветвление `selection.run` / `tutor.run` с историей | `app/agents/router.py` | B2 |
| `agents.selection.run` и тела 8 инструментов | `app/agents/selection.py` | B2 |
| `agents.tutor.run` и тела 3 инструментов | `app/agents/tutor.py` | B2 |
| `agents.observer.observe` → `observer.run` | `app/agents/observer.py` | B2 |
| `agents.jobs.observe_chat`; новый `agents.jobs.canonize_misconception` | `app/agents/jobs.py` | B2 |
| `postcheck` — функция есть, в цепочке нет | `app/agents/postcheck.py`, `selection.py`, `tutor.py` | B2 |
| `graph.context.build_topic_context` | `app/graph/context.py`, новый `app/graph/queries/context.py`, новый `app/apply/context.py` | B1 |
| обработчик `observation.extracted`, обработчики канонизации | новый `app/apply/observation.py`, строки в `events/handlers.py` | B1 (+ строки B3) |
| реестр воркеров: `observe_chat`, `canonize_misconception` в `interactive`; эмбеддер при старте `worker-interactive` | `app/workers/registry.py`, `app/workers/main.py` | B3 |
| транспорт чата: постановка наблюдателя после `done`, `observer.requested`, диф наблюдений, лок чата | `app/api/chat.py`, `app/api/sets.py`, `app/main.py` | B3 |

### 1.3 Что вне фазы 3

Тексты моделью вне чата (гайдлайны, объяснения, отчёт по сету, «подходит тебе», `CompareOut.conclusion`, резюме понимания как кэш) — фаза 4. `jobs.pregenerate_set`, `set_summary`, `soft_match`, `extract_program`, `search.extract`, `daily_aggregates` как крон, лента Quack, варианты по темпу — фаза 4. Персональные узлы навыков (`propose_personal_nodes`, `PART_OF`) — фаза 6. Replay и отложенное применение событий при упавшем графе — фаза 5 (здесь только сохраняется `processed_at=NULL` и идемпотентность). Эвал наблюдателя как гейт версии промпта — фаза 5/6 (в фазе 3 — ручной чек-лист на ≥ 10 фрагментах). Показ рассуждений модели (`ReasoningDelta`) — нет. Изменение SSE-контракта `StreamEvent` — нет (см. §3.6 «что получает пользователь»).

### 1.4 Входные контракты фазы 2, которые не меняются без явной дельты

Не меняются (любое изменение — только через §5 этого документа и `sync-log`): все модели `app/schemas/{common,profile,programs,knowledge,tasks,sets,roadmap,diagnostic,mocks,matching,chat,llm,health}.py` (кроме перечисленных в §5); `EventType` (кроме добавления `misconception.canonized`, §5); `EventIn`/`Event`; `StreamEvent` (`TextDelta | ToolCall | ToolResult | Done | StreamError`) и `AssistantMarkup`; `ChatCtx`, `ChatMessageIn`, `MessageOut`; `RuleDeps`, сигнатура `dispatch`, семантика «событие + правило в одной сессии Postgres, коммит после dispatch», маркер `GraphUnavailable`; `events.version.bump` как единственная точка инкремента; сигнатуры `apply.*` §7.2 дельты фазы 2 (кроме `apply.tasks.issue`, §5); сигнатуры чистых функций §7.1 (кроме дополнений `weights`/`reconcile`, §5); `db.repo.*` §7.4; ключи Redis §4.5/§4.4 (дополняются); `KnowledgeParams` (дополняется); правило слоёв `tests/test_layers.py`; `LLMLike`, `LLMClient` (поведение при ошибках не меняется: провайдерские исключения `openai.*` пробрасываются как есть, `LLMUnavailable` — только breaker/rate-limit/structured); `ToolRegistry.register/schemas/call/names`, `run_tool_loop` (дополняется, §5); `FakeLLMClient`.

---

## 2. Сквозные решения фазы

### 2.1 Цепочка выполнения одного хода чата

```
POST /chat/{kind}/messages (B3)
  → лок чата keys.lock(f"chat:{chat_id}") (SET NX EX CHAT_LOCK_TTL_S); занят → 409 conflict
  → append message.user (dispatch_event=False) + messages.append_message, commit
  → agents.router.run_chat(kind, ctx, message, deps)            (B2)
      → история: db.repo.messages.list_messages(limit=params.chat_window)
      → профиль: db.repo.profiles.get_profile
      → kind=selection: selection.run(ctx, message, history, profile, deps)
        kind=prep:      tutor.run(ctx, message, history, profile, deps)
          → системный промпт = load_prompt(...).render(...) + контекст (профиль / <learner_model> + <session>)
          → messages = [system] + история + user
          → registry = политика доступа инструментов на этот ход
          → run_tool_loop(deps.llm, registry, messages, "chat", ToolCtx(...), max_steps)
              → TextDelta наружу; ToolCall наружу; registry.call → ToolResult наружу; следующий шаг модели
              → LoopEnd(text_full, tool_results, steps)
          → postcheck (§3.6) — последний шаг перед done
          → Done(event_id=0, markup)  |  StreamError(code="postcheck_failed")
  → _wrap_agent (B3): на Done — append message.assistant + messages, event_id в Done; на StreamError — ничего не пишет
  → после Done для kind=prep: триггер наблюдателя (§3.12)
  → снять лок чата
```

Слот модели у обоих агентов — `chat`. Наблюдатель и канонизация — слот `settings.OBSERVER_SLOT` (по умолчанию `bulk`).

### 2.2 Единственный путь записи

| Кто | Что пишет | Как |
| :---- | :---- | :---- |
| Инструмент `update_profile` | профиль | `db.repo.profiles.apply_profile_update` + событие `profile.updated` (`by="assistant"`) + `dispatch` — тот же код, что `PATCH /profile` |
| Инструмент `save_program` | сохранённые | `db.repo.programs.save_program` + событие `program.saved` + `dispatch` — тот же код, что `POST /saved/{id}` |
| Инструмент `get_task` | экземпляр задачи | `apply.tasks.issue(..., chat_id=ctx.chat.chat_id)` → `task.issued` |
| Транспорт | `message.user`, `message.assistant`, `observer.requested` | `events.store.append` |
| `jobs.observe_chat` | `observation.extracted` (+ `mark_processed` окна) | `events.store.append(..., deps, dispatch_event=True)` |
| `jobs.canonize_misconception` | `misconception.personal_created` / `misconception.canonized` | `events.store.append(..., deps, dispatch_event=True)` |
| Правило `apply.observation` | `Evidence`, `KnowledgeState`, `MisconceptionState`, `ROOT_CAUSE`, `task.answered` (для `task_in_chat`), `daily_aggregates.pace_signals` | внутри `dispatch` |
| Любой воркер при финальной ошибке | `job.failed` | `events.store.append(dispatch_event=False)` |

Ни один инструмент репетитора не пишет в персональный слой (`TUTOR_TOOLS` остаётся `read_only=True`; `get_task` пишет только `task_instances` и событие `task.issued`, что допускается контрактом фазы 1 как «выдача задачи», не «запись в модель знаний»). Модель не получает ни `AsyncSession`, ни `driver`: тела инструментов сами открывают сессию `async with ctx.deps.pg() as session` и коммитят.

### 2.3 Зависимости и слои

`api → agents → apply → graph/db`. Разрешено: `agents` импортирует `apply`, `db.repo`, `graph.queries`, `matching`, `knowledge`, `events`. Запрещено: `apply`, `knowledge`, `graph` импортируют `app.agents`/`app.llm` (проверяет `tests/test_layers.py`; `apply/` дополнительно не импортирует `arq`). `app/api/*` не импортируется никем, кроме `main`.

### 2.4 Идемпотентность и ключи

| Что | Ключ идемпотентности | Механизм |
| :---- | :---- | :---- |
| Наблюдение → `Evidence` | `(event_id, skill_id, ordinal)` | `merge_evidence` MERGE по трём полям (§5); перед применением читается множество уже записанных ключей события |
| Наблюдение `task_in_chat` | `instance_id` | `task_instances.answered_at IS NOT NULL` → пропуск |
| `root_hint` | `(evidence_id, root_skill_id)` | `add_root_cause` MERGE |
| `proposed_misconception` → канонизация | `job_id = f"canon:{event_id}:{ordinal}"` | ARQ отвергает дубликат `job_id` в очереди; результат-событие проверяет `Misconception.source_event_id/ordinal` перед созданием узла |
| Постановка наблюдателя | `job_id = f"observe:{chat_id}"` | один активный job на чат; повторный триггер во время работы — дозапуск в конце job (§3.9) |
| Ход чата | лок `quack:lock:chat:{chat_id}` | параллельный запрос того же чата → 409 |
| Запись в граф одного ученика | лок `quack:lock:knowledge:{student_id}` (ожидание ≤ 5 с) | `apply.observation`, `apply.task_answered`, `apply.dispute` через общий помощник `apply._lock.student_lock` |
| Контекст топика | `quack:ctx:topic:{sid}:{skill}` → `{"version": knowledge_version, "set_id", "built_at", "graph": {...}}` | попадание при равенстве `version` и `set_id`; иначе пересборка; TTL `CTX_CACHE_TTL_S` |

### 2.5 Параметры

Дополнения к `KnowledgeParams` (и к §12 `memory-architecture-quack.md` одновременно, значения переопределяются `KNOWLEDGE__<ИМЯ>`):

| Параметр | Значение | Где |
| :---- | :---- | :---- |
| `observer_window_max` | 30 | максимум сообщений в одном окне наблюдателя (§3.9) |
| `assistant_max_questions` | 2 | постпроверка ассистента подбора: вопросительных знаков в ответе не больше (§3.6) |
| `assistant_readiness_threshold` | 0.6 | `profile.readiness`, при котором ассистент переходит к резюме понимания (§3.2) |
| `context_set_multiplier` | 1.5 | лимиты слотов контекста для чата сета (§3.7) |
| `tutor_escalate_after_failures` | 2 | после скольких подряд неудач поднимается уровень подсказки (§3.4) |

Дополнения к `Settings` (B3): `OBSERVER_SLOT: Literal["chat","bulk"] = "bulk"`, `CTX_CACHE_TTL_S: int = 3600`, `CHAT_LOCK_TTL_S: int = 120`, `OBSERVER_JOB_TIMEOUT_S: int = 100` (≥ `LLM_TIMEOUT_BULK_S + 10`), `CANON_JOB_TIMEOUT_S: int = 30`.

### 2.6 Логирование

`structlog`, JSON, `request_id` из middleware (API) или из аргумента job (воркер: `structlog.contextvars.bind_contextvars(request_id=...)` первой строкой каждой job). Тексты сообщений, промпты, ответы модели и аргументы инструментов **не логируются** целиком (00-contracts §3.2); допускаются: имена инструментов, `call_id`, длины, `event_id`, `chat_id`, `student_id`, коды ошибок, числа. Обязательные записи: `chat_turn_started{kind, chat_id, stage|mode}`, `tool_called{tool, call_id, ok, ms}`, `tool_denied{tool, reason}`, `postcheck{kind, ok, mismatches, questions}`, `chat_turn_done{steps, text_len, tools}`, `observer_enqueued{chat_id, trigger}`, `observer_job{chat_id, window, observations, ms}`, `observation_applied{event_id, applied, skipped, version}`, `observation_skipped{event_id, ordinal, reason}`, `canonize{event_id, ordinal, decision, similarity}`, `job_failed{job, job_id, reason}`, `ctx_topic{hit|miss|rebuilt, ms}`.

---

## 3. Компоненты

Формат каждого компонента: назначение · расположение · публичный интерфейс · вход · выход · зависимости · последовательность · ошибки · граничные случаи · идемпотентность · concurrency · логирование · тестируемое поведение.

### 3.1 `agents.router.run_chat` (B2)

**Назначение.** Единая точка входа чата: загрузить историю и профиль, выбрать агента по `kind`, отдать его поток как есть, сохранить семантику ошибок фазы 1 (`LLMUnavailable` до первого события — исключение, после — `StreamError`).

**Расположение.** `app/agents/router.py` (файл фазы 1, `AgentDeps` без изменений).

**Интерфейс.** `async def run_chat(kind: ChatKind, ctx: ChatCtx, message: ChatMessageIn, deps: AgentDeps) -> AsyncIterator[StreamEvent]` — сигнатура фазы 1 без изменений.

**Вход.** `kind`, `ctx` (в т. ч. `chat_id`, `session_id`, `request_id`, `set_id`, `topic_skill_id`), текст сообщения, `deps`.

**Выход.** События `TextDelta | ToolCall | ToolResult`, последним ровно одно из: `Done(event_id=0, mode, gave_task_instance_id, hint_level, referenced_skill_ids)` или `StreamError`.

**Зависимости.** `db.repo.messages.list_messages`, `db.repo.profiles.get_profile`, `selection.run`, `tutor.run`, `settings.knowledge.chat_window`.

**Последовательность.**
1. `async with deps.pg() as session`: `history = list_messages(session, ctx.student_id, ctx.chat_id, limit=params.chat_window)`; `profile = get_profile(session, ctx.student_id)`. Сессия закрывается до вызова агента (агент и инструменты открывают свои).
2. История нормализуется: если последний элемент — `role="user"` с текстом, равным `message.text`, он удаляется (транспорт уже записал текущее сообщение); текущее сообщение всегда добавляет сам агент последним.
3. `kind == "selection"` → `selection.run(ctx, message, history, profile, deps)`; `kind == "prep"` → `tutor.run(...)`. Иных `kind` нет (Pydantic отсекает раньше).
4. События агента отдаются без изменений. Если первое событие агента — `StreamError(code="llm_unavailable")` и до него ничего не отдано, роутер поднимает `LLMUnavailable` (транспорт → 503). Любой `StreamError` позже — отдаётся как есть, поток завершается.

**Ошибки.** Ошибка Postgres при чтении истории — исключение наружу (транспорт отдаёт `StreamError(internal)`; сообщение пользователя уже сохранено). `FileNotFoundError` промпта — исключение (баг конфигурации, не маскируется).

**Граничные случаи.** Пустая история (первый ход) — агент получает `[]`, ассистент подбора трактует как стадию `opening`. История длиннее `chat_window` — берутся последние `chat_window` сообщений (репозиторий отдаёт хронологически, oldest first). Сообщения с `markup=None` (user) и с `markup` (assistant) конвертируются в `LLMMessage(role, content=text)`; разметка в текст модели не попадает.

**Идемпотентность.** Роутер не пишет. Повторная отправка того же текста — новый ход (дедупликацию сообщений продукт не требует).

**Concurrency.** Лок чата — у транспорта (§3.12). Роутер параллельных ходов одного чата не допускает по контракту, но не проверяет.

**Логирование.** `chat_turn_started{kind, chat_id, history_len}`; `chat_turn_done` пишет агент.

**Тестируемое поведение.** §6.3 `tests/agents/test_router.py`: ветвление по `kind`, окно истории, удаление дубля текущего сообщения, 503-семантика.

### 3.2 Ассистент подбора — `agents.selection.run` (B2)

**Назначение.** Провести ученика от пустого профиля к сохранённым программам по политике product-logic §3.2: открытие → добор → резюме понимания → подборка → уточнение; каждое число и дата в ответе — из результата инструмента этого хода.

**Расположение.** `app/agents/selection.py` (реализация `run`, `_stage`, `_tool_policy`, `_system_prompt`, тела инструментов), промпт `app/agents/prompts/selection_v4.md`, модели результатов инструментов `app/schemas/agents.py`.

**Интерфейс.** `async def run(ctx: ChatCtx, message: ChatMessageIn, history: list[MessageOut], profile: Profile, deps: AgentDeps) -> AsyncIterator[StreamEvent]` — сигнатура стаба без изменений.

**Вход.** Как у стаба; дополнительно из Redis — снимок последней подборки `keys.matching_snapshot(student_id)`; из Postgres — прогнозы `forecast_cache` по экзаменам сохранённых (агрегат §10.3).

**Выход.** Поток событий; `Done(mode=<stage>, gave_task_instance_id=None, hint_level=None, referenced_skill_ids=[])`. `mode` для чата подбора несёт **стадию** (`opening|intake|summary|matching|refine`); транспорт кладёт её в `AssistantMarkup.mode` (тип `str | None`, контракт не меняется) и в `MessageAssistantPayload.mode=None` (там `Literal`, как и сейчас).

**Зависимости.** `run_tool_loop`, `SELECTION_TOOLS`, `postcheck.check_facts`, `load_prompt("selection")` (v4), `apply.matching.run_matching` (diff при старте хода), `matching.shift.diff`, `db.repo.forecast.get`, `db.repo.programs.list_saved_programs`, `keys.matching_snapshot`.

**Стадии диалога** (вычисляет код, не модель; `stage` попадает в system prompt и в `Done.mode`):

| Стадия | Условие (проверяется в этом порядке) | Что обязан сделать модельный ход (промпт) |
| :---- | :---- | :---- |
| `opening` | в `history` нет сообщений `assistant` | одна фраза «что сделаю» + один открытый вопрос; всё сказанное — в профиль |
| `intake` | `profile.readiness < assistant_readiness_threshold` и снимка подборки нет | записать новое в профиль; ≤ 2 вопросов, сначала влияющие на подборку (`direction.field`, `preferences.budget_per_year`/`grant_need`, `preferences.countries`, `level.grade`), затем «про человека»; не переспрашивать заполненное |
| `summary` | `readiness ≥ порога`, снимка подборки нет, последняя стадия ≠ `summary` | резюме понимания из четырёх блоков (сильные стороны, ограничения, цель, черты) + список допущений; попросить подтвердить; `run_matching` не вызывать, если ученик не просил показать |
| `matching` | последняя стадия `summary` (ученик ответил на резюме) или в тексте ученика просьба показать (`_wants_matching`) | правки → `update_profile`, затем `run_matching`; карточки — в `tool_result`, текст — краткая обвязка |
| `refine` | снимок подборки есть | цикл: правка профиля → назвать сдвиг; `compare`; `save_program`; вопросы по данным |

«Последняя стадия» — `markup.mode` последнего сообщения `assistant` в `history`, если оно из этого списка. `_wants_matching(text)` — регулярное выражение по нормализованному тексту: `покаж|показ|подбер|вариант|программ[ыу]|список`. Известное не переспрашивается: system prompt содержит снимок профиля с пометками, промпт запрещает спрашивать поле со значением; тест — по содержимому `calls[0].messages[0]`.

**Ограничение «не больше двух вопросов»** — в промпте и в постпроверке (§3.6): `text.count("?") > params.assistant_max_questions` → `postcheck_failed`.

**Правила доступа к инструментам** — `_tool_policy(stage, user_text, snapshot) -> ToolRegistry` (подмножество `SELECTION_TOOLS` через `ToolRegistry.subset(names)`, §5):

| Инструмент | opening | intake | summary | matching | refine |
| :---- | :---- | :---- | :---- | :---- | :---- |
| `update_profile` | да | да | да | да | да |
| `query_dataset`, `get_exam_format`, `get_admission_route`, `get_program_facts` | да | да | да | да | да |
| `run_matching` | нет | только при `_wants_matching` | да | да | да |
| `compare` | нет | нет | нет | да | да |
| `save_program` | нет | нет | нет | да | да |

Недоступный инструмент отсутствует в `tools` запроса; если модель всё же назовёт его, `registry.call` даёт `KeyError` → `ToolResult(error="unknown tool")`, лог `tool_denied`, ход продолжается.

**Резюме предпочтений** (`traits.summary`): промпт требует после каждой новой черты вызвать `update_profile("traits.verbatim", <цитата>)` и `update_profile("traits.summary", <полный новый текст>)`. Код это не проверяет.

**Модель знаний в подборе** — только агрегат §10.3: для каждого экзамена из сохранённых `ForecastOut.{predicted_scaled, coverage, note}` из `forecast_cache` строкой в system prompt; плюс diff: при старте хода `current = apply.matching.run_matching(session, rule_deps, student_id, limit=params.min_candidates * 2)`, `shifts = matching.shift.diff(snapshot.items, current.items)`, строки «после последнего разговора: <program> стал <realism>» (не более 5). Снимка нет — блок пуст.

**Системный промпт** = `load_prompt("selection").render(profile=..., stage=..., stage_rules=..., snapshot=..., knowledge=..., today=...)` — шесть плейсхолдеров `selection_v4.md`:
- `profile` — блок `<profile readiness="0.45">` со строками `path: value (сказал|предположили|по умолчанию)` только для непустых полей, затем `traits.verbatim` списком и `traits.summary`, затем `missing: direction.field, preferences.budget_per_year` (в порядке добора);
- `stage`, `stage_rules` — имя стадии и 2–4 строки обязанностей стадии (таблица выше);
- `snapshot` — `<last_matching>` список `program_id · университет · направление · realism` (≤ 10) или `нет`;
- `knowledge` — агрегат и сдвиги или `нет данных`;
- `today` — дата ISO.

**Последовательность хода.**
1. Стадия, политика инструментов, system prompt. `messages = [system] + history(LLMMessage) + [user(message.text)]`.
2. `ToolCtx(student_id=str(ctx.student_id), deps=deps, request_id=ctx.request_id, chat=ctx, turn=TurnState())`.
3. `async for ev in run_tool_loop(deps.llm, registry, messages, "chat", tool_ctx, max_steps=6)`: `TextDelta`/`ToolCall`/`ToolResult` — наружу; `StreamError` — наружу и выход; `LoopEnd` — в переменную.
4. Постпроверка (§3.6) по `LoopEnd.text_full`, `LoopEnd.tool_results`, `profile`, `message.text`. Не прошла → `StreamError(code="postcheck_failed", message="Ответ отозван: в нём есть данные, которых нет в результатах инструментов")`, конец.
5. `Done(event_id=0, mode=stage_after)`, где `stage_after = "matching"`, если в ходе был успешный `run_matching`, иначе стадия хода.

**Ошибки.** `LLMUnavailable`/провайдерская ошибка внутри цикла → `StreamError(llm_unavailable)` от `run_tool_loop` (§5: цикл ловит и `openai.APIError`); до первого события роутер превращает в 503. Ошибка внутри тела инструмента (`ValidationFailed`, `NotFound`, `Conflict`, ошибка Neo4j/Postgres) — `ToolResult(error=str(exc))`, ход продолжается; модель обязана сказать «этого в данных нет». `tool_loop_limit` — `StreamError` от цикла (накопленный текст не сохраняется: транспорт не пишет ответ без `Done`).

**Граничные случаи.** `MatchingOut.items == []` → инструмент возвращает `empty_reason` (из `matching.hard.explain_empty`), модель объясняет, какой фактор отсёк всё. Профиль без единого поля и «просто покажи» → `run_matching` на дефолтах, `assumptions` в результате. Повторный `update_profile` с тем же значением → `unchanged=true` без события. Два `run_matching` за ход → тот же результат, снимок перезаписан тем же. Сообщение на 4000 символов — как есть.

**Идемпотентность.** Ход не идемпотентен (модель), все записи идемпотентны на уровне инструментов (§3.3).

**Concurrency.** Один ход на чат (лок транспорта). Инструменты внутри хода выполняются последовательно в порядке `tool_calls` шага.

**Логирование.** `chat_turn_started{kind=selection, stage}`, `tool_called`, `tool_denied`, `postcheck`, `chat_turn_done`.

**Разметка `AssistantMarkup`** для подбора: `mode=<stage_after>`, остальное пусто.

**Тестируемое поведение.** §6.3.

### 3.3 Восемь инструментов ассистента подбора (B2, тела; данные — B1/B3)

Общее: сигнатура `async def <name>(args: <Args>, ctx: ToolCtx) -> <ResultModel>`; аргументы валидирует `ToolRegistry.call` (`ValidationFailed` → `ToolResult(error)`); сессия — `async with ctx.deps.pg() as session`, коммит внутри инструмента; `RuleDeps` — `agents._deps.rule_deps(ctx.deps)` (`graph=deps.graph, redis=deps.redis, params=settings.knowledge, now=utcnow`); результат — Pydantic-модель из `app/schemas/agents.py` (реестр сериализует в `dict`; тот же `dict` уходит модели в `role=tool` и фронту в `tool_result.data`). Модели аргументов из фазы 1 не меняются, кроме `GetTaskArgs` (§5). Все числа и даты, которые модель имеет право назвать, обязаны присутствовать в результате — поэтому результаты содержат `count`, `total`, валюты, `Source`.

| Инструмент | Вход (`Args`) | Что делает (последовательность) | Выход (`app/schemas/agents.py`) | Ошибки → `ToolResult.error` | Идемпотентность |
| :---- | :---- | :---- | :---- | :---- | :---- |
| `update_profile` (`read_only=False`) | `path`, `value`, `by` (игнорируется, всегда `"assistant"`) | 1) `profile = get_profile`; текущее значение по `path` равно `value` → `unchanged=True`, событий нет. 2) `apply_profile_update(session, sid, ProfileUpdateIn(path, value, by="assistant"))`. 3) `store.append(profile.updated, deps=rule_deps, dispatch_event=True)` → `apply_profile_updated`. 4) `before = snapshot` из Redis (если есть), `after = apply.matching.run_matching(...)`; `shift = matching.shift.diff(before.items, after.items)`. 5) commit; снимок **не** обновляется (обновляет только `run_matching`). | `ProfileUpdateResult(path, value, mark, readiness, unchanged: bool, shift: list[ShiftOut], missing: list[str])` | `unknown profile path` / `invalid profile value` (`ValidationFailed` репозитория) | равное значение → без события |
| `run_matching` | `limit` (по умолчанию 5, ограничивается `[min_candidates, 10]`) | 1) `apply.matching.run_matching(session, rule_deps, sid, limit)` — та же функция, что `GET /matching`. 2) Снимок в Redis `keys.matching_snapshot(sid)` = `MatchingSnapshot(items:[{program_id, university, direction, realism, score, factors:[{id,status}]}], as_of)`, TTL 7 дней. | `RunMatchingResult(count, total, forecast_used, empty_reason, profile_readiness, items: list[MatchCard])`; `MatchCard(program_id, university, direction, country, city, language, realism, score, tuition_per_year, living_per_year, currency, factors: list[FactorOut], assumptions: list[str], source: Source)` | граф недоступен → тест-даты пустые, подборка без фактора сроков (как в роутере) | детерминирована входами |
| `compare` | `program_ids` (2–4) | `apply.matching.compare_programs(session, rule_deps, sid, ids)` — та же функция, что `GET /matching/compare` | `CompareOut` (фаза 2, `conclusion=None`) | `select 2 to 4 distinct programs`, `program not found` | — |
| `save_program` (`read_only=False`) | `program_id` | 1) `programs.save_program(session, sid, program_id)`. 2) `store.append(program.saved, deps, dispatch_event=True)` → `on_program_change`. 3) commit. 4) `roadmap.requirements.build_requirements(saved, profile, exam_formats, test_dates, forecasts, params)` — для текста «что появилось в подготовке». | `SaveProgramResult(program_id, saved_count, exams: list[ExamRequirementOut])` | `program not found`, `program already saved` (второй вызов не пишет второе событие) | по `Conflict` репозитория |
| `get_program_facts` | `program_id` | `programs.get_program`; `flagged` → как не найдено | `ProgramFactsResult(program: Program, source: Source)` | `program not found` | — |
| `get_admission_route` | `country_id` | `kb.get_admission_route(driver, country_id)` + `kb.list_facts_about(driver, country_id)` | `AdmissionRouteResult(country_id, routes: list[AdmissionRouteOut], facts: list[FactOut])`; пусто → `routes=[]` | граф недоступен → `error="knowledge base unavailable"` (product-logic §6.3) | — |
| `get_exam_format` (общий с репетитором) | `exam_id` | `canonical.get_exam_format` + `kb.list_test_dates` (ближайшие 3 после сегодня) + `kb.list_facts_about(exam_id)` | `ExamFormatResult(format: ExamFormat, test_dates: list[TestDate], facts: list[FactOut])` | `exam format not found`; граф недоступен → `knowledge base unavailable` | — |
| `query_dataset` | `question`, `country?`, `direction?` | Детерминированный агрегат по `programs.list_all` (без `flagged`), фильтр `country`/`direction` (регистронезависимо, `direction` — подстрока); `question` только в лог и эхо. Считает `count`, `by_country`, `by_direction`, `tuition: {min, median, max, currency_mix}` по программам с `tuition_per_year`, `free_count` (`tuition_per_year == 0`), `with_scholarship_note`, `languages`, `exam_thresholds: {exam_id: {min, max}}` по `Requirement{type=exam_score}`, `programs` (≤ 15 карточек `program_id, university, city, country, tuition_per_year, currency`), `sources` (≤ 15). Если `country` не задан и `preferences.countries` непусто — фильтр по ним, `profile_filtered=true`. | `DatasetAggregateOut(question, filters, count, by_country, by_direction, tuition, free_count, with_scholarship_note, languages, exam_thresholds, programs, sources, profile_filtered)` | — (пусто → `count=0`) | — |

`TurnState` (в `ToolCtx.turn`, §5): счётчики на ход; у подбора — `matching_calls` (лог), у репетитора — `task_issued`.

Описания инструментов для модели — `description` в `@tool` (фаза 1, без изменений) плюс раздел «Инструменты» в `selection_v4.md` с форматами результатов словами; версия промпта фиксирует и описания.

### 3.4 Репетитор — `agents.tutor.run` (B2)

**Назначение.** Отвечать в контексте модели знаний (memory-architecture §9): system prompt с `<learner_model>` из контекста топика, строка сессии на каждое сообщение, режим «объясняю / разбираю» по последнему сообщению ученика, подсказки с уровня профиля и эскалация после второй неудачи, три инструмента только для чтения, разметка ответа для наблюдателя.

**Расположение.** `app/agents/tutor.py` (реализация `run`, `classify_mode`, `hint_level_for`, `_session_line`, `_render_learner_model`, тела инструментов), промпт `app/agents/prompts/tutor_v3.md` (плейсхолдеры `{{learner_model}}`, `{{session}}`).

**Интерфейс.** `async def run(ctx: ChatCtx, message: ChatMessageIn, history: list[MessageOut], profile: Profile, deps: AgentDeps) -> AsyncIterator[StreamEvent]` — без изменений. Чистые помощники (тестируются отдельно):
- `classify_mode(text: str) -> Literal["explain", "review"]`;
- `hint_level_for(profile: Profile, consecutive_failures: int, params) -> int` (1..3);
- `render_learner_model(context: TopicContext, topic_name: str, set_label: str, as_of: datetime) -> str` — блок §9.3, порядок слотов фиксирован: `topic, strengths, prerequisite_gaps, active_misconceptions, under_watch, low_data, deadline, profile, previous_set`; пустой слот печатается как `[]`.

**Вход.** `ctx.set_id`, `ctx.topic_skill_id` (обязательны для `kind=prep`; транспорт гарантирует), история, профиль, `deps`.

**Выход.** Поток; `Done(mode, gave_task_instance_id, hint_level, referenced_skill_ids)`:
- `mode`: `"task"`, если в ходе был успешный `get_task`; иначе `classify_mode(message.text)`;
- `gave_task_instance_id`: `id` из результата последнего успешного `get_task` этого хода, иначе `None`;
- `hint_level`: уровень, переданный модели в строке сессии;
- `referenced_skill_ids`: `[ctx.topic_skill_id] + skill_id` из аргументов успешных `get_task`/`explain_belief` этого хода (без дублей, порядок появления).

**Зависимости.** `apply.context.get_topic_context` (§3.7), `run_tool_loop`, `TUTOR_TOOLS`, `postcheck.check_facts(scope="exam_facts")`, `events.store.list_by_type` (последняя задача и неудачи), `db.repo.tasks.list_instances`, `load_prompt("tutor")` (v3).

**Построение `TopicContext`.** `context = await apply.context.get_topic_context(session, rule_deps, student_id, set_id, topic_skill_id)` (кэш и 4 Cypher внутри, §3.7). При `None` (граф недоступен) — блок `<learner_model>` пустой; промпт v3 предписывает вести обычное объяснение.

**История.** Окно `chat_window` сообщений из роутера как `LLMMessage`; текущее — последним.

**Режимы.** `classify_mode`: `review`, если текст содержит признак решения — знак `=` с цифрами по обе стороны, ≥ 2 строк с математическими операторами, слова `решил|получил|получилось|ответ|проверь|вот моё|я думаю что` или ссылку на выданную задачу (`ответ: A|B|C|D` и т. п.); иначе `explain` (вопросы, `объясни|почему|как|что такое`). При равенстве признаков — `explain` (политика §9.4: заблуждения включаются только в «разбираю»). Строка сессии несёт `mode`, промпт применяет соответствующие строки `policy`.

**Подсказки и эскалация.** База — `profile.questionnaire.pace.hint_level.value`: `minimal→1`, `normal→2`, `generous→3`, отсутствует → 2. `consecutive_failures` — число подряд идущих `task.answered` с `correct=false` (вычисляется по экземплярам чата: `events.store.list_by_type(student, [task.answered], since=начало сессии)` → для экземпляров с `mode="chat"` и `chat_id == ctx.chat_id` берётся `task_instances.correct`), считая от конца. `consecutive_failures ≥ params.tutor_escalate_after_failures` → `hint_level = min(3, base + 1)`, в строку сессии добавляется `escalate: yes`. Явная просьба ученика («подсказку», «не понимаю») эскалацию не форсирует — это делает модель по промпту.

**Строка сессии** (`{{session}}`): `<session minute="{N}" mode="{explain|review}" hint_level="{K}" escalate="{yes|no}" last_task="{correct|incorrect|none}" last_task_skill="{skill_id|-}" issued_in_chat="{instance_id|-}" />`, где `minute` — минуты с первого события текущей `session_id` (как `_session_minute` в `api/_answer.py`; тот же расчёт вынести в `events.session.session_minute(session, student_id, session_id, now)`, §5), `last_task` — последний `task.answered` ученика (любой режим) в этой сессии, `issued_in_chat` — последний `task.issued` этого чата без ответа (для наблюдателя и для модели: «ученик отвечает на эту задачу»).

**Последовательность хода.**
1. `rule_deps`; контекст топика; профиль; история; `mode`, `hint_level`, строка сессии.
2. `system = load_prompt("tutor").render(learner_model=<блок или "">, session=<строка>)`; `messages = [system] + history + [user]`.
3. `ToolCtx(..., chat=ctx, turn=TurnState())`; `run_tool_loop(deps.llm, TUTOR_TOOLS, messages, "chat", tool_ctx, max_steps=4)`.
4. Постпроверка `scope="exam_facts"` (§3.6); провал → `StreamError(postcheck_failed)`.
5. `Done(...)` по правилам выше.

**Ошибки.** Как у подбора. Ошибка `get_topic_context` (Neo4j) — ловится, контекст пустой, лог `ctx_topic{error}`; ход продолжается. Ошибка чтения событий для строки сессии — `minute=0`, `last_task=none`.

**Граничные случаи.** Первый ход в топике (история пуста) — обычный ход, `mode=explain`. `set_id`/`topic_skill_id` не принадлежат ученику — `get_topic_context` возвращает `None` (репозиторий сетов отдаёт `None` на чужой сет) → пустой блок; наблюдатель позже увидит `topic_skill_id` из событий. Навык топика без единого состояния — слот `topic` содержит `мало данных`. Ученик спрашивает про требования/даты — промпт отправляет в подбор; постпроверка режет любую дату без инструмента. Второй `get_task` за ход — `ToolResult(error="one task per turn")` (счётчик `turn["task_issued"]`).

**Идемпотентность / concurrency.** Как у подбора; `get_task` — не более одного за ход; лок чата у транспорта.

**Логирование.** `chat_turn_started{kind=prep, mode, hint_level, ctx=hit|miss|none}`, `tool_called`, `postcheck{scope=exam_facts}`, `chat_turn_done`.

**Тестируемое поведение.** §6.4.

### 3.5 Три инструмента репетитора (B2, тела; данные — B1)

`TUTOR_TOOLS = ToolRegistry(read_only=True)` без изменений: `explain_belief`, `get_task`, `get_exam_format` (общий `ToolSpec` из `selection.py`). Регистрация любого `read_only=False` по-прежнему `ValueError`.

| Инструмент | Вход | Последовательность | Выход | Ошибки | Ограничения |
| :---- | :---- | :---- | :---- | :---- | :---- |
| `explain_belief` | `skill_id` (id навыка **или** заблуждения, как в докстринге фазы 1) | 1) `items = apply.knowledge.explain(rule_deps, sid, node_id)` (EvidenceOut с `instance_id`/`message_id` — после исправления `merge_evidence`, §5). 2) Для `instance_id`: `repo.tasks.list_instances` → `stem_rendered`, а ответ ученика — из события `task.answered` по `event_id` (`events.store.get_event(session, sid, event_id)` → `payload.answer`), `correct` — из `task_instances.correct`. 3) Для `message_id`: `repo.messages.get_message(session, sid, message_id)` → фрагмент ≤ 300 символов вокруг `summary` (если `summary` не найден — первые 300). 4) Не более 10 самых свежих. | `ExplainBeliefResult(node_id, node_kind: Literal["skill","misconception"], items: list[BeliefItem])`, `BeliefItem(evidence_id, event_id, kind, source, tier, direction, weight, observed_at, summary, task: BeliefTask(instance_id, stem, student_answer, correct) \| None, message: BeliefMessage(message_id, text_fragment, created_at) \| None)` | граф недоступен → `error="knowledge model unavailable"`; неизвестный узел → `items=[]` | только чтение |
| `get_task` | `skill_id`, `difficulty?`, `with_trap?: str` (misconception_id), `exclude_seen: bool = True` — `GetTaskArgs` расширяется (§5, по memory-architecture §9.5) | 1) `turn["task_issued"]` уже 1 → `error`. 2) `skill_id` обязан быть навыком топика или его предпосылкой (список из `TopicContext.skill_ids`, §3.7); иначе `error="skill outside topic"`. 3) `out = apply.tasks.issue(session, rule_deps, sid, TaskRequestIn(skill_id, set_id=ctx.chat.set_id, mode="chat", with_trap, exclude_seen), chat_id=ctx.chat.chat_id)` → событие `task.issued{via="chat"}` с `chat_id` и `topic_skill_id`. 4) commit; `turn["task_issued"]=1`, `turn["gave_task_instance_id"]=out.id`. `difficulty` передаётся как подсказка выбору только если `TaskRequestIn` её примет (в фазе 2 нет поля — игнорируется, зафиксировано в §5). | `GetTaskResult(task: TaskInstanceOut, hint_level: int)` — **без правильного ответа и без `misconception_id` у вариантов** (`OptionOut`) | `no templates for skill`, `one task per turn`, `skill outside topic` | одна задача за ход; пишет только `task_instances` + `task.issued` |
| `get_exam_format` | `exam_id` | как в §3.3 | `ExamFormatResult` | как в §3.3 | только чтение |

Ответ ученика на выданную в чате задачу не проверяется инструментом: его извлекает наблюдатель (`task_in_chat`) и применяет правило как `task.answered` (§3.10). Репетитор в ответе опирается на собственное решение (у него нет ключа) — это сознательное ограничение: ключ в `tool_result` ушёл бы клиенту.

### 3.6 Постпроверка в цепочке — `agents.postcheck` (B2)

**Назначение.** Последний шаг перед `done` у обоих агентов: ни одно число и ни одна дата, которые обязаны приходить из инструментов, не уходят ученику без подтверждения результатом инструмента этого хода.

**Расположение.** `app/agents/postcheck.py` (чистый модуль без I/O — сохраняется), вызов из `selection.run` и `tutor.run`.

**Интерфейс.** `check_facts(text: str, tool_results: list[ToolResult], *, scope: Literal["all", "exam_facts"] = "all", extra_values: Iterable[float | date] = (), max_questions: int | None = None) -> PostcheckResult(ok, mismatches: list[str], questions: int)` — расширение сигнатуры фазы 1 с обратной совместимостью (старые вызовы дают то же поведение, §5).

**Момент выполнения.** После `LoopEnd` и до `Done`. Текст к этому моменту уже отдан потоком как `TextDelta` — см. «что получает пользователь».

**Что проверяется.**
- `scope="all"` (ассистент подбора): все числа и даты текста по правилам фазы 1 (целые/десятичные, разделители тысяч, проценты, четыре формата дат; годы 2024–2030 как голые числа не считаются; даты без года — по дню и месяцу).
- `scope="exam_facts"` (репетитор): все даты; все проценты; числа только в предложениях, содержащих маркер факта об экзамене или поступлении: `балл|заданий|задания|минут|модул|секци|раздел|шкал|максимум|проходн|порог|дедлайн|регистрац|подач|стоимост|цена|тенге|доллар|евро|CHF|USD|EUR|KZT`. Числа математического содержания (`x = 5`, `2x − 6 = 4`) не проверяются — они принадлежат задаче, а не датасету.
- `max_questions` (только подбор, `params.assistant_max_questions`): `text.count("?") > max_questions` → провал с `mismatches += ["questions>2"]`.

**Откуда authoritative values.** Объединение: (1) все числовые и датовые листья `ToolResult.data` успешных результатов текущего хода (рекурсивно, как в фазе 1); (2) `extra_values`: у подбора — все числовые/датовые значения полей снимка профиля, переданного в system prompt (`ProfileField.value` анкеты: бюджет, баллы, даты, класс, часы), и числа/даты из текста текущего сообщения ученика (он сам их назвал); у репетитора — числа/даты из текущего сообщения ученика и из `stem_rendered`/`options` задачи, выданной в этом ходе или указанной в строке сессии как `issued_in_chat`. Числа из истории прошлых ходов **не** authoritative: то, что ассистент говорил раньше, могло быть из инструмента прошлого хода — модель обязана вызвать инструмент снова.

**При несовпадении.** Агент не отдаёт `Done`; отдаёт `StreamError(code="postcheck_failed", message="Ответ отозван: в нём есть данные, которых нет в результатах инструментов")`. Транспорт (без изменений): на `StreamError` завершает поток, `message.assistant` и строка в `messages` **не** пишутся — отозванный ответ не попадает в историю и не станет входом следующего хода. Повторной генерации в этом ходе нет (сознательно: повторный проход добавляет 10–15 с при уже отданном черновике; см. §9).

**Что получает пользователь.** SSE-кадры `text_delta` черновика уже пришли; следом кадр `{"type":"error","code":"postcheck_failed","message":"…"}`. Контракт фронта (фиксируется в §5 как правило, не как тип): при `error` с кодом `postcheck_failed` клиент убирает частичный ответ и показывает «Ассистент не смог подтвердить данные в ответе, попробуйте спросить ещё раз». `GET /chat/{kind}/messages` отозванного ответа не содержит.

**Что логируется.** `postcheck{kind, scope, ok, mismatches: [...], questions, text_len, tools: [names]}` — только числа/даты и имена инструментов, не текст ответа.

**Ошибки/границы.** Пустой `tool_results` и есть проверяемое число → провал (как в фазе 1). Текст без чисел → `ok`. `ToolResult` с `error` не даёт значений. Число вида `1 500 CHF` совпадает с `1500`. Проценты: `85%` ищется как `85` и как `0.85`.

**Тестируемое поведение.** §6.5.

### 3.7 Контекст топика — `graph.context.build_topic_context` (B1)

**Назначение.** Собрать слоты §9.2 из графа четырьмя параллельными запросами, дополнить данными Postgres, отдать `TopicContext`; кэшировать графовую часть в Redis; пересобирать при изменении модели знаний.

**Расположение.** `app/graph/context.py` (`build_topic_context`, кэш, сборка слотов — B1), `app/graph/queries/context.py` (четыре запроса — B1), `app/apply/context.py` (`get_topic_context` — обёртка с Postgres-входами, B1).

**Интерфейс.**
```
graph.context.build_topic_context(driver: AsyncDriver, redis: Redis, student_id: UUID, topic_skill_id: str | None,
    set_id: UUID, *, exam_id: ExamId, extras: ContextExtras, params: KnowledgeParams, now: datetime) -> TopicContext
apply.context.get_topic_context(session: AsyncSession, deps: RuleDeps, student_id: UUID, set_id: UUID,
    topic_skill_id: str | None) -> TopicContext | None
```
`ContextExtras(set: SetOut | None, profile: Profile, previous_summary: str | None, p_target: float)` — модель в `graph/context.py`. `TopicContext` — модель фазы 1 без изменения слотов; добавляются служебные поля `skill_ids: list[str]` (навык топика + предпосылки — для проверки `get_task`), `topic_name: str`, `set_label: str`, `as_of: datetime`, `cache: Literal["hit","miss","none"]` (§5). Сигнатура стаба меняется (§5): добавлены `redis`, `exam_id`, `extras`, `params`, `now`; `topic_skill_id=None` — чат сета.

**Вход.** `topic_skill_id` (или `None` для сета), `set_id`, `exam_id` (из `SetOut.exam_id`), `extras`.

**Выход.** `TopicContext` со строками, готовыми к вставке (формат §9.3): `topic: ["раскрытие модуля — p=0.55 conf=0.80 trend=flat; в сете 2 из 3, дальше — формулы приведения"]`, `strengths: ["линейные уравнения: p=0.88 conf=0.90"]`, `prerequisite_gaps: ["линейные неравенства: p=0.42 conf=0.60 (корень 2 ошибок за 30 дней)"]`, `active_misconceptions: ["теряет вторую ветвь при |x−a| (подтверждено, 3 набл.; обычно — когда торопится)"]`, `under_watch: [...]`, `low_data: ["формулы приведения: мало данных"]`, `deadline: ["сет до 5 окт", "SAT 7 ноя"]`, `profile: ["подсказка уровня 2", "объяснения normal", "~4 ч/нед"]`, `previous_set: ["…"]`.

**Четыре параллельных запроса** (`asyncio.gather`, каждый — отдельная сессия драйвера; все начинаются с `MATCH (st:Student {id: $student_id})` там, где читают персональный слой):

| # | Функция `graph.queries.context` | Что возвращает | Из чего собирается |
| :---- | :---- | :---- | :---- |
| Q1 | `q_skill_slice(driver, student_id, exam_id, skill_ids: list[str]) -> list[SkillSliceRow(skill_id, name, state: KnowledgeStateOut \| None, history: list[KnowledgeStateOut])]` | навык топика + предпосылки 1–2 хопа с текущим состоянием по `exam_id` и последними 3 состояниями по `PREVIOUS` | `topic`, `strengths`, `prerequisite_gaps`, `low_data` |
| Q2 | `q_root_causes(driver, student_id, skill_ids, window_days) -> dict[str, tuple[int, float]]` | по навыку: число `ROOT_CAUSE` за окно и Σ confidence | порядок и пометка в `prerequisite_gaps` |
| Q3 | `q_misconceptions(driver, student_id, skill_ids) -> list[MisconceptionStateOut]` | состояния заблуждений `ABOUT` этих навыков (с `triggers`, `updated_at`) | `active_misconceptions`, `under_watch` |
| Q4 | `q_test_dates(driver, exam_id, after: date) -> list[TestDate]` | ближайшие даты экзамена | `deadline` |

Список `skill_ids` для Q1–Q3 вычисляется до `gather` одним вызовом `canonical.get_prerequisites(driver, topic_skill_id, depth=2)` (для сета — объединение по всем `SetOut.topics[].skill_id`). Q1 реализуется одним Cypher (не циклом по навыкам). Существующие функции `personal.get_states/get_state_history/list_root_causes/get_misc_states`, `kb.list_test_dates` можно вызывать внутри Q-функций, если это не превращает Q1 в N+1.

**Состав слотов и лимиты** (лимит ×`params.context_set_multiplier` с округлением вверх для чата сета):

| Слот | Лимит | Правило отбора (все пороги — `params`) |
| :---- | :---- | :---- |
| `topic` | 1 | навык топика: `p_recall`, `confidence` (2 знака), `trend` = `words.trend(history)`, `due_at` словами, если `< 7 дней`; «в сете i из n, дальше — <следующий открытый топик>» из `extras.set`; для сета — «сет: <топики через запятую>» |
| `strengths` | 2 | из slice: `p ≥ 0.8 и conf ≥ 0.5`, кроме навыка топика; сортировка по `p` убыв. |
| `prerequisite_gaps` | 3 | предпосылки с `p < 0.6 и conf > 0.5`; первыми — с `ROOT_CAUSE` (Q2), затем по `p` возр.; текст корня «корень N ошибок за 30 дней» |
| `active_misconceptions` | 2 | `visible_to(state, "tutor")` и `status == "confirmed"`; сортировка по `occurrence_count` убыв.; «(подтверждено, N набл.<; trigger_words>)» |
| `under_watch` | 1 | `status == "resolved"` и `visible_to(state, "tutor")` (моложе `under_watch_days`) |
| `low_data` | 2 | из slice `conf < c_vis` или нет состояния, кроме уже попавших выше; «мало данных» |
| `deadline` | 2 | `extras.set.deadline` → «сет до <d MMM>»; ближайшая `TestDate` → «<EXAM> <d MMM>» |
| `profile` | 3 | `pace.hint_level` → «подсказка уровня K», `explanation_depth`, `hours_per_week` → «~N ч/нед»; отсутствующее поле — строка не печатается |
| `previous_set` | 1 | `extras.previous_summary` целиком (≤ 300 символов) |

`suspected` и `disputed` в контекст не попадают (§11.1). Если после отбора слот пуст — `[]` («пустой слот лучше нерелевантного»). Уровни словами — `words.skill_level(state, p_target, params)`, `p_target = extras.p_target` (`apply.context` берёт `params.p_target_max`, как `apply.knowledge.states_view` в фазе 2; замена на `roadmap.requirements` — общий TODO фазы 2, не этой).

**Ограничение объёма.** Суммарная длина строк всех слотов ≤ `params.context_budget_tokens * 3` символов (3000 токенов ≈ 9000 символов кириллицы); при превышении — усечение снизу таблицы (`previous_set`, затем `low_data`, `under_watch`) до входа в бюджет. Лог `ctx_topic{truncated=true}`.

**Redis-кэш.** Ключ `keys.ctx_topic(student_id, topic_skill_id or f"set:{set_id}")`. Значение — JSON `{"version": <knowledge_version>, "set_id": "...", "exam_id": "...", "built_at": iso, "graph": {q1: [...], q2: {...}, q3: [...], q4: [...]}}` — кэшируется **сырьё четырёх запросов**, не готовые строки: слоты `deadline/profile/previous_set/topic("в сете i из n")` зависят от Postgres и собираются заново каждый вызов. Попадание: `version == events.version.get(redis, student_id)` и `set_id` совпал → `gather` не выполняется, `cache="hit"`. Промах → четыре запроса, запись с `EX=settings.CTX_CACHE_TTL_S`. Redis недоступен → без кэша, `cache="none"`, warning. Ключ `last_event_id` из `tech-stack §4.4` реализуется через `knowledge_version`: это то самое «последнее событие, изменившее персональный слой» (инкремент — единственная точка `events.version.bump`), и его уже поднимают `apply.task_answered`, `apply.dispute`, `apply.sets.rebuild_sets`, а с этой фазы — `apply.observation`.

**Инвалидация.** По событиям, требуемым §3.3 `backend-phases`: `observation.extracted` — `apply.observation` делает `bump` и дополнительно `DEL keys.ctx_topic(sid, topic_skill_id)`; изменение состояния навыка топика от задачи — `apply.task_answered` уже делает `bump`; `topic.completed` — роутер сетов (`api/sets.py`) после события делает `DEL` ключа закрытого топика и ключа сета (`f"set:{set_id}"`) (B3, §3.12). Версия меняется → любой старый кэш считается устаревшим при следующем чтении.

**`apply.context.get_topic_context`** (последовательность): 1) `set_out = repo.sets.get_set(session, student_id, set_id)`; `None` → вернуть `None` (чужой/несуществующий сет). 2) `topic_skill_id` не в `set_out.topics` → `None`. 3) `profile = repo.profiles.get_profile`. 4) `previous_summary` = `repo.summaries.get_latest_text(session, student_id, before_set_id=set_id)` (Postgres `set_summaries`; в фазе 3 всегда `None`, поле проводится). 5) `deps.graph is None` → `None`. 6) `build_topic_context(...)`; исключения драйвера (`ServiceUnavailable`, `SessionExpired`) → `None` + warning.

**Ошибки.** Один из четырёх запросов упал → весь `gather` падает → `None` у обёртки (частичный контекст не собирается: неполный `<learner_model>` хуже пустого). Кэш повреждён (не парсится) → как промах, ключ перезаписывается.

**Граничные случаи.** Нет предпосылок — slice из одного навыка. Нет состояний вообще — `topic: ["<навык>: мало данных"]`, остальное пусто, `profile`/`deadline` из Postgres. Сет без дедлайна невозможен (`SetOut.deadline: date`). Отсутствует тест-дата — `deadline` только про сет. `topic_skill_id` общий (`math.*`) — состояния читаются по `exam_id` сета.

**Идемпотентность.** Чтение; повторный вызов с той же версией — тот же результат (из кэша).

**Concurrency.** Два хода в разных чатах одного ученика одновременно строят один и тот же контекст — оба пишут в кэш одинаковое значение; лок не нужен.

**Логирование.** `ctx_topic{student_id, skill, set_id, cache, ms, truncated, slots: {name: n}}`.

**Тестируемое поведение.** §6.6.

### 3.8 Наблюдатель — `agents.observer.run` (B2)

**Назначение.** Один вызов модели со structured output над окном сообщений чата подготовки и срезом модели знаний: превратить разговор в список наблюдений по схеме `ObservationOut`. Не пишет никуда.

**Расположение.** `app/agents/observer.py` (`run`, сборка промпта, рендер окна); схема выхода переезжает в `app/schemas/observer.py` и реимпортируется отсюда (§5). Промпт `observer_v1.md` без изменений (плейсхолдеры те же).

**Интерфейс.** `async def run(client: LLMLike, window: ObserverWindow, context: ObserverContext, *, slot: ModelSlot) -> ObserverResult` — заменяет стаб `observe(client, window, context)` (§5).

Модели (`app/schemas/observer.py`):
```
WindowMessage(event_id: int, message_id: UUID | None, role: Literal["user","assistant"], text: str,
              markup: AssistantMarkup | None, occurred_at: datetime, session_id: UUID | None)
WindowTask(instance_id: UUID, issued_event_id: int, skill_id: str, stem: str, options: list[OptionOut], type: TaskType)
ObserverWindow(chat_id: UUID, student_id: UUID, exam_id: ExamId, set_id: UUID, topic_skill_id: str | None,
               messages: list[WindowMessage], tasks: list[WindowTask])
SkillForObserver(id: str, name: str, description: str, level: SkillLevel)
MisconceptionForObserver(id: str, name: str, description: str, status: MisconceptionStatus | None, scope: Literal["library","personal"])
ObserverContext(skills: list[SkillForObserver], misconceptions: list[MisconceptionForObserver], previous_summary: str | None)
ObserverResult(out: ObservationOut, extractor_version: str, model: str, raw_count: int)
```

**Вход.** Окно и контекст, собранные `jobs.observe_chat` (§3.9).

**Выход.** `ObserverResult` — выход модели после схемной валидации, без семантической фильтрации (фильтр по `confidence` и ссылочная проверка — в правиле §3.10, чтобы событие хранило ровно то, что сказала модель).

**Зависимости.** `load_prompt("observer")`, `client.structured(messages, ObservationOut, slot)`.

**Последовательность.**
1. `prompt = load_prompt("observer")`; `extractor_version = prompt.extractor_version` (`"observer_v1"`).
2. Рендер плейсхолдеров:
   - `window` — по строке на сообщение: `[event_id=4420] ученик: <текст>` / `[event_id=4421] репетитор (mode=review, hint=2, task=<instance_id>): <текст>`; текст сообщения обрезается до 2000 символов с пометкой `…`;
   - `skills` — `id — название: описание (уровень словами)` по одному на строку;
   - `misconceptions` — `id — название: описание (статус у ученика: confirmed | suspected | … | нет; library|personal)`;
   - `task_instance` — для каждой задачи окна: `instance_id, skill_id, тип, условие, варианты A..E: текст` или `нет`;
   - `previous_summary` — текст или `нет`.
3. `messages = [system(prompt.render(...)), user("Верни наблюдения по окну выше.")]`.
4. `out = await client.structured(messages, ObservationOut, slot)` — один встроенный повтор клиента при невалидном JSON; второй провал → `LLMUnavailable("structured output failed")` пробрасывается наверх (решение о `Retry`/`job.failed` — у job).
5. `ObserverResult(out, extractor_version, model=settings.MODEL_BULK|MODEL_CHAT по slot, raw_count=len(out.observations))`.

**Ошибки.** `LLMUnavailable` (breaker, rate-limit, structured) и провайдерские исключения — наверх. `KeyError` рендера — баг, наверх.

**Граничные случаи.** Пустое окно — `run` не вызывается (job возвращает раньше). Окно без сообщений ученика (только ответы репетитора) — вызывается; ожидается пустой список. `previous_summary=None` — «нет». Задача без вариантов (`numeric`) — печатается условие и `answer_forms` не печатаются (модель не должна знать ключ).

**Идемпотентность/concurrency.** Чистый вызов; параллельность ограничивает job.

**Логирование.** `observer_run{chat_id, window: n, tasks: k, skills: s, misconceptions: m, prompt_chars, observations: raw_count, ms}`; текст окна не логируется.

**Тестируемое поведение.** §6.7.

### 3.9 Задача `agents.jobs.observe_chat` (B2; данные — B1/B3)

**Назначение.** Выбрать необработанное окно чата, собрать контекст, вызвать `observer.run`, записать выход целиком событием `observation.extracted`, пометить окно обработанным, применить правило через `dispatch`, поставить канонизацию персональных заблуждений, при необходимости перезапустить себя.

**Расположение.** `app/agents/jobs.py`. Реестр — `app/workers/registry.py` (B3): `func(observe_chat, name="observe_chat", timeout=settings.OBSERVER_JOB_TIMEOUT_S, max_tries=3)`, очередь `interactive`.

**Интерфейс.** `async def observe_chat(ctx: dict, request_id: str, chat_id: UUID, student_id: UUID, trigger: Literal["every_n","topic_completed","set_completed","requested"] = "every_n") -> None` (добавлен `trigger` с умолчанием — стаб совместим, §5). `ctx` — контекст ARQ из `workers.main.startup`: `sessionmaker`, `neo4j`, `redis` (`ArqRedis`), `llm`, `job_try`, `job_id`.

**Окно сообщений и что считается необработанным.** `events.store.list_unprocessed(session, chat_id, limit=params.observer_window_max + 10, types=[message.user, message.assistant, task.issued])` (параметр `types` — §5) — события этого `chat_id` с `processed_at IS NULL`, по `id` возрастанию. «Необработанное» для `message.*` означает «не попадало ни в одно `observation.extracted`»: транспорт пишет `message.*` с `dispatch_event=False` (§3.12), поэтому `processed_at` у них ставит только наблюдатель. В окно входят первые `observer_window_max` сообщений `message.*` (по `id`); `task.issued` попадают, если их `id` внутри диапазона `[first.id, last.id]` окна или предшествуют первому сообщению окна не более чем на 20 событий (задача выдана, ответ — в окне). События после окна остаются необработанными и попадут в следующий запуск. Если сообщений `message.*` нет — job завершается без записи (`observer_job{window=0}`), кроме случая `trigger="requested"`: тогда пишется `observation.extracted` с пустым списком и `source_event_ids=[]`, чтобы кнопка получила ответ «новых наблюдений нет» (§3.12).

**Границы топика.** `topic_skill_id`, `set_id`, `exam_id` берутся из событий окна (`Event.topic_skill_id`, `Event.set_id`; `exam_id` — из `repo.sets.get_set(set_id).exam_id`). Окно одного `chat_id` всегда одного топика (по построению `chat_id`), для чата сета — `topic_skill_id=None`.

**Контекст для модели.** Срез: `canonical.get_prerequisites(topic_skill_id, depth=2)` (+ сам навык; для сета — по всем топикам сета) → `canonical.list_exam_skills(exam_id)` для имён/описаний → `personal.get_states(student_id, exam_id)` → `SkillForObserver.level = words.skill_level(state, p_target_max, params)`. Заблуждения: `canonical.list_misconceptions_for_skill` по каждому навыку среза (библиотечные) + `personal.get_misc_states(student_id, skill_ids)` (статусы; персональные `pers.*` — из тех же состояний) → `MisconceptionForObserver` (статус `None`, если состояния нет). Задачи окна — `repo.tasks.list_instances(session, student_id, [instance_id из payload task.issued])` → `WindowTask` (без `answer`, без `correct`, без `misconception_id`). `previous_summary` — `repo.summaries.get_latest_text(...)`.

**Последовательность.**
1. `bind_contextvars(request_id=...)`. Лок `keys.lock(f"observe:{chat_id}")` `SET NX EX OBSERVER_JOB_TIMEOUT_S`; не взят → лог `observer_job{skipped=locked}` и выход (дедупликацию обеспечивает `job_id`, лок — страховка от двух воркеров).
2. `async with sessionmaker() as session`: окно (см. выше). Пусто и не `requested` → выход.
3. Контекст (граф). `deps.graph is None`/ошибка драйвера → `raise Retry(defer=10)` при `job_try < max_tries`, иначе `job.failed` (граф нужен для среза; без него наблюдение бессмысленно).
4. `result = await observer.run(ctx["llm"], window, context, slot=settings.OBSERVER_SLOT)`.
5. В той же сессии: `event = store.append(session, redis, EventIn(type=observation.extracted, payload=ObservationExtractedPayload(...).model_dump(mode="json"), student_id, session_id=<session_id последнего сообщения окна>, exam_id, set_id, topic_skill_id, chat_id, extractor_version=result.extractor_version, source_event_ids=[ids сообщений окна]), deps=RuleDeps(graph=ctx["neo4j"], redis=ctx["redis"], params, now), dispatch_event=True)` → внутри `dispatch` → `apply.observation.apply_observation_extracted` (§3.10) → результат `ObservationApplyResult` в `results["apply_observation_extracted"]`.
6. `store.mark_processed(session, source_event_ids)` — **в любом случае**, даже если правило вернуло `GraphUnavailable` (работа модели сохранена событием; применение — забота правила и фазы 5).
7. `commit`.
8. Для каждого `ordinal` из `apply_result.pending_canonizations`: `enqueue(redis, "interactive", "canonize_misconception", _job_id=f"canon:{event.id}:{ordinal}", student_id=..., observation_event_id=event.id, ordinal=ordinal)`.
9. Перезапуск: `count = store.count_unprocessed(session, chat_id, types=[message.*])` (§5); если `count ≥ params.observer_every_n` или за время работы появилось событие `observer.requested`/`topic.completed`/`set.completed` для этого чата с `processed_at IS NULL` (проверка `list_unprocessed(types=[...])`) → `enqueue(... "observe_chat", _job_id=f"observe:{chat_id}", trigger=...)` после снятия лока. События `observer.requested`/`topic.completed`/`set.completed` job помечает `processed` вместе с окном (они не имеют обработчиков графа).
10. Снять лок. Лог `observer_job{chat_id, trigger, window, observations, applied, skipped, ms}`.

**Ошибки и ретраи.** Транзиентные (`LLMUnavailable` кроме `LLM_FORCE_DOWN`, `openai.APITimeoutError|APIConnectionError|RateLimitError|APIStatusError(5xx)`, `ServiceUnavailable`, `SessionExpired`, ошибка соединения Postgres) → при `ctx["job_try"] < 3` `raise arq.Retry(defer=10 * job_try)` (это и есть «ретрай ×2»); на третьей попытке — `job.failed`. Невалидный structured после встроенного повтора (`LLMUnavailable("structured output failed")`) — **не** ретраится job'ом (два вызова модели уже сделаны) → сразу `job.failed{reason="invalid_structured_output"}`. `LLM_FORCE_DOWN`/статус `down` → `job.failed{reason="llm_down"}` без ретрая (восстановление — фаза 5). Прочие исключения (баг) → `job.failed{reason=<type>}`. `job.failed` = `store.append(EventIn(type=job_failed, payload=JobFailedPayload(job="observe_chat", job_id, reason, args={chat_id, trigger}), student_id, chat_id), dispatch_event=False)` в отдельной сессии; окно при этом **не** помечается обработанным (будет подхвачено следующим триггером). Таймаут ARQ (`OBSERVER_JOB_TIMEOUT_S`) — ARQ снимает job; лок истекает по TTL; окно не помечено — повторится по следующему триггеру; ARQ сам пишет `TimeoutError` в результат, `job.failed` в этом случае пишет обёртка `agents.jobs._guarded(...)` через `asyncio.timeout(OBSERVER_JOB_TIMEOUT_S - 5)` внутри job, чтобы успеть записать событие.

**Граничные случаи.** Окно из одного сообщения ученика без ответа репетитора (кнопка нажата сразу) — обрабатывается. Окно превышает `observer_window_max` — берётся первое окно, остаток → перезапуск (шаг 9). Задача выдана в предыдущем окне, ответ — в этом: `task.issued` уже `processed` → в `list_unprocessed` не попадёт; поэтому задачи окна дополнительно ищутся по `task_instances` этого чата без `answered_at` (`repo.tasks.list_open_chat_instances(session, student_id, chat_id)`, §5). `chat_id` подбора (`kind=selection`) в очередь не ставится (транспорт не триггерит), а если поставлен вручную — job завершается `observer_job{skipped=not_prep}` (у событий нет `set_id`).

**Идемпотентность.** `job_id=f"observe:{chat_id}"` + лок + `processed_at`: повторное выполнение после сбоя до шага 7 — окно не помечено, событие не записано (транзакция откатилась) → полный повтор без дублей; после шага 7 — окно помечено, повтор находит пустое окно → выход. Повторная доставка ARQ (падение воркера между 7 и 8/10): канонизация ставится с тем же `job_id` (дубль отброшен ARQ), перезапуск — идемпотентен по `job_id`.

**Concurrency.** Один job на чат; параллельно с живым ходом чата — допустимо (окно читает уже закоммиченные сообщения; лок чата не берётся). Запись в граф — под `student_lock` внутри правила (§3.10).

**Логирование.** См. выше; `job_failed`.

**Тестируемое поведение.** §6.8.

### 3.10 Правило применения `observation.extracted` — `apply.observation` (B1)

**Назначение.** Превратить наблюдения в `Evidence`, состояния, статусы заблуждений, корни и `task.answered` по таблице §8.1 «Виды и как они применяются», с порогом `observer_min_confidence`, потолком `p_chat_cap`, правилом «`confirmed` только при `strong_count ≥ 1`», идемпотентно по `event_id`.

**Расположение.** `app/apply/observation.py`: `apply_observation_extracted`, `apply_misconception_canonized`, `apply_misconception_personal_created`; чистая часть — `knowledge/reconcile.py::reconcile_chat_evidence` (§5); графовые функции — `graph/queries/personal.py` (§5); лок — `app/apply/_lock.py`. Регистрация в `events/handlers.py` (B3): `on(observation_extracted)(apply_observation_extracted)`, `on(misconception_canonized)(apply_misconception_canonized)`, `on(misconception_personal_created)(apply_misconception_personal_created)`.

**Интерфейс.**
```
apply.observation.apply_observation_extracted(session, event, deps) -> ObservationApplyResult | GraphUnavailable
knowledge.reconcile.reconcile_chat_evidence(evidence: EvidenceIn, state: KnowledgeStateOut | None,
    misc_states: list[MisconceptionStateOut], misconception_id: str | None, avoided: bool,
    params: KnowledgeParams, now: datetime) -> ReconcileResult
personal.list_evidence_keys_for_event(driver, student_id, event_id) -> set[tuple[str, int]]      # (skill_id, ordinal)
personal.apply_chat_observation_tx(driver, student_id, evidence: EvidenceIn, new_state: KnowledgeStateOut,
    misc: MisconceptionChange | None, triggers: dict | None, source_event_id: int) -> str          # одна транзакция Neo4j
personal.latest_incorrect_evidence(driver, student_id, skill_id) -> EvidenceOut | None
apply._lock.student_lock(redis, student_id, *, ttl_s=15, wait_s=5) -> AsyncContextManager[bool]
```
`ObservationApplyResult(event_id, applied: int, skipped: list[tuple[int, str]], skills_changed: list[str], misconceptions_changed: list[MisconceptionChange], task_answered_event_ids: list[int], pending_canonizations: list[int], knowledge_version: int)` — модель в `app/schemas/observer.py`.

**Вход.** `Event` типа `observation.extracted` с `payload=ObservationExtractedPayload`, `extractor_version`, `source_event_ids`, `chat_id`, `set_id`, `topic_skill_id`, `exam_id`, `session_id`; `RuleDeps`.

**Выход.** `ObservationApplyResult`; `GraphUnavailable`, если `deps.graph is None` или драйвер упал до первой записи.

**Последовательность.**
1. Валидировать payload. `deps.graph is None` → `GraphUnavailable` (событие остаётся `processed_at=NULL`).
2. Загрузить срез: `skill_ids` = навык топика + `get_prerequisites(depth=2)` (для сета — по топикам сета через `repo.sets.get_set`); `exam_id`; известные `misconception_ids` = библиотечные `ABOUT` этих навыков ∪ персональные ученика (`get_misc_states`); `source_event_ids` события; открытые задачи чата (`repo.tasks.list_open_chat_instances`) ∪ задачи из `task.issued` в `source_event_ids`; `hint_level_before` — из `markup.hint_level` последнего `message.assistant` перед сообщением-источником (по `repo.messages` / событиям окна).
3. `applied_keys = list_evidence_keys_for_event(graph, sid, event.id)`.
4. `async with student_lock(deps.redis, sid) as got:` (`got=False` после `wait_s` → продолжить с warning `student_lock_timeout`, не блокировать).
5. Для `ordinal, obs in enumerate(payload.observations)` — по видам:
   - **фильтры (любой → `skipped.append((ordinal, reason))`, лог `observation_skipped`)**: `obs.kind != "pace_signal" and obs.confidence < params.observer_min_confidence` → `low_confidence`; `obs.skill_id` задан и не в `skill_ids` → `unknown_skill`; `obs.misconception_id` задан и не в известных → `unknown_misconception`; `obs.root_skill_id` не в `skill_ids` → `unknown_root`; `not set(obs.event_ids) <= set(source_event_ids)` → `event_ids_outside_window`; `(obs.skill_id, ordinal) in applied_keys` → `already_applied` (идемпотентность).
   - **`solution_step`, `applied`, `confusion`, `question`, `avoided_trap`**: `direction` = `+1` для `solution_step(correct)`, `applied`, `avoided_trap`; `−1` для `solution_step(incorrect)`, `confusion`, `question`. `tier = weights.tier_for("chat","chat",kind)` (2 для `solution_step`/`avoided_trap`, 3 иначе), `weight = weights.evidence_weight("chat","chat",kind, seen_before=False, matched=True, params=params)`. `EvidenceIn(event_id=event.id, ordinal, skill_id, exam_id, kind, tier, source="chat", weight, direction, summary=obs.summary, context=EvidenceContext(mode="chat", session_minute=<минуты от начала session_id до occurred_at сообщения-источника>, topic_skill_id, session_id, hint_level_before, message_id=<message_id первого из obs.event_ids>), observed_at=<occurred_at последнего из obs.event_ids>, extractor_version=event.extractor_version)`. `state = get_state(sid, skill_id, exam_id)`; `misc_states = get_misc_states(sid, [skill_id])`. `result = reconcile_chat_evidence(evidence, state, misc_states, misconception_id=obs.misconception_id if kind in {solution_step(incorrect), avoided_trap} else None, avoided=(kind == "avoided_trap"), params, now)`. Внутри: `hlr.apply_evidence` (потолок `p_chat_cap` для яруса 3 — уже в `hlr`; `has_strong` ставится только при ярусе ≤ 2, как для задач); заблуждение: попадание (`solution_step incorrect` с `misconception_id`) → `occurrence_count += 1`, `strong_count += 1` при `is_strong(tier)` (ярус 2 — да), `next_status(event="hit", strong=...)` — `confirmed` возможен только при `strong_count ≥ 1` (§5.1), `update_triggers` по контексту; `avoided_trap` → `consecutive_avoided += 1`, `next_status(event="avoided")`; общий навык `math.*` — кросс-экзаменное состояние `× transfer_cross_exam` без `has_strong` (как в `reconcile_task_answer`). Запись — одной транзакцией `apply_chat_observation_tx` (MERGE `Evidence{event_id, skill_id, ordinal}` с контекстом, CREATE нового `KnowledgeState` + `PREVIOUS` (+ кросс-экзаменного), MERGE `MisconceptionState`). `skills_changed.append(skill_id)`, `applied += 1`.
   - **`task_in_chat`**: `instance` из открытых задач чата по `obs.instance_id`; нет → `unknown_instance`; `answered_at` уже стоит → `already_answered`. Иначе `store.append(session, deps.redis, EventIn(type=task_answered, payload=TaskAnsweredPayload(instance_id, answer=obs.answer, time_spent_sec=clamp(occurred_at(answer msg) − occurred_at(task.issued), 0, 3600), mode="chat", session_minute, after_guideline=False, hint_level_before), student_id, session_id, exam_id, set_id, topic_skill_id, chat_id, occurred_at=<occurred_at сообщения с ответом>, source_event_ids=[event.id]), deps, dispatch_event=True)` → `apply_task_answered` (грейд по разметке экземпляра, свидетельство `source="chat", kind="task_in_chat", tier 2, weight 0.8` — требование к `reconcile_task_answer` для `mode="chat"`, §5; состояние; заблуждение по дистрактору; корень; `seen`; `mark_answered`). `task_answered_event_ids.append(id)`. `obs.answer` нормализуется к формату экземпляра: для `mcq*` — буква варианта (регистр не важен), для `numeric` — строка числа; не распознано → `skipped(unparsable_answer)`.
   - **`root_hint`**: `ev = ближайшее incorrect-свидетельство по obs.skill_id`: сначала среди только что записанных в этом событии, иначе `latest_incorrect_evidence(sid, skill_id)`; нет → `skipped(no_incorrect_evidence)`. `add_root_cause(evidence_id, obs.root_skill_id, confidence=0.6, source="observer")` (MERGE).
   - **`proposed_misconception`**: `pending_canonizations.append(ordinal)` (постановку делает job — `apply` не знает ARQ). Свидетельство по навыку не создаётся здесь (создаст правило канонизации).
   - **`pace_signal`**: `repo.aggregates.add_pace_signal(session, sid, day=occurred_at.date(), signal=obs.signal, source_event_id=event.id, ordinal)` (идемпотентно по `(event_id, ordinal)` внутри JSON `payload.pace_signals`).
6. Если `applied > 0` или `task_answered_event_ids`: `rebuild_sets(session, deps, sid, exam_id)` один раз (у `task.answered` он уже вызван внутри — повторный вызов под локом `rebuild:{sid}` пропускается, это допустимо), `version = bump(deps.redis, sid)`, `DEL keys.ctx_topic(sid, topic_skill_id)` и `DEL keys.ctx_topic(sid, f"set:{set_id}")`. Иначе `version = events.version.get`.
7. Вернуть `ObservationApplyResult`.

**Ошибки.** `ServiceUnavailable`/`SessionExpired` до первой записи → `GraphUnavailable` (диспетчер не ставит `processed_at`). Во время цикла (после части записей) → та же обработка: возвращается `GraphUnavailable`, применённые наблюдения остались (каждое — своя транзакция), при повторной доставке они пропускаются как `already_applied`. `ValidationError` payload — исключение наверх (диспетчер логирует и пробрасывает → транзакция job откатывается → событие не записано; job пишет `job.failed`). Неверный `misconception_id` в `next_status` (нет узла) — `upsert_misc_state` MATCH не находит `Misconception` → пустой результат → `assert` → исключение; поэтому ссылочный фильтр в шаге 5 обязателен.

**Граничные случаи.** Два наблюдения по одному навыку в одном событии — два `Evidence` с `ordinal` 0 и 1, состояние обновляется дважды последовательно. `solution_step(correct)` с `misconception_id` — `misconception_id` игнорируется (ловушка «обойдена» — это `avoided_trap`). `avoided_trap` по заблуждению без состояния — состояние создаётся `suspected`? Нет: `consecutive_avoided` без состояния бессмысленен → `skipped(no_misconception_state)`. `confusion` по навыку без состояния — состояние создаётся от стартового (`h0`, `p=0.5`). Наблюдение ярусa 3 не поднимает `p_at_obs` выше `p_chat_cap` и не ставит `has_strong`. Пустой список наблюдений — `applied=0`, версия не растёт.

**Идемпотентность.** По `(event_id, skill_id, ordinal)` для свидетельств (MERGE + предварительная выборка ключей), по `answered_at` для `task_in_chat`, MERGE для корней, `job_id` для канонизации, `(event_id, ordinal)` для темпа. Повторный `dispatch` того же события → `applied=0`, все `skipped(already_applied|already_answered)`, версия не растёт, состояния не создаются (тест §6.9).

**Concurrency.** `student_lock` на время цикла записей; `apply_task_answered` и `apply_dispute` берут тот же лок (реентерабельно внутри `task_in_chat`: лок хранит токен job/запроса, вложенный захват тем же токеном проходит). Ожидание ≤ 5 с — ученик, отвечающий на задачу параллельно, не ждёт дольше.

**Логирование.** `observation_applied{event_id, applied, skipped: n, task_answered: n, canon: n, version}`, `observation_skipped{event_id, ordinal, kind, reason}`.

**Тестируемое поведение.** §6.9.

### 3.11 Канонизация — `agents.jobs.canonize_misconception` + правило (B2 job, B1 правило и запросы, B3 реестр)

**Назначение.** §5.4: эмбеддинг предложенного заблуждения, top-5 по `misc_emb` среди библиотечных того же навыка и персональных ученика, пороги `canon_merge`/`canon_adjudicate`, точечный вызов модели «да/нет», результат — событие; узел персонального заблуждения и свидетельство создаёт правило.

**Расположение.** `app/agents/jobs.py` (`canonize_misconception`), промпт `app/agents/prompts/canon_v1.md` (`{{a}}`, `{{b}}`), `graph/queries/canonical.py` (`search_misconceptions`, `create_personal_misconception`), `apply/observation.py` (обработчики), `workers/main.py` (эмбеддер в `ctx["embedder"]` при старте `worker-interactive`; `Embedder(settings.EMBEDDING_MODEL, settings.EMBEDDING_DIM)`, прогрев `embed(["warmup"])`).

**Интерфейс.**
```
jobs.canonize_misconception(ctx: dict, request_id: str, student_id: UUID, observation_event_id: int, ordinal: int) -> None
canonical.search_misconceptions(driver, embedding: list[float], skill_id: str, student_id: UUID, k: int = 5)
    -> list[tuple[MisconceptionRef, float]]     # library ABOUT skill_id ∪ personal этого ученика; отбор из top-20 индекса
canonical.create_personal_misconception(driver, student_id, misconception_id, name, description, error_class,
    skill_id, embedding, source_event_id, ordinal) -> MisconceptionRef   # MERGE по id; ABOUT skill
CanonDecision(same: bool, reason: str = Field(max_length=200))   # app/schemas/observer.py
```
Payload-модели (`app/schemas/events.py`, §5): `MisconceptionCanonizedPayload(source_event_id, ordinal, skill_id, canonical_id, similarity, decided_by: Literal["threshold","model"], name, description, error_class)`; `MisconceptionPersonalCreatedPayload(misconception_id, source_event_id, ordinal, skill_id, name, description, error_class, embedding: list[float], best_similarity: float | None)`.

**Последовательность job.**
1. `bind_contextvars`. Прочитать событие `observation_event_id` (`store.get_event`), взять `obs = payload.observations[ordinal]`; `kind != proposed_misconception` → выход с логом.
2. Идемпотентность: если уже есть событие `misconception.canonized` или `misconception.personal_created` с `payload.source_event_id == observation_event_id and ordinal` (`store.list_by_type` + фильтр) → выход.
3. `vec = ctx["embedder"].embed([f"{obs.name}. {obs.description}"])[0]` (`ValueError` размерности → `job.failed`).
4. `cands = search_misconceptions(graph, vec, obs.skill_id, student_id, k=5)`; `best, sim = cands[0]` или `None`.
5. `sim > params.canon_merge` → `canonical_id=best.id`, `decided_by="threshold"`. `params.canon_adjudicate ≤ sim ≤ canon_merge` → `decision = await llm.structured([system(canon_v1.render(a=<name/description предложенного>, b=<name/description кандидата>)), user("Одно ли это заблуждение?")], CanonDecision, settings.OBSERVER_SLOT)`; `same` → `canonical_id=best.id`, `decided_by="model"`; иначе — создать. `sim < canon_adjudicate` или кандидатов нет → создать.
6. Событие: merge → `misconception.canonized`; create → `misconception.personal_created` с `misconception_id = f"pers.{student_id.hex[:8]}.{slug(obs.name)[:24]}"` (коллизия id при существующем узле → суффикс `-2`). `store.append(..., deps=RuleDeps(graph, redis, params, now), dispatch_event=True)` → правило.
7. Commit; лог `canonize{event_id, ordinal, decision, similarity, decided_by}`.

**Правило (B1).** `apply_misconception_personal_created`: `create_personal_misconception(...)` (MERGE по `id`, свойства `scope='personal'`, `student_id`, `embedding`, `source_event_id`, `ordinal`; `(:Misconception)-[:ABOUT]->(:Skill)`), затем как при `canonized`. `apply_misconception_canonized`: свидетельство по навыку — `EvidenceIn(event_id=event.id, ordinal=0, skill_id, kind="misconception_hit", tier=2, source="chat", weight=weights.base_weight("chat","chat","solution_step"), direction=-1, summary=description, extractor_version=<из исходного observation.extracted>)`, состояние навыка через `reconcile_chat_evidence(..., misconception_id=canonical_id)`, запись `apply_chat_observation_tx` → `MisconceptionState` `suspected` (или переход по `next_status`: `strong_count ≥ 1` ⇒ второе попадание даст `confirmed`); `bump`, `DEL ctx_topic`. `deps.graph is None` → `GraphUnavailable`.

**Ошибки.** Транзиентные — `Retry` до 3 попыток, затем `job.failed{job="canonize_misconception"}`; `structured` дважды невалиден → трактуется как `same=False` (создать персональное — консервативно? Нет: ложный узел хуже отсутствия, §11.2) → **пропуск**: `job.failed{reason="adjudication_failed"}`, наблюдение теряется до ручного повтора. Эмбеддер не загружен (`ctx["embedder"] is None`, tech-stack §8.3) → `job.failed{reason="embedder_unavailable"}` без ретрая.

**Граничные случаи.** `obs.skill_id` общий `math.*` — библиотечные кандидаты `ABOUT` этого узла. Пустая библиотека для навыка и нет персональных — создать. Два `proposed_misconception` в одном окне с одинаковым `name` — второй job найдёт первый как персонального кандидата с `sim ≈ 1.0` → merge.

**Идемпотентность.** `job_id`, проверка результата в шаге 2, MERGE узла по `id`, свидетельство по `(event_id, skill_id, 0)`.

**Concurrency.** `student_lock` в правиле; эмбеддер — синхронный вызов в воркере (одна модель на процесс, ~50 мс).

**Логирование.** `canonize`, `job_failed`.

**Тестируемое поведение.** §6.10.

### 3.12 Платформа: транспорт, триггеры, кнопка, реестр (B3)

**Транспорт `api/chat.py`.**
1. Лок чата: до записи `message.user` — `SET keys.lock(f"chat:{chat_id}") <request_id> NX EX CHAT_LOCK_TTL_S`; не взят → `409 conflict("assistant is still answering")`. Снятие — в `finally` `_wrap_agent` (только если значение равно своему `request_id`).
2. `message.user` и `message.assistant` пишутся с `dispatch_event=False` (у них нет обработчиков; `processed_at` этих событий принадлежит наблюдателю — §3.9). Сейчас они не помечаются лишь потому, что `deps=None` даёт `graph=None`; явный флаг убирает зависимость от случайности.
3. `Done` → как сейчас (`message.assistant` + `messages`, `event_id`); `StreamError` (в т. ч. `postcheck_failed`) → без записи, как сейчас.
4. Триггер наблюдателя после `Done` для `kind="prep"`: `count = store.count_unprocessed(session, chat_id, types=[message_user, message_assistant])`; `count ≥ params.observer_every_n` → `enqueue(app.state.arq, "interactive", "observe_chat", _job_id=f"observe:{chat_id}", chat_id, student_id, trigger="every_n")`. `app.state.arq: ArqRedis` создаётся в `main.lifespan` (`arq.create_pool(RedisSettings.from_dsn(settings.REDIS_URL))`) и закрывается при остановке. Ошибка постановки (Redis) — warning, ответ ученику не ломается.
5. `POST /chat/prep/observe` `{set_id, topic_skill_id}` → 202 `ObserveRequestedOut(job_id, since_event_id: int, knowledge_version: int)`: append `observer.requested` (`ObserverRequestedPayload(reason: Literal["button"])`, `chat_id`, `set_id`, `topic_skill_id`, `dispatch_event=False`) → `enqueue(... trigger="requested")`; `since_event_id` = id этого события. Rate-limit: не чаще раза в 10 с на чат (Redis `SET NX EX 10`, иначе 429).
6. `GET /chat/prep/observations?set_id&topic_skill_id&since_event_id=` → `ObservationsDiffOut(status: Literal["pending","done","failed"], observations: list[ObservationView], skills: list[SkillStateView], misconceptions: list[MisconceptionStateOut], knowledge_version: int)`: события `observation.extracted` этого `chat_id` с `id > since_event_id` (`store.list_by_type` + фильтр `chat_id`); `ObservationView(event_id, ordinal, kind, skill_id, skill_name, misconception_id, summary, confidence, applied: bool, message_ids: list[UUID])` — `applied` по наличию `Evidence` (`list_evidence_keys_for_event`) или `task_answered`; `message_ids` — по `event_ids` через `messages.event_id`; `skills` — `apply.knowledge.states_view` только по `skill_id` из наблюдений; `status`: `done`, если есть хотя бы одно событие после `since_event_id`; `failed`, если есть `job.failed{job=observe_chat, chat_id}` после `since_event_id` и нет наблюдений; иначе `pending`. Это и есть diff кнопки (§13.7): пустой `observations=[]` со `status=done` → фронт показывает «новых наблюдений нет». Заголовок `X-Knowledge-Version`.
7. Чат сета: `ChatMessageIn` с `set_id` и без `topic_skill_id` → `chat_id = uuid5(student_id, f"prep:{set_id}")` (сейчас 400; §5). Наблюдатель и контекст работают с `topic_skill_id=None`.

**Роутер сетов `api/sets.py`.** После `topic.completed` — `enqueue(observe_chat, _job_id=f"observe:{chat_id топика}", trigger="topic_completed")` и `DEL keys.ctx_topic(sid, skill_id)`, `DEL keys.ctx_topic(sid, f"set:{set_id}")`. После `set.completed` — по каждому топику сета `enqueue(observe_chat, trigger="set_completed")` (только для чатов с `count_unprocessed > 0`) и для чата сета. `enqueue` с занятым `job_id` возвращает `None` — это норма (job уже стоит).

**Реестр воркеров `workers/registry.py`.** `INTERACTIVE = [ping, func(observe_chat, timeout=settings.OBSERVER_JOB_TIMEOUT_S, max_tries=3), func(canonize_misconception, timeout=settings.CANON_JOB_TIMEOUT_S, max_tries=3)]`; `BULK = [ping]`. `WorkerInteractive.job_timeout` остаётся 30 (для `ping`), пер-функциональные таймауты выше. `startup` для `interactive`: `ctx["embedder"] = Embedder(...)` + прогрев в `asyncio.to_thread`; при исключении — `ctx["embedder"] = None` и warning (канонизация будет писать `job.failed`, tech-stack §8.3).

**`events/store.py`.** `list_unprocessed(session, chat_id, limit=50, types: list[EventType] | None = None)`, `count_unprocessed(session, chat_id, types) -> int`, `get_event(session, student_id, event_id) -> Event | None`. `_PAYLOAD_MODELS` += `observation_extracted`, `observer_requested`, `job_failed`, `misconception_canonized`, `misconception_personal_created`.

**`events/session.py`.** `session_minute(session, student_id, session_id, now) -> int` (перенос `_session_minute` из `api/_answer.py`; роутер вызывает новую функцию).

**Репозитории.** `db.repo.messages.get_message(session, student_id, message_id) -> MessageOut | None`, `list_by_event_ids(session, student_id, event_ids) -> dict[int, UUID]`; `db.repo.tasks.list_open_chat_instances(session, student_id, chat_id) -> list[TaskInstance]` (по `issued_event_id` → `events.chat_id`, `answered_at IS NULL`; для этого `apply.tasks.issue` начинает писать `issued_event_id` — §5); `db.repo.summaries.get_latest_text(session, student_id, before_set_id) -> str | None`; `db.repo.aggregates.add_pace_signal(session, student_id, day, signal, source_event_id, ordinal) -> None` (upsert `daily_aggregates`, `payload.pace_signals: [{signal, event_id, ordinal}]` без дублей).

**`keys.py`.** `matching_snapshot(student_id) -> "quack:matching:snapshot:{sid}"`; имена локов: `chat:{chat_id}`, `observe:{chat_id}`, `knowledge:{student_id}`, `observe_rl:{chat_id}` — через `keys.lock`.

**`main.py`.** `app.state.arq`; импорт `events.handlers` уже есть.

**Ошибки/границы/идемпотентность/логирование.** Постановка с занятым `job_id` — не ошибка. 429 на кнопку. `GET /chat/prep/observations` на чужой сет → 404. Лог `observer_enqueued{chat_id, trigger, job_id|null}`.

**Тестируемое поведение.** §6.11.

---

## 4. Ошибки и граничные случаи — сводная таблица

| Ситуация | Где ловится | Поведение | Что видит ученик / клиент | Лог / событие |
| :---- | :---- | :---- | :---- | :---- |
| LLM timeout (`openai.APITimeoutError`) в чате | `LLMClient` (breaker `_record`), затем `run_tool_loop` | до первого события: `StreamError(llm_unavailable)` → роутер → `LLMUnavailable` → 503; после: `StreamError(llm_unavailable)` последним | 503 `llm_unavailable` или кадр `error` | `llm_status` degraded/down; `chat_turn_done{error}` |
| HTTP 429 от провайдера | `LLMClient` | как таймаут; для `bulk` один внутренний повтор через 1 с; breaker считает | то же | то же |
| LLM 5xx | `LLMClient` | как таймаут (`bulk` — один повтор) | то же | то же |
| Circuit breaker `down` / `LLM_FORCE_DOWN` | `LLMClient._check_breaker` → `LLMUnavailable` без сети | чат: 503 до первого события; наблюдатель: `job.failed{llm_down}` без ретрая; канонизация — то же | «ассистент временно недоступен» через `/health.llm_status`; кнопка «обновить» → `status=failed` | `job_failed` |
| Собственный rate-limit (`LLMUnavailable("rate limit")`) | `LLMClient._acquire` | чат: как `down`; job: `Retry(defer=10*job_try)` ×2, затем `job.failed{rate_limit}` | 503 / кадр `error` | `job_failed` |
| Невалидный structured output наблюдателя | `LLMClient.structured` (1 повтор) → `LLMUnavailable("structured output failed")` | job не ретраит → `job.failed{invalid_structured_output}`; окно не помечено | кнопка → `status=failed`; по следующему триггеру повтор | `job_failed` |
| Невалидный structured у канонизации | то же | `job.failed{adjudication_failed}`, узел не создаётся | — | `job_failed` |
| Неизвестный tool (модель назвала имя вне реестра/политики) | `run_tool_loop` (`KeyError` из `registry.call`) | `ToolResult(error="unknown tool …")`, ход продолжается | кадр `tool_result` с `error` | `tool_denied` |
| Неверные аргументы tool | `ToolRegistry.call` → `ValidationFailed` | `ToolResult(error=<текст Pydantic>)`; модель повторяет вызов с исправлением (в пределах `max_steps`) | кадр `tool_result` с `error` | `tool_called{ok=false}` |
| Исключение внутри tool (`NotFound`, `Conflict`, Neo4j, Postgres) | `run_tool_loop` | `ToolResult(error=str(exc))`; сессия инструмента откатывается (`async with` без коммита) | кадр `tool_result` с `error`; модель говорит «нет в данных» | `tool_called{ok=false, error_type}` |
| Повторный tool call в одном ходе | тела инструментов | `update_profile` с равным значением → `unchanged`; `save_program` → `Conflict` → `error`; `get_task` второй → `error="one task per turn"`; `run_matching` — повтор детерминирован | — | `tool_called` |
| `steps > max_steps` | `run_tool_loop` | `StreamError(tool_loop_limit)`; ответ не сохраняется | кадр `error`, клиент предлагает повторить | `chat_turn_done{error=tool_loop_limit}` |
| Постпроверка не прошла | агент | `StreamError(postcheck_failed)`; ответ не сохраняется | кадр `error`, черновик убирается | `postcheck{ok=false, mismatches}` |
| Повторное сообщение (тот же текст дважды) | — | два хода, два ответа; истории не дедуплицируются | — | — |
| Параллельные запросы одного пользователя в одном чате | транспорт (лок `chat:{chat_id}`) | второй → 409 `conflict`, `message.user` не пишется | 409 | `http_request` |
| Параллельные запросы в разных чатах одного ученика | нет ограничения | оба хода; графовые записи сериализует `student_lock` | — | — |
| Пустая история | роутер/агенты | стадия `opening`; репетитор — обычный ход | — | — |
| Нет данных в графе (нет состояний, нет предпосылок) | `build_topic_context`, срез наблюдателя | пустые слоты (`[]`), `low_data`; наблюдатель получает срез из одного навыка | репетитор не ссылается на «данные о тебе» | `ctx_topic{slots}` |
| Neo4j недоступен | `apply.context` → `None`; инструменты `get_exam_format/get_admission_route/explain_belief` → `error`; `apply.observation` → `GraphUnavailable`; job → `Retry`, затем `job.failed` | чат работает без контекста; наблюдение записано событием, `processed_at=NULL` (применение — фаза 5) | репетитор отвечает без модели знаний | `graph_unavailable` |
| Redis недоступен | кэш контекста, снимок подборки, локи | без кэша; снимок «нет»; лок не берётся → ход разрешён (warning) | — | warning |
| Устаревший `TopicContext` (версия изменилась) | кэш | промах → пересборка | — | `ctx_topic{miss}` |
| Повторная обработка одного `event_id` (`observation.extracted` доставлен дважды) | `apply.observation` | все наблюдения `already_applied`/`already_answered`, версия не растёт | — | `observation_applied{applied=0}` |
| Падение воркера посреди job | ARQ (`max_tries`), локи с TTL, транзакция Postgres | до коммита — полный повтор; после коммита — пустое окно; канонизация — дубль `job_id` отброшен | — | ARQ лог |
| Повторное выполнение ARQ job (`Retry`, второй воркер) | `job_id`, лок `observe:{chat_id}`, `processed_at` | второй экземпляр видит лок → выход; после TTL — пустое окно | — | `observer_job{skipped=locked}` |
| Таймаут job ARQ | `asyncio.timeout` внутри job | `job.failed{timeout}`; окно не помечено | кнопка → `failed` | `job_failed` |
| Кнопка при пустом окне | `observe_chat(trigger=requested)` | событие с `observations=[]` | «новых наблюдений нет» | `observer_job{window=0}` |
| Ученик спрашивает репетитора о датах/требованиях | промпт + постпроверка `exam_facts` | ответ без дат; если дата всё же названа — отозван | «это в чате подбора» | `postcheck` |
| Ответ ученика на задачу не распознан (`task_in_chat.answer` не буква и не число) | `apply.observation` | `skipped(unparsable_answer)` | — | `observation_skipped` |

---

## 5. Контракты: изменения и добавления

Правило: старый контракт действует, если не указан здесь. Каждое изменение — со старым/новым видом, причиной и влиянием на B1/B2/B3/frontend. Фронт получает перегенерированный `schema.d.ts` (`make types`); чат подбора/подготовки на фронте ещё не потребляет SSE (проверено: в `frontend/src` нет `text_delta`/`tool_result`), поэтому влияние на фронт — только типы и правила поведения, зафиксированные ниже.

### 5.1 Схемы (`app/schemas/`) — B3 создаёт в скелете фазы, содержание согласовано здесь

| # | Старый контракт | Новый контракт | Причина | Влияние |
| :---- | :---- | :---- | :---- | :---- |
| C1 | `Observation`, `ObservationKind`, `ObservationOut` живут в `app/agents/observer.py` | переезжают в `app/schemas/observer.py` без изменения полей; `app/agents/observer.py` реэкспортирует (`from app.schemas.observer import …`) | payload события `observation.extracted` валидируется в `events.store` (B3), а `schemas` не может импортировать `agents` | B2: импорт; тесты `tests/agents/test_observer_schema.py` продолжают работать через реэкспорт |
| C2 | — | `app/schemas/observer.py` += `WindowMessage`, `WindowTask`, `ObserverWindow`, `SkillForObserver`, `MisconceptionForObserver`, `ObserverContext`, `ObserverResult`, `ObservationApplyResult`, `CanonDecision`, `ObservationView`, `ObservationsDiffOut`, `ObserveRequestedOut` (поля — §3.8–§3.12) | новые входы/выходы наблюдателя, правила и кнопки | B1, B2, B3, frontend (типы `ObservationsDiffOut`, `ObserveRequestedOut`) |
| C3 | — | `app/schemas/agents.py`: `ProfileUpdateResult`, `RunMatchingResult`, `MatchCard`, `MatchingSnapshot`, `SaveProgramResult`, `ProgramFactsResult`, `AdmissionRouteResult`, `ExamFormatResult`, `DatasetAggregateOut`, `ExplainBeliefResult`, `BeliefItem`, `BeliefTask`, `BeliefMessage`, `GetTaskResult`, `TurnState` (поля — §3.3, §3.5) | типизированные `tool_result.data` для фронта и постпроверки | B2, frontend (рендер карточек по `tool_result.tool`) |
| C4 | `EventType` без `misconception.canonized` | `EventType.misconception_canonized = "misconception.canonized"` | результат канонизации «свести к существующему» — не создание узла; отдельный тип честнее, чем `personal_created` с флагом | B3 (`store._PAYLOAD_MODELS`, `handlers`), B1 (обработчик), memory-architecture §1.2 таблица — дописать строку |
| C5 | payload-модели `observation.extracted`, `observer.requested`, `job.failed`, `misconception.personal_created` отсутствуют | `ObservationExtractedPayload(observations: list[Observation], window_from_event_id: int \| None, window_to_event_id: int \| None, topic_skill_id: str \| None, set_id: UUID, exam_id: ExamId, model: str, raw_count: int)`; `ObserverRequestedPayload(reason: Literal["button"])`; `JobFailedPayload(job: str, job_id: str \| None, reason: str, args: dict)`; `MisconceptionPersonalCreatedPayload(...)`, `MisconceptionCanonizedPayload(...)` (§3.11) | эти типы событий уже в `EventType`, но без схем payload (`store` пропускал как `dict`) | B3 (`_PAYLOAD_MODELS`), B1, B2 |
| C6 | `EvidenceIn` без `ordinal`; `EvidenceContext` без `instance_id`/`message_id` | `EvidenceIn.ordinal: int = 0`; `EvidenceContext.instance_id: UUID \| None = None`, `message_id: UUID \| None = None` | одно событие наблюдателя даёт несколько свидетельств по одному навыку; `explain_belief`/`EvidenceOut` требуют ссылку на экземпляр/сообщение (поля `list_evidence` читает, но никто не пишет) | B1 (`merge_evidence`, `reconcile` заполняет `context.instance_id`), B3 — нет |
| C7 | `TopicContext` (9 слотов) | += `skill_ids: list[str] = []`, `topic_name: str = ""`, `set_label: str = ""`, `as_of: datetime \| None = None`, `cache: Literal["hit","miss","none"] = "none"` | проверка `get_task` по срезу, заголовок блока §9.3, наблюдаемость кэша | B1, B2 |
| C8 | `AssistantMarkup.mode: str \| None` — любые строки | без изменения типа; **соглашение**: для `kind=selection` — стадия `opening\|intake\|summary\|matching\|refine`; для `kind=prep` — `explain\|review\|task` | стадия хранится в истории, а не в отдельной таблице | B2, frontend (может показывать стадию; не обязан) |
| C9 | `StreamError.code` — `llm_unavailable`, `tool_loop_limit`, `internal` | += `postcheck_failed` (ответ отозван, не сохранён), `conflict` не используется в потоке (409 до потока) | постпроверка в цепочке | frontend: при `error.code == "postcheck_failed"` убрать частичный ответ и показать подсказку «попробуйте спросить ещё раз» |
| C10 | `GetTaskArgs(skill_id, difficulty)` | `GetTaskArgs(skill_id, difficulty: int \| None = None, with_trap: str \| None = None, exclude_seen: bool = True)` | memory-architecture §9.5 (отложено в фазе 1 по sync-log) | B2; `difficulty` до появления поля в `TaskRequestIn` игнорируется (зафиксировано в `description`) |
| C11 | `KnowledgeParams` | += `observer_window_max=30`, `assistant_max_questions=2`, `assistant_readiness_threshold=0.6`, `context_set_multiplier=1.5`, `tutor_escalate_after_failures=2`; `Settings` += `OBSERVER_SLOT`, `CTX_CACHE_TTL_S`, `CHAT_LOCK_TTL_S`, `OBSERVER_JOB_TIMEOUT_S`, `CANON_JOB_TIMEOUT_S` | §2.5 | B3 (config), memory-architecture §12 — дописать |

### 5.2 Функции между слоями

| # | Старый контракт | Новый контракт | Причина | Влияние |
| :---- | :---- | :---- | :---- | :---- |
| F1 | `agents.observer.observe(client, window, context)` (стаб) | `agents.observer.run(client, window, context, *, slot) -> ObserverResult`; `observe` удаляется | имя из `backend-phases` §3, типизированные вход/выход | B2; тест на `pytest.raises(NotImplementedError)` заменяется |
| F2 | `agents.jobs.observe_chat(ctx, request_id, chat_id, student_id)` | `+ trigger: Literal[...] = "every_n"` | перезапуск и кнопка различают причину | B3 (`enqueue` передаёт `trigger`) |
| F3 | — | `agents.jobs.canonize_misconception(ctx, request_id, student_id, observation_event_id: int, ordinal: int)` | стаба не было | B3 (реестр) |
| F4 | `graph.context.build_topic_context(driver, student_id, skill_id, set_id)` (стаб) | `build_topic_context(driver, redis, student_id, topic_skill_id: str \| None, set_id, *, exam_id, extras: ContextExtras, params, now) -> TopicContext`; новый `apply.context.get_topic_context(session, deps, student_id, set_id, topic_skill_id) -> TopicContext \| None` | кэш, чат сета, Postgres-входы без импорта `db` из `graph` | B1, B2 (репетитор зовёт `apply.context`) |
| F5 | `graph.queries.personal.merge_evidence` — MERGE по `(event_id, skill_id)`, контекст не пишется | MERGE по `(event_id, skill_id, ordinal)`; `ON CREATE SET` также пишет `e.ordinal`, `e.ctx_task_type, ctx_difficulty, ctx_tags, ctx_mode, ctx_time_ratio, ctx_session_minute, ctx_after_guideline, ctx_hint_level_before, ctx_topic_skill_id, ctx_session_id, ctx_instance_id, ctx_message_id`; возвращаемый `evidence_id` — `"{event_id}:{skill_id}"` при `ordinal=0`, иначе `"{event_id}:{skill_id}:{ordinal}"`; индекс `evidence_key` расширяется на `(event_id, skill_id, ordinal)` (`schema.cypher`, идемпотентно) | C6; фаза 2 теряла контекст и схлопывала `misconception_hit` с основным свидетельством одного события (латентный дефект — исправляется здесь: `reconcile_task_answer` даёт `misconception_hit` с `ordinal=1`) | B1; `add_root_cause` разбирает `evidence_id` с необязательным третьим сегментом |
| F6 | — | `personal.list_evidence_keys_for_event`, `personal.apply_chat_observation_tx`, `personal.latest_incorrect_evidence` (§3.10); `canonical.search_misconceptions`, `canonical.create_personal_misconception` (§3.11); `graph.queries.context.q_skill_slice/q_root_causes/q_misconceptions/q_test_dates` (§3.7) | новые запросы | B1 |
| F7 | `knowledge.reconcile` — только `reconcile_task_answer`, `reconcile_prior` | += `reconcile_chat_evidence(evidence, state, misc_states, misconception_id, avoided, params, now) -> ReconcileResult` (чистая); `reconcile_task_answer` при `payload.mode == "chat"` даёт `source="chat", kind="task_in_chat"` (ярус 2, 0.8) и заполняет `context.instance_id` | наблюдатель и задачи в чате | B1; `weights._BASE_WEIGHTS` += `("task","chat",None): 0.8` для симметрии `tier_for` |
| F8 | `apply.tasks.issue(session, deps, student_id, req)` | `+ chat_id: UUID \| None = None` → `EventIn.chat_id`; также пишет `task_instances.issued_event_id` (колонка есть, не заполнялась) | окно наблюдателя и открытые задачи чата | B1; B3 роутер не меняется |
| F9 | `apply_task_answered`, `apply_dispute` без лока | оборачиваются в `apply._lock.student_lock(deps.redis, student_id)` (ожидание ≤ 5 с, при неудаче — продолжить с warning) | гонка «наблюдатель vs живой ответ на задачу» (read-modify-write состояния) | B1; поведение при доступном Redis не меняется |
| F10 | `events.store.list_unprocessed(session, chat_id, limit=50)` | `+ types: list[EventType] \| None = None`; новые `count_unprocessed(session, chat_id, types)`, `get_event(session, student_id, event_id)` | окно наблюдателя, триггер, `explain_belief` | B3 |
| F11 | `_session_minute` — приватная в `api/_answer.py` | `events.session.session_minute(session, student_id, session_id, now) -> int`; роутер использует её | строка сессии репетитора и контекст свидетельств наблюдателя считают минуту так же, как задачи | B3, B2, B1 |
| F12 | — | `db.repo.messages.get_message`, `list_by_event_ids`; `db.repo.tasks.list_open_chat_instances`; `db.repo.summaries.get_latest_text`; `db.repo.aggregates.add_pace_signal` | §3.12 | B3 |
| F13 | `api/matching.py` собирает подборку и сравнение внутри роутера | логика переносится в `apply/matching.py` (файл B3 внутри пакета `apply/` — исключение из владения, зафиксировать в шапке файла): `run_matching(session, deps, student_id, limit) -> MatchingOut`, `compare_programs(session, deps, student_id, program_ids) -> CompareOut`; роутер вызывает их | инструменты `run_matching`/`compare` обязаны давать те же числа, что `GET /matching` (шаг 4 жюри) | B3, B2 |
| F14 | `ToolCtx(student_id, deps, request_id)` | `+ chat: ChatCtx \| None = None`, `turn: TurnState = field(default_factory=TurnState)` | `chat_id`/`set_id` для `get_task`, счётчики на ход | B2; старые вызовы совместимы |
| F15 | `ToolRegistry` | `+ subset(names: list[str]) -> ToolRegistry` (новый реестр с теми же `ToolSpec`, флаг `read_only` наследуется) | политика доступа по стадиям | B2 |
| F16 | `run_tool_loop` ловит только `LLMUnavailable` | также `openai.APIError`, `httpx.HTTPError` → `StreamError(code="llm_unavailable")`; в `LoopEnd` добавляется `tool_calls: list[ToolCall]` (аргументы вызовов — для `referenced_skill_ids`) | провайдерские исключения пробрасываются клиентом как есть (тесты фазы 1), а поток не должен обрываться исключением | B2 |
| F17 | `postcheck.check_facts(text, tool_results)` | `+ scope="all"`, `extra_values=()`, `max_questions=None`; `PostcheckResult += questions: int` | §3.6 | B2 |
| F18 | `keys.py` | `+ matching_snapshot(student_id)`; имена локов §3.12 | §2.4 | B3 |
| F19 | `workers/registry.py` только `ping` | `INTERACTIVE` += `observe_chat`, `canonize_misconception` через `arq.func(...)` с таймаутами; `workers/main.py`: эмбеддер в `interactive`; `main.py`: `app.state.arq` | §3.12 | B3 |
| F20 | `_chat_id`: prep требует `set_id` и `topic_skill_id` | `set_id` без `topic_skill_id` → `uuid5(student_id, f"prep:{set_id}")` (чат сета); без `set_id` — по-прежнему 400 | чат сета (`backend-phases` §3.3) | B3, frontend (`GET /chat/prep/messages?set_id=` без топика) |
| F21 | `api/chat.py`: `message.*` через `store.append` с диспетчером по умолчанию | `dispatch_event=False`; лок чата; триггер; новые роуты `POST /chat/prep/observe`, `GET /chat/prep/observations` | §3.12 | B3, frontend (новые роуты) |
| F22 | промпты `selection_v3`, `tutor_v2` | `selection_v4.md` (плейсхолдеры `profile, stage, stage_rules, snapshot, knowledge, today`; форматы результатов инструментов словами; правило «числа только из инструмента этого хода», «≤ 2 вопросов»), `tutor_v3.md` (`learner_model`, `session`; правило «даты и требования не называю»), `canon_v1.md` (`a`, `b`) | версии промптов меняются вместе с описаниями инструментов | B2; `tests/agents/test_prompts_phase3.py` обновляется на v4/v3 |

### 5.3 Роуты (B3)

| Метод и путь | Тело → ответ | Что вызывает |
| :---- | :---- | :---- |
| `POST /chat/{kind}/messages` | без изменений; новые коды: 409 `conflict` (чат занят); кадр `error` с `postcheck_failed`; кадры `tool_call`/`tool_result` теперь реальные | лок, `run_chat`, триггер наблюдателя |
| `POST /chat/prep/observe` | `{set_id, topic_skill_id?}` → 202 `ObserveRequestedOut` | `observer.requested` + `enqueue(observe_chat, trigger=requested)`; 429 чаще раза в 10 с |
| `GET /chat/prep/observations` | `?set_id&topic_skill_id?&since_event_id` → `ObservationsDiffOut`, заголовок `X-Knowledge-Version` | события `observation.extracted`, `apply.knowledge.states_view`, `misconceptions_view` |
| `GET /prep/knowledge/version` | без изменений — polling фронта по tech-stack §2.4 | — |

### 5.4 Что НЕ меняется, хотя могло бы

`StreamEvent` (нет нового типа события для отзыва ответа — см. §9); `Done`; `LLMClient` (никаких второго клиента, обёрток или изменения обработки ошибок); `EventIn/Event`; `RuleDeps`, `dispatch`; `apply_task_answered` (кроме лока и `ordinal=1` у `misconception_hit`); `matching/*`, `sets/*`, `roadmap/*`; `messages`/`events` таблицы — **миграции в фазе 3 нет** (используются существующие колонки `issued_event_id`, `set_summaries`, `daily_aggregates.payload`).

---

## 6. Тесты

### 6.1 Стратегия

- Тесты пишутся **до кода** в отдельной сессии, PR `phase3-tests-<B>`, маркер `@pytest.mark.phase3` (добавить в `pyproject`), `xfail(strict=False)` до реализации — как в фазах 1–2.
- Три яруса: (1) чистые функции без I/O (`classify_mode`, `hint_level_for`, `render_learner_model`, `reconcile_chat_evidence`, `check_facts`, политика инструментов, стадии) — на числах и строках; (2) агенты, job'ы и правила на `FakeLLMClient` + `fakeredis` + `monkeypatch` репозиториев/графа (без БД) — проверяют выбор инструментов, аргументы, порядок вызовов, содержимое system prompt (`fake_llm.calls[i].messages`), SSE-последовательность, постпроверку, идемпотентность по ключам; (3) `integration` на живых Postgres + Neo4j (`db_session`, `seeded_graph`, `templates_db`) — сквозные: сообщение → окно → событие → граф → версия; повторная доставка события.
- Живой провайдер в автотестах не используется; ручной чек-лист `docs/tz/checklists/phase3-B2.md` по шагам 1–4 и 7 §9 (≥ 10 фрагментов наблюдателя).
- Общие фикстуры (B3 добавляет в `conftest.py`): `agent_deps(fake_llm, redis)` — `AgentDeps(llm=fake_llm, pg=<sessionmaker или AsyncMock>, graph=None|driver, redis=redis)`; `chat_ctx(kind, set_id, topic_skill_id)`; `profile_factory(**fields)`; `history_factory(pairs)`; `fake_graph` — объект с `AsyncMock` для функций `personal.*`/`canonical.*`/`kb.*` через `monkeypatch`; `observation_event(observations)` — `Event` типа `observation.extracted`; `arq_ctx(fake_llm, redis, sessionmaker, graph)`; `fake_enqueue` — шпион `workers.main.enqueue`.
- Фикстурные данные: `tests/fixtures/agents/` — 5 программ пола (уже есть в `tests/roadmap/fixtures`), мини-карта (`tests/fixtures/data/`), 3 фрагмента чата подготовки с ожидаемыми наблюдениями (для тестов job'а), скрипты `FakeLLMClient` в помощниках `tests/agents/_scripts.py`.

### 6.2 Обозначения

`FL[...]` — скрипт `FakeLLMClient` (по одному элементу на вызов `stream`/`structured`); `TC(name, args)` — `tool_call_turn`; `TXT(s)` — `text_turn(s)`; `S(model)` — `BaseModel` для `structured`.

### 6.3 `tests/agents/test_router.py` (B2) и `test_selection.py` (B2)

| Тест | Given → When → Then |
| :---- | :---- |
| `router_selection_branch` | история из 2 сообщений, `FL[TXT("ок")]` → `run_chat("selection")` → `calls[0].messages[0].role=="system"`, `messages[1..2]` — история, последнее — `user` с текущим текстом; `Done.mode` в множестве стадий |
| `router_prep_branch_uses_tutor` | `kind="prep"`, `monkeypatch apply.context.get_topic_context → TopicContext(...)` → system prompt содержит `<learner_model` и `<session` |
| `router_drops_duplicate_current_message` | история заканчивается `user:"привет"`, `message.text=="привет"` → модель видит ровно один `user:"привет"` в конце |
| `router_history_window` | 15 сообщений в репозитории, `chat_window=10` → модели ушло 10 (+ system) |
| `router_llm_unavailable_before_first_event_is_raised` | `FL[LLMUnavailable]` → `pytest.raises(LLMUnavailable)`; `FL[TC("update_profile"), LLMUnavailable]` → события `ToolCall, ToolResult, StreamError(llm_unavailable)` |
| `stage_opening_when_no_assistant_messages` | пустая история → `_stage()=="opening"`; system prompt содержит `stage: opening`; `run_matching` отсутствует в `calls[0].tools` |
| `stage_intake_and_missing_fields_order` | профиль только с `level.grade`, readiness 0.1 → `stage=="intake"`, строка `missing:` начинается с `direction.field, preferences.budget_per_year` |
| `stage_summary_at_threshold` | readiness 0.65, снимка нет, предыдущая стадия `intake` → `summary`; `run_matching` в `tools` есть, `compare/save_program` — нет |
| `stage_matching_after_summary` | последний `assistant` с `markup.mode=="summary"` → `matching`; все 8 инструментов в `tools` |
| `stage_refine_when_snapshot_exists` | снимок в Redis → `refine` |
| `wants_matching_regex_allows_run_matching_in_intake` | `intake`, текст «просто покажи варианты» → `run_matching` в `tools` |
| `known_fields_are_in_prompt_not_reasked` | профиль с `preferences.budget_per_year=5000 (stated)` → system prompt содержит `preferences.budget_per_year: 5000 (сказал)` и не содержит его в `missing` |
| `tool_call_order_update_then_matching` | `FL[TC("update_profile",{path:"preferences.budget_per_year",value:5000}), TC("run_matching",{limit:5}), TXT("Вот пять программ")]`, тела инструментов замоканы → события `ToolCall(update_profile), ToolResult, ToolCall(run_matching), ToolResult, TextDelta, Done(mode="matching")`; `fake_llm.tool_messages()` содержит два `role=tool` с `call_id` в порядке |
| `update_profile_forces_by_assistant` | модель передала `by:"user"` → репозиторий вызван с `by="assistant"` |
| `update_profile_unchanged_writes_no_event` | текущее значение равно → результат `unchanged=True`, `store.append` не вызван |
| `update_profile_returns_shift` | снимок `[A: try]`, после правки `run_matching` даёт `[A: possible]` → `shift == [ShiftOut(A, try→possible)]` |
| `run_matching_writes_snapshot_and_count` | результат содержит `count==len(items)`, `total`; Redis-ключ `matching_snapshot` записан |
| `save_program_twice_conflict` | второй вызов → `ToolResult.error` содержит `already saved`; событие `program.saved` записано один раз |
| `save_program_dispatches_rebuild` | шпион `on_program_change` вызван (через `dispatch`) |
| `query_dataset_aggregates` | 5 программ фикстуры, `country="DE"` → `count`, `tuition.min/median/max`, `free_count`, `sources` ≤ 15; `question` только в эхо |
| `get_admission_route_graph_down` | `deps.graph=None` → `ToolResult.error=="knowledge base unavailable"` |
| `tool_denied_unknown_name` | `FL[TC("delete_everything"), TXT("…")]` → `ToolResult(error)`, `TextDelta`, `Done` |
| `tool_validation_error_is_result_not_exception` | `TC("compare",{program_ids:["only-one"]})` → `ToolResult.error` содержит `2 to 4` |
| `assistant_markup_mode_is_stage` | → `Done.mode=="refine"` при снимке; `gave_task_instance_id is None` |

### 6.4 `tests/agents/test_tutor.py` (B2)

| Тест | Given → When → Then |
| :---- | :---- |
| `classify_mode_review_on_solution` | `"2x−6=4, x=5"` → `review`; `"почему модуль раскрывается на две ветви?"` → `explain`; пустая строка → `explain` |
| `hint_level_base_from_profile` | `hint_level=minimal` → 1; `generous` → 3; отсутствует → 2 |
| `hint_level_escalates_after_two_failures` | base 2, `consecutive_failures=2` → 3; `=1` → 2 |
| `render_learner_model_order_and_empty_slots` | `TopicContext(strengths=["a"], …)` → строки в порядке `topic, strengths, prerequisite_gaps, active_misconceptions, under_watch, low_data, deadline, profile, previous_set`; пустые как `[]`; заголовок содержит `topic=`, `set=`, `as_of=` |
| `system_prompt_contains_context_and_session` | `get_topic_context` → фикстурный контекст; → `calls[0].messages[0].content` содержит `<learner_model` и `<session minute="12" mode="review" hint_level="2"` |
| `context_none_gives_empty_block` | `get_topic_context → None` → в промпте `{{learner_model}}` заменён пустой строкой, нет `KeyError`, ход завершается `Done` |
| `get_task_writes_task_issued_with_chat_id` | `FL[TC("get_task",{skill_id: topic}), TXT("Реши…")]`, `apply.tasks.issue` — шпион → вызван с `chat_id==ctx.chat_id`, `TaskRequestIn.mode=="chat"`; `Done.mode=="task"`, `gave_task_instance_id==<id>`, `referenced_skill_ids==[topic]` |
| `get_task_result_has_no_answer` | результат `GetTaskResult.task.options` — только `key,text`; нет полей `answer`, `correct`, `misconception_id` |
| `get_task_second_call_denied` | два `TC("get_task")` в одном шаге → второй `ToolResult.error=="one task per turn"`, `issue` вызван один раз |
| `get_task_outside_topic_denied` | `skill_id` не из `TopicContext.skill_ids` → `error=="skill outside topic"` |
| `explain_belief_maps_evidence_to_task_and_message` | `apply.knowledge.explain` → 2 `EvidenceOut` (`instance_id`, `message_id`); репозитории замоканы → `items[0].task.stem`, `items[0].task.student_answer` из `payload.answer` события; `items[1].message.text_fragment` |
| `tutor_registry_stays_read_only` | `TUTOR_TOOLS.register(save_program)` → `ValueError` (регрессия фазы 1) |
| `referenced_skill_ids_from_tool_calls` | `explain_belief(skill_id=X)` → `Done.referenced_skill_ids==[topic, X]` |
| `postcheck_exam_facts_in_tutor` | `FL[TXT("В модуле 22 задания")]` без инструментов → `StreamError(postcheck_failed)`; `FL[TC("get_exam_format"), TXT("В модуле 22 задания")]` с результатом `n_items=22` → `Done` |
| `math_numbers_pass_in_tutor` | `FL[TXT("x = 5 или x = 1")]` → `Done` (числа без маркеров не проверяются) |

### 6.5 `tests/agents/test_postcheck.py` (B2, дополнение к фазе 1)

| Тест | Given → When → Then |
| :---- | :---- |
| `phase1_calls_unchanged` | старые 6 тестов фазы 1 без изменений |
| `extra_values_from_profile_pass` | текст «бюджет 5000», `tool_results=[]`, `extra_values=[5000]` → `ok` |
| `history_numbers_not_authoritative` | текст «1 500 CHF», результатов нет, `extra_values` без 1500 → не ok |
| `scope_exam_facts_keyword_sentences_only` | «В секции 22 задания, а x = 3» → проверяется только 22 |
| `scope_exam_facts_dates_and_percents_always` | «подача до 15 декабря» / «ты знаешь на 55%» → не ok без результатов |
| `max_questions` | «Что? Где? Когда?» с `max_questions=2` → `ok=False`, `questions==3`, `"questions>2"` в `mismatches` |
| `percent_matches_fraction` | «85%» против `{"coverage": 0.85}` → ok |
| `error_results_give_no_values` | `ToolResult(error="…", data=None)` + число в тексте → не ok |

### 6.6 `tests/graph/test_context.py` (B1; unit с `monkeypatch` запросов + `integration` на `seeded_graph`)

| Тест | Given → When → Then |
| :---- | :---- |
| `four_queries_run_in_parallel_once` | четыре Q-функции — `AsyncMock` → `build_topic_context` → каждая вызвана ровно один раз; `gather` (проверка через порядок старта/`asyncio.Event`) |
| `slots_limits_and_thresholds` | slice: topic `p=0.55,conf=0.8`; A `p=0.88,conf=0.9`; B `p=0.82,conf=0.7`; C `p=0.93,conf=0.6`; D `p=0.42,conf=0.6` + корень; E `conf=0.1` → `strengths==[A,B]` (лимит 2, C отсечён), `prerequisite_gaps==[D…(корень…)]`, `low_data==[E: мало данных]`, `topic` содержит `p=0.55 conf=0.80 trend=` |
| `misconceptions_visibility` | состояния: confirmed (occ 3), suspected, resolved 3 дня, resolved 20 дней, disputed → `active_misconceptions` — только confirmed с «подтверждено, 3 набл.»; `under_watch` — resolved 3 дня; остальных нет |
| `trigger_words_in_active` | `triggers.n=4, hurried=(3,4)` → строка содержит «обычно — когда торопится» |
| `set_multiplier` | `topic_skill_id=None`, `context_set_multiplier=1.5` → `strengths` до 3, `prerequisite_gaps` до 5 |
| `cache_hit_on_same_version` | Redis-ключ с `version==get()` и тем же `set_id` → Q-функции не вызваны, `cache=="hit"`; версия `bump` → вызваны, `cache=="miss"`, ключ перезаписан |
| `cache_corrupted_is_miss` | ключ с мусором → пересборка, без исключения |
| `budget_truncation` | `context_budget_tokens=50` → суммарно ≤ 150 символов, `previous_set` пустой первым |
| `apply_get_topic_context_foreign_set_is_none` | `repo.sets.get_set → None` → `None`; `deps.graph=None` → `None` |
| `integration_context_from_seeded_graph` | `seeded_graph` + два `task.answered` → `topic` слот с реальными `p/conf`, `deadline` из фикстурного календаря |

### 6.7 `tests/agents/test_observer.py` (B2)

| Тест | Given → When → Then |
| :---- | :---- |
| `prompt_renders_window_with_event_ids` | окно из 3 сообщений и 1 задачи → `calls[0].messages[0].content` содержит `[event_id=4420] ученик:` и `instance_id`, не содержит `answer_forms`/ключа |
| `structured_called_with_slot_and_schema` | `FL[S(ObservationOut(...))]` → `calls[0].method=="structured"`, `slot=="bulk"`, результат `raw_count` |
| `invalid_then_valid_uses_builtin_retry` | `FL['{"observations": [{"kind": "solution_step"}]}', S(valid)]` → один вызов `run`, `calls` длиной 2, второй содержит сообщение о валидации |
| `two_invalid_raise_llm_unavailable` | `FL['bad','bad']` → `LLMUnavailable("structured output failed")` |
| `example_from_memory_architecture_validates` | пример §8.1 (10 наблюдений) → `ObservationOut` без правок (регрессия) |

### 6.8 `tests/agents/test_jobs_observe.py` (B2; `fakeredis`, репозитории и граф — `monkeypatch`; `integration` — на живых БД)

| Тест | Given → When → Then |
| :---- | :---- |
| `window_selects_unprocessed_messages_only` | 8 событий чата: 6 `message.*` (2 с `processed_at`), 1 `task.issued`, 1 `observer.requested` → окно из 4 сообщений + задача; `source_event_ids` — их id |
| `window_max_and_requeue` | 40 необработанных сообщений, `observer_window_max=30`, `observer_every_n=6` → обработано 30; `fake_enqueue` вызван с `_job_id=="observe:<chat_id>"` |
| `empty_window_no_event` | нет необработанных, `trigger="every_n"` → `store.append` не вызван |
| `empty_window_requested_writes_empty_event` | `trigger="requested"` → событие с `observations==[]`, `source_event_ids==[]` |
| `event_written_with_extractor_version_and_sources` | → `EventIn.type==observation_extracted`, `extractor_version=="observer_v1"`, `payload.observations` равны выходу модели целиком (включая `confidence<0.7`), `mark_processed` вызван с id окна |
| `dispatch_result_used_for_canonization_enqueue` | `apply_observation_extracted` замокан → `pending_canonizations=[2]` → `fake_enqueue("canonize_misconception", _job_id="canon:<event_id>:2")` |
| `lock_skips_second_run` | лок занят → `run` не вызван, лог `skipped=locked` |
| `transient_error_retries` | `FL[openai.APITimeoutError]`, `job_try=1` → `pytest.raises(arq.Retry)`; `job_try=3` → событие `job.failed{reason}`; окно не помечено |
| `invalid_structured_no_retry` | `FL['bad','bad']` → `job.failed{reason=="invalid_structured_output"}`, без `Retry` |
| `forced_down_fails_without_retry` | `fake_llm.forced_status="down"` и `FL[LLMUnavailable("llm unavailable (forced down)")]` → `job.failed{llm_down}` |
| `graph_none_retries_then_fails` | `ctx["neo4j"]=None` → `Retry`; на третьей попытке `job.failed` |
| `integration_end_to_end` | живые БД: `POST /chat/prep/messages` ×6 (эхо-скрипт) → триггер → job с `FL[S(ObservationOut(solution_step incorrect + misconception))]` → в графе `Evidence{event_id, skill_id, ordinal=0}` с `extractor_version`, новый `KnowledgeState` с `PREVIOUS`, `MisconceptionState.suspected`; `GET /prep/knowledge/version` вырос; `GET /chat/prep/observations?since_event_id=` → `status=="done"`, `observations[0].message_ids` непусто |

### 6.9 `tests/apply/test_observation.py` (B1; unit с фейковым графом + `integration`)

| Тест | Given → When → Then |
| :---- | :---- |
| `confidence_filter` | наблюдения с `confidence` 0.69 и 0.7, `observer_min_confidence=0.7` → первое `skipped(low_confidence)`, второе применено |
| `referential_filters` | `skill_id` вне среза / `misconception_id` неизвестен / `event_ids` вне окна / `root_skill_id` вне среза → соответствующие `skipped(reason)`; исключений нет |
| `solution_step_incorrect_with_misconception` | состояние `p=0.6,h=48`, заблуждения нет → `Evidence(tier=2, weight=0.7, direction=-1)`, `h` уменьшился по `beta`, `MisconceptionState` создано `suspected`, `occurrence_count=1`, `strong_count=1` |
| `second_hit_confirms_only_with_strong` | суть §5.1: `suspected` с `occurrence=1, strong=0` + `solution_step` (ярус 2) → `confirmed`; + `confusion` (ярус 3, без `misconception_id`) → статус не меняется |
| `tier3_capped_by_p_chat_cap` | `applied` при `p=0.78` → `p_at_obs ≤ p_chat_cap (0.8)`, `has_strong` остаётся `False` |
| `avoided_trap_increments_consecutive` | `confirmed` с `consecutive_avoided=2` + `avoided_trap` → `3` → `resolved` |
| `avoided_trap_without_state_skipped` | нет `MisconceptionState` → `skipped(no_misconception_state)` |
| `root_hint_links_latest_incorrect` | в этом событии есть `solution_step incorrect` по X → `add_root_cause(evidence_id этого свидетельства, Y, 0.6, "observer")`; без него — `latest_incorrect_evidence` |
| `task_in_chat_appends_task_answered_once` | открытая задача чата, `answer="A"` → `store.append(task_answered, mode="chat", hint_level_before из разметки, source_event_ids=[event.id])` с `dispatch_event=True`; повторный `dispatch` → `skipped(already_answered)` |
| `task_in_chat_weight_is_chat_tier2` | `reconcile_task_answer(payload.mode="chat")` → `evidence[0].source=="chat"`, `kind=="task_in_chat"`, `tier==2`, `weight==0.8`, `context.instance_id` заполнен |
| `two_observations_same_skill_get_ordinals` | два `solution_step` по одному навыку → два `Evidence` с `ordinal` 0 и 1; состояние обновлено дважды |
| `idempotent_redelivery` | после применения — тот же `Event` снова → `applied==0`, все `already_applied`, `bump` не вызван, число `KnowledgeState` не выросло |
| `partial_failure_resumes` | граф падает после первого наблюдения (мок) → `GraphUnavailable`; повторная доставка → первое `already_applied`, второе применено |
| `proposed_misconception_pending` | → `pending_canonizations==[ordinal]`, ничего не записано по нему |
| `pace_signal_to_aggregates` | → `repo.aggregates.add_pace_signal` вызван; повторно — без дубля |
| `version_bump_and_cache_invalidation` | применено ≥ 1 → `bump` один раз, `DEL ctx_topic` для топика и сета; `applied==0` → не вызваны |
| `student_lock_taken_and_released` | `redis` содержит `quack:lock:knowledge:<sid>` во время цикла, снят после |
| `merge_evidence_ordinal_key_integration` | `seeded_graph`: `merge_evidence` дважды с одинаковым `(event_id, skill_id, ordinal)` → один узел; с `ordinal` 0 и 1 → два; контекст (`ctx_message_id`) читается через `list_evidence` |

### 6.10 `tests/agents/test_jobs_canonize.py` (B2) и `tests/apply/test_canonized.py` (B1)

| Тест | Given → When → Then |
| :---- | :---- |
| `merge_above_threshold` | `search_misconceptions → [(lib.x, 0.95)]` → событие `misconception.canonized{canonical_id=lib.x, decided_by=threshold}`; `structured` не вызван |
| `adjudicate_in_grey_zone_yes` | `sim=0.85`, `FL[S(CanonDecision(same=True))]` → `canonized{decided_by=model}` |
| `adjudicate_no_creates_personal` | `sim=0.85`, `same=False` → `misconception.personal_created{misconception_id startswith "pers.", embedding len 384}` |
| `below_threshold_creates` | `sim=0.5` / нет кандидатов → `personal_created` |
| `adjudication_failed_no_node` | `FL['bad','bad']` → `job.failed{adjudication_failed}`, событий нет |
| `embedder_missing` | `ctx["embedder"]=None` → `job.failed{embedder_unavailable}` без `Retry` |
| `idempotent_by_prior_result` | уже есть `canonized` с тем же `source_event_id/ordinal` → выход без событий |
| `apply_canonized_creates_evidence_and_state` | правило → `Evidence(kind=misconception_hit, tier 2, direction −1)`, `MisconceptionState.suspected`; повторный `dispatch` → без дублей |
| `apply_personal_created_merges_node` | → `create_personal_misconception` MERGE по id, `ABOUT` навык; повтор → один узел |

### 6.11 `tests/api/test_chat_phase3.py`, `test_sets_phase3.py`, `tests/events/test_store_phase3.py`, `tests/workers/test_registry.py` (B3)

| Тест | Given → When → Then |
| :---- | :---- |
| `sse_tool_call_and_result_frames` | агент замокан на `[ToolCall, ToolResult, TextDelta, Done]` → кадры в порядке, `done.event_id` = id записанного `message.assistant`, `tool_result` не в `messages` |
| `postcheck_failed_not_persisted` | агент → `[TextDelta, StreamError(postcheck_failed)]` → последний кадр `error`, `messages` без ответа, `message.assistant` не записано |
| `message_events_not_dispatched` | `store.append` — шпион → вызван с `dispatch_event=False` для `message.user`/`message.assistant`; `processed_at IS NULL` |
| `chat_lock_conflict` | лок занят → 409, `message.user` не записано; после ответа лок снят |
| `observer_trigger_every_n` | `observer_every_n=6`; 5 сообщений → `enqueue` не вызван; 6-е → вызван с `_job_id="observe:<chat_id>"`, `trigger="every_n"` |
| `observe_endpoint_202_and_rate_limit` | `POST /chat/prep/observe` → 202 с `since_event_id`, событие `observer.requested`, `enqueue(trigger=requested)`; второй в течение 10 с → 429 |
| `observations_diff_pending_done_failed` | нет событий после `since` → `pending`; событие с наблюдениями → `done` с `message_ids`, `skills` по навыкам; `job.failed` без наблюдений → `failed` |
| `observations_diff_foreign_set_404` | чужой `set_id` → 404 |
| `set_chat_id_without_topic` | `POST /chat/prep/messages {set_id}` → 200, `chat_id==uuid5(sid, f"prep:{set_id}")` |
| `topic_completed_enqueues_and_invalidates` | `POST /sets/{id}/topics/{skill}/complete` → `enqueue(trigger=topic_completed)`, ключи `ctx_topic` удалены |
| `set_completed_enqueues_each_topic_chat` | последний топик → `enqueue` для чатов с необработанными сообщениями |
| `store_list_unprocessed_types_and_count` | `types=[message_user]` фильтрует; `count_unprocessed` считает; `get_event` чужого ученика → `None` |
| `registry_interactive_functions_and_timeouts` | `INTERACTIVE` содержит `observe_chat` с `timeout==OBSERVER_JOB_TIMEOUT_S`, `canonize_misconception` с `CANON_JOB_TIMEOUT_S`, `max_tries==3`; `BULK` — только `ping` |
| `worker_startup_loads_embedder_or_none` | `Embedder` замокан на исключение → `ctx["embedder"] is None`, startup не падает |
| `payload_models_registered` | `store._validated_payload` для `observation.extracted`/`job.failed`/`misconception.canonized` валидирует по моделям (лишнее поле → `ValidationError`) |
| `layers` | `apply/` не импортирует `arq`, `app.agents`, `app.llm`; `agents/` не импортирует `app.api` |

### 6.12 Concurrency (B1/B2)

| Тест | Given → When → Then |
| :---- | :---- |
| `parallel_turns_same_chat_second_409` | два одновременных `POST` одного чата (тест API с `asyncio.gather`) → один 200 + поток, один 409 |
| `observer_and_task_answer_serialized` | `apply_observation` держит `student_lock`; параллельный `apply_task_answered` ждёт (`fakeredis`, проверка порядка записей в граф-мок) |
| `student_lock_timeout_does_not_block` | лок не освобождается 6 с → второй захват возвращает `got=False`, обработка продолжается, warning |
| `context_cache_double_build_consistent` | два одновременных `build_topic_context` → два одинаковых значения ключа, без исключений |

### 6.13 Ручной чек-лист `docs/tz/checklists/phase3-B2.md` (живой провайдер)

1. Шаг 1 §9: свободный текст → `update_profile` ≥ 3 полей с `assumed`, ≤ 2 вопросов, известное не переспрошено (3 прогона).
2. Шаг 2: «какая страна подходит, если…» → `query_dataset`, числа в ответе совпадают с `tool_result`, интерпретация черты проговорена и записана (`traits.summary` изменился).
3. Шаг 3: резюме из четырёх блоков + допущения; после подтверждения — `run_matching`, карточки в `tool_result`, ≥ 3 программ, ни одного процента.
4. Шаг 4: «бюджет теперь 5000» → `update_profile.shift` непуст и назван в тексте; тот же порядок, что `GET /matching`.
5. Шаг 7: топик с `confirmed`-заблуждением из замера → ответ в режиме «разбираю» учитывает его; через ≤ 15 с `GET /chat/prep/observations` → `done`, наблюдения раскрываются до `message_ids`.
6. Постпроверка: спровоцировать дату в ответе репетитора → кадр `error postcheck_failed`, истории нет.
7. Наблюдатель на ≥ 10 фрагментах: доля валидного JSON с первого раза, precision/recall по `(kind, skill)` вручную; время job'а.
8. `LLM_FORCE_DOWN=1`: чаты → 503; кнопка → `failed`; `GET /matching`, задачи, сеты — работают.

---

## 7. Acceptance Criteria — фаза 3 закрыта, когда

Соответствие шагам §9 `product-logic`: 1, 2, 3, 4 (через чат), 7.

- [ ] **Шаг 1.** На чистом профиле `POST /chat/selection/messages` с текстом «хочу на IT, куда-нибудь в Европу, SAT не сдавал, люблю тепло» даёт в потоке `tool_call update_profile` ≥ 3 раза (в т. ч. `traits.verbatim`/`traits.summary`), текст с ≤ 2 вопросами; `GET /profile` показывает поля с `mark="assumed"`, `traits.verbatim` дословно, `traits.summary` непустое. Повторная реплика с уже сказанным — известное не переспрашивается (проверено чек-листом на 3 прогонах).
- [ ] **Шаг 2.** Вопрос по данным → `tool_call query_dataset`; все числа текста есть в `tool_result.data`; `sources` в результате; черта интерпретирована и записана (`traits.summary` изменился через `update_profile`).
- [ ] **Шаг 3.** При `readiness ≥ assistant_readiness_threshold` ответ — резюме из четырёх блоков с допущениями (`Done.mode=="summary"`); следующий ход → `run_matching` с `count ≥ min_candidates`, `MatchCard.realism` только словами, ни одного `%` в тексте (постпроверка режет проценты без источника).
- [ ] **Шаг 4.** «бюджет теперь 5000» → `update_profile` с `shift` непустым, текст называет сдвиг; `GET /matching` сразу после даёт тот же порядок и те же `realism`, что `tool_result run_matching` (общая `apply.matching`). Ручной `PATCH /profile` даёт тот же результат, что реплика.
- [ ] **Шаг 7.** В чате топика с `confirmed`-заблуждением ответ в режиме `review` использует контекст (`<learner_model>` содержит его; `Done.mode=="review"`); после `observer_every_n` сообщений или кнопки `POST /chat/prep/observe` в течение ≤ 15 с `GET /chat/prep/observations?since_event_id=` → `status=="done"`, наблюдения с `message_ids`, `GET /prep/knowledge/version` вырос, `GET /knowledge` показывает `n_evidence` +1 по навыку, `GET /knowledge/explain/{skill}` содержит `message_id`.
- [ ] **Постпроверка.** Число/дата без источника в результатах инструментов → последний кадр `error{code=postcheck_failed}`, ответ отсутствует в `GET /chat/{kind}/messages`; > 2 вопросов у подбора — то же.
- [ ] **SSE.** Кадры `tool_call`/`tool_result`/`done` реальные: `tool_result.data` валидируется моделями `app/schemas/agents.py`; `done.event_id` — id `message.assistant`; `done` несёт настоящую разметку.
- [ ] **Наблюдатель.** `observation.extracted` записан с `extractor_version="observer_v1"`, `source_event_ids` = окно, payload = выход модели целиком; окно помечено `processed_at`; `job.failed` пишется после 3-й попытки на транзиентной ошибке и сразу — на невалидном structured; кнопка при пустом окне → `done` с пустым списком.
- [ ] **Идемпотентность.** Повторный `dispatch` того же `observation.extracted` не создаёт `Evidence`/`KnowledgeState`/`task.answered`, версия не растёт (интеграционный тест зелёный). Повторный `enqueue` с тем же `job_id` не запускает второй job.
- [ ] **Канонизация.** `proposed_misconception` → job → `misconception.canonized` или `misconception.personal_created` → правило → `MisconceptionState` и `Evidence`; узел `Misconception{scope:'personal'}` с `embedding` в индексе `misc_emb`.
- [ ] **Контекст.** `build_topic_context` выполняет 4 запроса параллельно, повторный вызов при той же версии — из кэша; `bump` инвалидирует; лимиты слотов и пороги по таблице §3.7.
- [ ] **Правила слоёв.** `tests/test_layers.py` зелёный с расширениями (`apply/` без `arq`, `agents/` без `app.api`); `TUTOR_TOOLS` отвергает пишущий инструмент; второго LLM-клиента нет (`grep "AsyncOpenAI("` — только `app/llm/client.py`).
- [ ] **Тесты.** `make test` зелёный (`phase1`+`phase2`+`phase3`), `make test-int` зелёный включая `integration_end_to_end` и `merge_evidence_ordinal_key_integration`; `tests/agents/test_prompts_phase3.py` обновлён (v4/v3).
- [ ] **Данные/документы.** `memory-architecture-quack.md` §12 и §1.2 дописаны (параметры C11, тип C4); `docs/decisions/llm-provider.md` — расход фазы 3; `docs/tz/checklists/phase3-B2.md` заполнен по 8 пунктам (≥ 10 фрагментов наблюдателя); `schema.d.ts` перегенерирован; `.env.example` — новые переменные.
- [ ] **Отказы.** `LLM_FORCE_DOWN=1`: оба чата 503, кнопка → `failed`, всё из фазы 2 без изменений (прогон `test_e2e_rules` с флагом).

---

## 8. Порядок работ и точки стыка

Порядок мержа фазы (как в `backend-phases` §7): **B3 (скелет) → B1 (контекст, правило, запросы) → B2 (агенты, job'ы)**. Правила должны быть зелёными до того, как агенты начнут их вызывать.

| Шаг | Кто | Что | Кто ждёт |
| :---- | :---- | :---- | :---- |
| 0 | все | подписать §5, `sync-log` | — |
| 1 | B3 | скелет `phase3-skeleton`: `schemas/observer.py`, `schemas/agents.py`, payload-модели и `EventType`, `KnowledgeParams`/`Settings`, `keys`, `store.list_unprocessed(types)/count_unprocessed/get_event`, `events.session.session_minute`, репозитории F12, `apply/matching.py` (перенос из роутера), стабы `apply/observation.py`, `apply/context.py`, `graph/queries/context.py` с сигнатурами и `NotImplementedError("phase 3")`, `handlers.py` строки, реестр воркеров, `app.state.arq`, эмбеддер в воркере, фикстуры §6.1, `phase3` маркер, `test_layers` расширение | B1, B2 |
| 2 | B1 | `merge_evidence` (ordinal + контекст), `reconcile_chat_evidence`, `weights` chat-task, `apply.tasks.issue(chat_id, issued_event_id)`, `student_lock`, `graph/queries/context.py`, `build_topic_context` + кэш, `apply.context`, `apply.observation`, `search/create_personal_misconception`, обработчики канонизации | B2 |
| 3 | B2 (параллельно шагу 2) | тесты `phase3-tests-B2`; `postcheck` расширение; `ToolRegistry.subset`, `ToolCtx` поля, `run_tool_loop` ошибки/`tool_calls`; промпты v4/v3/canon; `router`; `selection.run` + инструменты (на `apply.matching` B3, репозиториях B3; `get_admission_route/get_exam_format` на B1 фазы 1); `tutor.run` + инструменты (ждёт `apply.context` и `explain` с `message_id`); `observer.run`; `jobs.observe_chat` (ждёт `apply.observation`), `jobs.canonize_misconception` (ждёт `search_misconceptions`) | — |
| 4 | B3 | транспорт: лок, `dispatch_event=False`, триггер, `/chat/prep/observe`, `/chat/prep/observations`, чат сета, роутер сетов; интеграционный прогон `integration_end_to_end` | — |
| 5 | B2 | ручной чек-лист на живом провайдере, расход в `llm-provider.md` | — |
| 6 | B3 | `make test && make test-int` на `main`, `make types`, graphify | — |

Точки стыка (сигнатуры — §5): B2 → B1: `apply.context.get_topic_context`, `apply.knowledge.explain`, `apply.tasks.issue(chat_id)`, `apply.observation.apply_observation_extracted` (через `dispatch`), `canonical.search_misconceptions`, `get_prerequisites`, `list_exam_skills`, `list_misconceptions_for_skill`, `get_misc_states`, `get_states`. B2 → B3: `apply.matching.run_matching/compare_programs`, `store.list_unprocessed(types)/count_unprocessed/get_event/append`, `repo.messages.get_message/list_by_event_ids`, `repo.tasks.list_open_chat_instances/list_instances`, `repo.summaries.get_latest_text`, `repo.aggregates.add_pace_signal`, `repo.profiles`, `repo.programs`, `repo.forecast`, `keys.matching_snapshot`, `workers.main.enqueue`. B3 → B2: `agents.router.run_chat` (без изменений), `agents.jobs.observe_chat/canonize_misconception` (реестр), `agents.selection._wants_matching` не нужен B3. B1 → B3: `events.version.bump`, `repo.sets.get_set`, `repo.tasks.*`, `events.store.append` (для `task.answered` из правила).

---

## 9. Финальный review (senior backend architect + QA) — найденные проблемы и уточнения

Проверено по вопросам: реализуемость без догадок, слои, «модель не пишет в граф», необработанные ошибки, идемпотентность, concurrency, дублирование LLM-инфраструктуры, согласованность контрактов B1/B2/B3, тестируемость критических сценариев. Ниже — только то, что требует решения или внимания.

**Проблемы в существующем коде, которые фаза 3 вынуждена исправить (не её функциональность, но без них компоненты фазы не работают):**
1. `merge_evidence` не пишет контекст — `list_evidence` всегда отдаёт `instance_id=None, message_id=None`; `explain_belief` и раскрытие «до сообщения» невозможны без F5/C6. Заодно исправляется схлопывание `misconception_hit` с основным свидетельством одного события (один MERGE-ключ).
2. Идемпотентность `apply_task_answered` из фазы 2 фактически не обеспечена: `upsert_state` всегда создаёт новый узел, повторный `dispatch` удвоит счётчики. Для наблюдений это закрыто ключами `(event_id, skill_id, ordinal)` и предварительной выборкой; для `task.answered` — вне фазы, но тест фазы 2 «повторный dispatch — те же счётчики» стоит перепроверить (вероятно, он не покрывает состояние).
3. `message.*` события не помечаются `processed_at` только потому, что транспорт передаёт `deps=None` (`graph=None`). Явный `dispatch_event=False` (F21) обязателен, иначе первый же рефакторинг транспорта «съест» окно наблюдателя.
4. `apply.tasks.issue` пишет `task.issued` с `chat_id=None` и не заполняет `issued_event_id` — окно наблюдателя не увидит задачу репетитора (F8).
5. `weights._BASE_WEIGHTS` не содержит `("task","chat",None)` — ответ на задачу из чата получил бы вес 0 (F7).
6. В API нет `ArqRedis` — постановка job из транспорта невозможна без `app.state.arq` (F19).
7. `WorkerInteractive.job_timeout=30` при `LLM_TIMEOUT_BULK_S=90`: наблюдатель на `bulk` не уложится; введены пер-функциональные таймауты (F19) и `OBSERVER_JOB_TIMEOUT_S`.

**Архитектурные решения, принятые в этом ТЗ, которые нужно подтвердить на синке:**
8. **Постпроверка без повторной генерации.** Текст уже ушёл потоком; при провале — `error{postcheck_failed}` и ответ не сохраняется, клиент убирает черновик. Альтернативы (буферизация последнего шага; новый тип события «отзыв + перегенерация») отвергнуты как изменение контракта `StreamEvent` и +10–15 с латентности. Риск на демо: отозванный ответ виден жюри как ошибка. Нужно решение: оставить или ввести тип `retract` в `StreamEvent` (влияние на фронт, который SSE ещё не потребляет — самый дешёвый момент).
9. **Постпроверка репетитора в области «факты об экзамене»** (ключевые слова + все даты и проценты). Математические числа не проверяются — иначе репетитор неработоспособен. Список маркеров — в коде, тесты — на нём; это эвристика, а не гарантия.
10. **`last_event_id` кэша контекста реализован через `knowledge_version`**, а не через реальный id события. Семантически совпадает (единственная точка инкремента), но `topic.completed` версию не меняет — добавлена явная инвалидация в роутере сетов. Проверить, что все пути, меняющие сеты (`switch`, `PATCH deadline`), проходят через `rebuild_sets` с `bump` — иначе слот «в сете i из n» устареет до TTL.
11. **Наблюдатель на слоте `bulk` (DeepSeek V4 Pro, `reasoning=high`)**: «модель обновлена через несколько секунд» из §3.2 `backend-phases` при 30–60 с ответа не выполняется. Введён `OBSERVER_SLOT`; рекомендуется измерить в чек-листе и, при > 15 с, либо `LLM_REASONING_BULK=low` для job'ов, либо `OBSERVER_SLOT=chat` (тогда наблюдатель делит `LLM_RPM_CHAT` с живым чатом — поднять лимит). Решение — по данным чек-листа п. 7.
12. **Задача из чата без ключа у репетитора** (§3.5): ключ в `tool_result` ушёл бы клиенту. Репетитор проверяет ответ ученика собственным решением; авторитетная оценка — только через наблюдателя (`task_in_chat`) и правило. Если это неприемлемо для демо шага 7 — нужен второй канал результата инструмента (только модели), что меняет `run_tool_loop` и `ToolResult`.
13. **Стадия ассистента хранится в `AssistantMarkup.mode`** (соглашение C8) — без новых таблиц; альтернатива (отдельная колонка/Redis) отвергнута. Фронт может это игнорировать.
14. **`ownership` `apply/matching.py`** — файл B3 в пакете B1: единственное исключение, ради одной реализации подборки для роутера и инструмента.
15. **Лок `student_lock`** добавляется в `apply_task_answered`/`apply_dispute` фазы 2 (F9). Без него гонка «наблюдатель vs ответ на задачу» теряет одно из обновлений состояния. Ожидание ≤ 5 с, неудача не блокирует — сознательный компромисс.

**Уточнения, без которых разработчик будет догадываться (закрыть на синке до старта):**
16. `TaskRequestIn` не имеет `difficulty` — `GetTaskArgs.difficulty` игнорируется (C10). Добавлять поле в `TaskRequestIn` и `pick_template`? (B1, маленькое.)
17. `p_target` для уровней словами в контексте и срезе наблюдателя — `params.p_target_max` (как в `apply.knowledge.states_view` фазы 2, TODO на `roadmap.requirements`). Оставить общий TODO или закрыть в этой фазе одним помощником `apply.knowledge.p_target_for(session, deps, student_id, exam_id)`?
18. Формат `obs.answer` для `numeric`/`multi_select` задач в чате: приняты буква (mcq) и строка числа (numeric); `multi_select` — список букв через запятую/пробел. Подтвердить, что `tasks.answer.grade` принимает такие формы (иначе `skipped(unparsable_answer)`).
19. `query_dataset`: направления в поле программ — свободный текст (`direction: str`); фильтр «подстрока без регистра» может давать пустоту на синонимах («информатика» vs «Computer Science»). Нужен ли словарь синонимов в `data/knowledge_base` (B3) или это принимается как ограничение демо?
20. Кнопка «обновить модель знаний» при `LLM_FORCE_DOWN`: `status=failed` через `job.failed{llm_down}` — сообщение фронту фиксировано? Предложение: `ObservationsDiffOut.failed_reason: str | None`.
21. Чат сета (F20): `frontend` его не запрашивает; включать в фазу или отложить до фазы 4 вместе с `set_summary`? Контекст и наблюдатель его уже поддерживают (`topic_skill_id=None`), стоимость — только `_chat_id` и один тест.
22. `observer_window_max=30` и `chat_window=10` — новые/старые параметры не согласованы с §12 документа архитектуры; B1 должен внести строки в §12 одновременно с `KnowledgeParams` (правило фазы).
23. Размер `tool_result.data` у `run_matching`: `MatchCard.factors` содержит `text` каждого фактора (5 программ × ~8 факторов ≈ 3–4 КБ JSON в контекст модели на каждый ход после `run_matching`). Приемлемо для `chat_window=10`; при росте пола до 30 программ и `limit=10` — пересмотреть.
24. `LLMClient.structured` не отдаёт `usage` — расход наблюдателя/канонизации не измерим точно (уже отмечено в `llm-provider.md`). Оставить оценку по прайсу.
