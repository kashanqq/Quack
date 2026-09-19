# ТЗ фазы 4 — фон и Quack: тексты, мягкое соответствие, рекомендации, поиск

Quack! · фаза 4 · v0.1 · 19.09.2026. Один документ на троих: дельта контрактов + задания B1/B2/B3. Источники: `backend-phases.md` §4 и §7, `product-logic.md` §3.3, §3.4, §3.6, §4.1, §4.4, §5.1, §6.1–§6.5, §7, §8.5; `memory-architecture-quack.md` §1.2, §8 (таблица типов записи), §10.4, §10.7, §11.4, §12; `tech-stack.md` §2.5, §4.2, §4.6, §4.7; `00-contracts.md`, `00-contracts-phase2.md`; `phase3-agents.md` (когда появится — правки в §0.2 этого файла). Всё, что написано в контрактах Ф1–Ф3, действует; здесь только новое и изменённое.

Правила чтения те же: файл правит владелец, чужое — через `docs/sync-log.md`; параметры — только `settings.knowledge.<имя>` и `Settings`; миграция одна на фазу (`0003_phase4`), только B3; порядок мержа B3 (скелет) → B1 (правила) → B2 (генерация) → B3 (роутеры без фейков).

---

## 0. Состояние системы перед фазой

### 0.1 Что уже существует после Ф3 (на что опираемся, не переделываем)

| Слой | Есть | Где |
| :---- | :---- | :---- |
| События | `events.store.append(session, redis, EventIn, deps, dispatch_event=True)` — запись + `dispatch` в одной сессии Postgres, коммит в роутере; `list_by_type`, `list_unprocessed`, `mark_processed`; `EventType` со всеми типами Ф4 (`recommendation.accepted/declined`, `guideline.opened`, `explanation.opened`, `set.opened/completed`, `job.failed`) — enum есть, payload-моделей для рекомендаций и текстов нет | `app/events/store.py`, `app/schemas/events.py` |
| Диспетчер | `RuleDeps(graph, redis, params, now)`, `on(EventType)`, `dispatch(session, event, deps) -> dict[handler_name, result]`, маркер `GraphUnavailable`, `mark_processed` только при полном проходе; реестр `events/handlers.py` — единственное место регистрации | `app/events/dispatch.py`, `app/events/handlers.py` |
| Версия модели знаний | `events.version.bump/get`, заголовок `X-Knowledge-Version` | `app/events/version.py` |
| Правила Ф2 | `sets.queue/assemble/forecast` (чистые), `apply.sets.rebuild_sets` (лок `rebuild:{sid}` 10 с, `forecast_cache`), `apply.sets.open_set`, `matching.hard/realism/rank/compare/shift` (`rank` уже принимает `soft_scores: dict[program_id, float]` с весом `program`), `roadmap.requirements/milestones/conflicts/progress`, `knowledge.words`, `apply.knowledge.states_view` | `app/sets`, `app/apply`, `app/matching`, `app/roadmap` |
| Роутеры Ф2 | `POST /sets/{id}/open` пишет `set.opened` (payload `SetOpenedPayload{set_id, skill_ids}`); `POST /sets/{id}/topics/{skill}/complete` пишет `topic.completed` и, если все закрыты, `set.completed` + статус `done`; `GET /matching` собирает `MatchOut` с `soft_pending=True`, `fits_text=None`; `GET /matching/compare` — `conclusion=None`; `GET /overview` — `last_set_summary` с `text=None` | `app/api/sets.py`, `matching.py`, `overview.py` |
| Агенты Ф3 | `agents.router.run_chat`, `selection.run` с 8 инструментами (в т. ч. `run_matching`, `update_profile` → `profile.updated`), `tutor.run`, `observer.run`, `jobs.observe_chat`, `jobs.canonize_misconception` в `interactive`, `postcheck` в цепочке, `graph.context.build_topic_context` со слотом `previous_set` (читает `set_summaries`) | `app/agents/*`, `app/graph/context.py` |
| LLM | `LLMClient.structured(messages, schema, slot) -> T` — один ретрай на невалидный JSON, затем `LLMUnavailable`; `_acquire(slot)` — счётчик в Redis `quack:llm:ratelimit:{slot}` с окном 60 с и лимитами `LLM_RPM_CHAT` / `LLM_RPM_BULK` (при исчерпании ждёт до `_rate_limit_wait_s`, потом `LLMUnavailable("rate limit")`); circuit breaker `quack:llm:status` (`down` на 120 с после 3 ошибок за минуту), `LLM_FORCE_DOWN`; `load_prompt(name) -> Prompt(version, render)`, `Prompt.extractor_version` = `"<name>_v<N>"`; `FakeLLMClient` со сценариями structured (валидный/невалидный) | `app/llm/client.py`, `structured.py`, `prompts.py`, `fake.py` |
| Поиск | `search.client.search_programs(query, n)` — Tavily при ключе, иначе `ddgs`, `SearchUnavailable`; `fetch_page(url, max_chars=40000)` — httpx 10 с, только http(s), вырезает `script/style/nav/footer`, отдаёт текст | `app/search/client.py` |
| Промпты | `extract_program_v1.md` (правила «неизвестно вместо догадок», `is_demo=false`, `extracted_auto=true`) — есть; `guideline`, `explanation`, `set_summary`, `soft_match`, `compare`, `realism_text` — нет | `app/agents/prompts/` |
| Воркеры | `workers/main.py`: `startup/shutdown` (engine, sessionmaker, neo4j driver, redis, `LLMClient` в `ctx`), `enqueue(redis, queue, fn_name, **kwargs)` прокидывает `request_id`; `WorkerInteractive` (timeout 30, max_tries 3), `WorkerBulk` (timeout 90, max_tries 3); реестр `workers/registry.py`: `INTERACTIVE = [ping, observe_chat, canonize_misconception]` (после Ф3), `BULK = [ping]`; крона нет; compose-сервисы `worker-interactive`, `worker-bulk` | `app/workers/` |
| Таблицы Postgres (`0001_init`, `0002_phase2`) | `generated_texts(id, kind, input_hash, text, model, prompt_version, created_at)` с `UNIQUE(kind, input_hash)`; `set_summaries(id, student_id, set_id, text, stats, created_at)`; `recommendations(id, student_id, kind, payload, status, created_at, decided_at)`; `daily_aggregates(student_id, day, active_minutes, tasks_answered, messages, payload)` PK `(student_id, day)`; `programs_cache` с `source_url, checked_at, is_demo, extracted_auto, flagged, environment_text, payload`; `forecast_cache(student_id, exam_id, payload, as_of_event_id)`; `sets`, `set_topics`, `milestone_marks`, `task_instances(correct, mode, answered_at)`, `seen_templates` | `app/db/models.py` |
| Репозитории | `repo.texts.get_generated(kind, input_hash) / put_generated(...)`; `repo.programs.upsert_program(session, Program)`, `list_all` (без `flagged`), `list_saved_programs`; `repo.sets.*`, `repo.forecast.get/put`, `repo.milestones.list_marks`, `repo.profiles.get_profile / apply_profile_update`; репозиториев для `set_summaries`, `recommendations`, `daily_aggregates` — нет | `app/db/repo/` |
| Ключи Redis | `keys.llm_status/llm_ratelimit/llm_errors/llm_probe/knowledge_version/forecast/ctx_topic/lock/session` | `app/keys.py` |
| Схемы | `MatchOut.fits_text/soft_pending`, `CompareOut.conclusion`, `SetSummaryOut(set_id, text|None, stats, created_at)`, `ForecastOut(..., hours_needed, ready_by, test_date, on_track, as_of_event_id, note)`, `Program(... source_url, checked_at, is_demo, extracted_auto, flagged)`, `SearchHit`, `schemas/texts.GeneratedText` (внутренняя) | `app/schemas/` |

### 0.2 События и контракты, которые приходят из предыдущих фаз и на которые Ф4 подписывается

| Событие | Кто пишет | Payload | Что Ф4 делает |
| :---- | :---- | :---- | :---- |
| `set.opened` | роутер `POST /sets/{id}/open` (B3, Ф2) | `SetOpenedPayload{set_id, skill_ids}` | → `pregenerate_set` в `bulk` |
| `set.completed` | роутер `complete_topic` (Ф2) | `SetCompletedPayload{set_id}` | → `set_summary` в `interactive`; → `recommendations_batch(urgent)` |
| `profile.updated` | `PATCH /profile` (B3), `update_profile` ассистента (B2, Ф3) | `ProfileUpdatedPayload{field, value, by}` | `field == "traits.summary"` → `soft_match`; `field` из `preferences.*`, `constraints.*`, `academics.*`, `direction.*` → `soft_match` для новых кандидатов (состав кандидатов меняется) + `search_programs` прогрев по направлению/странам; `pace.hours_per_week`, `academics.sat_date`, `academics.*_target` → `recommendations_batch(urgent)` |
| `program.saved` / `program.removed` | `POST/DELETE /saved` | `ProgramSavedPayload{program_id}` | → `recommendations_batch(urgent)` (конфликты, темп) |
| `diagnostic.completed`, `mock.completed`, `set.deadline_changed`, `set.switched_by_user`, `milestone.done` | Ф2 | по Ф2 | → `recommendations_batch(urgent)` |
| `observation.extracted` с `pace_signal` | `jobs.observe_chat` (Ф3) | `ObservationOut` | читается `daily_aggregates` (`pace_signals`) |
| `task.answered`, `task.timed_out`, `message.user`, `mock.completed` | Ф2, Ф3 | — | сырьё `daily_aggregates` |
| `topic.opened` | Ф2 | `TopicOpenedPayload` | не триггер: гайдлайн к этому моменту уже должен быть в кэше; `GET /texts/...` — только чтение |

Уточнение к Ф3 (`phase3-agents.md`): если там слот `previous_set` контекста читается напрямую из `set_summaries`, сигнатура чтения фиксируется здесь как `repo.summaries.get_latest(session, student_id, exam_id) -> SetSummaryOut | None` (B3), B2 переключается на неё в первом пуше.

### 0.3 ARQ-механизмы, которые уже есть и на которые Ф4 опирается

- Две очереди, `job_timeout` на класс воркера (не на функцию): `interactive` 30 с, `bulk` 90 с. Ф4 добавляет для `bulk` `max_jobs = settings.BULK_MAX_JOBS` (§1.6) и `cron_jobs`.
- `max_tries = 3` на обеих; ARQ повторяет задачу при исключении `Retry` или при таймауте; после исчерпания — задача помечается failed, наш код в этот момент обязан записать `job.failed` (в Ф3 это уже делает `observe_chat` — тот же хелпер `agents.jobs._fail(ctx, name, kwargs, exc)` переиспользуется).
- Дедупликация: `enqueue_job(..., _job_id=...)` — ARQ не ставит вторую задачу с тем же `job_id`, пока первая в очереди или выполняется. Все задачи Ф4 ставятся с детерминированным `_job_id` (§1.3). `_defer_by` — отложенный старт, используется как дебаунс.
- `ctx` воркера: `sessionmaker`, `neo4j`, `redis`, `llm`, `request_id` (прокидывается `enqueue`). Задача сама открывает сессию `async with ctx["sessionmaker"]() as session`.

### 0.4 Владельцы

| Часть | Владелец |
| :---- | :---- |
| `app/agents/jobs.py` (`pregenerate_set`, `set_summary`, `soft_match`, `extract_program`, `search_programs`, `realism_texts`, `compare_text`), `app/agents/texts.py` (генераторы), `app/search/extract.py`, промпты `guideline_v1`, `explanation_v1`, `set_summary_v1`, `soft_match_v1`, `compare_v1`, `realism_text_v1` | **B2** |
| `app/sets/report.py` (статистика сета), `app/sets/pace.py` (варианты темпа), `app/quack/` (планировщик ленты: срочность, порядок — чистый), `app/knowledge/aggregates.py` (агрегаты — чистый), `matching.rank` с мягким фактором, `app/apply/quack.py`, `app/apply/aggregates.py`, `app/apply/summary_stats.py`, `app/apply/pace.py` (I/O-обёртки B1) | **B1** |
| `workers/registry.py`, `workers/main.py` (крон, `max_jobs`, `Retry`), `workers/jobs_infra.py` (`daily_aggregates`, `recommendations_batch`, `outbox_replay` как ARQ-функции — тонкие обёртки над `apply.*`), миграция `0003_phase4`, `db/models.py`, `db/repo/{texts,summaries,recommendations,aggregates,soft_matches,programs,outbox}.py`, `schemas/{quack,texts,matching,programs,events}.py`, `api/{quack,texts,programs}.py`, `events/handlers.py` (строки Ф4), `events/outbox.py`, `keys.py`, `config.py`, `search/client.py` (rate-limit, нормализация URL), `data/programs_floor` (без изменений) | **B3** |

### 0.5 Стабы, которые закрывает фаза

| Стаб (Ф1, `NotImplementedError("phase 2")`) | Заменяет | Кто |
| :---- | :---- | :---- |
| `agents.jobs.pregenerate_set(ctx, request_id, set_id, student_id)` | реализация §3 | B2 |
| `agents.jobs.set_summary(ctx, request_id, set_id, student_id)` | реализация §4 | B2 |
| `agents.jobs.soft_match(ctx, request_id, student_id, program_ids)` | реализация §5 | B2 |
| `agents.jobs.extract_program(ctx, request_id, url)` → сигнатура расширяется (§1.3): `extract_program(ctx, request_id, url, student_id: UUID | None = None, query: str | None = None)` | реализация §6 | B2 |
| `search.extract.extract_program(llm, html, url) -> Program` | реализация §6.4 (`html` — уже текст страницы из `fetch_page`, имя параметра сохраняется) | B2 |
| `MatchOut.fits_text=None`, `soft_pending=True` (константы в `api/matching.py`) | чтение `soft_matches` §5.6 | B3 |
| `CompareOut.conclusion=None` | `compare_v1` §7.1 | B2 (текст), B3 (роутер) |
| `OverviewOut.last_set_summary.text=None` | `set_summaries.text` | B3 |
| `workers.registry.BULK = [ping]` | §1.2 | B3 |
| `agents.jobs.propose_personal_nodes` | **не закрывается** (Ф6) | — |

---

## 1. Решения фазы

### 1.1 Что никогда не выполняется в запросе

В HTTP-запросе нет ни одного вызова модели, поиска или `fetch_page`. Роутер: (а) читает кэш/таблицы, (б) пишет событие → `dispatch` → коммит, (в) после коммита ставит задачи из outbox (§1.4). Единственное исключение из Ф3 — чат (`MODEL_CHAT`, стриминг) — не меняется. Тексты «почему реалистично» и `conclusion` сравнения тоже не генерируются в запросе: `GET /matching` и `GET /matching/compare` отдают то, что есть в `generated_texts`, и ставят задачу на недостающее (§7).

### 1.2 Реестр очередей после Ф4

    INTERACTIVE = [ping, observe_chat, canonize_misconception, set_summary]
    BULK        = [ping, pregenerate_set, soft_match, extract_program, search_programs,
                   daily_aggregates, recommendations_batch, realism_texts, compare_text,
                   outbox_replay]

`set_summary` — в `interactive` (tech-stack §2.5: ученик ждёт отчёт в Обзоре сразу после закрытия сета). Остальное — `bulk`. Таймауты — `job_timeout` класса; внутри задачи собственные бюджеты на вызов модели (`LLM_TIMEOUT_BULK_S`) и на программу (`soft_match`: 20 с на программу через `asyncio.wait_for`).

Крон (`WorkerBulk.cron_jobs`, B3):

    cron(daily_aggregates_cron,       hour=3,  minute=0)                        # UTC
    cron(recommendations_batch_cron,  hour=set(range(0, 24, recs_interval_h)), minute=15)
    cron(outbox_replay,               minute=set(range(0, 60, 10)))

`*_cron` — обёртки без аргументов, которые перебирают активных учеников (§10.3) и ставят по задаче на ученика с `_job_id` (дедуп). При старте воркера `startup` проверяет `quack:cron:last:{name}`: если старше интервала × 1.5 — ставит задачу сразу (компенсация пропущенного запуска, §9.7).

### 1.3 Идентификаторы задач и дедупликация

| Задача | `_job_id` | `_defer_by` | Смысл |
| :---- | :---- | :---- | :---- |
| `pregenerate_set` | `pregen:{set_id}:{inputs_hash[:12]}` | 0 | один прогон на версию входов сета |
| `set_summary` | `summary:{set_id}` | 0 | один отчёт на сет |
| `soft_match` | `softmatch:{student_id}:{summary_hash[:12]}` | `soft_match_debounce_s` (30) | быстрые правки резюме схлопываются в одну задачу |
| `search_programs` | `search:{sha1(normalized_query)[:16]}` | 0 | тот же запрос от двух учеников — одна задача |
| `extract_program` | `extract:{sha1(normalized_url)[:16]}` | 0 | один URL — одна задача |
| `daily_aggregates` | `aggr:{student_id}:{YYYY-MM-DD}` | 0 | не чаще раза в сутки на ученика, кроме `force` |
| `recommendations_batch` | `recs:{student_id}` | 5 с при `urgent`, 0 из крона | шторм событий → одна задача |
| `realism_texts` | `realism:{student_id}:{profile_hash[:12]}` | 10 с | |
| `compare_text` | `compare:{student_id}:{ids_hash[:12]}` | 0 | |

