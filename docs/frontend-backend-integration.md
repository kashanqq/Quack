# План связки фронта и бэка (после Фазы 3)

Состояние на 2026-09-19. Источники: `backend/app/api/*`, `backend/app/schemas/*`, `frontend/src/api/schema.d.ts`, `frontend/src/components/{account,quack,choice,prep,dashboard}`, `docs/sync-log.md`, ТЗ Фаз 4–5.

## 0. Где мы сейчас

**Бэкенд (Фазы 1–3 готовы).** Роутеры: `auth` (login/logout/me), `profile`, `saved`, `programs`, `matching` (+`/compare`), `chat` (`POST /chat/{selection|prep}/messages` → SSE, `GET` история, `/chat/prep/observe`, `/observations`), `sets`, `knowledge`, `tasks`, `diagnostic`, `mocks`, `overview`, `prep`, `health`. Ошибки — `{"error":{"code","message"}}`, ошибка валидации отдаётся как **400** `validation_failed` (не 422). Сессия — httpOnly-cookie `quack_token`.

**Фронтенд (полностью автономный).** Всё считается в браузере: ассистент (`choice/assistant.ts`), программы (`choice/programs.ts`), подготовка (`prep/prepData|prepModel|entContent|prepAssistant|diagnosticData.ts`), дашборд (`dashboard/dashboardRules.ts`), Quack (`quack/localSource.ts`). Есть переключатели `NEXT_PUBLIC_DATA_SOURCE` и `NEXT_PUBLIC_QUACK_SOURCE`, `remoteAuth.ts` и `remoteSource.ts` уже написаны «под ожидаемый контракт». `src/api/schema.d.ts` сгенерирован (`make types`), но ни один компонент его не импортирует, кроме `quack/contract.ts` (в комментарии).

## 1. Разрывы контракта (что ждёт фронт, а бэк не отдаёт)

| # | Фронт ожидает | Бэк сейчас | Решение |
|---|---|---|---|
| G1 | Кросс-origin запросы с cookie (`localhost:3000` → `:8000`) | Нет `CORSMiddleware` | Добавить CORS (точный origin, `allow_credentials=True`) — B3 |
| G2 | `POST /auth/register {name,email,password}` → 201 / 409 | Нет. `StudentCtx` без `name` | Эндпоинт + `name` в ответе (хранить в профиле) — B3 |
| G3 | `POST /auth/google`, `GET /auth/google/login`, `/auth/google/stub` | Нет | Решение продукта: демо-стаб (`/auth/google/stub` создаёт demo-аккаунт) для MVP; настоящий OAuth — вне MVP |
| G4 | `GET/PATCH/DELETE /state` (KV на студента: чаты, панели, карта, «увидено») | Нет | Таблица `student_state(student_id, key, value jsonb)` + миграция + роутер — B3. Это временный мост, пока экраны не переехали на доменные эндпоинты |
| G5 | `GET /quack/state`, `POST /quack/seen`, `POST /events`, `GET /sse?topics=quack` | Нет; `api/sse.py` — только фрейминг чата. Quack — это Фаза 4 | До Фазы 4 `NEXT_PUBLIC_QUACK_SOURCE=local`. Ниже — сверка контракта с ТЗ Ф4 |
| G6 | Чат-стрим через `EventSource` (в `README`) | Стрим отдаётся на **POST** — `EventSource` так не умеет | Клиент на `fetch` + `ReadableStream`-парсер `data: {json}\n\n` (держать keepalive-комментарии) |
| G7 | Модель программ `Program` (`costEur`, `ieltsMin`, `deadline` строкой, `region`…) | `Program` (`tuition_per_year`, `requirements[]`, `deadlines[]`) + `MatchOut` (`realism`, `factors`, `fits_text`) | Слой-адаптер на фронте `api/adapters/programs.ts`, UI не переписывать |
| G8 | Профиль как плоские слоты (`budget, direction, ent, grade, grant, ielts, language, location, sat, strong`) | Вложенный `Profile` с `ProfileField{value, mark, updated_at}`; `PATCH /profile {path, value, by}` | Таблица соответствия слот → `path` (см. §4.2), `by="user"` для ручных правок |
| G9 | 422 → «email» в `remoteAuth.fail` | 400 `validation_failed` | Читать `error.code`, а не HTTP-статус |
| G10 | Данные подготовки (сеты, навыки, задачи, диагностика, мок) — локальный контент | Полноценные `/sets`, `/knowledge`, `/tasks`, `/diagnostic`, `/mocks`, `/overview` | Переезд по экранам, Фаза I4 |

