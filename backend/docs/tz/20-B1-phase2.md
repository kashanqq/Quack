# ТЗ фазы 2 — B1, правила и граф

Quack! · фаза 2 «правила» · v0.1 · 18.09.2026. Читать вместе с `00-contracts-phase2.md` (дельта) и `00-contracts.md`. Формулы — из `memory-architecture-quack.md`, номера разделов указаны у каждого пункта; в коде ссылаться на них в докстрингах. Кода нет — сигнатуры в дельте §7.1–§7.2.

---

## 0. Сначала — что запушить сразу и чего ждать

### 0.1 Первый пуш: `phase2-b1-data` (60 минут, параллельно скелету B3, ничего не ждёт)

Всё в этом пуше зависит только от файлов фазы 1, которыми ты владеешь.

1. `data/misconceptions/library.json` → разложить по областям: `alg.json`, `adv.json`, `psda.json`, `geo.json` (SAT), `ent_alg.json`, `ent_geo.json` и т. д. по областям ЕНТ. `id` не меняются. `library.json` удалить.
2. `app/seed/misconceptions.py`: читать каталог `data/misconceptions/*.json`, объединять, проверять уникальность `id` по всем файлам, ссылки `skill_ids` на существующие навыки; отчёт по файлам. `scripts/seed.py --validate` должен проходить — сигнатура `seed_misconceptions(driver, path)` та же, `path` теперь каталог.
3. `docs/data-formats.md`: раздел про каталог заблуждений и владение файлами; раздел про папки шаблонов по областям (`templates/sat/{alg,adv,psda,geo}/`, `templates/ent/<area3>/`) с квотой «2–3 на навык» и правилом «дистрактор ссылается на заблуждение из файла своей области, чужое — через sync-log»; таблица «навык → сколько шаблонов есть» генерируется командой `seed.py --coverage` (добавить флаг: печатает навыки с числом шаблонов, помечает < 2).
4. `app/knowledge/words.py`: `skill_level`, `trend` (дельта §4.3) — маленькие, чистые, нужны всем.
5. Сигнатуры-стабы новых чистых модулей по дельте §7.1: `knowledge/diagnostic.py`, `knowledge/roots.py`, `tasks/select.py`, `tasks/mocks.py`, `matching/shift.py`, `matching.hard.explain_empty`. Модели, которых ещё нет в схемах (`ForecastOut`, `DiagnosticState` и др.), в аннотациях — строками с `TYPE_CHECKING`, чтобы не ждать скелет.
6. `graph/schema.cypher` + `schema.py`: индексы дельты §3.5. Идемпотентно.

Запушить, попросить B3 смержить до или сразу после скелета — конфликтов нет (разные файлы). После мержа скелета — ребейз, заменить строковые аннотации на импорты из `app.schemas`.

### 0.2 Чего ждать и когда

| Чего | От кого | Когда понадобится | Что делать до этого |
| :---- | :---- | :---- | :---- |
| скелет: схемы `sets/diagnostic/mocks/matching/roadmap`, дополнения `knowledge.py`, `RuleDeps`, стабы `apply/*` | B3 | начало работы в `app/apply/` и возвраты новых моделей из `graph/queries/personal.py` | чистые модули §2–§5: они на моделях Ф1 и твоих собственных (`QueueItem`, `SetPlan`, `HardResult`, `Ranked`) |
| репозитории `sets`, `diagnostic`, `mocks`, `forecast`, `tasks` с телами | B3 | интеграционные тесты `tests/apply/` | `pytest.skip("waiting: B3 repo")`; unit-тесты `apply/` с `fake` репозиториями через monkeypatch |
| `roadmap.requirements` (`p_target` по экзамену) | B2 | `apply.sets.rebuild_sets` | принимать `p_target` аргументом в чистых функциях (так и в дельте); в `rebuild_sets` до появления B2 брать `p_target_max` и `TODO(sync-log)` |
| шаблоны `psda`/`geo` (B3), `ent/**` (B2) | B3, B2 | сквозной замер на полной карте | свои `alg`/`adv` и мини-фикстура |

Порядок мержа: твои чистые модули можно мержить по мере готовности (никто не сломается — их ещё никто не вызывает), `apply/` — после скелета и репозиториев B3.

---

## 1. Что ты делаешь в этой фазе