ARQ хранит результат задачи `keep_result` 3600 с — с тем же `job_id` внутри часа задача **не поставится**. Для `recs:{sid}` и `aggr` это желательно; для `pregen`/`softmatch` хэш входов гарантирует, что новые входы дают новый id. B3 задаёт `keep_result=60` для обоих воркеров, чтобы не блокировать повтор на час.

### 1.4 Outbox: постановка задач только после коммита

Обработчик в `dispatch` работает внутри незакоммиченной транзакции; если он поставит ARQ-задачу напрямую, воркер может прочитать БД раньше коммита и не увидеть событие/сет. Поэтому:

- `RuleDeps` получает поле `jobs: JobOutbox` (B3, `app/events/outbox.py`): `enqueue(queue, fn_name, *, job_id, defer_by=0, **kwargs)` только накапливает.
- `api/deps.get_rule_deps` создаёт outbox на запрос; зависимость `flush_outbox` (в `api/deps.py`) после `session.commit()` вызывает `workers.main.enqueue` для каждой записи. Ошибка Redis при постановке — лог `outbox_enqueue_failed` + запись в таблицу `job_outbox` (§1.7) для повторной постановки кроном `outbox_replay`. Это единственный путь постановки из API.
- В воркере (`ctx["jobs"]`) — тот же класс с немедленной постановкой (транзакции воркера короткие, задача коммитит до постановки дочерних).
- Ф3-постановки наблюдателя из `api/chat.py` — не трогаем (после `done`, коммит уже был).

### 1.5 Статусы

- Сгенерированный текст: `generating | ready | failed` — колонка `generated_texts.status`; `stale` — вычисляется при чтении (есть `ready`-текст для другого `input_hash` того же `(student_id, kind, subject)`, для текущего — нет `ready`). Наружу `GeneratedTextOut.status: "ready" | "generating" | "stale" | "failed"`.
- Рекомендация: `pending → shown → accepted | declined`, плюс `expired` (причина исчезла до решения). `pending` = «сгенерирована, ещё не показана» (в терминах задания — `generated`).
- Программа из извлечения: `Program.extracted_auto=True`, `flagged=False`; «неверно» ставит `flagged=True` — поле уже есть, роутер `POST /programs/{id}/flag` добавляется здесь (B3), полноценная перепроверка — Ф5.

### 1.6 Параметры — дополнения

`KnowledgeParams` (B3, `config.py`; переопределение `KNOWLEDGE__<ИМЯ>`):

| Параметр | Значение | Где |
| :---- | :---- | :---- |
| `recs_interval_h` | 24 | крон `recommendations_batch` (product-logic §3.6: раз в 1–2 дня) |
| `urgent_milestone_days` | 5 | веха ближе → срочная рекомендация |
| `pace_hours_step` / `pace_max_hours` | 1 / 20 | вариант «увеличить часы» |
| `pace_target_step_sat` / `pace_target_step_ent` | 10 / 1 | вариант «снизить цель» (шаг в баллах шкалы) |
| `pace_min_target_share` | 0.6 | цель не снижается ниже 60 % от текущей |
| `soft_match_max_candidates` | 15 | верх списка `rank` для мягкого фактора + сохранённые |
| `soft_match_debounce_s` | 30 | |
| `soft_weight_key` | `"program"` | ключ `matching_priority_weights` для мягкого фактора |
| `aggregate_window_days` | 14 | окно дневных агрегатов и календаря активности |
| `activity_tz` | `"Asia/Almaty"` | день активности считается в этом поясе (в анкете пояса нет) |
| `session_gap_min` | 30 | разрыв, после которого минуты сессии не считаются (= TTL `session_id`) |
| `active_day_min_events` | 1 | день активен при ≥ 1 событии из списка §9.2 |
| `summary_top_growth` | 3 | «сильнее всего выросли» — топ-N |
| `text_stale_ok_on_error` | true | при LLM down отдавать `stale` с пометкой |
| `extract_max_urls_per_search` | 5 | |
| `extract_min_page_chars` | 800 | страница короче — «без данных» |
| `program_recheck_days` | 14 | повторное извлечение по тому же URL не раньше |
| `program_domain_denylist` | `["reddit.com","quora.com","youtube.com","facebook.com","instagram.com","tiktok.com","wikipedia.org"]` | не источники программ |

`Settings` (B3): `BULK_MAX_JOBS=2`, `SEARCH_RPM=5`, `SEARCH_MONTHLY_CAP=800`, `LLM_RETRY_DEFER_S=120`; `LLM_RPM_BULK` подбирается так, что `LLM_RPM_CHAT + LLM_RPM_BULK ≤ RPM провайдера` (записать в `docs/decisions/llm-provider.md`).

### 1.7 Postgres — миграция `0003_phase4` (B3, в скелете, одна)

| Таблица | Изменение |
| :---- | :---- |
| `generated_texts` | + `student_id UUID NULL` (общие тексты — NULL), + `subject TEXT NOT NULL DEFAULT ''` (`skill_id`, `program_id`, `"a,b,c"` для сравнения), + `set_id UUID NULL`, + `status TEXT NOT NULL DEFAULT 'ready'` (`generating/ready/failed`), + `attempts INT NOT NULL DEFAULT 0`, + `error TEXT NULL`, + `updated_at TIMESTAMPTZ`; `text` становится `NULL`-able (пока `generating`); индекс `(student_id, kind, subject, created_at DESC)`; `UNIQUE(kind, input_hash)` остаётся — `input_hash` включает `student_id` и `subject` (§3.4), коллизий между учениками нет |
| `set_summaries` | + `UNIQUE(set_id)`, + `exam_id TEXT`, + `status TEXT NOT NULL DEFAULT 'ready'` (`generating/ready/failed`), `text` → `NULL`-able, + `prompt_version TEXT NULL`, + `input_hash TEXT NULL` |
| `recommendations` | + `reason_hash TEXT NOT NULL`, + `urgency TEXT NOT NULL` (`urgent/high/normal/low`), + `position INT NOT NULL DEFAULT 0`, + `exam_id TEXT NULL`, + `shown_at TIMESTAMPTZ NULL`, + `expires_at TIMESTAMPTZ NULL`, + `batch_id UUID NULL`, + `decision_event_id BIGINT NULL`; `status` CHECK `pending/shown/accepted/declined/expired`; частичный уникальный индекс `(student_id, reason_hash) WHERE status IN ('pending','shown')` — открытая рекомендация по причине одна |
| `student_aggregates` (новая) | `student_id UUID PK`, `payload JSONB` (`StudentAggregates`), `computed_at TIMESTAMPTZ`, `as_of_event_id BIGINT` |
| `soft_matches` (новая) | `summary_hash TEXT`, `program_id TEXT`, `prompt_version TEXT`, `score FLOAT`, `text TEXT`, `model TEXT`, `created_at`; PK `(summary_hash, program_id, prompt_version)`; индекс `(program_id)` |
| `programs_cache` | + `extraction JSONB NULL` (`ExtractionMeta`), + `normalized_url TEXT` с уникальным индексом, + `university_slug TEXT`, `direction_slug TEXT`, индекс `(university_slug, direction_slug)` |
| `job_outbox` (новая) | `id BIGSERIAL`, `queue`, `fn_name`, `job_id`, `kwargs JSONB`, `defer_by INT`, `created_at`, `enqueued_at NULL` — только для случаев, когда Redis был недоступен при постановке |
| `daily_aggregates` | без изменений схемы; `payload` = `DailyAggregatePayload` §9 |
| `sets` | + `opened_forecast JSONB NULL` — снапшот `ForecastOut` в момент `set.opened` (§4.3) |

`downgrade` удаляет всё своё. `recommendations` до Ф4 пустая — миграция не заполняет `reason_hash` задним числом.

### 1.8 Redis — новые ключи (`app/keys.py`, B3)

| Функция | Ключ | Содержимое | TTL |
| :---- | :---- | :---- | :---- |
| `keys.text_job(kind, input_hash)` | `quack:text:job:{kind}:{hash}` | `job_id` задачи, которая генерирует | 600 с |
| `keys.search_ratelimit()` | `quack:search:rl` | счётчик за минуту | 60 с |
| `keys.search_monthly(yyyymm)` | `quack:search:month:{yyyymm}` | счётчик запросов Tavily | 40 дней |
| `keys.cron_last(name)` | `quack:cron:last:{name}` | ISO-время последнего запуска | — |
| `keys.lock("recs:{sid}")`, `keys.lock("aggr:{sid}")`, `keys.lock("extract:{urlhash}")`, `keys.lock("pregen:{set_id}")` | `quack:lock:...` | лок выполнения | 120 с |
| `keys.quack_batch(student_id)` | `quack:recs:batch:{sid}` | `{batch_id, at, n_new}` последней порции — для «кряканья» | — |
| `keys.soft_pending(student_id)` | `quack:softmatch:pending:{sid}` | `summary_hash`, для которого идёт расчёт | 300 с |
| `keys.pace(student_id)` | `quack:pace:{sid}` | `PaceOut` JSON + `as_of_event_id` (§8.3) | 600 с |
| `keys.search_status(search_id)` | `quack:search:status:{id}` | `SearchStatusOut` JSON (§6.1) | 3600 с |

---

## 2. Архитектура фоновых задач

### 2.1 Общий каркас задачи (B2 и B3 пишут по одному шаблону)

    async def <job>(ctx, request_id, **args):
        bind request_id в structlog
        lock = keys.lock(<job-specific>); если занят → return (другая копия уже работает)
        try:
            async with ctx["sessionmaker"]() as session:
                1. прочитать входы; если целевой объект исчез (сет удалён, ученик без профиля) → лог `job_skipped`, return
                2. посчитать input_hash; если результат для этого hash уже `ready` → return (идемпотентность)
                3. записать строку `generating` (там, где статус хранится) и commit
            вызов модели / поиска (вне транзакции Postgres)
            async with ctx["sessionmaker"]() as session:
                4. проверить, что входы не изменились (сравнить hash повторно там, где это дёшево — §3.7)
                5. записать результат, статус `ready`, commit
                6. ctx["jobs"].enqueue(...) дочерние задачи (после commit)
        except LLMUnavailable as e:
            если llm_status == down или e == rate limit → raise Retry(defer=LLM_RETRY_DEFER_S)   # не считаем ошибкой генерации
            иначе → статус `failed`, error=str(e)[:200]; raise (ARQ повторит до max_tries)
        except (SearchUnavailable, httpx.HTTPError): аналогично с defer 60 с
        except Exception: статус `failed`; raise
        finally: release lock
        on final failure (ctx["job_try"] == max_tries): events.store.append(job.failed {job, args, error}, dispatch_event=False)

Правила для всех: задача **никогда** не пишет в граф и не меняет модель знаний; задача не вызывает `dispatch` (только `append(dispatch_event=False)` для `job.failed` и служебных событий); все вызовы модели — слот `bulk`, кроме `set_summary` (тоже `bulk`-слот по модели, но очередь `interactive` — модель `MODEL_BULK` со structured output достаточна; `MODEL_CHAT` не используется в фоне вообще); повторный запуск с теми же аргументами безопасен.

### 2.2 Сводная таблица

| Job | Trigger | Queue | Вход | Зависимости | Timeout | Retry | Idempotency | Результат / запись | События |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| `pregenerate_set` | `set.opened` (handler `apply.sets.on_set_opened_enqueue` — B1 тонкая строка в `apply/sets.py`, регистрирует B3) | `bulk` | `set_id, student_id` | `repo.sets.get_set`, `apply.knowledge.states_view`, `graph.queries.personal.get_misc_states`, `repo.profiles.get_profile`, `repo.texts`, `LLMClient.structured` | 90 с на задачу; внутри ≤ 8 вызовов по `LLM_TIMEOUT_BULK_S`; если не уложилась — недоделанные остаются `generating` и задача перезапускается с тем же `job_id` (§3.6) | ARQ ×3 + `Retry` при LLM down | `UNIQUE(kind, input_hash)`, пропуск `ready` | `generated_texts` ×(топики × 2) | нет; `job.failed` при финальной ошибке |
| `set_summary` | `set.completed` (handler `apply.summary_stats.on_set_completed` — B1: считает статистику **в транзакции события**, пишет `set_summaries{status: generating, stats}` и кладёт в outbox задачу) | `interactive` | `set_id, student_id` | `repo.summaries`, `LLMClient.structured` | 30 с | ×3 + `Retry` | `UNIQUE(set_id)`; `ready` → пропуск | `set_summaries.text/status` | нет |
| `soft_match` | `profile.updated` с `field ∈ {traits.summary, preferences.*, constraints.*, direction.*, academics.*}` (handler `apply.quack.on_profile_updated_enqueue`); `extract_program` успех (для `student_id` инициатора); первый `GET /matching` ученика, у которого есть резюме и нет строк (роутер ставит через outbox) | `bulk` | `student_id, program_ids` (пусто → кандидаты считаются в задаче) | профиль, `repo.programs.list_all`, `matching.hard/realism/rank` для кандидатов, `repo.soft_matches`, LLM | 90 с; 20 с на программу | ×3 + `Retry` | PK `(summary_hash, program_id, prompt_version)`; готовые пары пропускаются | `soft_matches` | нет |
| `search_programs` | `POST /programs/search` (202); прогрев: `profile.updated` по `direction.field` / `preferences.countries` если `readiness ≥ 0.5`; инструмент `search_programs` ассистента (если Ф3 его ввёл — он ставит эту же задачу и отвечает «ищу») | `bulk` | `query, student_id` | `search.client.search_programs`, rate-limit §10.4 | 30 с | ×2 + `Retry` 60 с при `SearchUnavailable` | `job_id` по запросу; результат — постановка `extract_program` по URL (дедуп на их стороне) | нет записи, кроме счётчиков | нет |
| `extract_program` | из `search_programs` | `bulk` | `url, student_id?, query?` | `fetch_page`, `search.extract.extract_program`, `repo.programs`, LLM | 60 с | ×2 + `Retry` при LLM/fetch down | лок `extract:{urlhash}`; `normalized_url` уникален; `checked_at` свежее `program_recheck_days` → пропуск | `programs_cache` upsert | `program.extracted` **не вводится** (не персональное событие); лог |
| `daily_aggregates` | крон 03:00 UTC (для всех активных); `POST /quack/seen` (для одного ученика, `_job_id` дневной) | `bulk` | `student_id, day?` (`None` → сегодня), `force=False` | `events.store.list_events`, `graph.queries.personal.get_misc_states`, `repo.aggregates` | 90 с | ×3 | полный пересчёт окна — детерминирован, upsert | `daily_aggregates` (окно), `student_aggregates` | нет |
| `recommendations_batch` | крон раз в `recs_interval_h`; `urgent=True` из обработчиков событий §0.2 | `bulk` | `student_id, urgent: bool` | профиль, сохранённые, `repo.forecast`, `roadmap.*`, `sets.pace`, `repo.sets`, `repo.aggregates`, `matching.*` (для «стали подходить»), `repo.recommendations` | 90 с | ×3 | лок `recs:{sid}`; upsert по `reason_hash` | `recommendations`, ключ `quack:recs:batch` | нет (события пишет только ученик: accepted/declined) |
| `realism_texts` | `GET /matching` обнаружил отсутствие текста для `(student, profile_hash, program)` у первых `limit` программ | `bulk` | `student_id, program_ids` | `matching.hard` результат (пересчитывается в задаче), `repo.texts`, LLM | 90 с | ×2 | `generated_texts` `kind=realism` | `generated_texts` | нет |
| `compare_text` | `GET /matching/compare` без `conclusion` в кэше | `bulk` | `student_id, program_ids` | `matching.compare` (таблица), профиль, `repo.texts`, LLM | 60 с | ×2 | `kind=compare`, `subject="a,b,c"` (отсортированные id) | `generated_texts` | нет |

Все триггеры «событие → задача» регистрируются в `events/handlers.py` дополнительными строками (B3), обработчики-однострочники лежат в `app/apply/*` (B1) — тем же путём, что и правила Ф2, чтобы `test_handlers` видел полную таблицу. Ни один из этих обработчиков не трогает граф и не бросает исключений при ошибке постановки: outbox копит, ошибка при флаше — в `job_outbox`.

Конкретно:

- `set.opened → pregenerate_set`: `on_set_opened_enqueue` считает `inputs_hash` (§3.4) уже здесь (входы в транзакции: состояния уже в графе), кладёт `pregen:{set_id}:{hash}`. Если `llm_status == down` — всё равно ставит: воркер отложит через `Retry`.
- `set.completed → set_summary`: см. §4 — статистика синхронно правилом, задача только за текстом.
- `profile.updated → soft_match`: `by` любой (ассистент и ручная правка — одинаковый эффект, product-logic §3.1). Если `traits.summary` стало пустым — задача не ставится, `soft_matches` не трогаются (старые строки под старым хэшем просто не читаются).
- `program.extracted (внутренний) → soft_match`: задача `extract_program` после upsert ставит `soft_match(student_id, [program_id])`, если `student_id` задан и у ученика есть резюме.
- `cron → daily_aggregates`: обёртка `daily_aggregates_cron` выбирает `student_id` с событиями за `aggregate_window_days` (`events.store.list_active_students(session, since)` — B3 добавляет), ставит по задаче.
- `cron / urgent → recommendations_batch`: обёртка из крона — те же активные ученики; urgent — обработчики §0.2 через outbox с `defer_by=5`.