Дополнительно: `schema.d.ts` нужно регенерировать (`make types`) — в нём уже 40+ путей, но актуальность не проверена; нужен CI-чек «нет диффа после `make types`».

## 2. Принципы

1. **Один переключатель, поэтапно.** Не переводить всё сразу: каждый домен получает свой флаг (`NEXT_PUBLIC_SRC_AUTH|PROFILE|PROGRAMS|CHAT|PREP|QUACK` = `local|remote`), по умолчанию `local`, чтобы фронт можно было показывать без бэка.
2. **Типы — из OpenAPI.** Только `schema.d.ts` + тонкий клиент `src/api/client.ts` (`fetch`, `credentials:"include"`, единый разбор `{error:{code,message}}`, `X-Request-Id`). Никаких рукописных дублей схем.
3. **UI не знает про бэк.** Между ними — адаптеры (`src/api/adapters/*`), как уже сделано для auth/quack. Чистые функции `assistant.ts`/`programs.ts` остаются как офлайн-фолбэк и как эталон для тестов.
4. **Frozen contracts** (`backend/app/schemas/*`, `events/dispatch.py`, `events/handlers.py`, `keys.py`) — любое изменение через `docs/sync-log.md`, не «по дороге».
5. **Мягкий отказ.** Бэк при недоступности Neo4j/LLM отвечает 503/soft-fail (product-logic §6.3) — фронт показывает деградированное состояние, а не белый экран.

## 3. Фазы интеграции

### I0. Окружение и фундамент (1 день)
- `make up` (Postgres, Neo4j, Redis) → `alembic upgrade head` → `make seed` → `make api` (+ `make worker-interactive`, `make worker-bulk`); проверить `GET /health` = ok.
- `.env` бэка: `LLM_BASE_URL`, `LLM_API_KEY`, `MODEL_CHAT`, `MODEL_BULK` (без них чат → 503 `LLMUnavailable`), `JWT_SECRET`.
- `frontend/.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8000`.
- Добавить в корневой `Makefile` цели `dev` (api + фронт) и `types-check` (регенерация + `git diff --exit-code`).
- **Бэк (B3):** CORS (G1); демо-пользователь в `seed.py` (для жюри: известный логин/пароль, § Фаза 5).
- Проверка: `curl -i -X POST localhost:8000/auth/login` с Origin `http://localhost:3000` возвращает `Access-Control-Allow-Origin` и `Set-Cookie`.

### I1. Клиент API и типы (1 день)
- `src/api/client.ts`: `api.get/post/patch/delete`, тип `ApiError{status, code, message, requestId}`, ретраи только для идемпотентных GET, редирект на `/login?next=` при 401.
- `src/api/stream.ts`: `postSSE(path, body, onEvent, signal)` — парсер кадров `text_delta | tool_call | tool_result | done | error`, игнор `: keepalive`, отмена через `AbortController`.
- Тип событий берётся из схемы (`StreamEvent`); в OpenAPI SSE-тела нет, поэтому тип держим руками рядом с парсером и покрываем тестом на фикстуре из `tests/api/test_chat*.py`.
- Проверка: `npm run build` без ошибок типов.

