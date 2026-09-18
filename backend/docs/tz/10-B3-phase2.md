# ТЗ фазы 2 — B3, платформа и API

Quack! · фаза 2 «правила» · v0.1 · 18.09.2026. Читать вместе с `00-contracts-phase2.md` (дельта) и `00-contracts.md` (фаза 1). Стиль тот же: что сделать, где, как проверить. Кода нет — сигнатуры и модели в дельте.

---

## 0. Сначала — что запушить сразу и чего ждать

### 0.1 Первый пуш: скелет `phase2-skeleton` (90 минут, до всего остального)

Без него B1 не может начать `apply/`, а B2 — `roadmap/`. Порядок внутри пуша — по тому, кто чего ждёт раньше:

1. `app/schemas/`: `common.py` (новые `Literal` и `Source`), `knowledge.py` (дополнения), `sets.py`, `roadmap.py`, `diagnostic.py`, `mocks.py`, `matching.py`, `tasks.py` (дополнения), `events.py` (payload-модели) — ровно по дельте §6. Это первое, что нужно обоим.
2. `app/config.py`: параметры дельты §5 в `KnowledgeParams`.
3. `app/db/models.py` + `alembic/versions/0002_phase2.py` — таблицы дельты §3.4. `downgrade` удаляет всё своё.
4. `app/db/repo/`: `sets.py`, `diagnostic.py`, `mocks.py`, `milestones.py`, `forecast.py` — сигнатуры дельты §7.4; тела можно написать сразу (это твоя работа фазы), но пуш не ждёт тел. Дополнения в `tasks.py` и `programs.py`.
5. `app/events/dispatch.py`: `RuleDeps`, новая сигнатура `dispatch` с результатами; `app/events/version.py`; `app/events/handlers.py` — реестр, импортирующий стабы из `app/apply/*` (см. §3.2).
6. `app/apply/` и `app/roadmap/`: `__init__.py` и файлы-стабы со всеми сигнатурами дельты §7.2 и §7.3, тела `NotImplementedError("phase 2")`, докстринг со ссылкой на раздел документа. B1 и B2 заменят тела; файлы после этого — их.
7. `app/keys.py`: ключи дельты §4.4. `app/api/deps.py`: `get_rule_deps`.
8. `tests/conftest.py`: фикстуры дельты §9.3. `tests/test_layers.py`: `roadmap/` в список чистых, `apply/` — разрешены `app.db.repo`, `app.graph.queries`, `app.events`, запрещены `app.llm`, `app.agents`, `fastapi`.
9. `CLAUDE.md`: ссылка на `docs/tz/phase2/`, таблица владения из дельты §2, замороженные файлы: `schemas/*`, `events/dispatch.py`, `events/handlers.py`, `keys.py`.

Пуш мержится в `main` сразу, без ожидания тестов B1/B2 — только `ruff` и свои `make test`. Сообщить в чат: «скелет в main, ребейзьтесь».

### 0.2 Чего ждать и когда

| Чего | От кого | Когда понадобится | Что делать до этого |
| :---- | :---- | :---- | :---- |
| `apply.*` с телами | B1 | сквозные тесты роутеров `tasks`, `sets`, `diagnostic`, `mocks`, `knowledge` | тесты роутеров через `fake_apply` (monkeypatch); `integration`-тесты `pytest.skip("waiting: B1 apply")` |
| `matching.*` с телами | B1 | `GET /matching`, `GET /matching/compare` | monkeypatch `matching.hard.hard_filter` и др. на фикстурные результаты |
| `roadmap.*` с телами | B2 | `GET /overview` | monkeypatch `roadmap.*` |
| шаблоны `data/templates/sat/{alg,adv}`, `ent/**` | B1, B2 | сквозной прогон замера на полной карте | свой seed-прогон на мини-фикстуре `tests/fixtures/data/` |
| ничего от фронта | — | — | после мержа своих роутеров — `make types`, дифф `schema.d.ts` в PR |