### 2.3 Что происходит при недоступности каждого хранилища

| Недоступно | Поведение задачи |
| :---- | :---- |
| LLM (`down`, 429, timeout, 5xx) | `Retry(defer=LLM_RETRY_DEFER_S)`; статус строки остаётся `generating`; после `max_tries` — `failed` + `job.failed`. Читатели показывают `stale` (если есть) или «генерируется / недоступно». Ф5 добавит автоперезапуск при восстановлении; в Ф4 перезапуск — следующий триггер (следующее `set.opened`, следующая правка резюме) или ручной `POST /texts/.../regenerate` |
| Redis | `enqueue` падает → `job_outbox`; rate-limit LLM при ошибке Redis пропускает (уже так в клиенте); локи при ошибке Redis считаются свободными (лог `lock_redis_unavailable`), задача работает — дубли отсекаются уникальными индексами |
| Postgres | задача падает исключением → ARQ retry; ничего не записано частично, потому что запись — одна транзакция на шаг |
| Neo4j | `pregenerate_set` / `set_summary` без состояний → задача **не** генерирует по пустым входам: `Retry(defer=60)` до `max_tries`, затем `failed` (текст без модели знаний был бы ложью, product-logic §6.3: «ничего не работает наполовину»). `daily_aggregates` — `error_class_dist` из прошлого `student_aggregates` с пометкой `graph_stale=True`. `recommendations_batch` — прогноз из `forecast_cache` (Postgres), состав сетов из `sets` — работает |
| Поиск | `search_programs` → `Retry` 60 с ×2 → лог; `GET /matching` не меняется (пол + кэш); `POST /programs/search` уже вернул 202 — статус `GET /programs/search/{search_id}` = `unavailable` |
| Воркер упал посреди задачи | ARQ вернёт задачу в очередь по таймауту (`job_timeout`) — повтор безопасен: `generating`-строки и локи имеют TTL/перезаписываются, готовые пары пропускаются |

---

## 3. Предгенерация текстов — `jobs.pregenerate_set` (B2)

### 3.1 Какие топики и какие тексты

Вход — `SetOut` по `set_id`. Обрабатываются `topics[]` сета:

| `TopicOut.kind` | `guideline` | `explanation` |
| :---- | :---- | :---- |
| `topic` | да | да |
| `review` | да (короткий вариант: промпт получает `mode=review`) | да |
| `check` | нет (2–3 задачи, не топик) | да (короткое объяснение навыка нужно, если ученик откроет проверку) |

Два типа текста (product-logic §4.4): **гайдлайн** — как готовиться, что нужно уметь, типичные ловушки *этого ученика*, что решать; **объяснение навыка** — что это и как работает, без персонализации по заблуждениям (общий текст, `student_id=NULL`, переиспользуется между учениками — экономия вызовов). Порядок генерации: гайдлайн первого открытого топика → объяснение первого → остальные по `position`. Так при обрыве по таймауту первый топик готов.

### 3.2 Входы

`GuidelineInputs` (B2, `agents/texts.py`; сериализуется детерминированно для хэша):

    skill: {id, name, description, exam_id, area_name}
    state_words: SkillLevel                          # knowledge.words.skill_level — не числа
    p_target_words: str                              # «держать на уровне ~90 %» — из p_target, округлено до 5 %
    prerequisites: [{id, name, level: SkillLevel}]   # 1 хоп, ≤ 5
    active_misconceptions: [{id, name, description, trigger_words: str | None}]   # только confirmed + resolved < under_watch_days, visible_to("tutor")
    root_of: [skill names]                           # для кого этот навык — корень (is_root)
    set: {deadline, position_in_set, n_topics, kind}
    profile: {explanation_depth, hint_level, hours_per_week}
    exam_format_hint: {task_types: [...], calculator: bool}   # из ExamFormat секции
    template_tags: [str]                             # теги шаблонов навыка — «что решать» по типам задач
    mode: "topic" | "review"

`ExplanationInputs`: `skill`, `prerequisites` (имена), `exam_format_hint`, `explanation_depth`. Никаких чисел `p`/`conf` в промпт не идёт — только слова; никаких дат кроме дедлайна сета.

### 3.3 Промпты и версии

`guideline_v1.md`, `explanation_v1.md` — B2. Structured output: `GuidelineOut{how_to_prepare: str, must_know: list[str] (3–6), traps: list[str] (0–4, только из active_misconceptions), what_to_solve: list[str] (2–4), summary: str ≤ 300}`, `ExplanationOut{text: str, key_points: list[str] (2–5)}`. Сериализация в текст для `generated_texts.text` — детерминированная (`texts.render_guideline(out) -> str`, markdown с фиксированными заголовками); структура тоже сохраняется в `generated_texts.payload`? — нет, новых колонок не вводим: `text` хранит markdown, фронт рендерит markdown. Правила промпта: никаких процентов и обещаний; ловушки называть только те, что переданы; не называть навыки из `low_data` слабыми; язык — русский; длина гайдлайна ≤ 2000 символов.

`prompt_version` = `Prompt.extractor_version` (`guideline_v1`). Модель — `settings.MODEL_BULK`.

### 3.4 Хэш входов и cache key

    input_hash = sha256(canonical_json({
        "kind": kind, "student_id": student_id | None, "subject": skill_id,
        "inputs": <Inputs>.model_dump(mode="json"),        # без дат генерации
        "prompt_version": prompt_version, "model": model
    })).hexdigest()

`kind ∈ {"guideline", "explanation", "realism", "compare"}`. Cache key в таблице — `(kind, input_hash)`; поиск «текущего текста» — по `(student_id, kind, subject)` + вычисленный hash. `inputs_hash` сета для `_job_id` — sha256 от списка `input_hash` всех текстов сета.

Что входит в хэш и что меняет его: состояние навыка **словами** (`SkillLevel`), не `p` — иначе каждый ответ на задачу инвалидировал бы текст; набор и статусы видимых заблуждений; `trigger_words`; предпосылки словами; дедлайн сета; профиль (глубина, подсказка, часы); версия промпта; модель. Не входит: `request_id`, время, `set_id` (тот же топик в другом сете с теми же входами — тот же текст).

### 3.5 Статусы и чтение (`GET /texts/{set_id}/{skill_id}?kind=`, B3)

    current_hash = hash(текущие входы)                       # роутер считает так же, как задача (общая функция texts.inputs_hash — B2, чистая: app/agents/texts.py импортируется роутером только ради хэша; I/O-сборку входов делает apply.texts.collect_inputs — B1)
    row = repo.texts.get_generated(kind, current_hash)
    ready         → status=ready, text, generated_at, prompt_version, mark="generated"
    generating    → status=generating, text=None; если есть прошлый ready того же subject → status=stale, text=прошлый, mark="saved_version"
    failed / нет  → если прошлый ready есть → stale + mark="saved_version"; иначе status=failed, text=None, reason="llm_unavailable"|"not_generated"
    нет строки и нет задачи → роутер ставит `pregenerate_set` для этого сета через outbox (сет открыт вручную не через /open? — да, страховка) и отдаёт generating

`GET` не пишет в БД; постановка задачи — через outbox после ответа (нет коммита — outbox флашится и без него). `POST /texts/{set_id}/{skill_id}/opened {kind}` — пишет `guideline.opened` / `explanation.opened` (payload `TextOpenedPayload{set_id, skill_id, kind, text_hash}`), нужен для `after_guideline` и активности. `POST /texts/{set_id}/{skill_id}/regenerate` — принудительно ставит задачу (для демо и после `failed`), 202.

### 3.6 Повторная генерация, инвалидация, смена модели знаний и промпта

- **Изменение модели знаний** (новое состояние, новый статус заблуждения) → следующий расчёт `current_hash` даёт другой хэш → текст `stale`. Регенерация **не** запускается на каждое свидетельство (это съело бы лимит): триггеры регенерации — `set.opened` (в т. ч. повторное открытие после смены сета), `topic.opened` при `stale` (обработчик `apply.texts.on_topic_opened` ставит `pregenerate_set` с новым `inputs_hash`; дедуп по `job_id`), `regenerate` вручную. Между триггерами показывается `stale` с пометкой «сохранённая версия» — это честно: текст был верен на момент входа в топик.
- **Смена версии промпта / модели** → все старые строки становятся `stale` автоматически (хэш включает версию); старые не удаляются (нужны как `stale`-фоллбек); чистка старше 30 дней — не в этой фазе.
- **Ручное изменение состава сета** (`PATCH /sets`) → `rebuild` → при следующем `set.opened`/`topic.opened` новые топики генерируются, старые остаются в кэше.
- Задача пропускает тексты, у которых строка `ready` с текущим хэшем, и перезаписывает `generating`/`failed` (`attempts += 1`). Если `attempts ≥ 3` и статус `failed` — не пытается снова до `regenerate` вручную (защита от бесконечного расхода на «плохой» вход).

### 3.7 LLM failure

`LLMUnavailable` при `down`/rate limit → `Retry` (см. §2.1), строка остаётся `generating`; ключ `keys.text_job` с TTL 600 с показывает роутеру, что задача жива (иначе роутер после TTL считает генерацию потерянной и ставит задачу заново). Невалидный structured после ретрая клиента → строка `failed`, `error="invalid_output"`, задача продолжает со следующим текстом (одна плохая генерация не блокирует сет), в конце — если хоть один `failed` → `raise` для ARQ-повтора; при финальной попытке `job.failed` с перечнем `failed` subjects.

---

## 4. Отчёт по сету — `set_summary`

### 4.1 Разделение

    set.completed → [B1, синхронно в dispatch] apply.summary_stats.on_set_completed:
        stats = sets.report.set_stats(...)          # чистая функция, числа
        repo.summaries.upsert(set_id, stats, status="generating", text=None)
        deps.jobs.enqueue("interactive", "set_summary", job_id=f"summary:{set_id}", set_id, student_id)
    → [B2, задача] jobs.set_summary: читает stats → один вызов модели → text → repo.summaries.set_text(set_id, text, prompt_version, status="ready")

Модель не считает ничего: вход — готовые факты, схема выхода — только текст. Постпроверка (B2, та же `postcheck`-функция, что в Ф3, в режиме «числа из stats»): любое число в тексте обязано присутствовать в `stats` (как `int`/`float` в любом поле), иначе одна попытка регенерации с указанием ошибки, затем `failed` с `text=None` — Обзор показывает данные без текста (product-logic §6.3).

### 4.2 Структура статистики — `SetStats` (B1, `schemas/sets.py`, B3 пишет модель)

    SetStats(
      set_id, exam_id, kind,
      opened_at, completed_at, deadline, days_in_set: int, days_vs_deadline: int,      # +2 = на 2 дня раньше, −3 = позже
      tasks_answered: int, tasks_correct: int, mocks_completed: int,
      skills_total: int, skills_closed: int,
      skills: [SkillDelta(skill_id, name, level_before: SkillLevel, level_after: SkillLevel, p_before: float, p_after: float, delta_p: float)],
      top_growth: [skill_id]  (summary_top_growth по delta_p),
      misconceptions_resolved: [{id, name}], misconceptions_still_watching: [{id, name}], misconceptions_new_confirmed: [{id, name}],
      forecast_before: ForecastOut | None, forecast_after: ForecastOut | None,           # before — из forecast_cache на момент set.opened (снапшот, §4.3)
      on_track_after: bool | None, ready_by_shift_days: int | None,
      next_set: {set_id, deadline, topic_names: [str]} | None,
      previous_summary_id: UUID | None
    )

Источники: `tasks_answered/correct` — `repo.sets.count_progress` (уже есть); `mocks_completed` — `repo.mocks` по `set_id`; состояния до/после — `graph.queries.personal.get_state_history(..., n)` + фильтр по `created_at ≤ opened_at` для «до» (первое состояние после `set.opened` — «до», текущее — «после»; если истории нет — `level_before = low_data`, `p_before` приор); заблуждения — `get_misc_states` по навыкам сета, `resolved_at`/`updated_at` в интервале сета; дедлайн — `sets.deadline`; следующий сет — первый `upcoming` по `position`.

### 4.3 Прогноз до/после

`forecast_before` — снапшот `forecast_cache` в момент `set.opened`: обработчик `apply.sets.on_set_opened_enqueue` (тот же, что ставит предгенерацию) копирует текущий `ForecastOut` в `sets.opened_forecast JSONB` — **это ещё одна колонка `sets` в миграции 0003** (добавить в §1.7: `sets.opened_forecast JSONB NULL`). `forecast_after` — `forecast_cache` в момент `set.completed` (после `rebuild`, который дёргает `topic.completed`? — нет: `rebuild` на `set.completed` не зарегистрирован в Ф2; здесь `on_set_completed` вызывает `rebuild_sets` явно перед статистикой, чтобы `forecast_after` и `next_set` были свежими).

### 4.4 Промпт `set_summary_v1` и ограничения модели

Вход: `SetStats` словами (числа — только те, что в `stats`; уровни — `SkillLevel` по-русски; заблуждения — названия). Выход `SetSummaryTextOut{text: str ≤ 600, tone: "encouraging"}`. Правила: короткий, приободряющий; что закрыто, что стало увереннее, что исправлено, что «следим»; успевает ли (`on_track_after` словами: «успеваешь» / «пока не успеваешь — варианты в Quack»); следующий сет одной фразой; никаких процентов и обещаний; не выдумывать навыки, которых нет в `stats`.

### 4.5 Кэш и `previous_set`

- `set_summaries` — одна строка на `set_id` (`UNIQUE`), `input_hash = sha256(stats + prompt_version + model)`; повторный `set.completed` (не бывает по роутеру, но replay) — статистика пересчитывается и перезаписывается только если `input_hash` изменился и статус не `ready`; готовый текст не перегенерируется.
- `SetSummaryOut` дополняется: `status`, `exam_id`, `stats: SetStats` (типизировано вместо `dict`). `GET /overview.last_set_summary` — последняя по `created_at` для ученика (любой экзамен); `GET /sets/{id}/summary` — по сету (404 если нет).
- `previous_set` контекста репетитора (Ф3) читает `repo.summaries.get_latest(session, student_id, exam_id)`: текст при `ready`, иначе 2–3 факта из `stats` словами (`sets.report.stats_words(stats) -> str`, B1) — контекст не пустеет из-за недоступной модели.

---

## 5. Мягкое соответствие — `jobs.soft_match` (B2) + чтение в подборке (B3) + вес в ранжировании (B1)

### 5.1 Pipeline

    profile.updated (traits.summary | preferences | constraints | direction | academics)
      → [B1 handler] apply.quack.on_profile_updated_enqueue → outbox soft_match(student_id, program_ids=[])
      → [B2 job] кандидаты → для каждой пары (summary_hash, program_id, prompt_version) без строки → structured вызов
      → validation → repo.soft_matches.put
      → [B3 read] GET /matching: soft_scores из soft_matches → matching.rank(soft_scores) → MatchOut.fits_text / soft_pending

### 5.2 Кандидаты (в задаче, если `program_ids` пуст)

`hard_filter → realism → rank` на текущем профиле (те же вызовы, что `GET /matching`, вынесены B3 в `apply.matching.compute(session, deps, student_id) -> list[Ranked]`-подобную функцию `api/_matching.py`, чтобы задача и роутер не расходились), берём первые `soft_match_max_candidates` **плюс** все сохранённые, минус `flagged`. `impossible` не исключаются (порядок внутри уровня всё равно нужен), но идут последними. Если `traits.summary` пустое (после `strip`) — задача завершается сразу, ничего не пишет.

### 5.3 Входные признаки и что модели разрешено оценивать

Вход `SoftMatchInputs`: `traits_summary` (текст резюме предпочтений, ≤ 1500 символов, обрезка), `traits_verbatim` (≤ 10 последних, ≤ 100 символов каждая — для «дословно, как сказано»), `program: {university, country, city, language, direction, environment_text, scholarships_note}`. **Не подаются**: требования, пороги, стоимость, дедлайны, баллы ученика, бюджет — это жёсткие факторы, их уже посчитал `matching.hard`, и модель не должна их дублировать или спорить с ними.

Модели разрешено: оценить, насколько описание среды/города/программы совпадает с чертами; сказать одну-две фразы «подходит тебе: …» и (опционально) одну «но …». Запрещено (в промпте и в валидации): называть стоимость, баллы, даты, вероятности, ранжировать программы между собой, утверждать факты, которых нет в `environment_text`.

### 5.4 Structured output и валидация

    SoftMatchOut(score: float ∈ [0,1], fit_text: str (1–2 предложения, ≤ 240 символов), caveat: str | None (≤ 120),
                 matched_traits: list[str] (≤ 4, подстроки/перефраз черт), confidence: Literal["low","medium","high"])

