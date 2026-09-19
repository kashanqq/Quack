# Фаза 1 — общие контракты

Quack\! · фаза 1 «каркас» · v0.2 · 17.09.2026 Источники: `tech-stack.md` (стек, структура, очереди), `memory-architecture-quack.md` (события, граф, шаблоны, параметры), `product-logic.md` (анкета, поведение при отказах, сохранение состояния), кейс LOCUS (тестовый логин, секреты не в репозитории).

Этот файл читают все трое и он лежит в контексте каждой сессии Claude Code (ссылка из `CLAUDE.md`). Это не задание — задания в `10-B3.md`, `20-B1.md`, `30-B2.md`. Здесь — всё, что должно называться одинаково у троих. После мержа фазы менять можно только на синке.

---

## 1\. Что такое фаза 1

Три человека параллельно поднимают три слоя одного приложения `apps/api`:

- **B3 — платформа**: хранилища, HTTP, вход, события, очереди, деплой. Всё, что говорит с Postgres, Redis, сервером и браузером.  
- **B1 — движок и граф**: Neo4j, карта навыков, формулы состояния навыка, генерация задач из шаблонов. Всё, что считается правилом и лежит в графе.  
- **B2 — ИИ**: клиент языковой модели, инструменты агентов, цикл вызова инструментов, промпты. Всё, что говорит с моделью.

Зависимости идут в одну сторону: `api → agents → knowledge/tasks/sets/matching → graph/db`. В фазе 1 у каждого слоя есть свой законченный результат, проверяемый своими тестами, и точки стыка с другими слоями описаны здесь.

Результат фазы: на чистой машине `make up && make seed && make test` проходит; `GET /health` на VPS отвечает `ok`; авторизованный пользователь может прочитать и изменить профиль, сохранить программу, отправить сообщение в чат и получить потоковый ответ модели (пока без инструментов); в графе лежит карта навыков SAT Math и формат обоих экзаменов; из шаблона генерируется задача и проверяется ответ.

---

## 2\. Репозиторий и владение

quack/

  apps/api/app/

    main.py config.py keys.py errors.py logging.py     B3

    db/            engine, models, repo/                B3

    events/        store, session, dispatch             B3

    api/           роутеры, deps, sse                   B3

    workers/       ARQ main, registry                   B3

    search/        client (Tavily/ddgs), extract         B3 (extract — стаб, реализует B2 в Ф2)

    schemas/       Pydantic-модели, общие для всех      B3 пишет, содержание — §6 этого файла

    graph/         client, schema.cypher, queries/, context   B1

    knowledge/     hlr, weights, misconceptions, reconcile     B1

    tasks/         render, evaluate, generate, generators, answer   B1

    sets/          queue, assemble, forecast             B1 (стабы)

    matching/      hard, realism, rank, compare          B1 (стабы)

    embeddings.py                                       B1

    llm/           client, fake, tools, prompts, loop   B2

    agents/        router, selection, tutor, observer, postcheck, jobs, prompts/   B2

    seed/          users, programs, calendars           B3

                   skills, exam\_formats, misconceptions, templates, knowledge\_base   B1

  apps/api/alembic/                                     B3

  apps/api/tests/  conftest.py, api/, events/, db/, test\_layers.py, seed/test\_seed\_cli.py   B3

                   knowledge/, tasks/, graph/, seed/test\_data\_schemas.py   B1

                   llm/, agents/                        B2

  data/            exam\_formats/ skills/ misconceptions/ templates/ knowledge\_base/{exams,routes}.json   B1

                   users.json programs\_floor/ knowledge\_base/calendars.json   B3

  scripts/         seed.py gen\_types.sh                 B3

  deploy/          docker-compose.yml Caddyfile .env.example Dockerfile   B3

  docs/            product-logic.md memory-architecture-quack.md tech-stack.md

                   tz/ (этот пакет), sync-log.md, data-formats.md (B1), decisions/llm-provider.md (B2)

  .github/workflows/   ci.yml deploy.yml                B3

  .claude/skills/tz-executor/SKILL.md                   B3

  CLAUDE.md                                             B3

Отличия от `tech-stack.md` §2.1, принятые здесь: добавлены `keys.py`, `errors.py`, `logging.py`, `embeddings.py`, `search/`, `seed/`. Всё остальное — как в tech-stack.