Ты — последний в порядке мержа (роутеры без фейков), поэтому у тебя самый длинный хвост ожидания. Не сиди: пока B1 пишет `apply/`, у тебя репозитории, роутеры, данные (пол программ, календари, шаблоны своих областей), CI.

---

## 1. Что ты делаешь в этой фазе

Ты соединяешь событие с правилом: диспетчер получает зависимости и возвращает результаты, реестр обработчиков собирает функции B1 в одном файле, каждая запись в персональный слой поднимает `knowledge_version`. Ты пишешь все таблицы и репозитории фазы и все HTTP-роутеры «Подготовки» и «Подборки», в которых нет ни правил, ни модели — они только собирают входы из репозиториев и графа, вызывают функции B1/B2 и отдают модели из дельты. Плюс данные, которые у тебя: пол программ до 20–30, календари обоих экзаменов, шаблоны SAT по областям `psda` и `geo`. Плюс CI: `openapi-typescript` как контракт с фронтом. В конце фазы шаги 4–8 сценария жюри проходятся через `curl` без языковой модели.

Что ты не делаешь: любые правила (веса, статусы, очередь, факторы) — это B1; требования и вехи — B2; тексты — Ф4.

---

## 2. События

### 2.1 `app/events/dispatch.py`

- `RuleDeps` — dataclass дельты §3.1. Поле `now` — функция, чтобы тесты замораживали время.
- `dispatch(session, event, deps) -> dict[str, Any]`: обработчики по порядку регистрации; результат каждого кладётся по `handler.__name__`; исключение одного обработчика логируется с `event_id`, `type`, `handler`, пробрасывается — роутер отдаёт 500, транзакция откатывается целиком (событие тоже; ученик повторит действие). Исключение: ошибка драйвера Neo4j (`neo4j.exceptions.ServiceUnavailable`, `SessionExpired`) или `deps.graph is None` — не пробрасывается: обработчик сам должен вернуть результат без состояния, `processed_at` не ставится. Диспетчер это только логирует как `graph_unavailable`.
- `mark_processed` вызывается диспетчером после успешного прохода всех обработчиков, если ни один не вернул маркер `GraphUnavailable` (константа-объект в `dispatch.py`, B1 возвращает его из `apply/*`).

### 2.2 `app/events/handlers.py` — единственный реестр

Регистрирует через `on(EventType)`: `task.answered → apply.task_answered.apply_task_answered`; `task.skipped`, `task.timed_out → apply_task_skipped`; `profile.updated → apply.profile_updated.apply_profile_updated`; `program.saved`, `program.removed → apply.sets.on_program_change`; `set.switched_by_user`, `set.deadline_changed → apply.sets.on_set_change`; `misconception.disputed`, `undisputed → apply.dispute.apply_dispute`; `diagnostic.completed`, `mock.completed → apply.sets.on_run_completed`. Импортируется один раз в `main.create_app`. Тест: каждый тип из списка имеет ровно ожидаемые обработчики; типы вне списка — ноль. Файл после скелета не меняется без sync-log: B1 добавляет функцию — ты добавляешь строку.

### 2.3 `app/events/version.py`

`bump(redis, student_id) -> int` — `INCR`; `get(redis, student_id) -> int` — 0, если нет. Роутеры `tasks`, `diagnostic`, `mocks`, `knowledge`, `sets` ставят заголовок `X-Knowledge-Version` через зависимость `with_knowledge_version` в `api/deps.py`.

### 2.4 `app/events/store.py`

`list_unprocessed` и `mark_processed` — уже есть. Добавить `list_by_type(session, student_id, types: list[EventType], since: datetime | None, limit) -> list[Event]` — нужен B2 для статистики сета в Ф4 и тебе для `SetProgress`.

---

## 3. Данные в Postgres

### 3.1 Модели и миграция

Дельта §3.4. Проверки: `alembic upgrade head` с нуля и с `0001`; `downgrade -1` возвращает к `0001` без остатков; `tests/db/test_migrations.py` расширить.

### 3.2 Репозитории — `app/db/repo/`

Все `async`, сессия первым аргументом, `student_id` во всех запросах к персональным таблицам.