Валидация после Pydantic (B2, `texts.validate_soft_match`): `fit_text` без цифр и знака `%` (иначе — одна регенерация с указанием, затем пара помечается `failed` и в `soft_matches` пишется строка с `score=NULL`? — нет: не пишется вовсе; читатель видит `soft_pending=False, fits_text=None` только по `soft_matches`-строке, поэтому для «не удалось» пишем строку `score=0.5, text=NULL, model="failed"` — нейтральный вклад, без текста, чтобы не крутить задачу бесконечно); `environment_text` пустой → модель не вызывается, строка `score=0.5, text=NULL, model="no_environment"`.

### 5.5 Cache key, инвалидация, повторный расчёт

- Ключ: `(summary_hash, program_id, prompt_version)`, `summary_hash = sha256(normalize(traits.summary))` (trim, схлопнуть пробелы, lower не делаем — регистр может нести смысл? делаем: `casefold` + схлопывание пробелов, чтобы правка запятой не инвалидировала кэш; `verbatim` в хэш **не** входит — иначе каждая новая черта, уже отражённая в резюме, вызывала бы пересчёт всех программ).
- Инвалидация: новая версия резюме → новый хэш → пересчёт только тех пар, которых нет; старые строки остаются (ученик мог откатить резюме — попадёт в кэш). Изменение `environment_text` программы (повторное извлечение) → строка **не** инвалидируется автоматически: `extract_program` при изменении `environment_text` удаляет строки `soft_matches` по `program_id` (индекс есть). Смена `prompt_version` — новые строки, старые читаются как фоллбек при `text_stale_ok_on_error` (роутер сначала ищет текущую версию, затем любую с пометкой `stale`).
- Повторный запуск задачи — пропуск готовых пар; частичный результат полезен сразу (запись по одной паре с коммитом).

### 5.6 Чтение в `GET /matching` (B3) и ранжирование (B1)

- `soft_scores = {program_id: score}` из `repo.soft_matches.get_many(summary_hash, program_ids, prompt_version)` (текущая версия; при отсутствии — предыдущая версия как `stale`).
- `matching.rank(profile, hard_results, soft_scores, params)` — уже реализовано: вклад `weight("program") · score`. B1 уточняет (правка своего файла): при `score is None` (нет строки) вклад = `weight · 0.5` (нейтрально, не штрафует — как `unknown`); программы `impossible` не поднимаются мягким фактором выше уровня. Мягкий фактор **не меняет** `realism`, `factors[].status` жёстких, `assumptions`.
- `MatchOut.fits_text = row.text` (или `None`), `MatchOut.soft_pending = (резюме непустое) and (строки нет)`; `factors` получают один `FactorOut(id="soft:environment", kind="soft", status="in_range"|"unknown", text=fit_text or "подбираем под твои предпочтения", source=None, weight=weight("program"))`.
- Если резюме пустое → `soft_pending=False`, `fits_text=None`, фактор `soft` не добавляется.
- Роутер, увидев `soft_pending=True` хотя бы у одной из отданных программ и отсутствие `keys.soft_pending(student_id) == summary_hash`, ставит `soft_match` через outbox (страховка, если событие потерялось); ключ ставит задача при старте.

### 5.7 Ошибки

LLM `down`/429 → `Retry`; невалидный выход дважды → нейтральная строка (§5.4); программа исчезла из кэша между постановкой и выполнением → пропуск; профиль изменился во время выполнения → задача продолжает под **своим** `summary_hash` (взят один раз при старте): результат не «устаревает» — он просто относится к старому хэшу и не читается; новая версия резюме породила свою задачу. Гонки нет: разные хэши — разные строки.

---

## 6. Извлечение программ — `search_programs` → `extract_program` (B2 задача и извлечение, B3 клиент, репозиторий, роутеры)

### 6.1 Pipeline

    POST /programs/search {query}  →  202 {search_id}   (B3; search_id = job_id)
      → [bulk] search_programs(query, student_id):
          rate-limit (§10.4) → search.client.search_programs(query, n=extract_max_urls_per_search)
          → фильтр URL (§6.2) → для каждого URL: если programs_cache.normalized_url есть и checked_at свежий → пропуск
          → outbox extract_program(url, student_id, query)
      → [bulk] extract_program(url, student_id?, query?):
          lock extract:{urlhash} → fetch_page (httpx, 10 с, follow_redirects, ≤ 40000 символов)
          → проверка страницы (§6.3) → search.extract.extract_program(llm, text, url) → Program (§6.4)
          → verify_against_source (§6.5) → правила приёма (§6.6) → дедуп (§6.7)
          → repo.programs.upsert_program (+ extraction meta) → outbox soft_match(student_id, [program_id]) при резюме
    GET /programs/search/{search_id} → {status: queued|running|done|unavailable, found: [program_id], rejected: int}   (B3; статус из Redis-ключа задачи + ARQ job status)

Инструмент ассистента `search_programs` (если введён в Ф3) обязан идти этим же путём: ставит задачу и отвечает «ищу, покажу в подборке» — извлечение в ответе чата не ждётся.

### 6.2 Поиск: Tavily, fallback ddgs, лимиты

- `search.client.search_programs` — как есть; B3 добавляет: `SEARCH_RPM` (счётчик `quack:search:rl`, при превышении `SearchUnavailable("rate limit")` → задача `Retry` 60 с) и месячный счётчик Tavily `quack:search:month:{yyyymm}` (инкремент только при вызове Tavily; при `≥ SEARCH_MONTHLY_CAP` — сразу `ddgs`, лог `tavily_cap_reached`).
- Запрос формируется задачей из `query` ученика; прогрев (`profile.updated` по направлению/странам) — `f"{direction} bachelor program admission requirements {country}"` по каждой стране из `preferences.countries` (≤ 3 стран, ≤ 1 прогрев в час на ученика — `job_id` `search:` с хэшем запроса и `keep_result=3600` для прогревов: B3 ставит прогревы с `_job_id="warm:{student_id}:{hour}"`).
- Фильтр URL: только `http(s)`; домен не в `program_domain_denylist`; не PDF/не бинарный (по расширению и `Content-Type` после fetch); нормализация: lower host, убрать `#fragment`, `utm_*`, `fbclid`, trailing `/`.
- Оба провайдера недоступны → `SearchUnavailable` → `Retry` 60 с, ×2, затем статус поиска `unavailable`; `/health.checks.search` (сейчас `skipped`) — B3 переводит в `ok/down` по последней ошибке поиска (ключ `quack:search:last_error`, TTL 300 с).

### 6.3 Fetch: таймауты, ошибки, недоступная страница, HTML без данных

| Ситуация | Поведение |
| :---- | :---- |
| невалидный URL | `ValidationFailed` из `fetch_page` → задача завершает `rejected(reason="invalid_url")`, без ретрая |
| timeout / 5xx / connection | `SearchUnavailable("page fetch unavailable")` → `Retry` 30 с, ×2, затем `rejected(reason="fetch_failed")` |
| 4xx (403/404/410) | без ретрая → `rejected(reason="http_{status}")` (B3: `fetch_page` пробрасывает статус в исключении — `FetchFailed(status)` наследник `SearchUnavailable`) |
| `Content-Type` не `text/html` | `rejected(reason="not_html")` |
| текст короче `extract_min_page_chars` | `rejected(reason="empty_page")` — модель не вызывается |
| страница-список/каталог (эвристика: > 30 ссылок в тексте и нет слов `admission|requirements|tuition|deadline|поступ|стоимост`) | `rejected(reason="not_program_page")` — модель не вызывается |

`rejected` — только лог `extract_rejected{url, reason}` + счётчик в статусе поиска; в `programs_cache` ничего не пишется. Ретраи fetch — внутри задачи через `Retry`, а не через httpx-ретраи (иначе таймаут задачи).

### 6.4 Извлечение (B2, `search.extract.extract_program(llm, html, url) -> Program`)

- Промпт `extract_program_v1` (есть) — рендер `{{page_text}}`; structured схема `ExtractedProgram` (B2, `schemas/programs.py` — B3 добавляет в скелете):

      ExtractedProgram(university: str | None, country: str | None, city: str | None, direction: str | None,
                       language: str | None, duration_months: int | None,
                       tuition_per_year: int | None, living_per_year: int | None, currency: str | None,
                       requirements: list[ExtractedRequirement], deadlines: list[ExtractedDeadline],
                       scholarships_note: str | None, environment_text: str | None,
                       evidence: dict[str, str])          # поле → короткая цитата из текста (≤ 120 символов), на которой основано значение
      ExtractedRequirement(type: Literal["exam_score","language","gpa","document","other"], exam_name: str | None,
                           threshold: float | None, comparator: Literal[">=","<=","range","present"] | None, description: str)
      ExtractedDeadline(kind: Literal["application","scholarship","exam_registration","other"], date: date | None, round: str | None, raw: str)

  «Неизвестно» = `None`. `evidence` — обязательная цитата для каждого заполненного числового/датного поля и для `university`; это вход в §6.5.
- Маппинг в `Program`: `exam_name` → `exam_id` только по словарю (`"SAT"→SAT_MATH` если упомянута математика или просто SAT, `"ЕНТ|ENT|UNT"→ENT_MATH`); иначе `exam_id=None` (требование сохраняется как `other`-подобное с `exam_id=None` и `threshold` — **не** участвует в `hard_filter` по баллу, но показывается). `currency` — только ISO-4217 из белого списка (`USD, EUR, GBP, KZT, RUB, CHF, CAD, TRY, PLN, CZK, HUF, AED, KRW, JPY, CNY, SGD, HKD, MYR`), иначе `tuition/living → None`. `id` = `slugify(university)-slugify(direction)` (≤ 60 символов, ASCII); `source_url = url`, `checked_at = today`, `is_demo=False`, `extracted_auto=True`, `flagged=False`. `deadlines[].date` без даты → отбрасывается (дедлайн без даты бесполезен), `source=url`, `is_demo=False`.
- Одна попытка + один ретрай клиента на невалидный JSON (уже в `structured`); `LLMUnavailable` → наружу.

### 6.5 Галлюцинации: проверка против источника (B2, чистая `search.extract.verify_against_source(program, extracted, page_text) -> (Program, dropped: list[str])`)

Для каждого заполненного поля из списка `{tuition_per_year, living_per_year, duration_months, requirements[].threshold, deadlines[].date, university}`: цитата из `evidence[field]` должна встречаться в `page_text` (сравнение после нормализации пробелов и регистра, допускается расхождение в разделителях тысяч), **и** само значение (число как строка в любом из форматов `1500`, `1 500`, `1,500`, `1.500`; дата — как ISO, `dd.mm.yyyy`, `d Month yyyy` на en/ru) должно встречаться в `page_text`. Не встречается → поле обнуляется (`threshold=None` → требование остаётся с `comparator="present"` и описанием; дедлайн без подтверждённой даты удаляется), имя поля → `dropped`. `university` не подтвердился → вся запись отбрасывается (`rejected(reason="university_not_in_source")`). `environment_text` и `description` не проверяются (свободный пересказ допустим, помечен `extracted_auto`).

### 6.6 Правила приёма (partial extraction)

Программа **принимается**, если после §6.5: `university`, `country` (ISO-2 по словарю названий стран, иначе `rejected(reason="country_unknown")`), `direction`, `language` непусты **и** есть хотя бы одно из: требование `exam_score`/`language` с подтверждённым `threshold`; подтверждённый `deadline` с датой; подтверждённый `tuition_per_year`. Иначе `rejected(reason="insufficient_fields", dropped=[...])`. `city` пустой → `city="—"`? Нет: `Program.city: str` обязателен — пустой `city` → берётся `country` название с пометкой в `extraction.notes`; не отбрасываем. Принятая с пропусками запись — нормальная: `unknown`-статусы факторов уходят в допущения (Ф2).

`ExtractionMeta{prompt_version, model, page_chars, dropped_fields, notes, search_query, requested_by: student_id | None, extracted_at}` → `programs_cache.extraction`.

### 6.7 Дубликаты

1. `normalized_url` совпал: запись есть → если `checked_at` старше `program_recheck_days` — повторное извлечение и **обновление** только если запись `extracted_auto=True` (ручной пол никогда не перезаписывается); свежая → пропуск ещё на этапе `search_programs`.
2. `(university_slug, direction_slug)` совпали с другой записью: существующая `is_demo=False, extracted_auto=False` (пол) → новая **не пишется**, лог `duplicate_of_floor`; существующая тоже `extracted_auto` → остаётся та, у которой больше подтверждённых полей (при равенстве — новее), у проигравшей `flagged=True`, `extraction.notes="superseded_by:<id>"` — подборка её не видит (`list_all` фильтрует `flagged`).
3. Сохранённые ссылаются на `program_id` — при замене дубликата `saved_programs.program_id` **не** переписывается (ученик сохранил конкретную запись); поэтому правило 2 никогда не удаляет строки, только флагует.

### 6.8 Поля `source_url`, `checked_at`, `extracted_auto` в выдаче

Каждая программа из извлечения в `MatchOut.factors[].source = Source(label=university, url=source_url, checked_at, is_demo=False)`; `Program.extracted_auto=True` фронт показывает как «извлечено автоматически» рядом с числами (product-logic §6.2). `POST /programs/{id}/flag {reason}` → `flagged=True`, 200; повторное — 200 (идемпотентно); ответ ассистента/подборка перестают её показывать; пол (`extracted_auto=False`) флаговать нельзя → 409.

---

## 7. Тексты сравнения и объяснение реалистичности (B2 генерация, B3 чтение)

### 7.1 `conclusion` сравнения — `jobs.compare_text`

- Триггер: `GET /matching/compare?ids=` → таблица `matching.compare` (Ф2, детерминированная) → `input_hash` от `{student_id, subject=sorted ids, rows с differs=True и relevant_to_student=True (param, values), топ-3 приоритетов, traits.summary_hash, prompt_version, model}` → `generated_texts(kind=compare)`: `ready` → `conclusion=text`; иначе `conclusion=None`, `conclusion_status` (новое поле `CompareOut.conclusion_status: GeneratedTextStatus`), задача через outbox.
- Промпт `compare_v1`: вход — только различающиеся строки таблицы (значения как строки, с источниками), приоритеты ученика, резюме черт; выход `CompareTextOut{conclusion: str ≤ 400}` «для тебя разница — …». Постпроверка: каждое число в тексте есть в `values` переданных строк (иначе регенерация → `failed`). Модель не выбирает параметры сравнения и не ранжирует — только формулирует, что из различий значимо по чертам и приоритетам.

### 7.2 «Почему реалистично» текстом — `jobs.realism_texts`

- Триггер: `GET /matching` — для отданных программ без `ready`-текста `kind=realism`: `subject=program_id`, хэш от `{student_id, program_id, realism, factors[] (id, status, text, source.label), assumptions, prompt_version, model}` — это и есть «кэш по хэшу профиля»: профиль входит через результаты `hard_filter`, а не сырьём, поэтому изменение поля профиля, не влияющего на факторы этой программы, кэш не ломает.
- Промпт `realism_text_v1`: вход — уровень и факторы со статусами и источниками; выход `RealismTextOut{text ≤ 400}`; правило — пересказать факторы словами, ничего не добавляя, уровень не менять, процентов нет. Постпроверка: числа текста ⊂ чисел в `factors[].text`.
- Чтение: `MatchOut.realism_text: str | None`, `realism_text_status: GeneratedTextStatus` (новые поля). При `LLM down` — `stale`-версия для старого хэша с пометкой, иначе `None` — фронт показывает факторы таблицей (это уже честный минимум Ф2).
- Ограничение расхода: не больше `limit` (по умолчанию 10) программ за запрос и один `_job_id` на `(student, profile_hash)` — повторные `GET` за 10 с дебаунса не плодят задач.

---

## 8. Quack — лента, темп, активность (B1 правила, B3 хранение и API)

### 8.1 Модели (`schemas/quack.py`, B3 пишет в скелете)

    Urgency        = Literal["urgent","high","normal","low"]
    RecStatus      = Literal["pending","shown","accepted","declined","expired"]
    RecKind        = Literal["pace_variant","milestone_due","conflict","next_set","set_change",
                             "program_new_fit","saved_realism_shift","diagnostic_suggested","activity_pause"]
    ActionKind     = Literal["profile_update","requirement_update","program_remove","set_open","set_edit","milestone_open","acknowledge"]

    RecommendationAction(kind: ActionKind,
                         profile_path: str | None, profile_value: Any | None,        # profile_update
                         exam_id: ExamId | None, target_score: float | None, test_date: date | None,   # requirement_update
                         program_id: str | None,                                     # program_remove / program_new_fit
                         set_id: UUID | None, skill_ids: list[str] | None, deadline: date | None,     # set_open / set_edit
                         milestone_key: str | None)
    RecommendationOut(id: UUID, kind: RecKind, urgency: Urgency, position: int, status: RecStatus,
                      title: str, reason: str, action_text: str,                      # «причина» и «действие» словами
                      action: RecommendationAction,
                      forecast_after: ForecastOut | None,                             # для pace_variant — прогноз после принятия
                      exam_id: ExamId | None, program_id: str | None, milestone_key: str | None,
                      reason_hash: str, created_at, shown_at: datetime | None, decided_at: datetime | None, expires_at: datetime | None)

    PaceVariantKind = Literal["more_hours","move_date","remove_program","lower_target"]
    PaceVariantOut(kind: PaceVariantKind, text: str, params: dict,                    # params: {hours_per_week} | {test_date, registration_deadline} | {program_id, new_target} | {target_score}
                   forecast: ForecastOut, available: bool, unavailable_reason: str | None,
                   affected_program_ids: list[str], recommendation_id: UUID | None)   # id открытой рекомендации того же варианта, если есть
    ExamPaceOut(exam_id, forecast: ForecastOut | None, on_track: bool | None, test_date: date | None,
                hours_declared: int | None, hours_actual: float | None, variants: list[PaceVariantOut], words: str)
    PaceOut(exams: list[ExamPaceOut], as_of: datetime)

    ActivityDay(day: date, active: bool, tasks_answered: int, mocks_completed: int, chat_messages: int, active_minutes: int)
    ActivityOut(days: list[ActivityDay], window_days: int, active_days: int, hours_per_week_actual: float | None,
                hours_per_week_declared: int | None, computed_at: datetime | None, tz: str)

    QuackOut(pace: PaceOut, items: list[RecommendationOut], activity: ActivityOut,
             new_batch: bool, batch_at: datetime | None, n_new: int)                 # new_batch — есть pending после последнего POST /quack/seen
    QuackSeenIn(recommendation_ids: list[UUID] | None)                                 # None → все pending
    RecDecisionIn(reason: str | None)                                                  # для decline