Правило: файл правит только владелец. Нужно изменение в чужом файле — строка в `docs/sync-log.md` формата `[дата время] [кто → кому] что нужно и зачем`. Владелец вносит на синке или сразу, если блокирует.

---

## 3\. Решения фазы

### 3.1 Вход и учётные записи

Кейс требует тестовый логин, если вход есть; product-logic §6.4 требует привязку состояния к пользователю, не к вкладке; tech-stack §2.3 задаёт email \+ пароль и JWT в cookie. Принято:

- **Учётная запись** \= ученик. `users.id` (UUID) используется как `student_id` везде: в событиях, в профиле, в узле `(:Student {id})`.  
- **Создание аккаунтов** — только seed из `data/users.json`. Регистрации, восстановления пароля, смены email нет и не будет в хакатоне.  
- **Пароль** хранится как bcrypt (cost 12). Открытый пароль нигде не логируется и не возвращается.  
- **`POST /auth/login`** `{email, password}` → 200 `{student_id, email}` \+ cookie; при любой ошибке (нет такого email, неверный пароль) — 401 с одним и тем же сообщением `invalid credentials`. Различать «нет пользователя» и «неверный пароль» нельзя (перебор email).  
- **Cookie `quack_token`**: JWT HS256, claims `sub` (student\_id), `iat`, `exp` (30 дней). Атрибуты: `HttpOnly`, `SameSite=Lax`, `Path=/`, `Secure` при `ENV=prod`. Refresh-токена нет; по истечении — логин заново.  
- **`POST /auth/logout`** → 204, cookie сбрасывается (`Max-Age=0`).  
- **`GET /auth/me`** → `{student_id, email}`; здесь же идемпотентно создаётся `(:Student {id})` в графе.  
- **Все остальные роуты** требуют cookie. Нет cookie или JWT невалиден/просрочен → 401 `unauthorized`. `student_id` берётся **только из токена** — никогда из тела запроса или query.  
- **Rate-limit логина**: 10 попыток в минуту на IP (Redis), при превышении 429 `too_many_requests`.  
- **CSRF**: cookie `SameSite=Lax` \+ все мутирующие эндпоинты принимают только `Content-Type: application/json` (иначе 415). Для хакатона этого достаточно; фронт на том же origin через rewrites.

### 3.2 Безопасность — что обязательно в фазе 1

| Область | Правило | Кто |
| :---- | :---- | :---- |
| Секреты | Только в `.env`, `.env` в `.gitignore`. CI падает, если в репозитории есть файл `.env` или строка вида `sk-`/`AIza` в коде. Жюри проверяет явно (кейс). | B3 |
| Логи | structlog-процессор маскирует значения ключей, содержащих `password`, `secret`, `token`, `api_key`, `authorization`. Тела запросов не логируются, только метод, путь, статус, длительность, `request_id`. | B3 |
| Изоляция учеников | Каждый запрос к персональным данным (Postgres и Neo4j) параметризован `student_id` из токена. В Cypher персонального слоя первая строка всегда `MATCH (st:Student {id: $student_id})` (memory-architecture §2.4). Тест на чужой `program_id`/`instance_id` возвращает 404, не чужие данные. | B3, B1 |
| Ввод | Все тела запросов — Pydantic-модели. Текст сообщения чата ≤ 4000 символов, `path` в `PATCH /profile` — из белого списка путей анкеты. Аргументы инструментов агентов валидируются Pydantic до вызова функции. | B3, B2 |
| Выполнение кода | Выражения шаблонов задач считаются только `sympy.parse_expr` с явным словарём имён и `transformations` без `eval`. Строка с любым именем вне словаря — ошибка валидации шаблона. | B1 |
| Модель как источник | Ответ модели и результаты инструментов — данные. Инструменты репетитора только читают; в реестре репетитора функции записи не регистрируются (tech-stack §4.3). Числа и даты в ответе ассистента сверяются с результатами инструментов (`postcheck`) — в Ф1 функция есть, в цепочку ставится в Ф2. | B2 |
| Сеть | В prod-compose наружу опубликованы только порты Caddy 80/443. Postgres, Neo4j (7474/7687), Redis — только внутри сети compose. Neo4j auth включён, пароль из `.env`. | B3 |
| Ключи провайдеров | Ключ LLM и Tavily читаются из `Settings`, никогда не попадают в ответ `/health` и в события. | B3, B2 |
| Ошибки | Наружу — только `{error: {code, message}}` и `request_id`. Трейсбеки в теле ответа запрещены при `ENV=prod`. | B3 |

