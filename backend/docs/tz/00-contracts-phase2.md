# Фаза 2 — дельта контрактов

Quack! · фаза 2 «правила» · v0.1 · 18.09.2026. Дополняет `00-contracts.md` (фаза 1): всё, что там написано, действует, здесь только новое и изменённое. Источники: `memory-architecture-quack.md` §4–§8, §10, §12; `product-logic.md` §3.3–§3.5, §4.1–§4.4, §6.1, §9; `backend-phases.md` §2.

Читают все трое. Задания — в `10-B3-phase2.md`, `20-B1-phase2.md`, `30-B2-phase2.md`. После мержа скелета менять только через `docs/sync-log.md` и на синке.

---

## 1. Что такое фаза 2

Всё, что product-logic §7 называет правилами, работает без языковой модели: ответ на задачу меняет состояние навыка, статус заблуждения и сеты в одной транзакции; сохранённые программы порождают требования, вехи и конфликты; профиль порождает подборку с реалистичностью; замер спускается по пререквизитам; моки собираются по формату экзамена. Фронт получает read-модели «Подготовки» и «Подборки» с реальными числами. Всё работает при `LLM_FORCE_DOWN=1`.

Результат фазы: тестовый ученик через API отвечает на задачу и видит новое состояние навыка; проходит замер; сохраняет две программы и видит требования, вехи и конфликт; видит сет с дедлайном и прогноз; `GET /matching` возвращает ≥ 3 программы с уровнем реалистичности и факторами с источниками; `PATCH /profile` меняет порядок сразу. Шаги 4–8 сценария жюри проходятся без чата.

Принцип нарезки на троих (см. `backend-phases.md` §1): скелет B3 с контрактами до старта, дальше три ветки по владельцам модулей без общих файлов. Обязательные первые пуши каждого — в §9.

---