### 8.2 Генерация ленты — `quack.plan` (B1, чистый `app/quack/plan.py`) внутри `recommendations_batch`

Вход `PlanInputs` (собирает `apply.quack.collect_inputs` — B1 I/O): `today`, `profile`, `saved: list[Program]`, `requirements: list[ExamRequirementOut]`, `milestones`, `conflicts`, `forecasts: dict[ExamId, ForecastOut]`, `pace_variants: dict[ExamId, list[PaceVariantOut]]` (§8.3), `sets_by_exam`, `matching_now: list[MatchOut]` и `matching_prev: list[MatchOut] | None` (снапшот из последнего батча — `recommendations` с `kind=saved_realism_shift` хранят `from/to`; `matching_prev` восстанавливается из `quack:recs:batch` payload `{realism_by_program}`), `aggregates: StudentAggregates | None`, `open_recs: list[RecommendationOut]` (pending/shown), `declined_hashes: set[str]`, `params`.

Выход: `list[RecDraft(kind, urgency, title, reason, action_text, action, reason_hash, exam_id, program_id, milestone_key, forecast_after, expires_at)]` в итоговом порядке.

Правила (product-logic §3.6; всё детерминировано, без модели):

| kind | Когда | `reason_hash` от | Urgency | Действие |
| :---- | :---- | :---- | :---- | :---- |
| `pace_variant` | `forecast.on_track is False` по экзамену → по одному черновику на каждый `available` вариант | `("pace", exam_id, variant.kind, params)` | `urgent` (прогноз позже теста — product-logic §8.5) | по варианту (§8.3) |
| `conflict` | каждый `ConflictOut` | `("conflict", kind, sorted milestone_keys)` | `urgent` | `acknowledge`; текст `options` из Ф2 + для `exam_after_deadline` — ссылка на `move_date`-вариант |
| `milestone_due` | веха не `done`, `date − today ≤ urgent_milestone_days` → `urgent`; `≤ 14` → `high`; `≤ 30` → `normal` | `("milestone", key)` | по сроку | `milestone_open` |
| `next_set` | `current is None` и есть `upcoming` (сет закрыт, следующий не принят) | `("next_set", set_id)` | `high` | `set_open(set_id)` |
| `set_change` | `rebuild` изменил состав `upcoming[0]` относительно последнего батча (сравнение `skill_ids`) или дедлайн текущего сета прошёл | `("set_change", set_id, sorted skill_ids)` | `normal` | `set_edit` / `acknowledge` |
| `program_new_fit` | программа, которой не было в `matching_prev` с уровнем `possible/try`, теперь в топ-`limit` с `possible/try` (после изменения профиля или роста прогноза) | `("new_fit", program_id, realism)` | `normal` | `acknowledge` (действие — открыть карточку; сохранение — ученик сам) |
| `saved_realism_shift` | у сохранённой изменился `realism` (`matching.shift.diff`) | `("shift", program_id, from, to)` | `high` при ухудшении, `normal` при улучшении | `acknowledge` |
| `diagnostic_suggested` | есть требование с `has_knowledge_model` и нет завершённого замера по экзамену | `("diag", exam_id)` | `normal` | `acknowledge` |
| `activity_pause` | `aggregates.active_days_14 == 0` и есть текущий сет — **без укора**: «прогноз пересчитан, вот что изменить» (только если есть `pace_variant`-черновики — тогда не создаётся отдельно; иначе одна строка `low`) | `("pause", iso_week)` | `low` | `acknowledge` |

Порядок: `urgent` → `high` → `normal` → `low`; внутри — по дате (веха/дедлайн ближе — выше), затем по `kind` в порядке таблицы. `position` — индекс. Черновики с `reason_hash ∈ declined_hashes` — **не создаются** (отказ уважается, пока не изменилась причина; причина = хэш). Черновики, совпадающие с `open_recs` по `reason_hash`, обновляют `payload/position/urgency`, не создавая новых. Открытые рекомендации, чьего `reason_hash` нет в новом списке, → `expired`. `expires_at` — для `milestone_due` дата вехи, для остальных `None`.

`urgent=True`-запуск (из событий): считает всё то же самое, но **записывает** только `urgent`/`high` (плюс `expired` для исчезнувших); `normal/low` копятся до крона — «не шумит чаще ритма». Порция (`batch_id`, `quack:recs:batch`) фиксируется только при кроне или если urgent-запуск создал ≥ 1 новую `urgent` — тогда `new_batch=True` немедленно (product-logic §8.5: срочные выходят сразу).

`recommendations_batch` (B3 обёртка → `apply.quack.run_batch(session, deps, student_id, urgent)` — B1): лок `recs:{sid}`; входы; `quack.plan`; `repo.recommendations.reconcile(session, student_id, drafts, urgent_only) -> {created, updated, expired}`; ключ порции; `bump` **не** вызывается (Quack не модель знаний), но заголовок `X-Quack-Version`? — нет, фронт перечитывает `GET /quack` по таймеру и после действий.

### 8.3 Темп и четыре варианта — `sets.pace.variants` (B1, чистая) + `apply.pace.compute(session, deps, student_id, exam_id) -> ExamPaceOut`

Общий вход: `states` (из графа), `skill_weights`, `exam_format`, `p_target`, `hours_per_week` (профиль), `test_date` (планируемая: `academics.sat_date` при `stated`, иначе первая из `requirement.test_dates`), `effort`, `calendar: list[TestDate]`, `saved` с порогами по экзамену, `requirement` (target_score, target_source), `params`, `today`. Базовый прогноз — `sets.forecast.forecast(...)` (Ф2) с теми же входами; `on_track = ready_by ≤ test_date`.

| Вариант | input | deterministic recalculation | resulting forecast | response |
| :---- | :---- | :---- | :---- | :---- |
| `more_hours` | текущие `hours_per_week` h₀ | перебор `h = h₀ + k·pace_hours_step`, `k=1..`, пока `h ≤ pace_max_hours`; для каждого `forecast(hours_per_week=h)`; первый с `ready_by ≤ test_date` — ответ | `forecast(h*)` | `params={hours_per_week: h*}`, текст «6 ч/нед → готов 3 ноября»; `available=False, reason="exceeds_max_hours"` если не найден; действие `profile_update(pace.hours_per_week, h*)` |
| `move_date` | `calendar` | первая `TestDate.date > ready_by` (базового прогноза) с `registration_deadline ≥ today` | `forecast(test_date=d*)` (тот же `ready_by`, `on_track=True`) | `params={test_date, registration_deadline}`; `unavailable_reason="no_later_dates"`; действие `requirement_update(exam_id, test_date=d*)` → `profile.updated academics.sat_date` (SAT) / `academics.ent_date`? — ЕНТ даты нет в анкете: для `ENT_MATH` вариант формируется только если календарь даёт другой период, действие — `acknowledge` с текстом (не меняем анкету, поле не существует); отметить в §16 |
| `remove_program` | `saved` с `exam_score`-порогами по экзамену | программа с максимальным порогом (при равенстве — с более поздним дедлайном); `target' = max` остальных порогов (или `None`, если не осталось — вариант `available=False, reason="only_program"`); `p_target' = min(p_target_max, target'/max_raw)`; `forecast(p_target')` | `forecast'` | `params={program_id, new_target}`, `affected_program_ids=[program_id]`, действие `program_remove(program_id)` → событие `program.removed` — рекомендуется только если `forecast'.on_track` |
| `lower_target` | `target_score`, шаг `pace_target_step_*` | `t = target − k·step` вниз до `pace_min_target_share · target`; первый `t` с `forecast(p_target(t)).on_track` | `forecast(t*)` | `params={target_score: t*}`, `affected_program_ids` = сохранённые с порогом `> t*` (их реалистичность ухудшится — показывается словами), действие `requirement_update(exam_id, target_score=t*)` → `profile.updated academics.sat_target` (для ЕНТ — `academics.ent_target`: **поля нет в анкете Ф1**; добавить `Academics.ent_target: ProfileField[int]` в скелете — дельта §14.4, путь в белый список `PATCH /profile`) |

Все четыре считаются на каждый `GET /quack` (4–20 вызовов `forecast` на экзамен — чистая арифметика по ≤ 45 навыкам, миллисекунды; состояния — один Cypher, уже нужны прогнозу). Кэш: `PaceOut` целиком кладётся в Redis `keys.pace(student_id)` с `as_of_event_id = последний event_id ученика`; читается, пока `event_id` не вырос; TTL 600 с. LLM не участвует. `words` — «SAT Math: при 4 ч/нед готовность 20 ноября, тест 7-го — не успеваешь» из `sets.pace.words(...)` (B1, шаблонная строка).

`hours_actual` — из `student_aggregates.hours_per_week_actual` (§9), `hours_declared` — профиль.

### 8.4 Жизненный цикл рекомендации

    pending ──POST /quack/seen──▶ shown ──POST /quack/{id}/accept──▶ accepted
       │                            │─────POST /quack/{id}/decline─▶ declined
       └────── причина исчезла (батч) ─────────────────────────────▶ expired
    (pending может быть принята/отклонена и без seen — фронт мог показать её из urgent-порции)

| Операция | Событие | БД | Профиль / требования / сет | Idempotency и повторы |
| :---- | :---- | :---- | :---- | :---- |
| показ (`POST /quack/seen`) | нет (не действие ученика над знаниями; активность считается по `GET`? — нет: пишется событие? Решение: **нет события**, только `shown_at`; Quack-открытие как активность не считается — активность = задачи, моки, чат) | `pending → shown`, `shown_at` | — | повтор — 200, ничего |
| принять | `recommendation.accepted {recommendation_id, reason_hash, kind, action}` → `dispatch` → `apply.quack.apply_accept` (B1): по `action.kind` **пишет обычное событие** через `events.store.append(..., deps)` в той же сессии: `profile_update` → `profile.updated{by:"user"}`; `requirement_update.test_date` → `profile.updated academics.sat_date`; `requirement_update.target_score` → `profile.updated academics.*_target`; `program_remove` → `program.removed`; `set_open` → `apply.sets.open_set` + `set.opened`; `set_edit` → `repo.sets.update_set` + `set.deadline_changed`; `milestone_open`/`acknowledge` → ничего. Вложенный `append` с `dispatch` запускает те же правила Ф2 (пересборка, прогноз) — «как если бы ученик поменял сам» (product-logic §6.1) | `status=accepted`, `decided_at`, `decision_event_id`; в конце обработчика — outbox `recommendations_batch(urgent)` (лента обновится: принятый вариант темпа снимает остальные `pace_variant` того же экзамена как `expired`) | как в событии | повторный accept той же → 200 без событий; accept `declined`/`expired` → 409 `conflict`; чужая → 404; действие уже неактуально (сет `done`, программа не в сохранённых) → 409 `stale_recommendation` и статус `expired` |
| отклонить | `recommendation.declined {recommendation_id, reason_hash, kind, reason?}` → `dispatch` без правил (обработчик только логирует) | `status=declined`, `decided_at` | — | повторный decline → 200; decline `accepted` → 409; `declined_hashes` = все `declined` за 90 дней (`repo.recommendations.declined_hashes`) — та же причина не появится; изменение причины (новый хэш) — появится |
| устаревание | нет | `expired` батчем; `expires_at` прошло → тоже `expired` при следующем чтении? — нет, `GET` не пишет: батч ставит `expired`, `GET` просто фильтрует `expires_at < now` | — | принять/отклонить `expired` → 409 |

`GET /quack` отдаёт `items` = `pending` + `shown` (без `expired`), отсортированные по `position`; `GET /quack/history?limit=` — `accepted/declined/expired` последние N. Payload-модели: `RecommendationAcceptedPayload(recommendation_id: UUID, reason_hash: str, kind: RecKind, action: RecommendationAction)`, `RecommendationDeclinedPayload(recommendation_id, reason_hash, kind, reason: str | None)` — `reason_hash` в событии соответствует memory-architecture §1.2.

### 8.5 Роуты Quack (B3)

| Метод и путь | Тело → ответ | Что вызывает |
| :---- | :---- | :---- |
| `GET /quack` | → `QuackOut` | `apply.pace.compute` × экзамены требований (кэш Redis), `repo.recommendations.list_open`, `repo.aggregates.activity`, ключ порции |
| `GET /quack/pace` | → `PaceOut` | то же без ленты |
| `GET /quack/activity?days=` | → `ActivityOut` | `repo.aggregates` (`days ≤ aggregate_window_days`, иначе 400) |
| `POST /quack/seen` | `QuackSeenIn` → `{shown: int}` | `repo.recommendations.mark_shown`; outbox `daily_aggregates(student_id)` (открытие Quack — memory-architecture §10.7); сброс `new_batch` |
| `POST /quack/{id}/accept` | → `RecommendationOut` | append `recommendation.accepted` → dispatch → `apply_accept` |
| `POST /quack/{id}/decline` | `RecDecisionIn` → `RecommendationOut` | append `recommendation.declined` |
| `GET /quack/history?limit=` | → `Page[RecommendationOut]` | |

Заголовок `X-Knowledge-Version` — на `accept` (правила могли изменить сеты).

---

## 9. Дневные агрегаты — `daily_aggregates` (B1 правило `knowledge/aggregates.py`, B3 обёртка и репозиторий)

### 9.1 Что считается

    DailyAggregatePayload(day, tz, sessions: int, active_minutes: int, tasks_answered: int, tasks_correct: int, tasks_timed_out: int,
                          mocks_completed: int, chat_messages: int, guidelines_opened: int, first_event_at, last_event_at)
    StudentAggregates(student_id, window_days, computed_at, as_of_event_id,
                      hours_per_week_actual: float,             # Σ active_minutes за последние 7 полных дней / 60
                      hours_per_week_declared: int | None,
                      active_days: int,                          # дней с active=True в окне
                      active_days_by_day: dict[date, bool],
                      error_class_dist: dict[ErrorClass, float], # доли по Σ occurrence_count MisconceptionState (status ≠ disputed), Σ=1 или {} при отсутствии
                      pace_signals: {timeouts_7d: int, asked_to_slow_down_7d: int, hurried_share_7d: float | None, late_session_share_7d: float | None},
                      graph_stale: bool)

### 9.2 Источник событий и дедупликация

`events` за окно `[today − aggregate_window_days, today]` в `activity_tz` (границы дня переводятся в UTC): `task.answered` (+`correct` через `task_instances.correct` по `instance_id`), `task.timed_out`, `mock.completed`, `message.user` (только `chat_id` подготовки и подбора — все), `guideline.opened`/`explanation.opened`, `set.opened`, `diagnostic.completed`. Активность дня = `Σ событий из списка ≥ active_day_min_events`. `hurried_share` / `late_session_share` — из `task.answered.payload` (`time_spent_sec / time_reference` по экземпляру, `session_minute`). `asked_to_slow_down` — `observation.extracted` с `observations[].kind == "pace_signal"`. Дедупликация: событие считается один раз по `id`; повторная доставка события в лог невозможна (append-only с автоинкрементом), а повтор задачи пересчитывает окно целиком из тех же строк — результат идентичен (детерминированность — тест B1).

`active_minutes`: события группируются по `session_id`; минуты сессии = `last − first` (в минутах, минимум 1 на непустую сессию); сессия без `session_id` (старые события) — 1 минута на событие с потолком 30; разрывы длиннее `session_gap_min` внутри одной `session_id` (TTL продлевается при каждой записи, поэтому по построению не бывает) — режутся правилом на всякий случай. Сессия, пересекающая полночь, относится ко дню начала.

### 9.3 Timezone

`activity_tz` — один для всех (в анкете пояса нет; аудитория — Казахстан). День `d` = `[d 00:00, d+1 00:00)` в `Asia/Almaty`. В `ActivityOut.tz` возвращается имя пояса, чтобы фронт рисовал календарь в нём же.

### 9.4 Период, повторный запуск, пересчёт

Задача всегда пересчитывает **всё окно** (14 дней) и upsert-ит `daily_aggregates` по `(student_id, day)`; дни старше окна не трогаются (остаются как исторические). `student_aggregates` — одна строка, `as_of_event_id` = максимальный `event_id` ученика на момент расчёта. Повторный запуск в тот же день — тот же результат; `force=False` и `as_of_event_id` не вырос → пропуск (лог `aggregates_unchanged`).