### 3.3 Сессия работы ученика

`session_id` (UUID) нужен событиям (memory-architecture §1.2: «открытие приложения → 30 мин тишины»). Хранится в Redis `quack:session:{student_id}` с TTL 30 мин, продлевается при каждой записи события. Ключа нет → новый UUID. Единственная функция — `events.session.current_session_id`.

### 3.4 Postgres — вся схема сейчас

Все таблицы memory-architecture §1.1 создаются одной миграцией `0001_init` в этой фазе, включая ещё не используемые. Позже миграции создаёт только B3 и только на синке; остальные присылают изменения моделей через `sync-log.md`.

### 3.5 Neo4j

Vector index на `Misconception.embedding` размерностью `settings.embedding_dim = 384` (tech-stack §3.2, модель `intfloat/multilingual-e5-small`; значение 1024 из memory-architecture §2.4 заменяется на параметр). Индексы §2.4 применяются идемпотентно seed-скриптом.

### 3.6 Языковая модель

`openai` SDK с `base_url` и `api_key` из конфига. Два слота: `MODEL_CHAT` (стриминг, tool use), `MODEL_BULK` (structured output). Structured output — `response_format` с JSON Schema из Pydantic; `LLM_STRUCTURED_MODE=tool` переключает на один инструмент `emit` для провайдеров без `response_format`. Провайдера выбирает B2 в этой фазе (tech-stack §4.1).

### 3.7 Фоновые задачи

ARQ, две очереди `interactive` и `bulk` (tech-stack §2.5). Функции задач лежат у владельцев; `app/workers/registry.py` (B3) — единственное место, где они собираются в списки. В фазе 1 в реестре только `ping`; добавление — на синке.

### 3.8 Стабы

Функция, которую другой слой вызывает в фазе 2, но которая реализуется позже, в фазе 1 существует с точной сигнатурой из этого файла, докстрингом со ссылкой на раздел документа и телом `raise NotImplementedError("phase 2")`. Стаб можно вызывать в тестах только через `pytest.raises(NotImplementedError)`.

### 3.9 Локальный запуск и команды

`docker compose up` из `deploy/` поднимает только Postgres, Neo4j, Redis. API и воркеры — нативно с hot reload. `make up | down | api | worker-interactive | worker-bulk | seed | test | test-int | types | lint`. `make test` — без маркера `integration` (не требует БД); `make test-int` — всё.

---

## 4\. Соглашения

### 4.1 Идентификаторы

| Что | Формат | Пример |
| :---- | :---- | :---- |
| `exam_id` | фиксированные | `SAT_MATH`, `ENT_MATH` |
| `area_id` | `area.<exam>.<name>` | `area.sat.algebra` |
| `skill_id` экзаменный | `<exam>.<area3>.<name>` | `sat.alg.abs_value_eq`, `ent.geo.stereo_volume` |
| `skill_id` общий для двух экзаменов | `math.<area3>.<name>` — один узел, два ребра `HAS_SKILL` (memory-architecture §2.1) | `math.alg.quadratic_roots` |
| `misconception_id` | `lib.<name>` библиотека; `pers.<8 hex student_id>.<name>` персональное | `lib.abs_single_branch` |
| `template_id` | `tpl.<exam>.<area3>.<name>` | `tpl.sat.alg.abs_eq_sum_roots` |
| `program_id` | слаг латиницей `<uni>-<program>` | `nazarbayev-cs` |
| `country_id` | ISO alpha-2 | `KZ`, `US` |
| `event_id` | BIGINT Postgres | `4412` |
| `student_id`, `session_id`, `chat_id`, `set_id`, `instance_id` | UUID v4 | — |

Все `id` в JSON, API и графе — строки, кроме `event_id`. `chat_id` для чата подбора — детерминированный `uuid5(student_id, "selection")`; для чата подготовки — `uuid5(student_id, f"prep:{set_id}:{topic_skill_id}")`.