Ты закрываешь все свои стабы фазы 1 и добавляешь единственный слой с I/O, который тебе разрешён — `app/apply/`. Ответ на задачу проходит 11 шагов §8.2 в одной транзакции; заблуждения получают статусы, триггеры и видимость; корни ошибок пишутся тремя источниками; очередь навыков, сеты, дедлайны и прогноз считаются чистыми функциями и кладутся в таблицы B3; замер спускается по пререквизитам; моки собираются по формату экзамена и считаются по его правилам; подбор по жёстким факторам даёт три уровня словами с источниками. Плюс шаблоны SAT по областям `alg` и `adv`. В конце фазы `tests/apply/test_e2e_task.py` на живом графе: ответ → состояние → сет → прогноз.

Что ты не делаешь: роутеры, репозитории, требования/вехи/конфликты (B2), тексты, наблюдатель, контекст репетитора (Ф3 — `build_topic_context` остаётся стабом).

---

## 2. Модель знаний — `app/knowledge/`

Чистые функции. Никакого I/O, никаких импортов `app.db`, `app.graph`. Все параметры — `params.<имя>`.

### 2.1 `reconcile.py` — теперь чистый

`reconcile_task_answer(...) -> ReconcileResult` (дельта §7.1), шаги 2–8 §8.2 без записи:

- Грейд уже посчитан (`tasks.answer.grade`, вызывает `apply`). Из грейда: `correct` / `matched_misconception_id` / `partial` / `omitted_misconception_ids`.
- Вес: `weights.evidence_weight` по ярусу и режиму (§4.3), модификаторы `seen_template_factor` при `n_seen > 0`, `unmatched_incorrect_factor` при неверном без совпадения с дистрактором; `difficulty_factor` из `hlr`.
- `Evidence` по навыку задачи с контекстом `EvidenceContext` (все поля из экземпляра и payload: `time_ratio = time_spent / time_reference`). При `matched_misconception_id` — второе свидетельство `kind="misconception_hit"` по тому же навыку с `summary` названия заблуждения. При `multi_select` с `partial` — `direction=0`, `share`.
- Состояние: `hlr.apply_evidence` от текущего (или стартового: `h0`, `p_at_obs=0.5`, счётчики 0); для общего навыка `math.*` — второе состояние по другому экзамену с весом `× transfer_cross_exam` (§4.6), `exam_ids` приходят аргументом.
- Заблуждение: попадание → `occurrence_count += 1` (только если `event_id` новый — идемпотентность обеспечивает граф, здесь считать честно), `strong_count += 1` при `weights.is_strong(tier)`; верный ответ при `TRAPS` шаблона на confirmed-заблуждение → `consecutive_avoided += 1`; `misconceptions.next_status`; `update_triggers` по всем свидетельствам этого состояния (приходят в `misc_states[].triggers` как агрегат — обновляй инкрементально: `n`, доли).
- Корень: `roots.rule_root` — при ошибке и предпосылке с `p < 0.5, conf > 0.5` → `RootCauseOut(source="rule", confidence=0.4)`; если таких несколько — с наибольшей `strength`.
- `words` — состояние словами: «раскрытие модуля: шатко → уверенно» через `knowledge.words`.

`reconcile_prior(field, value, ...)` — §4.8: `academics.self_assessment` → по областям `Evidence{kind:'self_report', tier 3, weight 0.1}` и состояние `h0_prior`, `p_at_obs` 0.75/0.5/0.3 по «уверенно/средне/слабо» (1–5 → ≥4 / 3 / ≤2), `confidence=0.15`; `academics.ent_trial_score`, `sat_score` → по областям пропорционально `score_share` из `ExamFormat`. Только для навыков без состояния или с `confidence < c_vis` — приоры не перебивают данные.

### 2.2 `misconceptions.py`