### 9.5 Крон и пропуск

Крон 03:00 UTC (08:00 Алматы) — для активных за окно; открытие Quack (`POST /quack/seen`) — для одного ученика с `_job_id` `aggr:{sid}:{today}` (второе открытие в тот же день не ставит задачу; но события после первого расчёта не попадут до завтра — приемлемо? Нет: `hours_actual` в Quack должен видеть сегодняшнюю работу → `_job_id` дополняется часом: `aggr:{sid}:{YYYY-MM-DDTHH}` — не чаще раза в час на ученика, при пересчёте окна это дёшево). Пропущенный запуск (воркер лежал в 03:00): при `startup` ключ `quack:cron:last:daily_aggregates` старше 36 ч → постановка немедленно; окно 14 дней перекрывает любой разумный простой.

### 9.6 Чтение

`GET /quack/activity` и блок `activity` в `GET /quack` — из таблиц, без пересчёта; если строки `student_aggregates` нет → `hours_per_week_actual=None`, `computed_at=None`, календарь пустой с `active=False` (фронт показывает «считаем»); `POST /quack/seen` ставит задачу. Контекст репетитора (`profile`-слот, Ф3) читает `hours_per_week_actual` и `pace_signals` из `student_aggregates` — B1 добавляет чтение в `build_topic_context` (свой файл), при отсутствии строки — только заявленные часы.

---

## 10. Производительность и лимиты

### 10.1 Никогда в API-запросе

Вызов модели (кроме чата), поиск, `fetch_page`, генерация текстов любого вида, пересчёт агрегатов, планирование ленты (только чтение готовых строк), извлечение. `GET /quack/pace` — единственный «тяжёлый» расчёт в запросе, и он арифметический с кэшем по `event_id`.

### 10.2 Только в `bulk`

`pregenerate_set`, `soft_match`, `search_programs`, `extract_program`, `daily_aggregates`, `recommendations_batch`, `realism_texts`, `compare_text`, `outbox_replay`. В `interactive` из Ф4 — только `set_summary` (один вызов модели, ученик ждёт).

### 10.3 Параллельность

- `WorkerBulk.max_jobs = BULK_MAX_JOBS` (2): при `LLM_RPM_BULK = 10` две задачи по ~4 вызова в минуту не упираются в лимит; при большем лимите провайдера — поднять оба. `WorkerInteractive.max_jobs` — 10 (по умолчанию ARQ), задачи там короткие.
- Внутри задачи вызовы модели **последовательны** (никакого `gather` по программам/топикам): параллелизм регулируется числом воркеров, а не задачей — иначе rate-limit клиента превращается в очередь ожидающих корутин и таймаут задачи.
- Активные ученики для крона — `events` за `aggregate_window_days`; на хакатоне это единицы; верхняя граница задач на крон — 200 (лог при превышении, остальные — следующим запуском).

### 10.4 Rate limit LLM и приоритет чата

- Два независимых счётчика `quack:llm:ratelimit:chat` / `:bulk` уже есть; общий лимит провайдера делится конфигом: `LLM_RPM_CHAT + LLM_RPM_BULK ≤ RPM провайдера`, при этом `LLM_RPM_BULK ≤ 40 %` общего. Так `bulk` физически не может съесть долю чата.
- Дополнительно (B2, `LLMClient._acquire` для `slot="bulk"`): если `keys.llm_status()` == `degraded` **или** счётчик `chat` за текущую минуту ≥ 70 % `LLM_RPM_CHAT` (живой чат нагружен) — `bulk` ждёт до `_rate_limit_wait_s`, потом `LLMUnavailable("rate limit")` → задача `Retry(defer=30)`. Чат никогда не ждёт `bulk`.
- Ретраи и backoff: на уровне ARQ — `max_tries` (3 для генерации, 2 для поиска/извлечения через `ctx["job_try"]`-проверку внутри задачи), задержка `Retry(defer=…)`: LLM down — `LLM_RETRY_DEFER_S` (120), rate limit — 30, поиск/fetch — 60; экспоненты не нужно — источник задержки известен (TTL `down` = 120 с).
- Circuit breaker общий: `bulk`-ошибки тоже считаются в `quack:llm:errors` — 5xx провайдера на фоне уронят статус в `down` и остановят чат. Решение: `_record` для `slot="bulk"` **не** инкрементирует счётчик breaker при 429 (это наш лимит, не отказ провайдера), но инкрементирует при 5xx/timeout (провайдер действительно лежит — чат всё равно упадёт). B2, правка своего клиента, тест.

### 10.5 Rate limit поиска

`SEARCH_RPM` (5/мин, счётчик `quack:search:rl`), `SEARCH_MONTHLY_CAP` (800 из ~1000 Tavily free), `extract_max_urls_per_search` (5) → ≤ 5 извлечений на запрос → ≤ 5 вызовов `MODEL_BULK`. Прогрев — не чаще раза в час на ученика. `fetch_page` — 10 с, 40 000 символов; параллельных fetch нет.

### 10.6 Максимумы

| Что | Максимум |
| :---- | :---- |
| текстов на `pregenerate_set` | `2·(set_size + reviews) + checks` ≤ 10 вызовов |
| программ в `soft_match` | `soft_match_max_candidates + len(saved)` ≤ 15 + 10 |
| URL на поиск | 5; страниц на задачу извлечения — 1 |
| рекомендаций в ленте | 20 (`quack.plan` обрезает `low/normal` сверх лимита, `urgent/high` — все) |
| вариантов темпа | 4 на экзамен; перебор `more_hours` ≤ 20 шагов, `lower_target` ≤ 40 шагов |
| дней агрегатов | `aggregate_window_days` = 14 |
| `realism_texts` за запрос | `limit` (10) |

---

## 11. Ошибки — ожидаемое поведение

| Ситуация | Поведение |
| :---- | :---- |
| LLM timeout | `LLMUnavailable` от клиента; breaker учитывает; задача → `Retry(defer=LLM_RETRY_DEFER_S)`; строка остаётся `generating`; читатель — `stale`/`generating` |
| 429 провайдера / наш rate limit | `Retry(defer=30)`; breaker **не** трогается для `bulk` (§10.4); чат не страдает |
| 5xx провайдера | breaker: 3 за минуту → `down` 120 с; задача `Retry(defer=120)`; после `max_tries` — `failed` + `job.failed` |
| invalid structured output | клиент: один ретрай с сообщением об ошибке; второй провал → `LLMUnavailable("structured output failed")` → в задаче это **не** `Retry`: строка `failed`, `error="invalid_output"`, `attempts += 1`; задача идёт дальше по остальным элементам; повтор — только новым триггером или `regenerate` (нет смысла бить в ту же стену) |
| постпроверка не прошла (число не из фактов) | одна регенерация с указанием; затем `failed` с `error="postcheck"` — текст не отдаётся никогда (product-logic §6.2) |
| search failure (оба провайдера) | `Retry(defer=60)` ×2 → статус поиска `unavailable`; `/health.checks.search=down`; подборка — по полу и кэшу (пометка «показаны только проверенные программы» — фронт по `checks.search`) |
| fetch failure (timeout/5xx) | `Retry(defer=30)` ×2 → `rejected(fetch_failed)`; 4xx — без ретрая |
| invalid page (не HTML, короткая, каталог) | `rejected`, модель не вызывается, `job.failed` **не** пишется (это не сбой) |
| partial extraction | принимается по §6.6 с `dropped_fields` в `extraction`; недостаточно — `rejected(insufficient_fields)` |
| duplicate program | §6.7: пол выигрывает всегда; между авто — по числу подтверждённых полей; проигравшая `flagged` |
| Redis failure | постановка → `job_outbox` + `outbox_replay`; локи считаются свободными (лог); rate-limit пропускает (как в клиенте); `keys.pace` кэш — мимо, считаем заново; `knowledge_version`/`llm_status` — поведение Ф1–Ф3 |
| PostgreSQL failure | задача падает → ARQ retry; API — 500 как в Ф1; ничего наполовину: каждая запись — своя короткая транзакция |
| ARQ worker crash | незавершённая задача возвращается в очередь после `job_timeout`; `generating`-строки перезаписываются повтором; локи с TTL 120 с; ключ `text_job` TTL 600 с → роутер переставит задачу, если ARQ её потерял |
| duplicate job | `_job_id` + `keep_result=60`; внутри — лок и пропуск `ready`; уникальные индексы (`generated_texts`, `set_summaries.set_id`, `soft_matches` PK, `recommendations` частичный, `programs_cache.normalized_url`) — последняя линия |
| повторная доставка события (replay Ф5/Ф6, ручной `dispatch`) | обработчики Ф4 только ставят задачи с детерминированным `job_id` и пишут `set_summaries(generating)`/`opened_forecast` идемпотентно (upsert по `set_id`); `apply_accept` проверяет статус рекомендации до записи вложенных событий — повтор `recommendation.accepted` по уже `accepted` не создаёт второго `program.removed` |
| устаревший результат (входы изменились во время задачи) | текст: хэш взят при старте, результат пишется под этим хэшем; читатель считает текущий хэш → видит `stale` и (по триггеру) ставит новую задачу — старый результат не выдаётся за актуальный; `soft_match` — то же по `summary_hash`; рекомендации — батч перед записью перечитывает `open_recs` под локом; `set_summary` — сет `done`, входы заморожены |
| изменение профиля во время выполнения job | см. выше; плюс `recommendations_batch` при `urgent` дебаунс 5 с схлопывает серию правок; `search_programs`-прогрев с устаревшим направлением просто добавит программы в кэш — вреда нет, подборка фильтрует по текущему профилю |
| граф недоступен | §2.3 |
| сет удалён/пересобран до запуска `pregenerate_set` | `repo.sets.get_set` → `None` → `job_skipped`; частично — генерируются только существующие топики |
| ученик без резюме/без сохранённых | `soft_match` / `recommendations_batch` завершаются пустым результатом без ошибок; лента — `diagnostic_suggested` при требованиях, иначе пусто с `words` «сохрани программу — появится темп» (пустых экранов нет, product-logic §6.3) |

---

## 12. Кэширование — сводка

| Результат | Ключ | В хэше | TTL | Инвалидация | Stale-поведение | Версионирование | Старый результат при ошибке |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| гайдлайн | `generated_texts(kind=guideline, input_hash)`; поиск по `(student_id, kind, subject)` | навык (id, имя, описание), уровень словами, цель словами, предпосылки словами, видимые заблуждения + триггеры словами, `is_root`, дедлайн и позиция в сете, профиль (глубина, подсказка, часы), формат, теги шаблонов, `mode`, `prompt_version`, `model` | нет (строки живут) | смена любого входа → новый хэш; регенерация по `set.opened`/`topic.opened`/`regenerate` | показывается последний `ready` того же `subject` с `mark=saved_version` | `prompt_version` в хэше и в строке | да (`text_stale_ok_on_error`) |
| объяснение навыка | `kind=explanation`, `student_id=NULL`, `subject=skill_id` | навык, предпосылки (имена), формат, `explanation_depth`, версия, модель | нет | смена промпта/модели/данных навыка | как выше | да | да |
| отчёт по сету | `set_summaries(set_id)` | `SetStats` + версия + модель | нет | нет (сет закрыт, входы заморожены); повторный `set.completed` с другим `input_hash` — только если не `ready` | `text=None` + `stats` словами | `prompt_version` в строке | `stats` всегда есть — текст не критичен |
| soft match | `soft_matches(summary_hash, program_id, prompt_version)` | резюме (нормализованное), программа (id → `environment_text` меняется → строки удаляются), версия | нет | новое резюме → новые пары; новая версия → новые пары; `environment_text` изменился → удаление по `program_id` | предыдущая версия промпта читается как `stale` (без пометки наружу — `fits_text` тот же смысл) | да | да |
| извлечённая программа | `programs_cache(normalized_url)` | — (не хэш, а запись) | `program_recheck_days` для повторного извлечения | ручной `flag`; повторное извлечение только `extracted_auto` | запись `checked_at` показывается всегда | `extraction.prompt_version` | старая запись остаётся при провале повторного извлечения |
| рекомендация | `recommendations(student_id, reason_hash)` | kind + ключевые параметры причины (§8.2) | `expires_at` для вех | батч: причина исчезла → `expired`; решение ученика — терминально | лента отдаёт только `pending/shown`; `expires_at < now` фильтруется на чтении | нет | — |
| порция Quack | `quack:recs:batch:{sid}` | — | нет | каждый крон/urgent с новыми `urgent` | — | — | — |
| прогноз | `forecast_cache(student_id, exam_id)` (Ф2), `as_of_event_id` | — | нет | `rebuild_sets` при каждом событии Ф2 | `ForecastOut.note` | — | при графе `down` — последний из кэша с `note` (Ф2 поведение) |
| темп + варианты | `keys.pace(student_id)` (Redis, `PaceOut` JSON + `as_of_event_id`) | — | 600 с | `as_of_event_id` < последний `event_id` ученика → пересчёт | — | — | Redis недоступен → считаем заново |
| текст реалистичности | `kind=realism`, `subject=program_id` | результат `hard_filter` (уровень, факторы, допущения), версия, модель | нет | факторы изменились → новый хэш; задача по `GET /matching` | `stale` с пометкой | да | да |
| `conclusion` сравнения | `kind=compare`, `subject=sorted ids` | различающиеся строки, приоритеты, `summary_hash`, версия, модель | нет | как выше | `stale` | да | да |
| агрегаты | `daily_aggregates(student_id, day)`, `student_aggregates(student_id)` | — | нет | полный пересчёт окна; `as_of_event_id` | `computed_at` наружу | — | старая строка остаётся до успешного пересчёта |

---

## 13. Тесты — пишутся до кода, в отдельной сессии, `@pytest.mark.phase4`

Чистые модули — на числах, без БД. Всё с моделью — на `FakeLLMClient` со сценариями (валидный / невалидный / `LLMUnavailable` / rate limit). Живой провайдер — только чек-лист B2 в `docs/tz/checklists/phase4-live.md`.

### 13.1 B1 (`tests/quack/`, `tests/sets/`, `tests/knowledge/`, `tests/apply/`)

- `test_plan.py` — правила Quack: каждая строка таблицы §8.2 позитив/негатив; порядок `urgent → high → normal → low` и по дате внутри; `declined_hashes` подавляет; `open_recs` обновляются, не дублируются; исчезнувшая причина → `expired`; `urgent_only` не создаёт `normal/low`; лимит 20; `reason_hash` стабилен между вызовами и меняется при смене параметра причины.
- `test_urgency.py` — веха через 3 / 10 / 25 / 40 дней → `urgent/high/normal/нет`; `on_track=False` → `urgent`; конфликт → `urgent`; ухудшение реалистичности сохранённой → `high`, улучшение → `normal`.
- `test_pace.py` — четыре варианта на фикстуре из 5 навыков (числа из memory-architecture §4.7): `more_hours` находит минимальные часы; `pace_max_hours` → `available=False`; `move_date` — первая дата после `ready_by` с регистрацией в будущем; `remove_program` — программа с максимальным порогом, `affected_program_ids`, единственная программа → недоступен; `lower_target` — шаг и нижняя граница, `affected` = сохранённые с порогом выше; ни один вариант не вызывает ничего, кроме `forecast`; результат детерминирован.
- `test_report.py` — `set_stats`: `days_vs_deadline` ±; `top_growth` по `delta_p`; `level_before/after`; заблуждения `resolved` в интервале сета; `stats_words` без чисел вне `stats`.
- `test_aggregates.py` — на списке событий за 3 дня с двумя сессиями: `active_minutes`, `active_days`, `hours_per_week_actual`; граница дня в `Asia/Almaty` (событие в 22:30 UTC = следующий день); сессия через полночь — день начала; `error_class_dist` суммируется в 1; повторный расчёт даёт тот же результат (идемпотентность).
- `test_forecast_scenarios.py` — сценарии из product-logic §3.6 («при 4 ч/нед готовность 20 ноября, тест 7-го — не успеваешь; 6 ч/нед → 3 ноября; перенос на 5 декабря; убрать МИТ → готов 1 ноября») на фикстуре с подобранными `effort_h` — числа в ассертах.
- `test_rank_soft.py` — `soft_scores` меняют порядок только внутри уровня; `None` → нейтрально 0.5; `impossible` не поднимается.
- `tests/apply/test_quack_apply.py` (integration) — `apply_accept` по каждому `ActionKind` пишет ровно одно вложенное событие нужного типа; повторный accept — ни одного; `stale_recommendation` при сете `done`; `run_batch` под локом; `test_summary_stats.py` — `on_set_completed` пишет `set_summaries(generating)` и кладёт задачу в outbox; `test_pace_apply.py` — кэш `keys.pace` по `as_of_event_id`.

### 13.2 B2 (`tests/agents/`, `tests/search/`, `tests/llm/`)