### I2. Авторизация (1–2 дня) — флаг `AUTH`
- **Бэк:** `POST /auth/register` (G2, bcrypt уже есть в `auth.py`, `upsert_user` в `db/repo/users.py`; 409 при дубле; сразу выставлять cookie), `name` в `StudentCtx`/ответах; стаб Google (G3).
- **Фронт:** `remoteAuth.ts` — маппинг ошибок по `error.code` (G9), убрать угадывание форм `student_id ?? id`.
- Rate-limit `/auth/login` (10/мин на IP) → `AuthError("rate")` уже обработан.
- Проверка: регистрация → `/choice` открывается; обновление страницы сохраняет сессию (`/auth/me`); logout чистит cookie; неверный пароль → «invalid».

### I3. Профиль, сохранённые программы, подборка (3–4 дня) — флаги `PROFILE`, `PROGRAMS`
1. **Профиль.** `ProfilePanel` читает `GET /profile`, правит `PATCH /profile {path,value,by:"user"}`. Метки `stated/assumed/default` показывать как «сказал / предположил / по умолчанию» (уже есть в продуктовой логике). Таблица слотов — §4.2.
2. **Программы.** `GET /programs`, `GET /programs/{id}`, `GET/POST/DELETE /saved` → замена `PROGRAMS` и локального «сохранено». Адаптер G7; `is_demo` → плашка «демо».
3. **Подборка и сравнение.** `GET /matching` заменяет `calcRealism`; `factors[]` рендерить в панели «Подробнее»; `soft_pending` → скелетон «уточняем». `GET /matching/compare?ids=` → `CompareView` (`collapsed_same`, `relevant_to_student`).
- **Шкала реалистичности:** сверить строки `Realism` бэка с `Level` фронта (`realistic|try|unlikely`) — если расходятся, приводить в адаптере, схему не менять.
- Проверка: смена бюджета в профиле меняет порядок подборки; сохранить/удалить программу переживает перезагрузку.

### I4. Чат подбора (3–4 дня) — флаг `CHAT`
- `ChoiceApp` вместо `assistant.ts`: `postSSE("/chat/selection/messages", {text})`; `text_delta` → дописывание в пузырь; `tool_result` инструмента подбора → карточки программ (`data` — полный ответ инструмента); `done{event_id, mode, referenced_skill_ids}` → закрыть стрим и сохранить `event_id`.
- История: `GET /chat/selection/messages` при открытии; локальные чаты (`state`-ключи) → серверные.
- Обновление профиля агентом (событие `profile.updated`) → перечитать `GET /profile` и `GET /matching` после `done`.
- Ошибки: 503 `llm_unavailable` → «ассистент временно недоступен, вот подборка по правилам» (`assistant.ts` как фолбэк); 429/409 от `chat lock` (`CHAT_LOCK_TTL_S`) → блокировать поле ввода на время ответа.
- Проверка: реплика «бюджет 8000 евро, хочу CS в Испании» → профиль обновился, карточки пришли потоком, повтор запроса из истории идентичен.

### I5. Подготовка (7–10 дней, самая большая) — флаг `PREP`
Идём по экранам, каждый — отдельный PR:

| Экран фронта | Эндпоинты | Замена |
|---|---|---|
| `Overview.tsx` | `GET /overview`, `POST /overview/milestones/{key}` | `prepModel.ts` |
| `SetsView/SetDetail/RouteView` | `GET /sets`, `POST /sets/switch`, `GET|PATCH /sets/{id}`, `POST /sets/{id}/open` | `prepData.ts` |
| `TopicWorkspace` | `POST /sets/{id}/topics/{skill}/open|complete`, `POST /tasks`, `/tasks/{id}/answer|skip|solution` | `entContent.ts`, `topicContent.ts` |
| `SkillGraph/GraphCanvas` | `GET /knowledge`, `GET /knowledge/explain/{node}`, `POST /knowledge/refresh`, `POST /knowledge/misconceptions/{id}/dispute` | локальный граф |
| `DiagnosticMock` | `POST /diagnostic`, `GET /diagnostic/active`, `POST /{id}/answer|finish`; `POST /mocks…` | `diagnosticData.ts` |
| Чат репетитора | `POST /chat/prep/messages` (`topic_skill_id`, `set_id`), `POST /chat/prep/observe`, `GET /chat/prep/observations` | `prepAssistant.ts` |
| Инвалидация | `GET /prep/knowledge/version` (поллинг раз в N секунд/при фокусе) | — |