- `next_status` — таблица §5.1 целиком, включая `disputed` (любой → `disputed` по событию; `disputed → confirmed` при росте `strong_count` на 2 после `disputed_at`; `undisputed` → `previous_status`). Аргументы стаба Ф1 + `disputed_at`, `strong_at_dispute`, `previous_status`, `event: Literal["hit","avoided","dispute","undispute"]` — сигнатуру расширить, это твой файл.
- `update_triggers` — §5.3: `by_task_type`, `by_difficulty` (`"≥4"`), `hurried` (`time_ratio < 0.7`), `late_session` (`session_minute > 30`), `after_guideline`, `by_tag`, `n`. Хранится долями как `(hits, n)`, отдаётся долями.
- `visible_label` — «подозрение, 1 из 2» / «подтверждено, N наблюдений» / «исправлено, следим» / «оспорено» / пусто для `resolved ≥ under_watch_days` (§5.2).
- `visible_to(state, audience)` — таблица §5.2: `student` видит всё кроме старых `resolved`; `tutor` — `confirmed` и `resolved < 14д`; `sets` — `confirmed` (предпочитать ловушки) и `resolved < 14д` (одна проверочная).
- `trigger_words(triggers, params) -> str | None` — только при `n ≥ trigger_min_n` и доле `≥ trigger_min_share`: «обычно — на задачах с отрицательной ветвью и когда торопится». Нужно Ф3, пиши сейчас — 20 строк.

### 2.3 `roots.py`

`rule_root` (§6 `rule`), `diagnostic_root(error_skill, prereq_skill) -> RootCauseOut` (0.8), `root_boost_skills(root_causes, params, now) -> set[str]` — навыки, на которые ведут корни за `root_window_days` с Σ confidence ≥ 1.0 (§10.1).

### 2.4 `diagnostic.py` — §8.4, чистый автомат

- `start`: бюджет `diag_base` (или `n_tasks` для защиты, пропорционально) по областям по `score_share` → список навыков с наибольшим `weight` в области; `reserve = diag_reserve` (пропорционально при сокращении); известные корни первыми в `pending_descent`.
- `next_skill`: если `reask_queue` содержит пару с счётчиком 0 — она (повтор ловушки через `diag_reask_after`); иначе `pending_descent` (спуск); иначе следующий по бюджету; `None` — конец.
- `apply_answer`: верно → `firm`, предпосылкам косвенное свидетельство `prior_indirect_weight` (возвращается в `state.indirect: list[(skill, weight)]` — `apply` создаст `Evidence`); неверно → `shaky`, если `reserve_left > 0` — самая сильная по `strength` предпосылка в `pending_descent`, приоритет корням; неверно на предпосылке при спуске → `roots_found += diagnostic_root`, спуск дальше; попадание в ловушку → `reask_queue.append((skill, diag_reask_after))`, счётчики других пар уменьшаются с каждым ответом.
- `finish`: `DiagnosticResult`: `firm`, `shaky`, `roots`, `suspected` (заблуждения из попаданий), `start_from` — самые нижние `shaky` без `shaky`-предпосылок, `words` — «Тригонометрия шатко, корень — свойства окружности…».

### 2.5 `hlr.py`, `weights.py` — без изменений, кроме

`weights.evidence_weight` принимает `kind="indirect"` (0.3 при замере) и `kind="self_report"` (0.1). `hlr.apply_evidence` — потолок `p_chat_cap` для яруса 3 (уже в Ф1 — проверить тестом).

---

## 3. Сеты и прогноз — `app/sets/`

### 3.1 `queue.py` — §10.1

`build_queue(states, skill_weights, prerequisites, days_to_test, p_target, root_causes, params)`: `gap = max(0, p_target − p_recall)` (без состояния — `p_recall` по приору или 0.5, `conf = 0`), `urgency = 1 + max(0, (60 − days_to_test)/60)`, `root_boost` из `roots.root_boost_skills`, `need = weight · gap · urgency · root_boost`. Сортировка по `need`; затем стабильная топологическая перестановка: предпосылка с `gap > 0` и `conf ≥ c_vis` — раньше зависящего; предпосылка с `conf < c_vis` и `gap > 0` — `is_check=True` (короткая проверка). Навыки с `level == closed` — не в очереди; `resolved < under_watch_days` заблуждение по навыку — навык остаётся с `need` минимум `weight · 0.05` (одна проверочная задача). Общий навык `math.*` — один раз, `exam_id` текущего экзамена.

### 3.2 `assemble.py` — §10.1, product-logic §4.3