- `test_texts_inputs.py` — `inputs_hash` детерминирован; меняется от `SkillLevel`, набора заблуждений, `prompt_version`, `model`; **не** меняется от `p_recall`, `request_id`, `set_id`; сериализация входов не содержит `p`/`conf` числами.
- `test_pregenerate.py` — `FakeLLMClient`: сет из 3 топиков + 1 check → 3 гайдлайна + 4 объяснения; порядок (первый топик первым); `ready` пропускается; невалидный выход дважды → строка `failed`, остальные `ready`, задача бросает; `LLMUnavailable(down)` → `Retry`; `attempts ≥ 3` → пропуск; постпроверка «ловушки только из входов».
- `test_set_summary.py` — текст из `stats`; число не из `stats` → регенерация → `failed`, `text=None`; `ready` не перегенерируется.
- `test_soft_match.py` — structured схема; цифры/% в `fit_text` → регенерация → нейтральная строка; пустое `environment_text` → без вызова; `summary_hash` нормализация (пробелы/регистр не меняют, слово меняет); пары `ready` пропускаются; 20 с на программу (`wait_for` с фейком, который спит).
- `test_extract.py` — `verify_against_source`: цитата и число есть → поле сохраняется; числа нет → `dropped`; `university` не подтверждён → `rejected`; форматы чисел `1 500`/`1,500`; даты `15.12.2026`/`15 December 2026`; маппинг `exam_name → exam_id`; валюта вне списка → `tuition=None`; правила приёма §6.6 (по одному случаю на каждое условие); `id`-слаг детерминирован.
- `test_extract_job.py` — пайплайн на фейках `fetch_page`/`search`: короткая страница → `rejected` без вызова модели; 404 → без ретрая; timeout → `Retry`; дубликат по `normalized_url` свежий → пропуск; дубликат с полом → не пишется; авто-дубликат — проигравшая `flagged`.
- `test_compare_realism_texts.py` — хэши; постпроверка чисел; `conclusion` только из различающихся строк.
- `test_prompts_phase4.py` — `guideline_v1`, `explanation_v1`, `set_summary_v1`, `soft_match_v1`, `compare_v1`, `realism_text_v1` загружаются, версия из имени, все `{{переменные}}` рендерятся на фикстуре без `KeyError`.
- `tests/llm/test_bulk_priority.py` — при `chat`-счётчике ≥ 70 % `bulk` ждёт и получает `LLMUnavailable("rate limit")`; `chat` не ждёт; 429 на `bulk` не инкрементирует `quack:llm:errors`, 5xx — инкрементирует.
- `test_retry_semantics.py` — таблица §11: какой `LLMUnavailable` даёт `Retry`, какой — `failed`.

### 13.3 B3 (`tests/workers/`, `tests/db/`, `tests/api/`, `tests/events/`)

- `test_registry.py` — `INTERACTIVE`/`BULK` ровно по §1.2; `cron_jobs` три записи с нужным расписанием; `keep_result=60`; `max_jobs`.
- `test_outbox.py` — `JobOutbox` копит; `flush_outbox` после коммита вызывает `enqueue` с `_job_id`/`_defer_by`; ошибка Redis → строка `job_outbox`; `outbox_replay` ставит и помечает `enqueued_at`; при откате транзакции outbox **не** флашится.
- `test_handlers_phase4.py` — таблица «тип → обработчики» дополнена строками Ф4 (`set.opened → on_set_opened_enqueue`, `set.completed → on_set_completed`, `profile.updated → on_profile_updated_enqueue`, `recommendation.accepted → apply_accept`, `recommendation.declined → log`, события §0.2 → `enqueue_recs_urgent`); типы вне списка — ноль новых.
- `test_migrations.py` — `0003` вверх/вниз; уникальные/частичные индексы существуют.
- `test_repo_texts.py` (integration) — `put/get` по `(kind, hash)`, поиск последнего `ready` по `(student, kind, subject)`, статусы, `attempts`; `test_repo_summaries.py` — `UNIQUE(set_id)`, `get_latest`; `test_repo_recommendations.py` — `reconcile` создаёт/обновляет/экспайрит, частичный индекс держит одну открытую на `reason_hash`, `declined_hashes` за 90 дней, `mark_shown`; `test_repo_soft_matches.py` — PK, `get_many` по версии с фоллбеком, удаление по `program_id`; `test_repo_aggregates.py` — upsert окна, `student_aggregates`; `test_repo_programs_phase4.py` — `normalized_url` уникален, `list_all` без `flagged`, слаги.
- `test_api_texts.py` — `GET /texts/{set}/{skill}?kind=` четыре статуса по таблице §3.5; нет строки и нет задачи → в outbox `pregenerate_set`; `opened` → событие `guideline.opened`; `regenerate` → 202 и задача; чужой сет → 404.
- `test_api_quack.py` — `GET /quack` собирает `QuackOut` с `fake_apply`; `seen` → `shown`, задача агрегатов в outbox, `new_batch=False`; `accept` → событие + результат обработчика + `X-Knowledge-Version`; повторный `accept` → 200 без нового события; `decline` после `accept` → 409; чужая → 404; `history`; `activity?days=100` → 400.
- `test_api_matching_phase4.py` — `fits_text`/`soft_pending` из `soft_matches`; пустое резюме → `soft_pending=False`; недостающие `realism`-тексты → задача в outbox один раз на `(student, hash)`; `compare` с `conclusion` из кэша и `conclusion_status`.
- `test_api_programs_search.py` — `POST /programs/search` → 202 + `search_id`, задача `search_programs` в outbox с `job_id` по запросу; `GET /programs/search/{id}` статусы; `flag` → `flagged`, пол → 409.
- `test_search_client_phase4.py` — нормализация URL; denylist; `SEARCH_RPM` → `SearchUnavailable`; месячный cap → `ddgs`; `FetchFailed(status)`.
- `test_cron.py` — `daily_aggregates_cron` ставит по задаче на активного ученика; `startup` при старом `cron_last` ставит задачу; `recommendations_batch_cron` пишет `cron_last`.
- `test_e2e_phase4.py` (integration, `FakeLLMClient` в воркере, ARQ в режиме `burst`): сценарии §15.

### 13.4 Критические сценарии — Given → When → Then (обязательные, интеграционные, `event → dispatch → job → result → read model`)

1. **Given** ученик с текущим сетом из 3 топиков и состояниями в графе, `FakeLLMClient` с валидными `GuidelineOut/ExplanationOut`. **When** `POST /sets/{id}/open`. **Then** событие `set.opened` записано; в outbox `pregen:{set_id}:{hash}`; после `worker.run(burst)` в `generated_texts` 3 `guideline` + 3 `explanation` со `status=ready`; `GET /texts/{set}/{skill}?kind=guideline` → `status=ready`, `mark=generated`, `prompt_version=guideline_v1`; повторный `POST /open` → задача с тем же `job_id` не выполняется второй раз (счётчик вызовов фейка не вырос).
2. **Given** то же, фейк отдаёт `LLMUnavailable` (down). **When** открыть сет, прогнать воркер. **Then** строки `generating`, задача завершилась `Retry`; `GET /texts` → `status=generating`; после переключения фейка на валидный и повторного прогона — `ready`.
3. **Given** ученик ответил на задачу после генерации (уровень навыка изменился со `shaky` на `solid`). **When** `GET /texts` для этого топика. **Then** `status=stale`, `text` прежний, `mark=saved_version`; **When** `POST /sets/{set}/topics/{skill}/open`. **Then** в outbox новая `pregen` с другим хэшем.
4. **Given** сет с 3 топиками, 5 отвеченных задач (4 верно), одно заблуждение перешло в `resolved` в интервале сета, `opened_forecast` сохранён. **When** закрыть последний топик (`set.completed`). **Then** `set_summaries` со `stats` (`tasks_answered=5, tasks_correct=4, misconceptions_resolved=[...]`, `forecast_before/after`) и `status=generating` в той же транзакции; после воркера `interactive` — `text` из фейка, `status=ready`; `GET /overview.last_set_summary.text` заполнен; `GET /sets/{id}/summary` тот же; фейк с числом «7 задач» → `failed`, `text=None`, `stats` на месте.
5. **Given** профиль с пустым резюме и 5 программами в кэше. **When** `PATCH /profile {path: traits.summary, value: "тёплый климат, небольшой город"}`. **Then** событие `profile.updated`; outbox `softmatch:{sid}:{hash}` с `defer 30`; после воркера — строки `soft_matches` для кандидатов; `GET /matching` → `soft_pending=False`, `fits_text` заполнен, порядок внутри уровня изменился относительно снапшота до задачи; уровни `realism` не изменились.
6. **Given** фейковый поиск отдаёт 2 URL, фейковый `fetch_page` — одну валидную страницу с университетом, порогом SAT 1400 и дедлайном, вторую — каталог. **When** `POST /programs/search {query}` → воркер. **Then** `programs_cache` +1 запись с `extracted_auto=True, source_url, checked_at=today, is_demo=False`, `extraction.dropped_fields` пуст; вторая — `rejected(not_program_page)`, модель вызвана один раз; `GET /programs/search/{id}` → `done, found=[id], rejected=1`; `GET /matching` содержит новую программу с `Source.url`. Фейк-модель подставляет `tuition=2000`, которого нет на странице → `tuition_per_year=None`, `dropped_fields=["tuition_per_year"]`.
7. **Given** две сохранённые программы (SAT 1450 и 1300), прогноз `ready_by` позже тест-даты, календарь с более поздней датой. **When** `GET /quack`. **Then** `pace.exams[SAT].on_track=False`, четыре варианта: `more_hours.available`, `move_date.params.test_date` > `ready_by`, `remove_program.params.program_id` = программа с 1450, `lower_target.affected_program_ids` содержит её; у каждого `forecast.on_track=True` (кроме недоступных); в `items` — `pace_variant`-рекомендации `urgent` с `forecast_after`.
8. **Given** п. 7. **When** `POST /quack/{id}/accept` на `more_hours`. **Then** события `recommendation.accepted` и вложенное `profile.updated{field: pace.hours_per_week, value: h*, by: user}`; профиль изменён; `forecast_cache` пересчитан (`on_track=True`); рекомендация `accepted`; после urgent-батча остальные `pace_variant` того же экзамена → `expired`; повторный `accept` → 200, событий не прибавилось.
9. **Given** п. 7. **When** `POST /quack/{id}/decline` на `remove_program`, затем крон-батч. **Then** `declined`, событие `recommendation.declined`; в новой ленте варианта `remove_program` с тем же `reason_hash` нет; **When** ученик сохраняет третью программу с порогом 1500. **Then** `reason_hash` варианта изменился → вариант снова в ленте.
10. **Given** события за 3 дня (задачи, мок, сообщения) с `occurred_at` по обе стороны полуночи Алматы. **When** `POST /quack/seen` → воркер. **Then** `daily_aggregates` по дням с ожидаемыми счётчиками, `student_aggregates.hours_per_week_actual` по формуле; `GET /quack/activity` → `active_days` = 3, `tz="Asia/Almaty"`; повторный запуск — те же строки.
11. **Given** веха регистрации через 3 дня, лента пустая. **When** `POST /overview/milestones/{other_key}` (любое событие из §0.2) → urgent-батч. **Then** `milestone_due` с `urgency=urgent`, `new_batch=True` немедленно (без ожидания крона); `normal`-черновики не записаны до крона.
12. **Given** сет закрыт, `set_summaries.ready`. **When** открыть первый топик следующего сета (Ф3 контекст). **Then** слот `previous_set` содержит текст summary; при `status=failed` — `stats_words`.

---

## 14. Дельта контрактов фазы 4 (`app/schemas/`, B3 пишет в скелете)

Поле с `?` — Optional. Всё ниже — добавления; ни одна существующая сигнатура Ф1–Ф3 не меняется, кроме явно перечисленных в §14.7.

### 14.1 `common.py`

    GeneratedTextStatus = Literal["ready","generating","stale","failed"]
    TextKind            = Literal["guideline","explanation","realism","compare"]
    TextMark            = Literal["generated","saved_version"]          # «сгенерировано» / «сохранённая версия»

### 14.2 `texts.py` — `GeneratedTextOut` (наружу; внутренняя `GeneratedText` остаётся)

| Поле | Тип | Обяз. | Значения |
| :---- | :---- | :---- | :---- |
| `kind` | `TextKind` | да | |
| `subject` | `str` | да | `skill_id` / `program_id` / `"a,b,c"` |
| `set_id` | `UUID?` | нет | |
| `status` | `GeneratedTextStatus` | да | |
| `text` | `str?` | нет | `None` при `generating`/`failed` без stale |
| `mark` | `TextMark?` | нет | `generated` при `ready`, `saved_version` при `stale` |
| `prompt_version` | `str?` | нет | `guideline_v1` … |
| `generated_at` | `datetime?` | нет | |
| `input_hash` | `str` | да | текущий хэш — для отладки и `regenerate` |
| `reason` | `str?` | нет | `llm_unavailable` / `not_generated` / `invalid_output` / `postcheck` при `failed` |

`TextOpenedIn(kind: Literal["guideline","explanation"])`.

### 14.3 `roadmap.py` / `sets.py`

    SetStats — §4.2 (в sets.py); SkillDelta(skill_id, name, level_before: SkillLevel, level_after: SkillLevel, p_before: float, p_after: float, delta_p: float)
    SetSummaryOut(set_id: UUID, exam_id: ExamId, status: Literal["generating","ready","failed"], text: str | None,
                  stats: SetStats, prompt_version: str | None, created_at: AwareDatetime, updated_at: AwareDatetime | None)
        # было: stats: dict[str, Any] — типизируется; text None допустим как и раньше

### 14.4 `profile.py`

    Academics += ent_target: ProfileField[int]          # цель по ЕНТ вручную (нужна lower_target и roadmap.requirements target_source=manual для ЕНТ)
    белый список путей PATCH /profile += "academics.ent_target"

### 14.5 `matching.py`

    SoftMatchOut(program_id: str, score: float (0..1), fit_text: str | None, caveat: str | None, matched_traits: list[str],
                 confidence: Literal["low","medium","high"], prompt_version: str, stale: bool)     # выход задачи и read-модель строки soft_matches
    MatchOut += realism_text: str | None, realism_text_status: GeneratedTextStatus, soft: SoftMatchOut | None
        # fits_text остаётся (= soft.fit_text) для совместимости фронта; soft_pending — как было
    CompareOut += conclusion_status: GeneratedTextStatus
    FactorOut.id для мягкого фактора: "soft:environment", kind="soft"

### 14.6 `programs.py`

    Program — поля без изменений; семантика: extracted_auto=True, is_demo=False, flagged=False для извлечённых; checked_at = дата извлечения
    Program += extraction: ExtractionMeta | None
    ExtractionMeta(prompt_version: str, model: str, page_chars: int, dropped_fields: list[str], notes: list[str],
                   search_query: str | None, requested_by: UUID | None, extracted_at: datetime)
    ExtractedProgram, ExtractedRequirement, ExtractedDeadline — §6.4 (схема structured output; все поля Optional, evidence: dict[str, str])
    SearchIn(query: str = Field(min_length=3, max_length=200)); SearchStartedOut(search_id: str, status: Literal["queued"])
    SearchStatusOut(search_id, status: Literal["queued","running","done","unavailable"], found: list[str], rejected: int, error: str | None)
    ProgramFlagIn(reason: str = Field(max_length=300))

### 14.7 `quack.py` — §8.1 целиком (`RecommendationOut`, `RecommendationAction`, `PaceOut`, `ExamPaceOut`, `PaceVariantOut`, `ActivityOut`, `ActivityDay`, `QuackOut`, `QuackSeenIn`, `RecDecisionIn`, `StudentAggregates`, `DailyAggregatePayload`)

Обязательность: в `RecommendationOut` все поля обязательны, кроме `forecast_after`, `exam_id`, `program_id`, `milestone_key`, `shown_at`, `decided_at`, `expires_at`. В `RecommendationAction` обязателен только `kind`; остальные — по `kind` (валидатор: `profile_update` требует `profile_path`+`profile_value`; `program_remove` — `program_id`; `set_open` — `set_id`; `set_edit` — `set_id` и хотя бы одно из `skill_ids`/`deadline`; `requirement_update` — `exam_id` и одно из `target_score`/`test_date`; `milestone_open` — `milestone_key`). `PaceVariantOut.forecast` обязателен даже при `available=False` (тогда — базовый прогноз).

### 14.8 `events.py` — payload-модели Ф4

    RecommendationAcceptedPayload(recommendation_id: UUID, reason_hash: str, kind: RecKind, action: RecommendationAction)
    RecommendationDeclinedPayload(recommendation_id: UUID, reason_hash: str, kind: RecKind, reason: str | None)
    TextOpenedPayload(set_id: UUID, skill_id: str, kind: Literal["guideline","explanation"], text_hash: str)   # guideline.opened / explanation.opened
    JobFailedPayload(job: str, args: dict, error: str, tries: int)                                              # job.failed (в Ф3 писался dict — закрепляется схема)
    _PAYLOAD_MODELS += recommendation.accepted/declined, guideline.opened, explanation.opened, job.failed

Новые типы событий **не вводятся**: `EventType` Ф1 уже содержит всё нужное.

### 14.9 Job payloads (kwargs ARQ; все — именованные, `request_id` добавляет `enqueue`)