- `sets.py`: `replace_plan` — транзакционно: сеты со статусом `done` не трогаются; `current` при `keep_current=True` сохраняет `id`, `opened_at`, статусы топиков (совпадающие `skill_id` остаются `closed`), обновляется только `deadline` и `reason`; `upcoming` удаляются и создаются заново по `plans` с `position` по порядку; `id` новых — UUID v4. `count_progress` — из `task_instances` по `mode in (topic, mock_topic, mock_set)` и `skill_id in set_topics`, `tasks_correct` — из событий `task.answered` через `payload->>'correct'`? Нет: результат ответа в событии нет. Решение: `task_instances` получает колонку `correct BOOL?` (в миграции), `apply_task_answered` пишет через `repo.tasks.mark_answered(session, instance_id, answered_at, correct)`. Сигнатуру `mark_answered` расширить в скелете.
- `diagnostic.py`: один активный на `(student_id, exam_id)` — `create_run` при существующем активном бросает `Conflict`.
- `mocks.py`: `save_progress(session, run_id, answered_instance_ids)`; `complete_run(session, run_id, raw, scaled)`.
- `milestones.py`: `set_mark(done=False)` удаляет строку.
- `forecast.py`: `put` — upsert.
- `tasks.py`: `list_templates_for_skills` — из `task_templates` (JSON копия), группировка по `skill_id`; `get_seen_many`; `list_instances`; `mark_answered`.
- `programs.py`: `list_all` — весь кэш, `flagged=False`; `list_saved_programs` — join с `saved_programs`, порядок по `saved_at`.

### 3.3 Данные — `data/`

- `programs_floor/programs.json` — с 5 до 20–30 (product-logic §10.1): распределение — 8–10 Казахстан (не меньше 4 с грантом и порогом ЕНТ), 8–10 Европа, 3–5 США/Азия; у каждой ≥ 2 требования (`exam_score` с `exam_id` и порогом обязательно), ≥ 1 дедлайн с `kind`, `tuition_per_year`, `living_per_year`, `environment_text` 2–3 предложения, `source_url`, `is_demo` там, где не проверено. Требования должны давать разные статусы для тестового профиля: минимум по 3 программы на каждый уровень реалистичности при профиле `test@quack.kz`.
- `knowledge_base/calendars.json` — `TestDate` для SAT (все даты сезона 2026–27 с регистрацией и late) и ЕНТ (основной и повторный периоды) с источниками.
- `templates/sat/psda/*.json`, `templates/sat/geo/*.json` — по 2–3 шаблона на каждый навык этих областей (квота ~30–40 шаблонов), типы и сложность по `sat_math.json` `ExamFormat`; дистракторы с `misconception_id` из `data/misconceptions/psda.json`, `geo.json` (твои файлы). Формат — `docs/data-formats.md`. Каждый PR с данными — `seed.py --validate`.

---

## 4. HTTP-роутеры — `app/api/`

Общее: тело — модели дельты; `student_id` из токена; чужой объект → 404; действия → события через `store.append` → `dispatch` → коммит. Роутер не считает ничего сам: собирает входы, вызывает `apply.*` / `matching.*` / `roadmap.*`, отдаёт результат. Полная таблица — дельта §8. Ниже только то, что не очевидно из неё.