`assemble_sets(...) -> list[SetPlan]` — весь маршрут: режет очередь на сеты по `set_size` топиков (проверки `is_check` не считаются топиками, входят в `checks`); дедлайн сета `i` = дедлайн `i−1` + `Σ gap·effort_h / hours_per_week` недель, округление вверх до дня, не позже `next_test_date − consolidation_days`; навыки с `due_at` в `review_window_days` — в `reviews` ближайшего сета; последний сет перед тестом — `kind="consolidation"` без новых навыков (топики = навыки с наибольшим `weight` из закрытых); если очередь пуста и тест есть — один `review`-сет. `current` не пересобирается: если передан, его `skill_ids` исключаются из очереди, а `deadline` пересчитывается по остатку `gap` (product-logic §4.3: ручная смена уважается). `reason` — одна фраза: «предпосылка для тригонометрии, корень 2 ошибок» / «наибольший вес в алгебре» / «повторение: забудется через 5 дней».

### 3.3 `forecast.py` — §4.7

`forecast(...) -> ForecastOut`: `predicted_raw = Σ weight·p_recall` по навыкам с `conf ≥ c_vis`, остальные — `p` приора с пометкой; `coverage`; `predicted_scaled` по `ScaleTable` формата (интерполяция между точками; SAT — `note="оценочно"`); `hours_needed = Σ gap·effort_h`; `ready_by = today + hours_needed / hours_per_week` недель; `on_track = ready_by ≤ test_date` (None без даты); `note` — «по модели знаний» при `coverage ≥ c_cov`, иначе «по твоей оценке».

---

## 4. Задачи — `app/tasks/`

### 4.1 `select.py` — §10.2

`pick_template`: кандидаты навыка; предпочтение `n_seen == 0`; сложность: на шаг выше последней верной, на шаг ниже после двух неверных подряд (`last_grades` — последние 3 по навыку), старт — медиана сложностей пула; `with_trap` — только шаблоны с `TRAPS`/дистрактором на это заблуждение; `other_structure_than` — исключить шаблоны с тем же `stem`-скелетом (сравнение `template_id` без суффикса после последнего `_`); пул исчерпан — минимальный `n_seen` (product-logic §6.3: повтор с перемешанными вариантами — сид другой).

### 4.2 `mocks.py` — §8.3, §10.2

`assemble_mock(kind, section, templates_by_skill, seen, rng, params)`: `mock_set` — навыки сета, `n ∈ [mock_set_min, mock_set_max]`, доли типов `section.item_types` и сложности `difficulty_shares` пропорционально, время `minutes · n / n_items`; `mock_topic` — один навык, `[mock_topic_min, mock_topic_max]`; `mock_misconception` — `mock_misc_n` шаблонов с `TRAPS` на заблуждение, по разным навыкам если есть. `score(section, grades, exam_format)` — по `scoring_rule` (`"1 per correct"`, `"partial multi_select"`, штрафы, если в формате есть), `scaled` через `ScaleTable` пропорционально `max_raw_score`.

### 4.3 Данные — `data/templates/sat/alg/`, `sat/adv/`

По 2–3 шаблона на каждый навык областей Algebra и Advanced Math (~40–50 шаблонов), типы и сложность по формату, дистракторы с `misconception_id` из `alg.json`/`adv.json`. Расширять библиотеку своих областей по мере шаблонов. `seed.py --coverage` без навыков `< 2` в твоих областях.

---

## 5. Подбор — `app/matching/`

### 5.1 `hard.py` — product-logic §3.3

`hard_filter(profile, programs, forecasts, test_dates, today, params) -> list[HardResult]`. По каждому `Requirement` программы — `FactorOut` со статусом и источником (`Source` из `Program.source_url/checked_at/is_demo`):

- `exam_score`: балл ученика против порога — прогноз `predicted_scaled` при `coverage ≥ c_cov` (`forecast_used`), иначе `academics.sat_score / ent_trial_score` с пометкой «по твоей оценке»; нет ни того, ни другого → `unknown`; `comparator` `>=` → `below/in_range/above` с зоной `in_range` ±5 % от порога.
- `language`: `ielts_score` против порога, аналогично.
- `budget`: `tuition + living` против `budget_per_year` (валюта — как есть, конвертации нет: разная валюта → `unknown` с допущением); `grant_need == only_grant` и нет `scholarships_note` → `below`.
- страна/город/язык/направление из `preferences` и `constraints` (`required`/`excluded`) — `in_range` или `below`; `[]` — любые.
- `deadline`: ближайший `Deadline{kind: application}` против планируемой даты экзамена (`academics.sat_date` или ближайшая `TestDate` после сегодня) — экзамен позже дедлайна → `below`.
- `unknown` не штрафует — уходит в `assumptions` («бюджет не указан — считаем, что подходит»).