| Job | kwargs | Обяз. |
| :---- | :---- | :---- |
| `pregenerate_set` | `set_id: UUID, student_id: UUID` | оба |
| `set_summary` | `set_id: UUID, student_id: UUID` | оба |
| `soft_match` | `student_id: UUID, program_ids: list[str]` | `program_ids` может быть `[]` |
| `search_programs` | `query: str, student_id: UUID | None, warm: bool = False` | `query` |
| `extract_program` | `url: str, student_id: UUID | None = None, query: str | None = None` | `url` |
| `daily_aggregates` | `student_id: UUID, day: date | None = None, force: bool = False` | `student_id` |
| `recommendations_batch` | `student_id: UUID, urgent: bool = False` | `student_id` |
| `realism_texts` | `student_id: UUID, program_ids: list[str]` | оба |
| `compare_text` | `student_id: UUID, program_ids: list[str]` | оба, 2–4 |
| `outbox_replay` | — | |

UUID передаются как `str` в kwargs (ARQ сериализует pickle — допустимо и UUID, но для читаемости логов — строки; задача конвертирует).

### 14.10 Сигнатуры между слоями

    # B1 чистые
    quack.plan.plan(inputs: PlanInputs, params, today) -> list[RecDraft]
    quack.plan.reason_hash(kind, **key) -> str
    sets.pace.variants(base: ForecastOut, inputs: PaceInputs, params, today) -> list[PaceVariantOut]
    sets.pace.words(exam_pace: ExamPaceOut) -> str
    sets.report.set_stats(inputs: ReportInputs, params, now) -> SetStats;  sets.report.stats_words(stats) -> str
    knowledge.aggregates.daily(events: list[Event], instances: dict[UUID, TaskInstance], tz: str, window: tuple[date, date]) -> list[DailyAggregatePayload]
    knowledge.aggregates.summarize(days: list[DailyAggregatePayload], misc_states: list[MisconceptionStateOut], profile: Profile, observations: list[Event], now) -> StudentAggregates
    # B1 I/O
    apply.quack.collect_inputs(session, deps, student_id) -> PlanInputs
    apply.quack.run_batch(session, deps, student_id, urgent: bool) -> BatchResult(created: int, updated: int, expired: int, batch_id: UUID | None)
    apply.quack.apply_accept(session, event, deps) -> RecommendationOut;  apply.quack.log_decline(session, event, deps) -> RecommendationOut
    apply.quack.on_profile_updated_enqueue(session, event, deps) -> None;  apply.quack.enqueue_recs_urgent(session, event, deps) -> None
    apply.pace.compute(session, deps, student_id, exam_id) -> ExamPaceOut;  apply.pace.compute_all(session, deps, student_id) -> PaceOut
    apply.summary_stats.on_set_completed(session, event, deps) -> SetStats
    apply.sets.on_set_opened_enqueue(session, event, deps) -> None          # opened_forecast + pregen job
    apply.texts.collect_inputs(session, deps, student_id, set_id, skill_id, kind) -> GuidelineInputs | ExplanationInputs
    apply.texts.on_topic_opened(session, event, deps) -> None                # stale → pregen
    apply.aggregates.run(session, deps, student_id, day, force) -> StudentAggregates
    # B2
    agents.texts.inputs_hash(kind, student_id, subject, inputs, prompt_version, model) -> str   # чистая
    agents.texts.generate_guideline(llm, inputs) -> str;  generate_explanation(llm, inputs) -> str
    agents.texts.generate_summary(llm, stats) -> str;  generate_soft_match(llm, inputs) -> SoftMatchOut
    agents.texts.generate_compare(llm, rows, priorities, summary) -> str;  generate_realism(llm, match: MatchOut) -> str
    agents.jobs.* — §14.9;  search.extract.extract_program(llm, html, url) -> Program;  search.extract.verify_against_source(...)
    # B3
    events.outbox.JobOutbox.enqueue(queue, fn_name, *, job_id, defer_by=0, **kwargs);  api.deps.flush_outbox
    workers.jobs_infra.daily_aggregates / recommendations_batch / outbox_replay / *_cron
    repo.texts.get_current(session, student_id, kind, subject, input_hash) -> tuple[GeneratedText | None, GeneratedText | None]   # (текущий, последний ready)
    repo.texts.mark(session, kind, input_hash, status, *, text=None, error=None, student_id, subject, set_id, model, prompt_version)
    repo.summaries.upsert_stats / set_text / get / get_latest
    repo.recommendations.list_open / reconcile / mark_shown / decide / declined_hashes / history
    repo.soft_matches.get_many / put / delete_for_program
    repo.aggregates.upsert_days / put_summary / activity / get_summary
    repo.programs.upsert_extracted(session, program, meta) -> Literal["created","updated","skipped_floor","superseded"];  find_duplicate(session, university_slug, direction_slug);  flag(session, program_id, reason)
    events.store.list_active_students(session, since) -> list[UUID]
    search.client.normalize_url(url) -> str;  search.client.allowed_url(url, params) -> bool;  FetchFailed(SearchUnavailable) с .status

---

## 15. Acceptance Criteria

Каждый пункт проверяется через API/БД/логи на `main` после мержа троих; сценарии 1–12 из §13.4 — автотестами, ниже — ручной прогон (`docs/tz/checklists/phase4-e2e.md`, ведёт B3).

1. **Открытие сета → гайдлайны.** `POST /sets/{id}/open` → в логах воркера `pregenerate_set` с `job_id pregen:*`; в течение 60 с `GET /texts/{set}/{skill}?kind=guideline` → `ready` для всех топиков; до этого — `generating`; при `LLM_FORCE_DOWN=1` — `generating`/`stale` с `mark=saved_version`, никогда пустой ответ без статуса.
2. **Завершение сета → summary.** Закрытие последнего топика → `set_summaries` со `stats` немедленно; `GET /overview.last_set_summary.text` заполнен в течение 10 с; при `LLM_FORCE_DOWN=1` — `text=None`, `stats` полные.
3. **Изменение предпочтений → soft match.** `PATCH /profile traits.summary` → через ≤ 60 с `GET /matching` отдаёт `fits_text` у ≥ 3 программ, `soft_pending=False`; `realism` не изменилась ни у одной.
4. **Поиск → extraction → Program.** `POST /programs/search` → 202; в течение 90 с `GET /programs/search/{id}` = `done`, `found ≥ 1` (на живом поиске) или `unavailable` при отключённом; новая запись в `programs_cache` с `extracted_auto=True`, `source_url`, `checked_at=today`; у каждого числа в карточке есть цитата в `extraction`/источник; `POST /programs/{id}/flag` убирает её из `GET /matching`.
5. **Quack feed.** `GET /quack` у ученика с сохранёнными: `pace` с прогнозом по каждому экзамену, `items` упорядочены по срочности, у каждой — `reason`, `action_text`, `action`; `activity` с 14 днями.
6. **Темп и варианты.** При `on_track=False` — 4 варианта, у доступных `forecast.on_track=True` и текст с датой; всё считается при `LLM_FORCE_DOWN=1` без изменений.
7. **Принятие.** `POST /quack/{id}/accept` меняет профиль/требование/сет (видно в `GET /profile`, `GET /overview`, `GET /sets`), прогноз пересчитан, рекомендация `accepted`; повтор — без изменений.
8. **Отказ.** `decline` → `declined`; после крона (или `recommendations_batch` вручную через `arq` CLI) та же причина не возвращается; изменение причины — возвращается.
9. **Activity days.** `POST /quack/seen` → в течение 30 с `GET /quack/activity` показывает сегодняшнюю задачу; `hours_per_week_actual` > 0 после сессии работы.
10. **Срочные.** Сохранение программы с конфликтом дат / веха ≤ 5 дней → в `GET /quack` в течение 15 с `urgent` с `new_batch=True`, без ожидания крона.
11. **Отчёт по сету** виден в Обзоре и в `GET /sets/{id}/summary`; следующий топик получает `previous_set`.
12. **Сквозное.** `make test && make test-int` зелёные; `openapi.json` содержит роуты §3.5, §6.1, §8.5; `schema.d.ts` перегенерирован; `pytest -m phase4` без `xfail`; `LLM_FORCE_DOWN=1` не меняет ни один ответ роутеров Ф2 и не ломает Ф4-роутеры (только статусы `generating/stale/failed`); в логах нет `job.failed` при живом провайдере на сценариях 1–11; `LLM_RPM_CHAT + LLM_RPM_BULK ≤` лимит провайдера записан в `llm-provider.md`.

---

## 16. Архитектурный review ТЗ — найденные проблемы и уточнения

Проверка по списку из задания; ниже то, что **не** закрывается текстом выше само собой, и решения, которые надо подтвердить на синке.

| # | Проверка | Вердикт | Проблема / уточнение |
| :---- | :---- | :---- | :---- |
| 1 | Тяжёлая работа синхронно в API | ок, с одним исключением | `on_set_completed` (статистика) и `apply_accept` (вложенные события → `rebuild_sets`) выполняются в транзакции запроса. Это правила Ф2 (полсекунды) — допустимо; но `set_stats` читает `get_state_history` по всем навыкам сета (≤ 5 навыков × 2 запроса) — держать ≤ 300 мс, тест на время в `test_summary_stats`. `GET /quack` считает 4 варианта × 2 экзамена — арифметика, но требует состояний из графа: кэш `keys.pace` обязателен, иначе каждое открытие Quack — Cypher. |
| 2 | `bulk` блокирует `interactive` | ок | Разные очереди и воркеры; разные RPM-бакеты; §10.4 добавляет уступку чату. **Открыто:** общий circuit breaker — 5xx на `bulk` уронит чат; принято осознанно (провайдер лежит для всех), 429 исключено из breaker. |
| 3 | Дубликаты при retry | ок | Уникальные индексы на всех кэшах; `_job_id`; локи. **Уточнение:** ARQ при `Retry` сохраняет `job_id` — повторная постановка того же `pregen` из роутера (страховка §3.5) отсекается ARQ; но если ARQ потерял задачу (Redis flush) — `keys.text_job` TTL 600 с даёт роутеру право переставить. |
| 4 | Идемпотентность jobs | ок | Каждая — пропуск готового + upsert; `daily_aggregates` — полный пересчёт окна; `recommendations_batch` — reconcile по `reason_hash`. **Открыто:** `search_programs` не идемпотентна по побочному эффекту «расход Tavily» — повтор после `Retry` тратит второй запрос; принято (лимит 800/мес с запасом). |
| 5 | Устаревание после изменения профиля | ок | Хэши берутся при старте задачи, читатель пересчитывает хэш → `stale`. **Уточнение:** гайдлайн включает часы/подсказку из профиля — смена `hours_per_week` через принятие `more_hours` инвалидирует все гайдлайны сета (`stale`), регенерация только по `topic.opened`. Это ожидаемо (текст «что решать» зависит от темпа слабо) — можно исключить `hours_per_week` из `GuidelineInputs`, оставив `explanation_depth`/`hint_level`. **Предлагаю исключить** — решить на синке. |
| 6 | Инвалидация кэша | ок | §12. **Проблема:** `soft_matches` не привязаны к `student_id` — два ученика с идентичным резюме делят строки (это плюс), но удаление по `program_id` при смене `environment_text` бьёт по всем — приемлемо. |
| 7 | Доверие данным поиска | ок | §6.5–6.6: ничего числового без цитаты в источнике; `university` без подтверждения — отказ; пол не перезаписывается; `flagged` убирает из подборки. **Открыто:** `environment_text` не верифицируется (пересказ) — помечен `extracted_auto`, в soft match идёт как есть; риск — модель «додумает» климат. Смягчение: промпт извлечения требует только факты страницы; тест на промпт-инъекцию в странице (текст «ignore instructions…» не меняет `university`) — добавить в `test_extract_job`. |
| 8 | LLM вместо правил | ок | Модель получает готовые факты и отдаёт текст/оценку соответствия; `postcheck` на числа во всех текстах; варианты темпа, лента, агрегаты, приём/отказ — без модели. |
| 9 | Race conditions | 2 замечания | (а) `set.opened` → `pregen` и одновременный `task.answered` → `rebuild` → состав `upcoming` меняется — на текущий сет не влияет (`keep_current`), ок. (б) `recommendations_batch(urgent)` и крон одновременно — лок `recs:{sid}` 120 с, второй пропускает: если пропущен крон — `normal`-рекомендации отложатся до следующего крона (до 24 ч). **Решение:** при занятом локе задача делает `Retry(defer=10)` вместо пропуска. (в) `apply_accept` пишет вложенные события в той же транзакции, а `flush_outbox` — после коммита: задачи из вложенных обработчиков попадают в тот же outbox (один на запрос) — ок. |
| 10 | Падение worker | ок | §11; `job_timeout` бросает задачу назад. **Уточнение:** `set_summary` в `interactive` с `job_timeout=30` при `LLM_TIMEOUT_BULK_S=90` — вызов модели может пережить таймаут задачи. Задача обязана вызывать модель через `asyncio.wait_for(…, 25)`; B2. |
| 11 | Безопасный повтор любой job | ок | см. 4; исключение — `search_programs` (расход), `extract_program` (`checked_at` свежий → пропуск, повтор безопасен). |
| 12 | Совпадение контрактов B1/B2/B3 | 3 несостыковки, закрыты в тексте | (а) `SetSummaryOut.stats: dict` (Ф2) → `SetStats` — фронт перегенерирует типы, поле остаётся объектом; (б) `Academics.ent_target` отсутствовал — добавлен (§14.4), `roadmap.requirements` (B2) должен читать его для `target_source=manual` по ЕНТ — строка в sync-log; (в) стаб `extract_program(ctx, request_id, url)` расширяется необязательными аргументами — совместимо. |

**Требуют решения на синке (не блокируют старт):**

1. Исключать ли `hours_per_week` из входов гайдлайна (см. 5).
2. `move_date` для ЕНТ: в анкете нет поля даты ЕНТ — вариант информационный (`acknowledge`) или добавляем `academics.ent_date`? Предлагаю добавить `ent_date` вместе с `ent_target` в 0003 (одно поле анкеты, белый список), тогда `requirement_update.test_date` работает для обоих экзаменов.
3. `POST /quack/seen` без события: активность Quack не считается в `active_days` — соответствует product-logic §3.6 (активность = задачи, моки, чат). Подтвердить.
4. Порог `70 %` уступки чату в `_acquire` — число из головы; калибровать по реальному RPM провайдера.
5. `explanation` без `student_id` (общий текст) — при персональных узлах (Ф6) потребуется `subject` с `student_id`; сейчас ок.
6. `phase3-agents.md` ещё не опубликован: если там `observe_chat` уже ввёл хелпер `job.failed` и `AgentDeps` в воркере — B2 переиспользует; если сигнатура `previous_set` другая — правка §0.2.

---

## 17. Порядок фазы и что вне

### 17.1 Первые пуши (параллельно, ничего не ждут)

| Кто | Что |
| :---- | :---- |
| **B3** | скелет `phase4-skeleton` (90 мин): схемы §14, `KnowledgeParams`/`Settings` §1.6, миграция `0003` + модели, репозитории с сигнатурами §14.10, `events/outbox.py` + `RuleDeps.jobs` + `flush_outbox`, `keys.py`, реестр §1.2 с импортом стабов (B2-стабы уже есть; для `realism_texts`, `compare_text`, `search_programs` — стабы `NotImplementedError("phase 4")` в `agents/jobs.py` добавляет B3 одной строкой каждый и отдаёт файл B2), `workers/jobs_infra.py` с обёртками, вызывающими стабы `apply.quack.run_batch` / `apply.aggregates.run`, `handlers.py` строки Ф4 на стабы `apply/*`, роутеры-заготовки с `fake_apply`, `test_layers` (`quack/` чистый; `apply/` без `app.llm`) |
| **B1** | `sets/pace.py`, `sets/report.py`, `quack/plan.py`, `knowledge/aggregates.py` — чистые, на моделях Ф2 + свои (`PlanInputs`, `PaceInputs`, `ReportInputs`, `RecDraft` — в своих файлах, поля по §8–§9); тесты §13.1 на числах |
| **B2** | промпты шести видов + `agents/texts.py` (генераторы + `inputs_hash` + валидаторы) на `FakeLLMClient`; `search/extract.py` (`verify_against_source` — чистая, тестируется без сети); тесты §13.2 |

### 17.2 Порядок мержа

1. B3 скелет → все ребейзятся.
2. B1 чистые (`pace`, `report`, `plan`, `aggregates`) → B3 снимает `fake_apply` на `GET /quack/pace`.
3. B2 `texts` + `extract` (без задач) → B1 `apply.*` (I/O) → B2 `jobs.*` (используют `apply.texts.collect_inputs`, `repo.*`).
4. B3 роутеры без фейков, крон, `test_e2e_phase4`; ручной прогон §15; `make types`.
5. Синк: sync-log, дельта контрактов Ф5.

### 17.3 Вне фазы

Персональные узлы (`propose_personal_nodes`), replay, полный SAT-мок, напоминания вне Quack (Ф6); фоллбек-контроллер как единая точка, автоперезапуск отложенных задач при восстановлении модели, отложенное применение событий при упавшем графе, демо-аккаунт, деплой, эмуляция отказов (Ф5); чистка старых `generated_texts`; timezone в анкете; конвертация валют; любые вызовы `MODEL_CHAT` из фона.