## 2. Владение — что добавляется

    apps/api/app/
      schemas/  sets.py roadmap.py diagnostic.py mocks.py matching.py   B3 пишет в скелете, содержание — §6
                knowledge.py  (+ MisconceptionStateOut, EvidenceOut, RootCauseOut, ForecastOut)
                events.py     (+ payload-модели §6.7)
      db/models.py (+ таблицы §3.4), db/repo/ sets.py diagnostic.py mocks.py milestones.py forecast.py   B3
      events/dispatch.py (RuleDeps, результаты обработчиков), events/handlers.py (реестр), events/version.py   B3
      api/ tasks.py sets.py diagnostic.py mocks.py matching.py overview.py knowledge.py   B3
      apply/     task_answered.py profile_updated.py dispute.py sets.py diagnostic.py mocks.py   B1  (единственный слой B1 с I/O)
      knowledge/ reconcile.py (чистый) misconceptions.py diagnostic.py roots.py   B1
      sets/      queue.py assemble.py forecast.py   B1
      matching/  hard.py realism.py rank.py compare.py   B1
      tasks/     select.py mocks.py   B1
      roadmap/   requirements.py milestones.py conflicts.py   B2  (чистый, без I/O)
      seed/      misconceptions.py — читает каталог, не файл   B1
    scripts/     gen_templates.py   B2
    data/        templates/sat/{alg,adv}/   B1 · templates/sat/{psda,geo}/   B3 · templates/ent/**   B2
                 misconceptions/<area>.json — владелец тот же, что у шаблонов области
                 programs_floor/programs.json, knowledge_base/calendars.json   B3
    tests/       apply/ knowledge/ sets/ matching/ tasks/   B1 · roadmap/ llm/ agents/   B2 · api/ db/ events/   B3
    docs/tz/phase2/   этот пакет

Правило владения из фазы 1 без изменений: файл правит только владелец, остальное через `sync-log.md`.

**Изменение правила слоёв (contracts §4.4).** `knowledge/`, `tasks/`, `sets/`, `matching/`, `roadmap/` — чистые, без I/O, без импорта `app.db`, `app.graph`, `app.llm`, `app.agents`, драйверов. `knowledge/reconcile.py` из фазы 1 нарушал это (принимал `session`) — в фазе 2 он становится чистым, а I/O переезжает в новый пакет `app/apply/` (B1), которому разрешены `app.db.repo`, `app.graph.queries`, `app.events`. `tests/test_layers.py` (B3) расширяется на `roadmap/` и `apply/`.

---

## 3. Решения фазы

### 3.1 Событие → правило → результат

Один путь записи для всего персонального: роутер → `events.store.append` → `events.dispatch.dispatch(session, event, deps)` → обработчики из `events/handlers.py`. Обработчик — функция из `app/apply/` (B1) или `app/db/repo` (B3).

- `RuleDeps` — dataclass в `events/dispatch.py` (B3): `graph: AsyncDriver | None`, `redis: Redis`, `params: KnowledgeParams`, `now: Callable[[], datetime]`. B3 конструирует из `app.state` в `api/deps.py` (`get_rule_deps`).
- Сигнатура обработчика: `async def handler(session: AsyncSession, event: Event, deps: RuleDeps) -> Any`. `dispatch` возвращает `dict[str, Any]` — результат каждого обработчика по его `__name__`. Роутер `POST /tasks/{id}/answer` берёт `AnswerResult` из результата `apply_task_answered`, не пересчитывает.
- Транзакция: `append` и все обработчики в одной сессии Postgres; коммит после `dispatch`. Граф пишется внутри обработчика через `graph.queries.personal.*` (своя транзакция Neo4j). Если граф упал (`deps.graph is None` или ошибка драйвера) — обработчик пишет событие как есть, `processed_at` остаётся `NULL`, роутер отдаёт результат по грейду без состояния (`state_after=None`), продукт не падает (memory-architecture §11.4). Отложенное применение — фаза 5, но `processed_at` ставится только при успешной записи в граф уже сейчас.
- `knowledge_version`: единственная точка инкремента — `events.version.bump(redis, student_id) -> int` (B3). Вызывает `apply/*` в конце каждого обработчика, который тронул персональный слой.
- Идемпотентность: `Evidence` — `MERGE {event_id, skill_id}`; повторный `dispatch` того же события не удваивает счётчики (условие replay §8.8). Тест B1.

### 3.2 Где лежат сеты, замер, моки, вехи

В Postgres, как read-модели, ссылками на `skill_id` графа. В графе только состояния, свидетельства, заблуждения, корни. Причина: списки и статусы нужны фронту простыми запросами; пересборка очереди — чистая функция над состояниями из графа, результат кладётся в таблицы. Таблицы — §3.4.

Пересборка сетов (`apply/sets.rebuild_sets`) вызывается: после каждого `task.answered` (шаг 10 §8.2), `profile.updated` по путям `pace.hours_per_week`, `academics.sat_date`, `academics.sat_target`, `academics.ent_trial_score`, `program.saved/removed`, `set.switched_by_user`, `set.deadline_changed`, `misconception.disputed/undisputed`, `diagnostic.completed`, `mock.completed`. Пересборка не трогает сет со статусом `done` и не меняет текущий сет без явного `set.switched_by_user`, только его дедлайн-прогноз и состав предстоящих.

Прогноз кэшируется в `forecast_cache` по `(student_id, exam_id)` с `as_of_event_id`; читает подбор (`matching.realism`) и обзор.

### 3.3 Целевой балл и цель по навыку

Цель по экзамену `target_score` = максимальный порог `Requirement{type: exam_score}` среди сохранённых (product-logic §4.1), переопределяется полем анкеты `academics.sat_target` / целевой ЕНТ, если ученик выставил вручную. `p_target` навыка = `min(p_target_max, target_score / max_raw_score)` для всех навыков экзамена (memory-architecture §4.4). Считает `roadmap.requirements` (B2), читает `sets.queue` (B1) через `RequirementOut.target_score`. Связывает их `apply.targets.p_target_for(session, deps, student_id, exam_id)`: если порог назван в шкалированных баллах (SAT 700 при `max_raw_score` 58), он сперва переводится в сырые по таблице экзамена — иначе доля всегда больше единицы и цель ни на что не влияет.

### 3.4 Postgres — миграция `0002_phase2`

Одна миграция, B3, в скелете. Все таблицы сразу.

| Таблица | Колонки | Заметка |
| :---- | :---- | :---- |
| `sets` | `id UUID PK`, `student_id`, `exam_id`, `status` (`upcoming/current/done`), `position INT`, `deadline DATE`, `reason TEXT`, `kind` (`regular/review/consolidation`), `opened_at`, `completed_at`, `created_at`, `rebuilt_at` | индекс `(student_id, exam_id, status)` |
| `set_topics` | `set_id FK`, `skill_id`, `position`, `kind` (`topic/check/review`), `status` (`open/closed`), PK `(set_id, skill_id)` | `check` — короткая проверка 2–3 задачи для `conf < c_vis` |
| `diagnostic_runs` | `id UUID PK`, `student_id`, `exam_id`, `status` (`active/completed/abandoned`), `state JSONB` (`DiagnosticState`), `result JSONB` (`DiagnosticResult`), `started_at`, `completed_at` | один активный на ученика и экзамен |
| `mock_runs` | `id UUID PK`, `student_id`, `exam_id`, `kind` (`mock_set/mock_topic/mock_misconception`), `set_id?`, `skill_id?`, `misconception_id?`, `section_name`, `instance_ids UUID[]`, `predicted_before FLOAT?`, `raw_score FLOAT?`, `scaled_score FLOAT?`, `status` (`active/completed/abandoned`), `started_at`, `completed_at` | |
| `milestone_marks` | `student_id`, `milestone_key TEXT`, `done_at`, PK `(student_id, milestone_key)` | вехи выводятся правилом, хранится только отметка |
| `forecast_cache` | `student_id`, `exam_id`, `payload JSONB` (`ForecastOut`), `as_of_event_id BIGINT`, `updated_at`, PK `(student_id, exam_id)` | |
| `task_instances` | + `mode TEXT?`, + `issued_event_id BIGINT?`, + `answered_at?`, + `correct BOOL?` | `correct` пишет `apply_task_answered` через `repo.tasks.mark_answered` — для `SetProgress` и статистики сета |

### 3.5 Neo4j — новое в персональном слое

`MisconceptionState` с полями §2.2 (`status`, `occurrence_count`, `strong_count`, `consecutive_avoided`, `triggers` JSON-строкой, `first_seen_at`, `updated_at`, `disputed_at?`, `previous_status?`), связи `(:Student)-[:HAS_MISC]->(:MisconceptionState)-[:ABOUT]->(:Misconception)`; `ROOT_CAUSE` от `Evidence` к `Skill` с `confidence`, `source`, `created_at`; `KnowledgeState` со связью `PREVIOUS` — уже есть. Индексы: `MisconceptionState(student_id, misconception_id)`, `Evidence(student_id, observed_at)`. Схема и индексы — B1, применяются `apply_schema` идемпотентно.

### 3.6 Датасет фазы

Цель — по 2–3 шаблона на каждый навык обоих экзаменов, распределение типов и сложности как в `ExamFormat.sections[].item_types / difficulty_shares`. Владение по папкам (§2), формат — `docs/data-formats.md` без изменений. Библиотека заблуждений режется на файлы по областям: `data/misconceptions/<area3>.json` (`alg.json`, `adv.json`, `psda.json`, `geo.json`, `ent_*.json`), загрузчик читает каталог. Существующий `library.json` B1 раскладывает по областям в своём первом пуше. Новое заблуждение добавляет владелец области; ссылка на чужое — через `sync-log`. `seed.py --validate` в CI обязателен: сломанный шаблон не доезжает до `main`.

---

## 4. Соглашения — дополнения

### 4.1 Идентификаторы

| Что | Формат | Пример |
| :---- | :---- | :---- |
| `set_id`, `run_id` (замер, мок) | UUID v4 | — |
| `milestone_key` | `<kind>:<exam_or_program_id>:<date>` | `registration:SAT_MATH:2026-10-10`, `application:nazarbayev-cs:2026-12-15` |
| `factor_id` жёсткого фактора | `<type>[:<exam_id>]` | `exam_score:SAT_MATH`, `budget`, `grant`, `language`, `deadline` |
| `evidence_id` | `"{event_id}:{skill_id}:{ordinal}"` (как возвращает `merge_evidence`; `ordinal` разводит несколько свидетельств одного события по одному навыку — ответ и попадание в заблуждение) | `4412:sat.alg.abs_value_eq:0` |

### 4.2 HTTP — новые правила

- Все новые роуты требуют cookie (contracts §3.1). Чужой `set_id` / `run_id` / `instance_id` → 404.
- Действия над состоянием (`answer`, `skip`, `switch`, `dispute`, `milestone done`) — `POST`, 200 с обновлённым объектом. Создание (`start` замера, мока) — 201.
- Read-модели отдаются из Postgres; из графа только `knowledge/*` (состояния и свидетельства). Ни один `GET` не пишет.
- Заголовок `X-Knowledge-Version` на ответах роутеров `tasks`, `diagnostic`, `mocks`, `knowledge`, `sets` — текущее значение после запроса, чтобы фронт не ждал polling.

### 4.3 Уровни реалистичности и статусы — словами

`Realism = "impossible" | "try" | "possible"` (уже в `common.py`). Статус жёсткого фактора `FactorStatus = "below" | "in_range" | "above" | "unknown"`. Состояние навыка словами `SkillLevel = "low_data" | "weak" | "shaky" | "solid" | "closed"` — функция `knowledge.words.skill_level(state, params)` (B1): `conf < c_vis → low_data`; иначе по `p_recall`: `< 0.5 weak`, `< p_target shaky`, `≥ p_target и conf ≥ c_close → closed`, иначе `solid`. Одна функция, одни пороги для обзора, сетов, контекста репетитора.

### 4.4 Redis — новые ключи (`app/keys.py`, B3)

| Функция | Ключ | Содержимое | TTL |
| :---- | :---- | :---- | :---- |
| `keys.forecast(student_id, exam_id)` | `quack:forecast:{sid}:{exam}` | резерв, не используется в Ф2 (кэш в Postgres) | — |
| `keys.lock(f"rebuild:{sid}")` | `quack:lock:rebuild:{sid}` | лок пересборки сетов, 10 с | 10 с |

---

## 5. Параметры — дополнения к `KnowledgeParams`

Добавляет B3 в скелете, значения из memory-architecture §12 и product-logic; переопределяются `KNOWLEDGE__<ИМЯ>`.

| Параметр | Значение | Где |
| :---- | :---- | :---- |
| `check_size` | 3 | короткая проверка предпосылки в сете (§10.1) |
| `review_window_days` | 7 | навыки с `due_at` в окне идут повторением |
| `consolidation_days` | 7 | последний сет перед тестом — закрепление |
| `mock_set_min` / `mock_set_max` | 8 / 12 | §10.2 |
| `mock_topic_min` / `mock_topic_max` | 5 / 7 | §10.2 |
| `mock_misc_n` | 3 | §10.2 |
| `diag_reask_after` | 3 | повтор ловушки через N задач (§8.4) |
| `min_candidates` | 3 | подборка не короче трёх программ (§3.3) |
| `matching_priority_weights` | `{realism: 3, cost: 2, ranking: 1, location: 1, program: 2, research: 1, mobility: 1}` | веса факторов по умолчанию; ранжирование приоритетов ученика их переупорядочивает (§3.3) |

---

## 6. Общие Pydantic-модели — дополнения к `app/schemas/`

Пишет B3 в скелете. Поле с `?` — Optional.

### `common.py`

    FactorStatus = Literal["below","in_range","above","unknown"]
    SkillLevel   = Literal["low_data","weak","shaky","solid","closed"]
    SetStatus    = Literal["upcoming","current","done"]
    TopicKind    = Literal["topic","check","review"]
    RunStatus    = Literal["active","completed","abandoned"]
    MockKind     = Literal["mock_set","mock_topic","mock_misconception"]
    Source(label: str, url: str | None, checked_at: date | None, is_demo: bool)   # рядом с каждым числом

### `knowledge.py` — дополнения

    MisconceptionStateOut(misconception_id, name, status: MisconceptionStatus, occurrence_count: int, strong_count: int,
                          consecutive_avoided: int, triggers: dict, first_seen_at, updated_at, skill_ids: list[str],
                          visible_label: str)                       # «подозрение, 1 из 2» / «подтверждено, N наблюдений» / «исправлено, следим»
    EvidenceOut(evidence_id: str, event_id: int, ordinal: int, skill_id, kind, tier, source, weight, direction, observed_at,
                summary: str | None, instance_id: UUID | None, message_id: UUID | None)   # раскрытие «почему так считаешь»
    RootCauseOut(from_skill_id, root_skill_id, confidence: float, source: Literal["diagnostic","observer","rule"], created_at)
    SkillStateView(skill_id, name, area_id, exam_id, weight: float, p_target: float, level: SkillLevel, p_recall, confidence,
                   trend: Literal["up","flat","down"], due_at: datetime | None, is_root: bool, n_evidence: int)
    ForecastOut(exam_id, predicted_raw: float, predicted_scaled: float | None, coverage: float, hours_needed: float,
                ready_by: date | None, test_date: date | None, on_track: bool | None, as_of_event_id: int, note: str)   # note: «оценочно» / «по твоей оценке»
    ReconcileResult(evidence: list[EvidenceIn], state_after: KnowledgeStateOut, cross_exam_state: KnowledgeStateOut | None,
                    misconception_change: MisconceptionChange | None, root_causes: list[RootCauseOut], words: str)
    MisconceptionChange(misconception_id, from_status: MisconceptionStatus | None, to_status: MisconceptionStatus, counters: dict)

### `sets.py` — product-logic §4.3–§4.4, memory-architecture §10.1

    TopicOut(skill_id, name, kind: TopicKind, position: int, status: Literal["open","closed"], level: SkillLevel,
             is_root: bool, misconception_labels: list[str], subtitle: str | None)
    SetOut(id: UUID, exam_id, area_ids: list[str], status: SetStatus, kind: Literal["regular","review","consolidation"],
           position: int, deadline: date, reason: str, topics: list[TopicOut], progress: SetProgress, opened_at?, completed_at?)
    SetProgress(topics_closed: int, topics_total: int, tasks_answered: int, tasks_correct: int)
    SetsByExam(exam_id, forecast: ForecastOut | None, current: SetOut | None, upcoming: list[SetOut], done: list[SetOut])
    SetSwitchIn(set_id: UUID)
    SetEditIn(skill_ids: list[str] | None, deadline: date | None)     # ручная смена состава/дедлайна

### `roadmap.py` — product-logic §3.5, §4.1

    ExamRequirementOut(exam_id, target_score: float, target_source: Literal["programs","manual"], max_raw_score: float,
                       program_ids: list[str], test_dates: list[TestDate], has_knowledge_model: bool, current_estimate: float | None,
                       estimate_note: str)                            # «по модели знаний» / «по твоей оценке»
    MilestoneOut(key: str, kind: Literal["registration","test","application","document","scholarship","window"],
                 date: date, title: str, exam_id: ExamId | None, program_id: str | None, source: Source, done: bool, done_at?)
    ConflictOut(kind: Literal["same_day_applications","exclusive_rounds","exam_after_deadline"], milestone_keys: list[str],
                text: str, options: list[str])
    OverviewOut(requirements: list[ExamRequirementOut], milestones: list[MilestoneOut], conflicts: list[ConflictOut],
                progress: list[ExamProgress], last_set_summary: SetSummaryOut | None)
    ExamProgress(exam_id, readiness: float, forecast: ForecastOut | None, milestones_done: int, milestones_total: int)
    SetSummaryOut(set_id, text: str | None, stats: dict, created_at)   # text None в Ф2

### `diagnostic.py` — memory-architecture §8.4

    DiagnosticState(exam_id, budget_left: int, reserve_left: int, asked: list[UUID], answered: int,
                    pending_descent: list[str], reask_queue: list[tuple[str, int]], roots_found: list[RootCauseOut],
                    trap_hits: list[str], firm: list[str], shaky: list[str], last_grade_correct: bool | None)
    DiagnosticOut(run_id: UUID, status: RunStatus, state: DiagnosticState, next_task: TaskInstanceOut | None)
    DiagnosticResult(firm: list[str], shaky: list[str], roots: list[RootCauseOut], suspected: list[str],
                     start_from: list[str], words: str)
    DiagnosticStartIn(exam_id, n_tasks: int | None)                    # n_tasks — сокращённый замер для защиты

### `mocks.py` — memory-architecture §8.3, §10.2

    MockStartIn(kind: MockKind, exam_id, set_id: UUID | None, skill_id: str | None, misconception_id: str | None)
    MockOut(run_id: UUID, kind, exam_id, section_name, status: RunStatus, tasks: list[TaskInstanceOut],
            minutes: int, answered: int, predicted_before: float | None)
    MockResultOut(run_id, raw_score: float, max_raw: float, scaled_score: float | None, scale_note: str | None,
                  per_skill: list[SkillStateView], brier_point: float | None)

### `tasks.py` — дополнения

    TaskInstanceOut(id, template_id, exam_id, type, skill_id, stem_rendered, options: list[OptionOut], figure_url,
                    time_reference_sec, difficulty, tags, mode: TaskMode, provenance: Literal["template","manual"])
    OptionOut(key, text)                                           # без correct и misconception_id — наружу не уходят
    TaskRequestIn(skill_id: str | None, set_id: UUID | None, mode: TaskMode = "topic",
                  with_trap: str | None, exclude_seen: bool = True)
    TaskSkipIn(instance_id: UUID, reason: Literal["skipped","timed_out"], time_spent_sec: int)
    AnswerResult — из фазы 1, добавить: state_words: str, knowledge_version: int, misconception_change: MisconceptionChange | None

### `matching.py` — product-logic §3.3–§3.4

    FactorOut(id: str, kind: Literal["hard","soft"], status: FactorStatus, text: str, source: Source | None, weight: float)
    MatchOut(program: Program, realism: Realism, factors: list[FactorOut], assumptions: list[str], score: float,
             fits_text: str | None, soft_pending: bool)            # fits_text из Ф4; soft_pending=True в Ф2
    MatchingOut(items: list[MatchOut], total: int, profile_readiness: float, forecast_used: bool, empty_reason: str | None)
    CompareRow(param: str, values: dict[str, str], differs: bool, relevant_to_student: bool, source: Source | None)
    CompareOut(program_ids: list[str], rows: list[CompareRow], collapsed_same: list[str], conclusion: str | None)   # conclusion из Ф4
    ShiftOut(program_id, from_realism, to_realism, changed_factors: list[str])   # «ассистент называет сдвиг» — Ф3 читает

### `events.py` — payload-модели фазы 2

    TaskSkippedPayload(instance_id, mode, time_spent_sec)                 # и task.timed_out
    DiagnosticProgressPayload(run_id, state: DiagnosticState)
    DiagnosticCompletedPayload(run_id, result: DiagnosticResult)
    MockStartedPayload(run_id, kind, exam_id, predicted_before: float | None)
    MockCompletedPayload(run_id, raw_score, scaled_score: float | None, predicted_before: float | None)
    SetOpenedPayload(set_id, skill_ids: list[str]); SetCompletedPayload(set_id)
    SetSwitchedByUserPayload(from_set_id: UUID | None, to_set_id); SetDeadlineChangedPayload(set_id, old: date, new: date)
    TopicOpenedPayload(set_id, skill_id); TopicCompletedPayload(set_id, skill_id)
    MisconceptionDisputedPayload(misconception_id)                       # и undisputed
    MilestoneDonePayload(milestone_key, done: bool)
    ProgramSavedPayload — без изменений

---

## 7. Сигнатуры функций между слоями

Только то, что вызывает чужой слой. Владелец меняет тело, не сигнатуру.

### 7.1 B1 — чистые (`knowledge/`, `sets/`, `matching/`, `tasks/`)

    knowledge.reconcile.reconcile_task_answer(instance: TaskInstance, grade: Grade, payload: TaskAnsweredPayload,
        state: KnowledgeStateOut | None, prereq_states: list[tuple[Prerequisite, KnowledgeStateOut | None]],
        misc_states: list[MisconceptionStateOut], n_seen: int, exam_ids: list[ExamId], params, now) -> ReconcileResult
    knowledge.reconcile.reconcile_prior(field: str, value, exam_skills: list[SkillWeight], areas: list[AreaOut],
        states: dict[str, KnowledgeStateOut], params, now) -> list[tuple[EvidenceIn, KnowledgeStateOut]]      # §4.8
    knowledge.misconceptions.next_status(...) -> MisconceptionStatus                  # сигнатура Ф1 + disputed
    knowledge.misconceptions.update_triggers(evidences, *, params) -> dict
    knowledge.misconceptions.visible_label(state: MisconceptionStateOut, params, now) -> str
    knowledge.misconceptions.visible_to(state, audience: Literal["student","tutor","sets"], params, now) -> bool   # §5.2
    knowledge.roots.rule_root(error_skill_id, prereq_states, params) -> RootCauseOut | None                       # §6 rule
    knowledge.words.skill_level(state, p_target, params) -> SkillLevel;  knowledge.words.trend(states: list) -> str
    knowledge.diagnostic.start(exam_skills, areas, prerequisites, known_roots, budget: int | None, params) -> DiagnosticState
    knowledge.diagnostic.next_skill(state, prerequisites, params) -> str | None
    knowledge.diagnostic.apply_answer(state, skill_id, grade, prerequisites, params) -> DiagnosticState
    knowledge.diagnostic.finish(state, states: dict[str, KnowledgeStateOut], params) -> DiagnosticResult
    sets.queue.build_queue(states, skill_weights, prerequisites, days_to_test, p_target, root_causes, params) -> list[QueueItem]
    sets.assemble.assemble_sets(queue, effort: dict[str, float], hours_per_week, next_test_date, misc_states, current: SetOut | None,
        done_skill_ids, params, today) -> list[SetPlan]            # весь маршрут, не один сет
    sets.forecast.forecast(states, skill_weights, exam_format, p_target, hours_per_week, test_date, effort, params, now) -> ForecastOut
    tasks.select.pick_template(templates: list[TaskTemplateSpec], seen: dict[str, int], last_grades: list[bool],
        with_trap: str | None, other_structure_than: str | None, rng) -> TaskTemplateSpec | None            # §10.2
    tasks.mocks.assemble_mock(kind, section: Section, templates_by_skill: dict[str, list[TaskTemplateSpec]], seen, rng, params) -> list[tuple[str, TaskTemplateSpec]]
    tasks.mocks.score(section: Section, grades: list[Grade], exam_format: ExamFormat) -> tuple[float, float | None]  # raw, scaled
    matching.hard.hard_filter(profile, programs, forecasts: dict[ExamId, ForecastOut], test_dates, today, params) -> list[HardResult]
    matching.realism.realism(hard: HardResult, params) -> Realism
    matching.rank.rank(profile, hard_results, soft_scores: dict[str, float], params) -> list[Ranked]
    matching.compare.compare(profile, programs, hard_results) -> CompareOut       # conclusion=None
    matching.shift.diff(before: list[MatchOut], after: list[MatchOut]) -> list[ShiftOut]
    matching.hard.explain_empty(hard_results: list[HardResult]) -> str            # какой фактор отсёк всё и что даст его ослабление (§6.3)

`HardResult(program_id, realism_inputs: dict, factors: list[FactorOut], assumptions: list[str])`, `Ranked(program_id, score, factors: dict)`, `QueueItem(skill_id, exam_id, need, urgency, gap, is_root, is_check)`, `SetPlan(kind, skill_ids, checks: list[str], reviews: list[str], deadline, reason)` — модели B1 в его файлах, поля зафиксированы здесь.

### 7.2 B1 — с I/O (`apply/`, `graph/queries/personal.py`)

    apply.task_answered.apply_task_answered(session, event, deps) -> AnswerResult
    apply.task_answered.apply_task_skipped(session, event, deps) -> None
    apply.profile_updated.apply_profile_updated(session, event, deps) -> None        # приоры + пересборка при нужных путях
    apply.dispute.apply_dispute(session, event, deps) -> MisconceptionStateOut       # и undisputed
    apply.sets.rebuild_sets(session, deps, student_id, exam_id) -> SetsByExam         # чистая пересборка + запись через repo.sets + forecast_cache
    apply.sets.open_set(session, deps, student_id, set_id) -> SetOut                  # событие set.opened, пишет роутер
    apply.sets.on_program_change(session, event, deps) -> None                        # program.saved/removed → rebuild по экзаменам сохранённых
    apply.sets.on_set_change(session, event, deps) -> None                            # set.switched_by_user / set.deadline_changed → rebuild
    apply.sets.on_run_completed(session, event, deps) -> None                         # diagnostic.completed / mock.completed → rebuild
    apply.diagnostic.start(session, deps, student_id, exam_id, n_tasks) -> DiagnosticOut
    apply.diagnostic.answer(session, deps, student_id, run_id, result: AnswerResult) -> DiagnosticOut
        # роутер сначала пишет task.answered (mode=diagnostic) и делает dispatch как для обычной задачи,
        # затем передаёт AnswerResult сюда — автомат замера обновляется, dispatch не дублируется
    apply.diagnostic.finish(session, deps, student_id, run_id) -> DiagnosticResult
    apply.mocks.start(session, deps, student_id, body: MockStartIn) -> MockOut
    apply.mocks.answer(session, deps, student_id, run_id, result: AnswerResult) -> MockOut   # тот же порядок, что у замера
    apply.mocks.finish(session, deps, student_id, run_id) -> MockResultOut
    apply.tasks.issue(session, deps, student_id, req: TaskRequestIn, chat_id: UUID | None = None) -> TaskInstanceOut
        # выбор шаблона, генерация, task.issued (с chat_id, если задачу выдал репетитор), insert_instance с mode и issued_event_id
    apply.knowledge.states_view(session, deps, student_id, exam_id) -> list[SkillStateView]
    apply.knowledge.misconceptions_view(deps, student_id, exam_id) -> list[MisconceptionStateOut]
    apply.knowledge.explain(deps, student_id, node_id) -> list[EvidenceOut]
    graph.queries.personal.get_misc_states(driver, student_id, skill_ids) -> list[MisconceptionStateOut]
    graph.queries.personal.upsert_misc_state(driver, student_id, misconception_id, status, counters, triggers) -> MisconceptionStateOut
    graph.queries.personal.add_root_cause(driver, evidence_id, root_skill_id, confidence, source) -> None
    graph.queries.personal.list_evidence(driver, student_id, skill_id, limit) -> list[EvidenceOut]
    graph.queries.personal.list_root_causes(driver, student_id, window_days) -> list[RootCauseOut]
    graph.queries.personal.get_state_history(driver, student_id, skill_id, exam_id, n=3) -> list[KnowledgeStateOut]

### 7.3 B2 — чистые (`roadmap/`)

    roadmap.requirements.build_requirements(saved: list[Program], profile: Profile, exam_formats: dict[ExamId, ExamFormat],
        test_dates: dict[ExamId, list[TestDate]], forecasts: dict[ExamId, ForecastOut | None], params: KnowledgeParams) -> list[ExamRequirementOut]
    roadmap.milestones.build_milestones(saved, requirements, test_dates, calendars: list[TestDate], marks: dict[str, datetime], today) -> list[MilestoneOut]
    roadmap.conflicts.find_conflicts(milestones, saved, planned_test_dates: dict[ExamId, date | None]) -> list[ConflictOut]
    roadmap.progress.exam_progress(requirement, states: list[SkillStateView], forecast, milestones) -> ExamProgress

### 7.4 B3 — репозитории и события

    db.repo.sets: list_sets(session, student_id, exam_id) -> list[SetOut]; get_set(session, student_id, set_id) -> SetOut | None;
                  replace_plan(session, student_id, exam_id, plans: list[SetPlan], keep_current: bool) -> list[SetOut];
                  set_status(session, student_id, set_id, status); set_topic_status(session, set_id, skill_id, status);
                  update_set(session, student_id, set_id, skill_ids | None, deadline | None); count_progress(session, student_id, set_id) -> SetProgress
    db.repo.diagnostic: create_run, get_active_run, save_state, complete_run
    db.repo.mocks: create_run, get_run, save_progress, complete_run
    db.repo.milestones: list_marks(session, student_id) -> dict[str, datetime]; set_mark(session, student_id, key, done: bool)
    db.repo.forecast: get(session, student_id, exam_id) -> ForecastOut | None; put(session, student_id, exam_id, forecast, as_of_event_id)
    db.repo.tasks: list_templates_for_skills(session, skill_ids) -> dict[str, list[TaskTemplateSpec]]; get_seen_many(session, student_id, skill_ids) -> dict[str, int];
                   mark_answered(session, instance_id, answered_at, correct: bool); list_instances(session, student_id, ids) -> list[TaskInstance]
    events.store.list_by_type(session, student_id, types: list[EventType], since: datetime | None, limit: int) -> list[Event]
    db.repo.programs: list_all(session) -> list[Program]; list_saved_programs(session, student_id) -> list[Program]
    events.dispatch.dispatch(session, event, deps: RuleDeps) -> dict[str, Any]
    events.version.bump(redis, student_id) -> int; events.version.get(redis, student_id) -> int
    api.deps.get_rule_deps() -> RuleDeps

---

## 8. Роуты фазы 2 (B3)

| Метод и путь | Тело → ответ | Что вызывает |
| :---- | :---- | :---- |
| `POST /tasks` | `TaskRequestIn` → 201 `TaskInstanceOut` | `apply.tasks.issue` |
| `POST /tasks/{instance_id}/answer` | `AnswerIn` → `AnswerResult` | append `task.answered` → dispatch → результат `apply_task_answered` |
| `POST /tasks/{instance_id}/skip` | `TaskSkipIn` → 200 `{}` | append `task.skipped` / `task.timed_out` |
| `GET /tasks/{instance_id}/solution` | → `{solution: list[str]}` | только после ответа или пропуска, иначе 409 |
| `GET /sets?exam_id=` | → `SetsByExam` | `repo.sets` + `repo.forecast`; если пусто — `apply.sets.rebuild_sets` |
| `GET /sets/{set_id}` | → `SetOut` | |
| `POST /sets/{set_id}/open` | → `SetOut` | append `set.opened`, `apply.sets.open_set` |
| `POST /sets/switch` | `SetSwitchIn` → `SetsByExam` | append `set.switched_by_user` → dispatch (rebuild) |
| `PATCH /sets/{set_id}` | `SetEditIn` → `SetOut` | append `set.deadline_changed` при дате → dispatch |
| `POST /sets/{set_id}/topics/{skill_id}/open` | → `TopicOut` | append `topic.opened` |
| `POST /sets/{set_id}/topics/{skill_id}/complete` | → `SetOut` | append `topic.completed`; если все закрыты — `set.completed` |
| `POST /diagnostic` | `DiagnosticStartIn` → 201 `DiagnosticOut` | `apply.diagnostic.start`; активный есть → 409 |
| `GET /diagnostic/active?exam_id=` | → `DiagnosticOut` или 404 | |
| `POST /diagnostic/{run_id}/answer` | `AnswerIn` → `DiagnosticOut` | append `task.answered` (mode=diagnostic) → dispatch → `apply.diagnostic.answer(result)` |
| `POST /diagnostic/{run_id}/finish` | → `DiagnosticResult` | `apply.diagnostic.finish` (досрочно тоже) |
| `POST /mocks` | `MockStartIn` → 201 `MockOut` | `apply.mocks.start` |
| `GET /mocks/{run_id}` | → `MockOut` | |
| `POST /mocks/{run_id}/answer` | `AnswerIn` → `MockOut` | append `task.answered` (mode=kind мока) → dispatch → `apply.mocks.answer(result)` |
| `POST /mocks/{run_id}/finish` | → `MockResultOut` | `apply.mocks.finish` |
| `GET /matching?limit=` | → `MatchingOut` | профиль + программы + прогнозы → `hard_filter` → `realism` → `rank` |
| `GET /matching/compare?ids=a,b,c` | → `CompareOut` | `matching.compare` |
| `GET /overview` | → `OverviewOut` | `roadmap.*` + `repo.forecast` + `repo.milestones` + последний `set_summaries` |
| `POST /overview/milestones/{key}` | `{done: bool}` → `MilestoneOut` | append `milestone.done`, `repo.milestones.set_mark` |
| `GET /knowledge?exam_id=` | → `{skills: list[SkillStateView], misconceptions: list[MisconceptionStateOut], roots: list[RootCauseOut]}` | `apply.knowledge.*` |
| `GET /knowledge/explain/{node_id}` | → `{items: list[EvidenceOut]}` | `apply.knowledge.explain` |
| `POST /knowledge/misconceptions/{id}/dispute` | `{disputed: bool}` → `MisconceptionStateOut` | append `misconception.disputed/undisputed` → dispatch |
| `POST /knowledge/refresh` | `{kind, set_id?, topic_skill_id?}` → `RefreshOut{status: "queued"\|"empty"\|"failed", job_id, window_size, failed_reason}` | append `observer.requested`, `enqueue("interactive", "observe_chat")` |
| `PATCH /profile` | без изменений, но теперь → dispatch `profile.updated` | `apply_profile_updated`, пересчёт подборки — `GET /matching` считает на лету |
| `POST /saved/{id}`, `DELETE` | без изменений, но → dispatch `program.saved/removed` | пересборка сетов |

Всё без языковой модели. `GET /matching` при пустом результате отдаёт `empty_reason` — какой фактор отсёк всё (product-logic §6.3).

---

## 9. Точки стыка и порядок

### 9.1 Что каждый пушит первым, ни от кого не завися

| Кто | Что | Когда |
| :---- | :---- | :---- |
| **B3** | скелет `phase2-skeleton`: схемы §6, `KnowledgeParams` §5, миграция `0002`, модели, репозитории с сигнатурами §7.4 (тела можно сразу), `RuleDeps` + новый `dispatch`, `events/handlers.py` с импортом стабов `apply/*`, `events/version.py`, `api/deps.get_rule_deps`, пустые пакеты `app/apply/`, `app/roadmap/` с `__init__.py`, стабы `apply/*` и `roadmap/*` по сигнатурам §7 с `NotImplementedError("phase 2")`, фикстуры conftest §9.3, расширенный `test_layers.py` | первые 90 минут фазы, до всего остального |
| **B1** | `phase2-b1-data`: библиотека заблуждений разложена по `data/misconceptions/<area>.json`, `seed/misconceptions.py` читает каталог, `docs/data-formats.md` дополнен (каталог, папки шаблонов по областям, квоты); `knowledge/words.py`; сигнатуры новых чистых модулей (`knowledge/diagnostic.py`, `knowledge/roots.py`, `tasks/select.py`, `tasks/mocks.py`, `matching/shift.py`) со стабами | параллельно скелету, не ждёт его — эти файлы не зависят от новых схем; после мержа скелета — ребейз |
| **B2** | `phase2-b2-tests`: `tests/llm`, `tests/agents` из ветки `b2_phase1` возвращены в `main` и зелёные; `scripts/gen_templates.py` каркас (аргументы, выход в папку, вызов `seed --validate`) | параллельно скелету |

### 9.2 Кто чего ждёт

| Кто ждёт | Чего | От кого | Когда это нужно | Что делать до этого |
| :---- | :---- | :---- | :---- | :---- |
| B1 | скелет (схемы `sets/diagnostic/mocks/matching/roadmap`, репозитории, `RuleDeps`) | B3 | перед началом `apply/` и `graph/queries/personal` возвратов новых моделей | чистые модули: `misconceptions`, `reconcile`, `sets/*`, `matching/*`, `tasks/select`, `tasks/mocks`, `diagnostic` — все на моделях фазы 1 плюс свои |
| B1 | `repo.sets/diagnostic/mocks/forecast/tasks` с телами | B3 | интеграционные тесты `tests/apply/` | `pytest.skip("waiting: B3 repo")` |
| B1 | `roadmap.requirements` для `p_target` | B2 | `apply.sets.rebuild_sets` | принимать `p_target` аргументом; в `rebuild_sets` временно `p_target_max` |
| B3 | чистые функции B1 и `apply/*` | B1 | сквозные тесты роутеров | тесты роутеров с `monkeypatch` на `apply.*` (возвращают фикстурные модели); `integration`-тесты `skip("waiting: B1 apply")` |
| B3 | `roadmap.*` | B2 | `GET /overview` | то же — `monkeypatch` |
| B2 | скелет (`schemas/roadmap.py`) | B3 | старт `roadmap/` | тесты `tests/roadmap/` с ожидаемыми числами; генератор шаблонов; ENT-шаблоны |
| B2 | ничего от B1 | — | — | — |
| все | `seed.py --validate` в CI на `data/` | B3 (уже есть) | каждый PR с данными | — |

### 9.3 Фикстуры conftest (B3, скелет)

Дополнения к фазе 1: `rule_deps` — `RuleDeps(graph=graph_or_None, redis=redis, params=KnowledgeParams(), now=frozen)`; `frozen_now` — фиксированная дата `2026-09-18T12:00:00Z`, монкипатчится в `apply` и `dispatch`; `seeded_graph` (integration) — мини-карта из `tests/fixtures/data/` (1 экзамен, 2 области, 5 навыков, 2 заблуждения, 2 шаблона); `student_with_saved` — ученик с двумя сохранёнными программами из пола; `templates_db` — те же 2 шаблона в Postgres; `fake_apply` — фабрика `monkeypatch` для всех `apply.*` с фикстурными ответами.

### 9.4 Порядок фазы

1. Дельта контрактов (этот файл) — на синке, 30 минут, три подписи.
2. Первые пуши §9.1 — параллельно, B3 мержит скелет первым, остальные ребейзятся.
3. Тесты первыми в отдельной сессии, PR `phase2-tests-<B>`, `@pytest.mark.phase2`, `xfail(strict=False)` до реализации.
4. Ветки `phase2/B1`, `phase2/B2`, `phase2/B3`, подзадачи через `tz-executor`, PR на подзадачу, каждая привязана к тесту. Приоритет подзадач — в каждом ТЗ, чтобы обрыв давал демо.
5. Мерж: B3 скелет → B2 (`roadmap`, маленький и ранний) → B1 (чистые, потом `apply`) → B3 (роутеры без фейков) → общий прогон `make test && make test-int`.
6. Сквозная проверка шагов 4–8 §9 руками на `main` — B3 ведёт, все чинят своё.
7. Синк: `sync-log.md`, дельта контрактов фазы 3.

---

## 10. Вне фазы

Любой вызов модели в рантайме; тексты (гайдлайны, объяснения, «подходит тебе», резюме, `conclusion` сравнения); история чата; наблюдатель; персональные узлы и заблуждения; replay; поиск и извлечение программ; лента рекомендаций и варианты по темпу (Ф4) — но `ForecastOut.on_track` считается уже сейчас; отложенное применение событий при упавшем графе (Ф5) — только `processed_at = NULL`.