`realism_inputs` — только академические и финансовые статусы. `explain_empty` — фактор, который у всех программ `below`, и что даст его ослабление.

### 5.2 `realism.py`

Три уровня из `realism_inputs`: любой академический `below` с разрывом > 15 % или финансовый `below` при `only_grant` → `impossible`; все `in_range/above` → `possible`; иначе `try`. Без процентов наружу — только в `factors[].text` словами («SAT 1450+, у тебя план на декабрь»).

### 5.3 `rank.py`

Веса `matching_priority_weights`, переупорядоченные `priorities.ranking` ученика (первый в ранжировании ×2, последний ×0.5, линейно); `score = Σ weight_f · s_f`, `s_f ∈ {above:1, in_range:0.8, unknown:0.5, below:0}`; `soft_scores` с весом «program» (пусто в Ф2). Сортировка: сначала уровень (`possible > try > impossible`), внутри — `score`. Не меньше `min_candidates` — при нехватке добавлять из следующего уровня.

### 5.4 `compare.py`, `shift.py`

`compare` — `CompareRow` по: требованиям с различающимся статусом (`relevant_to_student=True`), топ-3 приоритетам ученика, стандартным параметрам (стоимость, жизнь, длительность, язык, стипендии; мобильность и наука — из `environment_text` ключевыми словами, помечать `is_demo`); одинаковые значения → `collapsed_same`. `conclusion=None`. `shift.diff` — программы, у которых изменился уровень или статус фактора.

---

## 6. Граф — `app/graph/queries/personal.py`, `schema`

Реализации стабов Ф1 по дельте §7.2 + `list_root_causes`, `get_state_history`. Все запросы начинаются с `MATCH (st:Student {id: $student_id})`. `upsert_misc_state` — `MERGE` по `(student_id, misconception_id)`, `triggers` — JSON-строка. `merge_evidence` — без изменений, но `EvidenceIn.kind` теперь включает `misconception_hit`, `indirect`, `self_report`. `add_root_cause` — `MERGE` по `(evidence_id, root_skill_id)`. `list_evidence` — с `instance_id` из `context` (для `EvidenceOut`).

---

## 7. Применение — `app/apply/` (I/O)

Единственный слой B1 с I/O. Каждая функция: собрать входы (репозитории B3 + свои Cypher), вызвать чистую функцию, записать результат, `events.version.bump`. Граф недоступен (`deps.graph is None` или исключение драйвера) — вернуть результат без состояния и маркер `GraphUnavailable` (см. B3 §2.1); ничего не падает.