Замечания: `POST /tasks` — стриминга нет (обычный JSON); `knowledge/refresh` ставит job в ARQ — нужен воркер и опрос версии; `Done.gave_task_instance_id` из чата репетитора → открыть задачу в рабочей области. Нужен явный мап `skill_id` ↔ узлы карты фронта.
- Проверка сквозная: ответ на задачу → `knowledge` меняется → сет пересобирается → `overview` показывает новый прогноз.

### I6. Дашборд и Quack (после Фазы 4)
- До готовности Ф4 — `QUACK=local` (текущее поведение). Дашборд (`dashboardRules.ts`) переводим на `GET /overview` + `GET /matching`, локальные правила остаются как расчёт «изменил → изменилось».
- После Ф4: реализовать/свериться с `/quack/state`, `/quack/seen`, `/sse?topics=quack`, `POST /events` из `remoteSource.ts` против §API ТЗ Ф4. Если ТЗ иное — правим **фронт** (`remoteSource.ts`), т.к. бэк-контракт первичен. `EventSource` с `withCredentials` тут корректен (GET).
- Заменяем `POST /events` (клиентские события) на серверные эффекты: профиль/сохранённое/подготовка уже порождают события на бэке (`profile.py` → `store.append`), фронту репортить их не нужно.

### I7. `/state` и вывод из эксплуатации локального хранилища (1–2 дня)
- Реализовать G4 как мост; оставить **только** UI-предпочтения (ширины панелей, вкладки, «FirstHint показан», положение карты). Всё доменное (профиль, чаты, программы, прогресс) — из доменных эндпоинтов.
- Миграция данных не нужна (MVP): при первом входе в `remote` локальные данные аккаунта не переносятся.

### I8. Демо, устойчивость, деплой (Фаза 5)
- Демо-аккаунт и предгенерированные тексты (ТЗ Ф5), `is_demo`-плашки.
- Прод: Caddy отдаёт фронт и проксирует `/api/*` на бэк **одним origin** → cookie `Secure`, CORS не нужен; `NEXT_PUBLIC_API_URL=/api`. Отключить буферизацию для SSE (`X-Accel-Buffering: no` уже отдаётся; в Caddy `flush_interval -1`).
- Скрипт бэкап/восстановление и runbook — по ТЗ Ф5.

## 4. Справочные таблицы

### 4.1 Порядок и владельцы
| Этап | Бэкенд (кто) | Фронт | Блокер |
|---|---|---|---|
| I0 | CORS, demo-seed (B3) | env, Makefile | Docker, LLM-ключи |
| I1 | — | client/stream | — |
| I2 | register, name, google-stub (B3) | remoteAuth | I0 |
| I3 | — (эндпоинты есть) | адаптеры, панели | I2 |
| I4 | — (LLM/агенты B2) | ChoiceApp | I3, LLM |
| I5 | `/sets` и `/tasks` стабы закрыть (B1/B3, см. sync-log) | 6 экранов | I4, seed графа |
| I6 | Фаза 4 (B1/B2/B3) | remoteSource | Ф4 |
| I7–I8 | `/state`, Ф5 (B3) | чистка store | I3–I5 |

Параллелится: I1 || I0; I3 (профиль/программы) || I2 после общего клиента; I5 по экранам.