### 4.2 Время

UTC везде, `datetime` только tz-aware. В API — ISO 8601 с `Z`. В Neo4j — тип `datetime`. Часы (`half_life_h`, `effort_h`) — float.

### 4.3 HTTP

- Объекты — без обёртки. Списки — `{"items": [...], "total": N}`.  
- Ошибки — `{"error": {"code": "...", "message": "..."}}` плюс заголовок `X-Request-Id`.

| HTTP | `code` | Когда |
| :---- | :---- | :---- |
| 400 | `validation_failed` | Pydantic не принял тело/параметры |
| 401 | `unauthorized` | нет/невалидный токен; неверный логин |
| 403 | `forbidden` | зарезервировано |
| 404 | `not_found` | нет объекта или он чужой |
| 409 | `conflict` | повторное сохранение программы и т. п. |
| 415 | `unsupported_media_type` | мутирующий запрос не JSON |
| 429 | `too_many_requests` | rate-limit |
| 500 | `internal` | необработанное исключение |
| 503 | `llm_unavailable`, `search_unavailable` | внешний сервис недоступен (product-logic §6.3) |

- Мутирующие запросы: `POST` создание → 201, действие → 200, `DELETE` → 204\.  
- Стриминг чата: `text/event-stream`, каждая запись `data: <json StreamEvent>\n\n`, последняя — `done` или `error`.

### 4.4 Python

- `snake_case`, глаголы для функций (`get_`, `list_`, `upsert_`, `append_`, `build_`, `apply_`).  
- Все функции, работающие с I/O, — `async`. Чистые модули (`knowledge`, `tasks`, `sets`, `matching`) — синхронные функции без I/O и без импорта `app.db`, `app.graph`, `app.llm`, `app.agents`, `sqlalchemy`, `neo4j`, `redis`, `openai` (проверяет `tests/test_layers.py`).  
- Параметры из memory-architecture §12 — только через `settings.knowledge.<имя>`, никаких литералов в коде.  
- Enum'ы — `StrEnum`; значения совпадают со строками из документов (`"message.user"`, `"mcq4"`, `"confirmed"`).

### 4.5 Ключи Redis

Префикс `quack:`. Строятся только через `app/keys.py`:

| Функция | Ключ | Содержимое | TTL |
| :---- | :---- | :---- | :---- |
| `keys.session(student_id)` | `quack:session:{sid}` | UUID сессии | 30 мин |
| `keys.llm_status()` | `quack:llm:status` | `ok|degraded|down` | — |
| `keys.llm_ratelimit(slot)` | `quack:llm:ratelimit:{slot}` | токен-бакет | — |
| `keys.login_ratelimit(ip)` | `quack:auth:rl:{ip}` | счётчик | 60 с |
| `keys.knowledge_version(student_id)` | `quack:knowledge:version:{sid}` | int | — |
| `keys.ctx_topic(student_id, skill_id)` | `quack:ctx:topic:{sid}:{skill}` | JSON контекста (Ф2) | — |
| `keys.lock(name)` | `quack:lock:{name}` | — | по месту |

---

## 5\. Переменные окружения (`Settings`)

| Переменная | Назначение | Пример |
| :---- | :---- | :---- |
| `ENV` | `local` / `prod` | `local` |
| `DATABASE_URL` | asyncpg DSN | `postgresql+asyncpg://quack:***@localhost:5432/quack` |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | граф | `bolt://localhost:7687` |
| `REDIS_URL` |  | `redis://localhost:6379/0` |
| `JWT_SECRET` | ≥ 32 байта |  |
| `JWT_TTL_DAYS` |  | `30` |
| `LLM_BASE_URL`, `LLM_API_KEY` | OpenAI-совместимый провайдер |  |
| `MODEL_CHAT`, `MODEL_BULK` | два слота |  |
| `LLM_STRUCTURED_MODE` | `response_format` / `tool` |  |
| `LLM_TIMEOUT_CHAT_S`, `LLM_TIMEOUT_BULK_S` |  | `60`, `30` |
| `LLM_RPM_CHAT`, `LLM_RPM_BULK` | rate-limit в минуту |  |
| `LLM_FORCE_DOWN` | эмуляция отказа на защите | `0` |
| `TAVILY_API_KEY` | пусто → фоллбек ddgs |  |
| `EMBEDDING_MODEL`, `EMBEDDING_DIM` |  | `intfloat/multilingual-e5-small`, `384` |
| `LOG_LEVEL` |  | `INFO` |

