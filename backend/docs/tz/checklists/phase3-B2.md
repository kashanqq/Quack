# Чек-лист фазы 3 (B2) — живой провайдер

Источник: `docs/tz/phase3-agents.md` §6.13, §7. Выполняется руками на живом
провайдере (`.env` с `LLM_*`, `make up`, `make seed`, `make api`,
`make worker-interactive`). Автотесты провайдер не вызывают.

**Статус: не выполнен.** Код фазы готов, автотесты (unit + интеграционные на
Postgres/Neo4j) зелёные; прогон на живой модели ещё не сделан — результаты
ниже заполняются при прогоне, пустая строка значит «не проверено».

| # | Шаг | Как проверить | Результат |
| :-- | :-- | :-- | :-- |
| 1 | Шаг 1 §9: свободный текст → профиль | `POST /chat/selection/messages` «хочу на IT, куда-нибудь в Европу, SAT не сдавал, люблю тепло» ×3 прогона: `tool_call update_profile` ≥ 3 раз (включая `traits.verbatim`/`traits.summary`), ≤ 2 «?», поля с `mark="assumed"` в `GET /profile`; повтор сказанного — не переспрошено | |
| 2 | Шаг 2: вопрос по данным | «какая страна подходит, если…» → `query_dataset`; все числа текста есть в `tool_result.data`; `traits.summary` изменился | |
| 3 | Шаг 3: резюме → подборка | при `readiness ≥ 0.6` — резюме из 4 блоков с допущениями (`done.mode="summary"`); следующий ход → `run_matching`, ≥ 3 карточек, ни одного `%` | |
| 4 | Шаг 4: сдвиг | «бюджет теперь 5000» → `update_profile.shift` непуст и назван в тексте; порядок и `realism` совпадают с `GET /matching` | |
| 5 | Шаг 7: репетитор + наблюдатель | топик с `confirmed`-заблуждением: ответ в `review` учитывает его; ≤ 15 с после `POST /chat/prep/observe` → `GET /chat/prep/observations` `status="done"`, наблюдения с `message_ids`; `GET /prep/knowledge/version` вырос | |
| 6 | Постпроверка | спровоцировать дату в ответе репетитора → кадр `error postcheck_failed`, в `GET /chat/prep/messages` ответа нет | |
| 7 | Наблюдатель на ≥ 10 фрагментах | доля валидного JSON с первого раза; precision/recall по `(kind, skill)` вручную; время job'а (лог `observer_job.ms`) — решение по `OBSERVER_SLOT` (§9 п. 11) | |
| 8 | Отказ | `LLM_FORCE_DOWN=1`: оба чата → 503; кнопка → `status="failed"`, `failed_reason="llm_down"`; `GET /matching`, задачи, сеты работают | |

Расход прогона записать в `docs/decisions/llm-provider.md`, раздел «Фаза 3».