### 4.2 Слоты профиля → `PATCH /profile path`
Соответствие уточнить по `backend/app/schemas/profile.py` (поля `level.grade`, `academics.sat_score|sat_target|sat_date|ielts_score|ielts_target|ent_trial_score`, `preferences.budget_per_year|countries|cities|language|grant_need`, `direction.field`, `priorities.ranking`, `constraints.*`). Фронтовый `strong` («сильные предметы») прямого поля не имеет — либо `academics.self_assessment`, либо оставить в `/state`; решить на синке. `grant` → `grant_need` (`only_grant|preferred|not_needed`).

## 5. Тестирование и приёмка

- **Контрактные:** CI-шаг `make types` без диффа; тест SSE-парсера на записанных кадрах; юнит-тесты адаптеров (программы, профиль, ошибки).
- **Сквозные (Playwright, локальный стек):** регистрация → анкета в чате → подборка → сохранить программу → подготовка → ответ на задачу → рост шансов на дашборде.
- **Сценарий жюри (product-logic §9):** проходить его же как e2e-скрипт после I5.
- **Негативные:** остановить Neo4j (soft-fail), убрать LLM-ключ (503 → фолбэк-текст), 401 при протухшей cookie, двойная отправка в чат (lock).
- **Критерий готовности:** при `все флаги = remote` в `frontend/src` нет импортов `programs.ts`/`prepData.ts` вне фолбэка; `local`-режим по-прежнему собирается и работает.

## 6. Риски

| Риск | Митигация |
|---|---|
| Расхождение моделей программ/реалистичности (G7) | Адаптеры + фикстуры; не менять frozen-схемы |
| Стрим через POST, прокси буферизуют | Свой `fetch`-парсер; `flush_interval -1` в Caddy; проверять в проде, а не только локально |
| LLM недоступна/лимиты (`LLM_RPM_CHAT=10`) | Фолбэк на правила, 429 → «подожди секунду» |
| Пустой граф без `make seed` | `health` показывает Neo4j; фронт — «карта строится»; seed в демо-инструкции |
| Раздувание `/state` в «вторую БД» | Только UI-предпочтения; ревью каждого нового ключа |
| Часть эндпоинтов Ф2 — стабы (`repo.sets/diagnostic/mocks` в sync-log) | Проверить в I5 первым шагом каждого экрана; заводить записи в `sync-log.md` |
| Конфликт веток B1/B2/B3 из-за frozen-контрактов | Правки схем только через sync-log → владелец → rebase |

## 7. Ближайшие шаги (первая неделя)
1. I0: поднять стек, CORS, `curl`-проверка cookie с origin фронта.
2. I1: `client.ts` + `stream.ts` + тесты парсера.
3. I2: `/auth/register` + `remoteAuth`, включить `AUTH=remote` локально.
4. Открыть в `docs/sync-log.md` записи: G2/G3/G4 (B3), сверка `Realism`/слотов профиля (B1), формат `/quack/*` (Ф4).

## 8. Статус выполнения