`Settings.knowledge: KnowledgeParams` — все параметры memory-architecture §12 под теми же именами, значения по умолчанию из таблицы §12, переопределяются переменными `KNOWLEDGE__<ИМЯ>`.

---

## 6\. Общие Pydantic-модели — `app/schemas/`

Файлы создаёт B3 в скелете. Содержание согласовано здесь; поля — из документов, ссылки указаны. Поле с `?` — `Optional`.

### `common.py`

ExamId       \= Literal\["SAT\_MATH", "ENT\_MATH"\]

Tier         \= Literal\[1, 2, 3\]                                   \# ma §4.3

TaskMode     \= Literal\["topic","mock\_set","mock\_topic","mock\_misconception","diagnostic","chat"\]   \# ma §8.2–8.4

TaskType     \= Literal\["mcq4","mcq5","multi\_select","numeric"\]     \# ma §3.1

ErrorClass   \= Literal\["computational","conceptual","attention","procedural"\]   \# ma §2.1

Realism      \= Literal\["impossible","try","possible"\]              \# product-logic: три уровня словами

class Page(BaseModel, Generic\[T\]): items: list\[T\]; total: int

### `auth.py`

LoginIn(email: EmailStr, password: str)

StudentCtx(student\_id: UUID, email: str)

### `profile.py` — product-logic §3.1

ProfileFieldMark \= Literal\["stated","assumed","default"\]        \# сказал / предположили / по умолчанию

class ProfileField(BaseModel, Generic\[T\]): value: T | None; mark: ProfileFieldMark; updated\_at: datetime | None

Level(grade: ProfileField\[int\], admission\_year: ProfileField\[int\])

Direction(field: ProfileField\[str\], alternatives: ProfileField\[list\[str\]\])

Academics(self\_assessment: ProfileField\[dict\[str, int\]\],            \# предмет → 1..5

          ent\_trial\_score: ProfileField\[int\], ent\_profile\_pair: ProfileField\[list\[str\]\],

          sat\_score: ProfileField\[int\], sat\_target: ProfileField\[int\], sat\_date: ProfileField\[date\],

          ielts\_score: ProfileField\[float\], ielts\_target: ProfileField\[float\])

Preferences(countries: ProfileField\[list\[str\]\],                     \# \[\] \== «любые»

            cities: ProfileField\[list\[str\]\], language: ProfileField\[str\],

            budget\_per\_year: ProfileField\[int\], currency: ProfileField\[str\],

            grant\_need: ProfileField\[Literal\["only\_grant","preferred","not\_needed"\]\])

Constraints(required: ProfileField\[list\[str\]\], excluded: ProfileField\[list\[str\]\])

Priorities(ranking: ProfileField\[list\[Literal\["realism","cost","ranking","location","program","research","mobility"\]\]\])

Pace(hours\_per\_week: ProfileField\[int\], explanation\_depth: ProfileField\[Literal\["short","normal","deep"\]\],

     hint\_level: ProfileField\[Literal\["minimal","normal","generous"\]\])

Questionnaire(level, direction, academics, preferences, constraints, priorities, pace)

Traits(verbatim: list\[str\], summary: str)                          \# дословно \+ текстовое резюме предпочтений

Profile(student\_id, questionnaire: Questionnaire, traits: Traits, readiness: float)   \# readiness 0..1

ProfileUpdateIn(path: str, value: Any, by: Literal\["assistant","user"\])

    \# path — точечный путь до поля анкеты: "preferences.countries", "academics.sat\_target";

    \# или "traits.summary", "traits.verbatim" (append). Другие пути → 400\.

### `events.py` — memory-architecture §1.2