- `task_answered.apply_task_answered` — 11 шагов §8.2: `repo.tasks.get_instance` → `tasks.answer.grade` → входы (состояние, пререквизиты с состояниями `get_prerequisites` + `get_states`, `get_misc_states`, `get_seen`) → `reconcile_task_answer` → `merge_evidence` ×N, `upsert_state` (+ кросс-экзаменное), `upsert_misc_state`, `add_root_cause`, `bump_seen`, `mark_answered(correct)` → `sets.rebuild_sets` для экзамена → `bump` → `AnswerResult` (`solution` из экземпляра, `state_words`, `misconception_change`, `knowledge_version`). Пропуск/таймаут — только `mark_answered(correct=None)`.
- `profile_updated` — при путях `academics.*` → `reconcile_prior` → запись; при путях из дельты §3.2 → `rebuild_sets` для экзаменов сохранённых.
- `dispute` — `upsert_misc_state` с новым статусом через `next_status(event="dispute"|"undispute")` → `rebuild_sets` → `bump`.
- `sets.rebuild_sets` — лок `keys.lock(f"rebuild:{sid}")` 10 с (повторный вызов внутри лока — пропуск); входы: `list_exam_skills`, `get_prerequisites` всех, `get_states`, `get_misc_states`, `list_root_causes`, профиль (`hours_per_week`, даты), `p_target` (от `roadmap.requirements` через B3? нет — `apply` не импортирует `roadmap`? Импортировать можно: `roadmap` чистый; до его появления — `p_target_max`), `get_exam_format`, эффорты из `SkillRef.effort_h` → `build_queue` → `assemble_sets` → `repo.sets.replace_plan(keep_current=True)` → `forecast` → `repo.forecast.put` → `SetsByExam`. `open_set` — статус `current`, предыдущий `current` → `upcoming` (если не `done`), `set.opened` пишет роутер. `on_program_change`, `on_set_change`, `on_run_completed` — тонкие обёртки над `rebuild_sets`.
- `diagnostic.*` — `start`: карта, известные корни → `knowledge.diagnostic.start` → `repo.diagnostic.create_run` → первая задача через `tasks.issue(mode=diagnostic)`. `answer(session, deps, student_id, run_id, result: AnswerResult)`: событие `task.answered` и `dispatch` уже сделал роутер (дельта §8) — сюда приходит готовый `AnswerResult`; здесь: косвенные свидетельства предпосылкам при верном (`merge_evidence` с `kind="indirect"`), `knowledge.diagnostic.apply_answer`, `repo.diagnostic.save_state`, событие `diagnostic.progress` (внутреннее, пишет `apply` через `events.store.append` без `dispatch`), следующая задача через `tasks.issue`. `finish`: `knowledge.diagnostic.finish` → событие `diagnostic.completed` → `rebuild_sets` → `complete_run`.
- `mocks.*` — `start`: `section` формата, шаблоны навыков → `assemble_mock` → экземпляры через `generate_instance` + `insert_instance(mode=kind)` → `predicted_before` из `forecast_cache` → событие `mock.started` → `create_run`. `answer(…, result: AnswerResult)` — как у замера: роутер уже записал `task.answered` с `mode=kind`; здесь `save_progress`. `finish` — грейды по `instance_ids` (из `task_instances.correct` и повторного `grade` для `partial`) → `score` → событие `mock.completed` → `rebuild_sets` → `MockResultOut` (`brier_point = (predicted_before/max − raw/max)²`).
- `tasks.issue` — шаблоны навыка (или сета), `seen`, последние грейды (`repo.tasks.list_instances` по навыку с `correct`), `pick_template` → `generate_instance(seed=rng)` → `insert_instance(mode)` → событие `task.issued` → `TaskInstanceOut` без правильного ответа.
- `knowledge.*` — `states_view` (карта + состояния + история для `trend` + корни → `SkillStateView`), `misconceptions_view` (`visible_to("student")`), `explain` (`list_evidence` + экземпляры из `repo.tasks.list_instances`).

---

## 8. Тесты — пишутся до кода, в отдельной сессии

`@pytest.mark.phase2`; чистые — на числах, без БД; `tests/apply/` — unit с monkeypatch репозиториев и `integration` на живом графе (фикстура `seeded_graph`).

`tests/knowledge/`

- `test_reconcile.py`: верный ответ mcq4 уровня 1 → одно свидетельство, `h` вырос по `alpha`; неверный с дистрактором → два свидетельства, `misconception_change` `None → suspected`; второй неверный из другого события с `strong` → `confirmed`; верный при `TRAPS` на confirmed ×3 → `resolved`; общий навык → `cross_exam_state` с весом `× 0.6`; `seen > 0` → вес ×0.8; неверный без совпадения → ×0.7; `partial` multi_select → `direction 0`, `share`; корень по правилу при предпосылке `p 0.4 / conf 0.6`; повторный вызов с тем же `event_id` даёт те же числа (чистота).
- `test_prior.py`: самооценка 5 → `p_at_obs 0.75`, `h0_prior`, `conf 0.15`; пробный балл 28/50 → доли по областям; не перебивает состояние с `conf ≥ c_vis`.
- `test_misconceptions.py`: все переходы таблицы §5.1 включая `disputed` и рецидив; `update_triggers` на 4 свидетельствах даёт `hurried 3/4`; `trigger_words` только при `n ≥ 3, ≥ 0.75`; `visible_label`, `visible_to` по таблице §5.2.
- `test_roots.py`, `test_words.py`, `test_diagnostic.py` (сценарий §8.4: 8+4, ошибка → спуск на сильнейшую предпосылку, ошибка там → корень 0.8, ловушка → повтор через 3, прерывание/восстановление состояния, сокращение до 6 пропорционально, `finish.start_from`).

`tests/sets/`

- `test_queue.py`: `need` по формуле на трёх навыках; предпосылка раньше зависящего; `conf < c_vis` → `is_check`; `closed` не в очереди; корни ×1.5.
- `test_assemble.py`: 7 навыков, `set_size 3` → 3 сета; дедлайны по часам; не позже теста − 7 дней; `current` сохраняется; `consolidation` последним; `reviews` из `due_at`.
- `test_forecast.py`: числа §4.7 на 3 навыках; `coverage`; `ScaleTable` интерполяция; `on_track`; `note`.