- **I0 (частично).** Готово: CORS (`CORS_ORIGINS` в `config.py`, по умолчанию `localhost:3000/3001`), проверено preflight-запросом и тестом. Не сделано: demo-пользователь в `seed.py`, цели `dev`/`types-check` в `Makefile`.
- **I1 готово.** `frontend/src/api/client.ts` (`api.get/post/patch/delete`, `ApiError` с `code`), `frontend/src/api/stream.ts` (`postSSE`, разбор кадров; проверен на разорванных кадрах, `\r\n` и keepalive). `schema.d.ts` перегенерирован.
- **I2 готово (без Google).** `POST /auth/register`, миграция `0003_user_name`, `name` в ответах `/auth/login|register|me` (в `/me` имя берётся из JWT-claim, без обращения к БД), `remoteAuth.ts` переведён на `api` и коды ошибок. Проверено на живом стеке: регистрация → cookie → `/auth/me` → повтор даёт 409 → login. G3 (Google) остаётся открытым.
- **Замечание для B2/B3.** Без `LLM_API_KEY` приложение не стартует (`OpenAIError: Missing credentials` в `LLMClient`), хотя по продуктовой логике LLM должна деградировать мягко. Локально запускать с любым непустым ключом.
- **Замечание про Windows.** `scripts/gen_types.sh` ищет `node_modules/.bin/openapi-typescript` как исполняемый файл и на Windows падает; типы генерировались вручную через `node node_modules/openapi-typescript/bin/cli.js`.
- **G4 готово (мост `/state`).** `GET/PATCH/DELETE /state`, таблица `student_state` (миграция `0004`), лимиты: 200 ключей на PATCH, ключ до 200 символов. Без него `store.open` падал с `state 404` сразу после входа.
- **Google-вход убран из UI** (`LoginView.tsx`); `loginWithGoogle` в контракте и `remoteAuth.ts` оставлены, кнопки нет. G3 отложен.
- **I3 (подборка на каталоге бэка) — код готов, в браузере не проверен.** Решение: основной каталог — бэка (23 демо-программы из `data/programs_floor`, надо выполнить `seed.py --only users,calendars,programs`). Реализовано: `src/api/backend.ts` (типизированные вызовы), `choice/catalog.ts` (адаптер `Program`/`MatchOut` → модель фронта, перевод чат-профиля в пути анкеты `PATCH /profile`, загрузка `/matching` и `/saved`), реестр `catalog`/`remoteEvaluations` в `programs.ts` (`programById` и `evaluate` читают его, вызовы экранов не менялись), синхронизация «Избранного» и подборки в `ChoiceApp.tsx` только при `NEXT_PUBLIC_DATA_SOURCE=remote`. Поля, которых нет на бэке (климат, размер города, наука, обмен, IELTS), скрыты для программ с бэка. Не сделано: серверное сравнение (`/matching/compare`), чат через агента (I4), очистка профиля/избранного на бэке при «начать заново».
- **Починен `scripts/seed.py`** (импортировал `_optional_layer` из `app.main`, а он давно в `app.loader`). Полный `seed.py` на этой машине падает на шаге misconceptions: модель эмбеддингов не грузится из-за нехватки файла подкачки Windows (`os error 1455`); шаги users/skills/exam_formats/calendars/programs проходят.
- **I4 (чат подбора через агента) — код готов, в браузере не проверен.** `choice/remoteChat.ts`: `sendSelectionMessage` (стрим `POST /chat/selection/messages`; `run_matching` → карточки, `compare` → открыть сравнение, `update_profile`/`save_program` → перечитать профиль/избранное), `backendToProfile` (анкета бэка → слоты панели), `loadHistory`. В `ChoiceApp.tsx` при `remote`: ответ печатается по мере стрима, сценарий «резюме → подтвердить» и локальный `assistant.ts` не используются; профиль и история читаются с сервера (один серверный чат на студента, id `server`); правка в панели профиля шлёт только изменённые слоты (`syncFields`), автосинк всего профиля убран, чтобы не затирать данные агента. Ошибки: 503 `llm_unavailable`, 409 (ещё отвечает), 429 показываются сообщением в чате. Замечание для B2: агент записал `sat_score=1300` (порог SAT_MATH до 800), панель показывает значения ≤800 удвоенными.
- **I7.** `/state` остаётся мостом для UI-состояния; в `remote` профиль, чат и избранное читаются с доменных эндпоинтов. «Начать заново» теперь очищает и серверное избранное.
- **I8 (прод, один origin).** `deploy/Dockerfile.web` собирает статический экспорт фронта (`NEXT_PUBLIC_DATA_SOURCE=remote`, `NEXT_PUBLIC_API_URL=/api`) в образ Caddy; `Caddyfile`: `/api/*` → api (префикс срезается, `flush_interval -1` для SSE), `/health` → api (release smoke), остальное — статика с `try_files`. CORS в проде не нужен. Демо-аккаунты — из Фазы 5 (`demo@quack.kz` / `quack-demo`). Локально образ не собран: Docker Desktop падает на `npm ci` (нехватка памяти/подкачки); `npm run build` с этими переменными проходит.