class EventType(StrEnum):

    message\_user="message.user"; message\_assistant="message.assistant"

    task\_issued="task.issued"; task\_answered="task.answered"; task\_skipped="task.skipped"; task\_timed\_out="task.timed\_out"

    mock\_started="mock.started"; mock\_completed="mock.completed"

    diagnostic\_progress="diagnostic.progress"; diagnostic\_completed="diagnostic.completed"

    observation\_extracted="observation.extracted"; observer\_requested="observer.requested"

    set\_opened="set.opened"; set\_completed="set.completed"; set\_switched\_by\_user="set.switched\_by\_user"; set\_deadline\_changed="set.deadline\_changed"

    topic\_opened="topic.opened"; topic\_completed="topic.completed"

    misconception\_disputed="misconception.disputed"; misconception\_undisputed="misconception.undisputed"

    skill\_personal\_created="skill.personal\_created"; misconception\_personal\_created="misconception.personal\_created"

    profile\_updated="profile.updated"; program\_saved="program.saved"; program\_removed="program.removed"

    milestone\_done="milestone.done"; recommendation\_accepted="recommendation.accepted"; recommendation\_declined="recommendation.declined"

    guideline\_opened="guideline.opened"; explanation\_opened="explanation.opened"

    job\_failed="job.failed"

EventIn(type: EventType, payload: dict, student\_id: UUID,

        session\_id: UUID | None \= None,          \# проставляет store.append, если None

        exam\_id: ExamId | None, set\_id: UUID | None, topic\_skill\_id: str | None, chat\_id: UUID | None,

        occurred\_at: datetime | None \= None,      \# None → now()

        extractor\_version: str | None, source\_event\_ids: list\[int\] | None)

Event(EventIn \+ id: int, ingested\_at: datetime, processed\_at: datetime | None)

\# payload-модели фазы 1 (остальные — Ф2):

MessageUserPayload(text: str)

MessageAssistantPayload(text: str, mode: Literal\["explain","review","task"\] | None,

                        gave\_task\_instance\_id: UUID | None, hint\_level: int | None, referenced\_skill\_ids: list\[str\])

TaskIssuedPayload(instance\_id: UUID, template\_id: str, skill\_id: str, mode: TaskMode, via: Literal\["topic","mock","diagnostic","chat"\])

TaskAnsweredPayload(instance\_id: UUID, answer: Any, time\_spent\_sec: int, mode: TaskMode, session\_minute: int,

                    after\_guideline: bool, hint\_level\_before: int)

ProfileUpdatedPayload(field: str, value: Any, by: Literal\["assistant","user"\])

ProgramSavedPayload(program\_id: str)          \# и для program.removed

### `programs.py` — product-logic §5.1, memory-architecture §2.3

Requirement(type: Literal\["exam\_score","language","gpa","document","other"\], exam\_id: ExamId | None,

            threshold: float | None, comparator: Literal\["\>=","\<=","range","present"\], description: str, source: str | None)

Deadline(kind: Literal\["application","scholarship","exam\_registration","other"\], date: date, round: str | None,

         source: str, checked\_at: date, is\_demo: bool)

Program(id: str, university: str, country: str, city: str, direction: str, language: str,

        duration\_months: int | None, tuition\_per\_year: int | None, living\_per\_year: int | None, currency: str,

        requirements: list\[Requirement\], deadlines: list\[Deadline\],

        scholarships\_note: str | None, environment\_text: str | None,     \# текст среды для мягких факторов

        source\_url: str, checked\_at: date, is\_demo: bool, extracted\_auto: bool, flagged: bool)

SavedProgram(program\_id: str, saved\_at: datetime)

SearchHit(title: str, url: str, snippet: str)

### `knowledge.py` — memory-architecture §2, §4

SkillRef(id: str, name: str, description: str, exam\_ids: list\[ExamId\], effort\_h: float, base\_half\_life\_h: float | None)

SkillWeight(skill: SkillRef, area\_id: str, weight: float)

Prerequisite(skill\_id: str, strength: float, depth: int)

KnowledgeStateOut(skill\_id: str, exam\_id: ExamId, p\_recall: float, p\_at\_obs: float, half\_life\_h: float,

                  confidence: float, evidence\_mass: float, n\_correct: int, n\_incorrect: int, n\_partial: int,

                  has\_strong: bool, last\_observed\_at: datetime, created\_at: datetime)

EvidenceContext(task\_type: TaskType | None, difficulty: int | None, tags: list\[str\] | None, mode: TaskMode | None,

                time\_ratio: float | None, session\_minute: int | None, after\_guideline: bool | None,

                hint\_level\_before: int | None, topic\_skill\_id: str | None, session\_id: UUID | None)