`tests/tasks/`

- `test_select.py`: `n_seen 0` первым; сложность ±1; `with_trap`; `other_structure_than`; исчерпание.
- `test_mocks.py`: доли типов и сложности при `n=10`; `score` по правилам секции; `mock_misconception` только с ловушкой.

`tests/matching/`

- `test_hard.py`: профиль и 5 программ из фикстуры → статусы каждого фактора с источником; `unknown` в `assumptions`; прогноз при `coverage ≥ c_cov`, иначе самооценка; дедлайн против даты SAT.
- `test_realism.py`, `test_rank.py` (порядок уровней, приоритеты меняют порядок внутри уровня, `min_candidates`), `test_compare.py` (различающееся/схлопнутое), `test_shift.py`.

`tests/graph/test_personal_phase2.py` (integration): `upsert_misc_state` MERGE, `add_root_cause` без дублей, `list_evidence` порядок, `get_state_history`.

`tests/apply/`

- `test_task_answered.py`: unit с фейковыми репо/графом — вызовы в правильном порядке, `bump` в конце, `GraphUnavailable` при `graph=None`; integration на `seeded_graph` + `templates_db`: ответ → `KnowledgeState` с `PREVIOUS`, `Evidence`, `MisconceptionState`, `seen`, `correct` в `task_instances`, `forecast_cache`, сеты; повторный `dispatch` того же события — те же счётчики (идемпотентность).
- `test_sets_rebuild.py` (integration), `test_diagnostic_flow.py` (integration, полный замер на мини-карте), `test_mocks_flow.py`, `test_tasks_issue.py` (нет правильного ответа в `TaskInstanceOut`; `task.issued` записан), `test_knowledge_view.py`.
- `test_e2e_task.py` (integration): «ответил → состояние → сет → прогноз → версия» на живых Postgres + Neo4j.

`tests/seed/test_data_schemas.py`: каталог заблуждений без дублей `id`; шаблоны `alg`/`adv` проходят `validate_template`; `--coverage` без `< 2` в твоих областях.

---

## 9. Порядок подзадач (чтобы обрыв давал демо)

1. Первый пуш §0.1.
2. `reconcile` + `misconceptions` + `roots` + `words` (чистые) — мерж.
3. `sets/*` + `forecast` (чистые) — мерж.
4. `graph/queries/personal` реализации — мерж.
5. `apply.task_answered`, `apply.sets`, `apply.tasks.issue`, `apply.knowledge` — это шаги 7–8 §9. Мерж — B3 снимает `skip` на `tasks/sets/knowledge`.
6. `matching/*` — шаг 4. Мерж.
7. `diagnostic` (чистый + apply), `mocks` — шаг 6.
8. Шаблоны `alg`/`adv` — по ходу, отдельными PR.
9. `apply.profile_updated`, `apply.dispute`.

---

## 10. Приёмка фазы

- Все стабы Ф1 в твоих модулях, кроме `graph.context.build_topic_context`, заменены; `pytest.raises(NotImplementedError)` остался только на нём.
- `tests/knowledge`, `tests/sets`, `tests/tasks`, `tests/matching` зелёные без БД; `tests/apply`, `tests/graph` зелёные с `make test-int`.
- `test_e2e_task` проходит; повторный `dispatch` идемпотентен.
- `seed.py --coverage`: ни одного навыка SAT `alg`/`adv` с < 2 шаблонов; каталог заблуждений загружается.
- `tests/test_layers.py` зелёный: `knowledge/`, `sets/`, `matching/`, `tasks/` без I/O; `apply/` без `app.llm`/`app.agents`/`fastapi`.

## 11. Вне скоупа

Контекст репетитора и `explain_belief` как инструмент (Ф3); применение `observation.extracted` (Ф3 — но `reconcile` должен быть готов принять свидетельства ярусов 2–3 от наблюдателя: не завязывай его на `TaskInstance` там, где можно передать `EvidenceIn`); персональные узлы и заблуждения; replay; статистика отчёта по сету и варианты по темпу (Ф4); ЕНТ информатика; генерация шаблонов моделью.