- `tasks.py`: `POST /tasks/{id}/answer` — проверить, что экземпляр принадлежит ученику и не отвечен (иначе 409); append `task.answered` с `TaskAnsweredPayload` + `session_minute` (считать из `events.session` — минуты с первого события сессии); dispatch; ответ — `results["apply_task_answered"]`; заголовок версии. `GET .../solution` — 409 до ответа/пропуска.
- `sets.py`: `GET /sets` при отсутствии строк для экзамена вызывает `apply.sets.rebuild_sets` один раз (первый вход в подготовку). `POST /sets/switch` — 404 на чужой, 409 на `done`. `PATCH` — `deadline` раньше сегодня → 400. `topics/{skill}/complete` — если после закрытия все топики сета `closed` → append `set.completed`, статус `done`, следующий `upcoming` не становится `current` автоматически (product-logic §4.1: принять в Обзоре) — `current=None` пока не `open`.
- `diagnostic.py`: `n_tasks` ≤ `diag_max`; `POST /diagnostic` при активном → 409 с `run_id` в `message`. `POST .../answer`: проверить, что `instance_id` из тела принадлежит этому `run_id`; append `task.answered` с `mode=diagnostic` → dispatch → `apply.diagnostic.answer(result)` → `DiagnosticOut`. Один и тот же код записи ответа для `tasks`, `diagnostic`, `mocks` — вынести в `api/_answer.py` (`record_answer(session, deps, student, instance_id, body, mode) -> AnswerResult`).
- `mocks.py`: `POST .../answer` — тот же `record_answer` с `mode=kind` мока → `apply.mocks.answer(result)`.
- `matching.py`: `GET /matching` — профиль, `list_all` программ, прогнозы из `forecast_cache` по экзаменам сохранённых, тест-даты из графа (`kb.list_test_dates`), сегодня; `hard_filter` → для каждой `realism` → `rank` с `soft_scores={}`; собрать `MatchOut` (`soft_pending=True`, `fits_text=None`); `limit` по умолчанию 10, не меньше `min_candidates`; пусто → `empty_reason` от `matching.hard.explain_empty(hard_results)` (B1 добавит; до этого — общий текст). `compare` — 2–4 `ids`, иначе 400; чужих программ нет — все из кэша.
- `overview.py`: сохранённые программы, форматы (`canonical.get_exam_format`), тест-даты, прогнозы, отметки → `roadmap.requirements` → `milestones` → `conflicts` → `progress` (с `apply.knowledge.states_view`). Последний `set_summaries` — `text=None` допустим.
- `knowledge.py`: `GET /knowledge` — три списка из `apply.knowledge.*`; `explain/{node_id}` — `node_id` это `skill_id` или `misconception_id`.
- `profile.py`, `saved.py`: после `append` теперь `dispatch`.
- `health.py`: `checks["graph_pending"]` — число событий с `processed_at IS NULL` за последний час (0 → нет ключа). Нужно фазе 5.

`main.py`: подключить роутеры, импортировать `events.handlers`.

---

## 5. CI и деплой

- `make types` → `frontend/src/api/schema.d.ts`; job `types` в `ci.yml`: генерирует и падает на диффе (сейчас пропущен). Согласовать с F1/F2 путь файла одной строкой в чате.
- `seed.py --validate` уже в CI — добавить `--validate` на `data/misconceptions/` как каталог (после пуша B1).
- Деплой на VPS: секреты в GitHub, `deploy.yml` перестаёт пропускаться; `alembic upgrade head` при старте контейнера `api`. Если VPS ещё нет — записать в sync-log, это блокер фазы 5, не этой.
- `pytest -m phase2` в CI с `xfail(strict=False)` до реализации — как в Ф1.

---

## 6. Тесты — пишутся до кода, в отдельной сессии

Все `@pytest.mark.phase2`; `integration`, где нужна живая БД или граф. Роутеры тестируются с `fake_apply` — фикстурные ответы `apply.*`; это проверяет транспорт, права, коды, события, а не правила.

`tests/events/`

- `test_dispatch.py`: `dispatch` возвращает результаты по именам; исключение обработчика откатывает транзакцию, событие не записано; `GraphUnavailable` не пробрасывается, `processed_at` остаётся `NULL`; `mark_processed` после успешного прохода.
- `test_handlers.py`: таблица «тип → обработчики» совпадает с §2.2.
- `test_version.py`: `bump` монотонен, `get` без ключа — 0.

`tests/db/`

- `test_migrations.py`: `0002` вверх/вниз.
- `test_repo_sets.py` (integration): `replace_plan` сохраняет `done`, сохраняет `id` и закрытые топики `current` при `keep_current`, пересоздаёт `upcoming`; `count_progress`.
- `test_repo_diagnostic.py`, `test_repo_mocks.py`, `test_repo_milestones.py`, `test_repo_forecast.py`: CRUD, изоляция по `student_id`, `Conflict` на второй активный замер.
- `test_repo_tasks.py`: `list_templates_for_skills`, `get_seen_many`, `mark_answered`.