EvidenceIn(event\_id: int, skill\_id: str, exam\_id: ExamId, kind: str, tier: Tier,

           source: Literal\["task","mock","diagnostic","chat","self\_report"\],

           weight: float, direction: Literal\[1,-1,0\], share: float | None,     \# share — для partial

           difficulty\_factor: float \= 1.0, summary: str | None, context: EvidenceContext,

           observed\_at: datetime, extractor\_version: str | None)

MisconceptionStatus \= Literal\["suspected","confirmed","resolved","disputed"\]

MisconceptionRef(id: str, name: str, description: str, error\_class: ErrorClass, skill\_ids: list\[str\])

Section(name: str, n\_items: int, minutes: int, item\_types: dict\[str,int\], scoring\_rule: str, calculator: bool,

        adaptive: bool, area\_shares: dict\[str,float\], difficulty\_shares: dict\[str,float\], answer\_forms: list\[str\])

ExamFormat(exam\_id: ExamId, name: str, max\_raw\_score: float, sections: list\[Section\],

           scale\_note: str | None, source: str, checked\_at: date, is\_demo: bool)

TestDate(exam\_id: ExamId, date: date, registration\_deadline: date, late\_deadline: date | None, source: str, checked\_at: date, is\_demo: bool)

### `tasks.py` — memory-architecture §3

ParamSpec(range: tuple\[int,int\] | None, choices: list\[Any\] | None)

DistractorSpec(expr: str, misconception\_id: str | None)

OmissionTrap(omit: str, misconception\_id: str | None)

TaskTemplateSpec(id: str, exam\_id: ExamId, type: TaskType, difficulty: int, skill\_id: str, tags: list\[str\],

                 time\_reference\_sec: int, kind: Literal\["template","manual"\] \= "template",

                 params: dict\[str, ParamSpec\], constraints: list\[str\], stem: str,

                 correct: str | list\[str\],                       \# list для multi\_select

                 distractors: list\[DistractorSpec\],

                 omission\_traps: list\[OmissionTrap\] | None,      \# multi\_select

                 answer\_forms: list\[str\] | None, trap\_answers: list\[DistractorSpec\] | None,   \# numeric

                 solution: list\[str\], generator: str | None, figure: str | None)

Option(key: str, text: str, correct: bool, misconception\_id: str | None)

TaskInstance(id: UUID, template\_id: str, seed: int, exam\_id: ExamId, type: TaskType, skill\_id: str,

             stem\_rendered: str, options: list\[Option\], answer: Any, trap\_answers: list\[Option\],

             solution\_rendered: list\[str\], figure\_url: str | None, time\_reference\_sec: int, difficulty: int, tags: list\[str\])

Grade(correct: bool, matched\_misconception\_id: str | None, partial: float | None, omitted\_misconception\_ids: list\[str\])

AnswerIn(instance\_id: UUID, answer: Any, time\_spent\_sec: int, mode: TaskMode, after\_guideline: bool, hint\_level\_before: int)

AnswerResult(grade: Grade, solution: list\[str\], state\_after: KnowledgeStateOut | None, misconception\_change: str | None)

### `chat.py` — tech-stack §2.4

ChatKind \= Literal\["selection","prep"\]

ChatMessageIn(text: str \= Field(max\_length=4000), topic\_skill\_id: str | None, set\_id: UUID | None)

TextDelta(type: Literal\["text\_delta"\], text: str)

ToolCall(type: Literal\["tool\_call"\], tool: str, args: dict, call\_id: str)

ToolResult(type: Literal\["tool\_result"\], tool: str, call\_id: str, data: Any, error: str | None)

Done(type: Literal\["done"\], event\_id: int, mode: str | None, gave\_task\_instance\_id: UUID | None,

     hint\_level: int | None, referenced\_skill\_ids: list\[str\])

StreamError(type: Literal\["error"\], code: str, message: str)

StreamEvent \= TextDelta | ToolCall | ToolResult | Done | StreamError   \# discriminator "type"

AssistantMarkup(mode, gave\_task\_instance\_id, hint\_level, referenced\_skill\_ids)

