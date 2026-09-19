# Ручной прогон фазы 4 (§15)

Ведёт B3. Прогон на поднятой инфраструктуре (`make up`, `make seed`), два
воркера (`make worker-interactive`, `make worker-bulk`) и API (`make api`).
Каждый пункт — что сделать и что должно получиться. Пункт не «зелёный»,
пока не видно результата в API или в БД: логов воркера недостаточно.

Перед прогоном:

- [ ] `make test` — зелёный (`pytest -m phase4` без `xfail`).
- [ ] миграции применены: `cd backend && uv run alembic upgrade head` →
      `0003_phase4`.
- [ ] в `.env` заданы `LLM_BASE_URL`, `MODEL_BULK`, `LLM_RPM_CHAT`,
      `LLM_RPM_BULK` (сумма — не выше лимита провайдера, §1.6).

## 1. Открытие сета → гайдлайны

- [ ] `POST /sets/{id}/open`.
- [ ] в логах `worker-bulk` — `pregenerate_set` с `job_id pregen:*`.
- [ ] в течение 60 с `GET /texts/{set}/{skill}?kind=guideline` → `ready`
      для всех топиков, `mark=generated`, `prompt_version=guideline_v1`.
- [ ] до этого тот же запрос отвечает `generating` — не пустым телом.
- [ ] повторный `POST /open` не вызывает вторую генерацию (в логах нет
      второго `pregenerate_set` с тем же `job_id`).
- [ ] с `LLM_FORCE_DOWN=1`: `generating`, а при уже сохранённом тексте —
      `stale` с `mark=saved_version`.

## 2. Завершение сета → отчёт

- [ ] закрыть последний топик → строка в `set_summaries` со `stats`
      появляется сразу (`GET /sets/{id}/summary`).
- [ ] в течение 10 с `GET /overview` → `last_set_summary.text` заполнен.
- [ ] с `LLM_FORCE_DOWN=1` → `text=null`, `stats` полные, `status=failed`
      или `generating`.

## 3. Предпочтения → мягкое соответствие

- [ ] `PATCH /profile {path: "traits.summary", value: "тёплый климат,
      небольшой город", by: "user"}`.
- [ ] через ≤ 60 с `GET /matching` → `fits_text` у ≥ 3 программ,
      `soft_pending=false`.
- [ ] уровни `realism` не изменились ни у одной программы.

## 4. Поиск → извлечение → программа

- [ ] `POST /programs/search {"query": "..."}` → 202 и `search_id`.
- [ ] в течение 90 с `GET /programs/search/{id}` → `done`, `found ≥ 1`
      (или `unavailable`, если поиск отключён).
- [ ] новая запись в `programs_cache`: `extracted_auto=true`,
      `source_url`, `checked_at` = сегодня, `is_demo=false`.
- [ ] у каждого числа в карточке есть цитата в `extraction.evidence`
      или поле пустое.
- [ ] `POST /programs/{id}/flag {"reason": "..."}` убирает её из
      `GET /matching`; на «пол» (`extracted_auto=false`) — 409.

## 5. Лента Quack

- [ ] `GET /quack` у ученика с сохранёнными: `pace` с прогнозом по
      каждому экзамену, `items` по убыванию срочности, у каждой —
      `reason`, `action_text`, `action`; `activity` на 14 дней.

## 6. Темп и варианты

- [ ] при `on_track=false` — четыре варианта, у доступных
      `forecast.on_track=true` и текст с датой.
- [ ] с `LLM_FORCE_DOWN=1` ответ тот же: варианты считаются без модели.

## 7. Принятие

- [ ] `POST /quack/{id}/accept` меняет профиль / требование / сет —
      видно в `GET /profile`, `GET /overview`, `GET /sets`.
- [ ] прогноз пересчитан, рекомендация `accepted`, заголовок
      `X-Knowledge-Version` присутствует.
- [ ] повторный `accept` — 200 и никаких новых событий в `events`.

## 8. Отказ

- [ ] `POST /quack/{id}/decline` → `declined`.
- [ ] после ручного батча (`arq` CLI или следующий крон) та же причина
      не возвращается.
- [ ] изменение причины (например, сохранена программа с бо́льшим
      порогом) — вариант появляется снова.

## 9. Активность

- [ ] `POST /quack/seen` → в течение 30 с `GET /quack/activity`
      показывает сегодняшнюю задачу.
- [ ] `hours_per_week_actual > 0` после сессии работы.

## 10. Срочные

- [ ] сохранение программы с конфликтом дат или веха ≤ 5 дней →
      в `GET /quack` в течение 15 с `urgent` и `new_batch=true`, без
      ожидания крона.

## 11. Отчёт и контекст

- [ ] отчёт виден в Обзоре и в `GET /sets/{id}/summary`.
- [ ] следующий топик получает слот `previous_set` (видно в логе сборки
      контекста или в ответе репетитора).

## 12. Сквозное

- [ ] `make test && make test-int` — зелёные.
- [ ] `openapi.json` содержит `/texts/*`, `/quack/*`, `/programs/search*`,
      `/programs/{id}/flag`, `/sets/{id}/summary`.
- [ ] `make types` перегенерировал `frontend/src/api/schema.d.ts`.
- [ ] `LLM_FORCE_DOWN=1` не меняет ни один ответ роутеров фазы 2.
- [ ] в логах нет `job.failed` при живом провайдере на пунктах 1–11.
- [ ] `LLM_RPM_CHAT + LLM_RPM_BULK ≤` лимита провайдера записано в
      `docs/decisions/llm-provider.md`.