`tests/api/`

- `test_tasks.py`: `POST /tasks` → 201 и событие `task.issued` (через `fake_apply`); `answer` → событие `task.answered` с `session_minute`, ответ = результат обработчика, заголовок `X-Knowledge-Version`; повторный ответ → 409; чужой экземпляр → 404; `skip` → `task.skipped`; `solution` до ответа → 409.
- `test_sets.py`: `GET` пусто → вызван `rebuild_sets` один раз; `switch` чужого → 404, `done` → 409; `PATCH` дата в прошлом → 400; `complete` последнего топика → `set.completed`, статус `done`, `current=None`.
- `test_diagnostic.py`: старт → 201, второй → 409; `answer`, `finish` — события и коды.
- `test_mocks.py`: старт → 201 с `predicted_before`, `finish` → `MockResultOut`.
- `test_matching.py`: с monkeypatch `matching.*` — сборка `MatchOut`, `soft_pending=True`, `limit`, `min_candidates`, пусто → `empty_reason`; `compare` с 1 или 5 id → 400.
- `test_overview.py`: с monkeypatch `roadmap.*` — сборка `OverviewOut`; `milestones/{key}` → событие `milestone.done`, отметка в БД, повтор с `done=false` снимает.
- `test_knowledge.py`: три списка; `dispute` → событие и ответ обработчика.
- `test_profile.py`, `test_saved.py`: после `PATCH`/`POST` вызван `dispatch` (обработчик-шпион).
- `test_e2e_rules.py` (integration, `skip` до мержа B1): сохранить 2 программы → `GET /overview` есть требования; `GET /sets` есть текущий сет и прогноз; `POST /tasks` + `answer` → версия выросла, `GET /knowledge` содержит навык с `n_evidence=1`; `PATCH /profile` бюджет → порядок `GET /matching` изменился. Это и есть шаги 4–8 §9.

`tests/seed/test_data_schemas.py`: пол ≥ 20 программ, у каждой `exam_score`-требование; календари обоих экзаменов; шаблоны `psda`/`geo` проходят `validate_template`.

`tests/test_layers.py`: `roadmap/` чистый; `apply/` без `app.llm`, `app.agents`, `fastapi`.

`tests/test_secrets.py`: без изменений, но прогоняется.

---

## 7. Порядок подзадач (чтобы обрыв давал демо)

1. Скелет §0.1 — мерж.
2. Репозитории `sets`, `tasks`, `forecast` + роутеры `tasks`, `sets`, `knowledge` — это шаги 7–8 §9 (задачи двигают состояние, сет и прогноз).
3. `matching`, `overview` роутеры + пол программ + календари — шаги 4–5.
4. `diagnostic`, `mocks` — шаг 6.
5. Шаблоны `psda`/`geo`.
6. CI типы, деплой, `health.graph_pending`.
7. После мержа B1 и B2: снять `skip`, прогнать `test_e2e_rules`, прогнать шаги 4–8 `curl` на `main`, записать вывод в `docs/tz/phase2/checklists/phase2-e2e.md`.

---

## 8. Приёмка фазы

- `make test` и `make test-int` зелёные на `main` после мержа всех троих.
- `openapi.json` содержит все роуты дельты §8; `schema.d.ts` перегенерирован и закоммичен.
- `test_e2e_rules` проходит на живых БД без `skip`.
- Пол ≥ 20 программ, календари, шаблоны `psda`/`geo` — в `main`, `seed.py --validate` зелёный.
- `LLM_FORCE_DOWN=1` не меняет ни один ответ роутеров этой фазы (тест: прогон `test_e2e_rules` с флагом).
- `docs/tz/phase2/checklists/phase2-e2e.md` заполнен.

## 9. Вне скоупа

Тексты и любые вызовы модели; отложенное применение событий при упавшем графе (только `processed_at = NULL`); лента рекомендаций; поиск программ; `daily_aggregates`; WebSocket; правила любого рода.