ChatCtx(student\_id: UUID, kind: ChatKind, chat\_id: UUID, session\_id: UUID, request\_id: str,

        topic\_skill\_id: str | None, set\_id: UUID | None)

MessageOut(id: UUID, role: Literal\["user","assistant"\], text: str, markup: AssistantMarkup | None, event\_id: int, created\_at: datetime)

### `llm.py`

ModelSlot \= Literal\["chat","bulk"\]

LLMMessage(role: Literal\["system","user","assistant","tool"\], content: str | None,

           tool\_calls: list\[ToolCallOut\] | None, tool\_call\_id: str | None, name: str | None)

ToolCallOut(call\_id: str, name: str, args: dict)

LLMUsage(prompt\_tokens: int, completion\_tokens: int)

LLMResult(text: str, tool\_calls: list\[ToolCallOut\], usage: LLMUsage | None, finish\_reason: str)

LLMStatus \= Literal\["ok","degraded","down"\]

### `health.py`

HealthOut(status: Literal\["ok","degraded"\], checks: dict\[str, Literal\["ok","down","skipped"\]\], llm\_status: LLMStatus, version: str)

---

## 7\. Точки стыка между слоями в фазе 1

| Кто вызывает | Что | У кого | Когда |
| :---- | :---- | :---- | :---- |
| B3 `main.lifespan` | `graph.client.create_driver(settings)`, `graph.client.close_driver(driver)` | B1 | Ф1 |
| B3 `api/auth.me` | `graph.queries.personal.ensure_student(driver, student_id)` | B1 | Ф1 |
| B3 `main.lifespan` | `llm.client.LLMClient(settings, redis)` | B2 | Ф1 |
| B3 `api/chat` | `agents.router.run_chat(kind, ctx, message, deps)` | B2 | Ф1 (эхо) |
| B3 `api/health` | `llm_client.status()` | B2 | Ф1 |
| B3 `scripts/seed.py` | `seed.skills.seed_skills`, `seed.exam_formats.seed_exam_formats`, `seed.misconceptions.seed_misconceptions`, `seed.templates.seed_templates`, `seed.knowledge_base.seed_knowledge_base` | B1 | Ф1 |
| B3 `conftest.fake_llm` | `llm.fake.FakeLLMClient(script)` | B2 | Ф1 |
| B1 `seed.templates` | `db.repo.tasks.upsert_template(session, spec)` | B3 | Ф1 |
| B1 `seed.misconceptions` | `embeddings.Embedder` | B1 | Ф1 |
| B2 `llm.client` | `keys.llm_status()`, `keys.llm_ratelimit(slot)`, `errors.LLMUnavailable` | B3 | Ф1 |

`deps` в `run_chat` — dataclass `AgentDeps(llm: LLMClient, pg: async_sessionmaker, graph: Driver, redis: Redis)`, объявлен в `app/agents/router.py` (B2); B3 только конструирует его в `api/chat.py` из `app.state`.

---

## 8\. Порядок фазы

1. **Тесты первыми.** Каждый пишет тесты из своего ТЗ в отдельной сессии Claude Code (не той, что реализует), PR `phase1-tests-<B>`. Тесты помечены `@pytest.mark.phase1`; до реализации CI запускает их с `--runxfail`\-исключением через `xfail(strict=False)` — B3 настраивает в `conftest`.  
2. **Скелет B3** (`phase1-skeleton`, 40 минут): структура папок, `pyproject`, все файлы `schemas/` по §6, `conftest.py`, `Makefile`, compose, `CLAUDE.md`, скилл `tz-executor`, пустой `docs/sync-log.md`. Мержится до начала реализации у B1 и B2; они ребейзятся.  
3. **Реализация** в ветках `phase1/B1`, `phase1/B2`, `phase1/B3` по подзадачам через `tz-executor`. Каждая подзадача ссылается на тест, который должна позеленить.  
4. **Мерж** B3 → B1 → B2. CI: ruff, `pytest -m "not integration"`, `seed.py --validate`, `openapi-typescript` diff.  
5. **Общий прогон** `make test && make test-int` на `main` — B3. Чужой тест упал → чинит тот, чей мерж сломал.  
7. **Синк**: `sync-log.md` разбирается, контракты правятся одним PR, миграция если нужна, ТЗ фазы 2\.

