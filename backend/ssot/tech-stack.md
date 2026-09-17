# Технический стек — Quack\!

Версия 0.2-draft · 17.09.2026 · дополняет `product-logic.md` и `memory-architecture-quack.md`. Описывает, на чём строим, почему, и что из этого критично. Не описывает API-контракты (отдельный документ `api-contract.md`) и продуктовую логику.

Принцип выбора: **три бэкендера и два фронтендера, 72 часа, бюджет на внешние сервисы — ноль, деплой должен жить до 24.09 без внимания.** Всё, что можно не поднимать, — не поднимаем. Всё, что поднимаем, — в одном `docker compose` на VPS. Все внешние сервисы — только бесплатные тиры, каждый заменяем без правки кода.

Метки: `[OPEN]` — не закрыто; `[B1]`/`[B2]`/`[B3]`/`[F1]`/`[F2]` — владелец по product-logic §10.6.

---

## 0\. Обзор

| Слой | Выбор | Владелец |
| :---- | :---- | :---- |
| Фронт | Next.js (App Router) \+ TypeScript \+ Tailwind \+ shadcn/ui | F1, F2 |
| API | Python 3.12 \+ FastAPI \+ Pydantic v2 | B1, B2 |
| Фоновые задачи | ARQ (asyncio-воркер) поверх Redis, две очереди | B3 |
| Реляционная БД | PostgreSQL 16 | B3 |
| Граф \+ вектор | Neo4j 5 Community (vector index встроен) | B1 |
| Кэш / очередь / статус | Redis 7 | B3 |
| Языковая модель | провайдер `[OPEN]`, через OpenAI-совместимый API; кандидаты с бесплатным тиром — §4.1 | B2 |
| Эмбеддинги | локально, `sentence-transformers` (`multilingual-e5-small`, 384 dims) | B1 |
| Поиск программ | Tavily (free tier), фоллбек `ddgs` без ключа | B3 |
| Деплой | VPS \+ docker compose \+ Caddy (бэк, БД, воркеры); Vercel (фронт) | B3 |

---

## 1\. Фронтенд `[F1, F2]`

**Next.js 15+, App Router, TypeScript, React 19\.** Приложение `apps/web`.

- **Стили:** Tailwind CSS 4 \+ **shadcn/ui** как база компонентов (разрешено кейсом с раскрытием в README). Дизайн-система F1 строится поверх: токены в `globals.css`, компоненты shadcn не переопределяются на ходу.  
- **Данные с сервера:** **TanStack Query** — единый слой для всех read-моделей (профиль, подборка, сохранённые, сеты, состояния навыков). Инвалидация по ключам после любого мутирующего действия — это и есть «изменил → изменилось» на фронте (product-logic §6.1).  
- **Локальное состояние:** Zustand только для UI (открытый топик, активный мок, таймер). Ничего доменного в браузере — product-logic §6.4.  
- **Чат (подбор и подготовка):** SSE через `fetch` \+ `ReadableStream`, свой хук `useSseChat`. Не Vercel AI SDK: его протокол потока пришлось бы имитировать на FastAPI, выигрыш — только `useChat`. Результаты инструментов ассистента (карточки программ, сравнение, задача) приходят в том же потоке типизированными событиями `{type: "tool_result", tool: "run_matching", data}` и рендерятся компонентами.  
- **Математика:** KaTeX (`katex` \+ `react-katex`), условия задач в LaTeX-разметке из шаблонов. Рисунки — статические SVG/PNG из репозитория.  
- **Граф сета:** `@xyflow/react` (React Flow) — 3–5 вершин, зум и драг отключены, читаемо на 375px.  
- **Календарь активности, прогресс, темп:** свои компоненты на CSS grid; библиотека графиков не нужна.  
- **Типы API:** генерируются из OpenAPI FastAPI командой `openapi-typescript` → `apps/web/src/api/schema.d.ts`. **Это контракт между фронтом и бэком**: меняешь Pydantic-модель — перегенерируешь типы, фронт ломается на сборке, а не на демо.  
- **Звук:** `quack.mp3` в `public/`, `<audio>` по событию новой порции рекомендаций.  
- **Mobile-first:** макеты рисуются от 375px; десктоп — расширение, не отдельная версия.

---

## 2\. Бэкенд `[B1, B2]`

**Python 3.12, FastAPI, Pydantic v2, uvicorn.** Приложение `apps/api`. Пакетный менеджер — **uv** (lock-файл, быстрая установка в Docker). Линтер и форматтер — ruff. Тесты — pytest, только для правил: HLR, confidence, статусы заблуждений, сборщик сетов, инварианты шаблонов.

### 2.1 Структура

apps/api/

  app/

    main.py              \# FastAPI, роутеры, lifespan (пулы Postgres/Neo4j/Redis)

    config.py            \# pydantic-settings; параметры memory-architecture §12 — здесь

    db/                  \# SQLAlchemy 2 async \+ asyncpg, Alembic

    graph/               \# neo4j async driver, Cypher-запросы как функции, индексы

    events/              \# запись событий, диспетчер «событие → правило»

    knowledge/           \# HLR, confidence, статусы заблуждений, корни, триггеры — чистый Python

    tasks/               \# шаблоны, генерация экземпляров, инварианты, проверка ответа

    sets/                \# очередь навыков, сборка сетов, прогноз

    matching/            \# жёсткие факторы, реалистичность, ранжирование, сравнение

    llm/                 \# клиент, промпты с версиями, structured output, таймауты, circuit breaker

    agents/              \# ассистент подбора, репетитор, наблюдатель, генераторы текстов

    workers/             \# ARQ-функции по двум очередям (§2.5)

    api/                 \# роутеры: auth, profile, chat, matching, saved, prep, sets, tasks, quack

  alembic/

  tests/

Правило слоёв: `knowledge/`, `tasks/`, `sets/`, `matching/` — **чистые функции без I/O**: принимают данные, возвращают результат. Это то, что product-logic §7 называет «правила»: мгновенно, повторяемо, тестируемо, replay без модели.

### 2.2 Ключевые библиотеки

| Что | Библиотека | Зачем |
| :---- | :---- | :---- |
| Postgres | SQLAlchemy 2 (async) \+ asyncpg, Alembic | события, профиль, кэш программ, read-модели |
| Neo4j | `neo4j` (async driver 5.x) | канонический и персональный слой, база знаний |
| Redis | `redis` (asyncio) | очереди ARQ, кэш контекста топика, флаг статуса модели |
| Очередь | **ARQ** | asyncio-нативный, минимум кода вместо Celery; ретраи, отложенный запуск, крон |
| LLM | `openai` SDK с `base_url` | любой OpenAI-совместимый провайдер без правки кода (§4.1) |
| Эмбеддинги | `sentence-transformers` | локальная модель, без ключей; используется только для канонизации заблуждений |
| Вычисление шаблонов | **sympy** | выражения шаблонов вычисляются символьно — точные дроби, без float-ошибок и без `eval` (§3.4) |
| HTTP наружу | httpx | таймауты и ретраи к поиску и провайдеру |
| Аутентификация | `pyjwt` \+ `passlib[bcrypt]` | тестовый логин по требованию кейса |
| Логи | `structlog` | JSON-логи, `request_id` сквозь api → worker |

### 2.3 Аутентификация

Кейс требует тестовый логин, если вход есть. Минимум: email \+ пароль, JWT в httpOnly-cookie, `POST /auth/login`; регистрация только через seed-скрипт. Next.js ходит в API через `rewrites` (`/api/*` → бэк): cookie идёт автоматически, CORS не нужен. Тестовый аккаунт с заранее пройденным путём — для шагов 1–5 защиты (product-logic §9).

### 2.4 Чат и стриминг

`POST /chat/{kind}/messages` → `StreamingResponse` (SSE). События потока:

- `text_delta` — токены ответа;  
- `tool_call` / `tool_result` — вызов инструмента и его результат (для рендера карточек);  
- `done` — id события `message.assistant` и разметка `{mode, gave_task_instance_id, hint_level, referenced_skill_ids}`.

Ответ репетитора **не ждёт** наблюдателя: после `done` API ставит задачу в очередь `interactive`, если сработал триггер (memory-architecture §8.1). Фронт узнаёт об обновлении модели знаний через polling `GET /prep/knowledge/version` (раз в 3 с в течение 30 с после сообщения). WebSocket не поднимаем: polling проще и переживает любой прокси.

### 2.5 Фоновые задачи — ARQ, две очереди `[B3]`

Один Docker-образ, два сервиса в compose с разным `--queue`. Разделение по тому, ждёт ли ученик результата:

| Очередь | Задача | Триггер | Таймаут |
| :---- | :---- | :---- | :---- |
| `interactive` | `observe_chat` | N сообщений / переход топика / кнопка | 30 с |
| `interactive` | `set_summary` | `set.completed` | 30 с |
| `interactive` | `propose_personal_nodes` | `set.opened` | 30 с |
| `interactive` | `canonize_misconception` | наблюдение `proposed_misconception` | 15 с |
| `bulk` | `pregenerate_set` — гайдлайны и объяснения всех топиков | `set.opened` | 90 с |
| `bulk` | `soft_match` | изменение резюме предпочтений, новые кандидаты | 20 с на программу |
| `bulk` | `extract_program` | новая программа в поиске | 60 с |
| `bulk` | `daily_aggregates` | крон 03:00 \+ открытие Quack | — |
| `bulk` | `recommendations_batch` | крон раз в `recs_interval_h` | — |

Почему две: при открытии сета в очередь падает десяток гайдлайнов; если наблюдатель стоит за ними, «модель обновлена» приходит через минуту вместо трёх секунд. Каждая задача: ретрай ×2, при финальной ошибке — событие `job.failed` в лог, и ничего не сломано: правила работают без текста (product-logic §6.3).

---

## 3\. Данные

### 3.1 PostgreSQL 16 `[B3]`

Всё из memory-architecture §1.1: `events` (append-only), `profiles`, `saved_programs`, `programs_cache`, `task_templates` (копия JSON для выборки; истина — граф), `task_instances`, `seen_templates`, `generated_texts` (кэш по хэшу входов), `set_summaries`, `messages` (read-модель), `recommendations`, `users`. Alembic-миграции в репозитории, `alembic upgrade head` при старте контейнера.

### 3.2 Neo4j 5 Community `[B1]`

Схема — memory-architecture §2 целиком. Vector index на `Misconception.embedding`: размерность — **параметр конфига** (`embedding_dim`, для `multilingual-e5-small` \= 384), cosine. Индексы из §2.4 создаются seed-скриптом идемпотентно (`IF NOT EXISTS`). Community-издания хватает: один инстанс, без кластера; vector index поддерживается с 5.11. Heap 2 GB в compose.

Aura Free не берём: лишний сетевой хоп, холодные соединения и ещё один аккаунт — риск на защите при нулевом выигрыше.

### 3.3 Статические данные в репозитории `[владельцы по product-logic §10.4]`

data/

  exam\_formats/        sat\_math.json, ent\_math.json

  skills/              sat\_math.json, ent\_math.json   (области, навыки, веса, REQUIRES)

  misconceptions/      library.json

  templates/           sat/\*.json, ent/\*.json         (шаблоны, §3.4)

  manual\_tasks/        \*.json \+ figures/\*.svg

  programs\_floor/      programs.json                  (20–30 проверенных)

  knowledge\_base/      exams.json, routes.json, calendars.json

`scripts/seed.py` — один идемпотентный скрипт: валидирует JSON через Pydantic-схемы, прогоняет каждый шаблон по 50 сидам (memory-architecture §3.4), грузит в Postgres и Neo4j, считает эмбеддинги библиотеки заблуждений. Запускается в CI на каждый PR в `data/` — сломанный шаблон не доедет до `main`.

### 3.4 Шаблоны задач — JSON с выражениями `[B2]`

Закрывает memory-architecture §13.3. **Шаблон — данные, не код.** Формат — JSON по схеме §3.1 memory-architecture: `stem`, `params` с диапазонами, `constraints`, `correct`, `distractors` с `misconception_id`, `trap_answers`, `solution`.

Почему не Python-функции:

- данные валидируются одинаково для всех через seed, функцию проверить как данные нельзя;  
- редактирует любой из пяти без знания Python — датасет пишут все;  
- модель генерирует шаблоны пачками как JSON по схеме, а не как код, который потом надо читать;  
- JSON мержится без конфликтов, не несёт риска исполнения произвольного кода.

Вычисление: `sympy.parse_expr` с ограниченным словарём (`sqrt`, `Abs`, `Rational`, `floor`, тригонометрия, константы), без `eval`. Результат — точный: дроби сравниваются с `answer_forms` без float-ошибок; для `numeric` допустимые записи выводятся из sympy-значения (дробь, десятичная с точностью, целое).

Исключение: поле `"generator": "sat.geom.circle_chord"` — ссылка на зарегистрированную Python-функцию в `tasks/generators.py` для 2–3 шаблонов, где выражением не обойтись (кусочные условия, перебор). Проходят те же инварианты и тот же прогон по 50 сидам.

---

## 4\. ИИ `[B2]`

### 4.1 Провайдер и модели — `[OPEN]`, бюджет ноль

Клиент — `openai` SDK с `base_url` и `api_key` из конфига: **любой OpenAI-совместимый провайдер подключается без правки кода**. Модели — два слота в конфиге: `MODEL_CHAT` (ассистент, репетитор, резюме понимания, отчёт по сету — нужен стриминг и tool use) и `MODEL_BULK` (наблюдатель, извлечение программ, мягкое соответствие, гайдлайны, персональные узлы, адъюдикация — нужен structured output, дёшево и быстро).

Кандидаты с бесплатным тиром, проверить лимиты в день выбора:

| Провайдер | Плюсы | Риски |
| :---- | :---- | :---- |
| Google Gemini Flash (через OpenAI-совместимый эндпоинт) | structured output, стриминг, tool use, щедрый free tier | лимит запросов в минуту — фоновые задачи держать в rate-limit |
| Groq (Llama) | очень быстрый, free tier | слабее на инструментах и русском; лимит токенов в день |
| OpenRouter — бесплатные модели | много вариантов одним ключом | нестабильная доступность, на защите риск |

Решение — B2 до вечера 17.09 после теста наблюдателя (structured output на русском) и ассистента (tool use) на 3–5 фрагментах. Один общий rate-limit в Redis, чтобы очередь `bulk` не съела дневной лимит во время живого чата. Ключи — в `.env`, в репозиторий не попадают (кейс проверяет явно).

### 4.2 Structured output

Все фоновые вызовы — через `response_format` с JSON Schema из Pydantic-модели (или tool use с одним инструментом, если провайдер не поддерживает `response_format`; выбирается флагом в конфиге). Выход валидируется Pydantic, невалидный — ретрай один раз, затем `job.failed`. Наблюдатель (memory-architecture §8.1), извлечение программ, персональные узлы — один и тот же код.

### 4.3 Инструменты агентов

Инструменты — обычные Python-функции с Pydantic-аргументами; реестр генерирует JSON Schema для `tools`. Ассистент подбора: `update_profile`, `run_matching`, `compare`, `save_program`, `get_program_facts`, `get_admission_route`, `get_exam_format`, `query_dataset`. Репетитор: `explain_belief`, `get_task`, `get_exam_format`. Только чтение у репетитора — на уровне кода: функции записи в его реестре не зарегистрированы.

**Постпроверка выхода** (product-logic §6.2): числа и даты в ответе ассистента сверяются с результатами инструментов текущего хода; несовпавшее — ответ помечается и не отдаётся. Последний шаг перед `done`.

### 4.4 Промпты и контекст

`app/agents/prompts/*.md` с версией в имени (`observer_v3.md`). Версия пишется в `extractor_version` события и каждого `Evidence`. Контекст репетитора (`<learner_model>`, memory-architecture §9.3) собирается кодом из 4 параллельных Cypher-запросов и кэшируется в Redis по `(student_id, topic_skill_id, last_event_id)`.

### 4.5 Эмбеддинги — локально

`sentence-transformers` с `intfloat/multilingual-e5-small` (384 dims, CPU, \~120 MB). Единственный потребитель — канонизация персональных заблуждений (memory-architecture §5.4): несколько десятков вызовов за весь хакатон. Модель грузится в воркере `interactive` при старте; библиотека заблуждений эмбеддится в seed. Ключей нет, сеть не нужна.

### 4.6 Поиск программ

**Tavily** — free tier (порядка 1000 запросов в месяц, хватает на демо): поиск → URL → `httpx` fetch страницы → извлечение полей `MODEL_BULK` по схеме программы. Фоллбек без ключа — `ddgs` (DuckDuckGo) той же цепочкой. URL источника пишется в запись кэша с пометкой «извлечено автоматически». Если поиск недоступен — подбор по полу (product-logic §6.3).

### 4.7 Фоллбеки

Один флаг `llm_status` в Redis: `ok | degraded | down`. Ставится клиентом при таймауте/5xx/429 (circuit breaker: 3 ошибки за минуту → `down` на 2 минуты, потом проба). `GET /health` отдаёт его фронту; фронт показывает единый статус «ассистент временно недоступен». На защите фоллбек эмулируется переменной `LLM_FORCE_DOWN=1`.

---

## 5\. Инфраструктура и деплой `[B3]`

### 5.1 Схема

Vercel ──── apps/web (Next.js)

               │  rewrites /api/\* →

VPS (docker compose, Caddy TLS)

   ├─ api                 FastAPI, uvicorn, 2 воркера

   ├─ worker-interactive  ARQ \--queue interactive (+ модель эмбеддингов)

   ├─ worker-bulk         ARQ \--queue bulk

   ├─ postgres            16, volume

   ├─ neo4j               5 community, volume, heap 2 GB

   └─ redis               7

VPS есть. Ориентир по ресурсам: 4 vCPU / 8 GB — Neo4j 2 GB, эмбеддинги \~0.5 GB, остальное с запасом. Фронт на Vercel — ноль усилий, превью на каждый PR для F1/F2.

### 5.2 Окружения

- `local`: `docker compose up` поднимает БД и Redis; api, воркеры и web — нативно с hot reload. Seed — `make seed`.  
- `prod`: тот же compose \+ `.env.prod`. Деплой — GitHub Action на push в `main`: SSH → `git pull && docker compose up -d --build`. Никаких ручных шагов на сервере.

### 5.3 CI (GitHub Actions)

На PR: ruff \+ pytest (правила) \+ `seed.py --validate` (данные и шаблоны) \+ `tsc --noEmit` \+ diff сгенерированных OpenAPI-типов (контракт не разъехался). Пять минут, блокирует merge.

### 5.4 Наблюдаемость

Минимум: `structlog` JSON, `X-Request-Id` сквозь api → worker, `GET /health` со статусом Postgres / Neo4j / Redis / LLM / поиска. Sentry не ставим.

---

## 6\. Репозиторий

Монорепо, `main` защищена, работа через короткие PR (история Git проверяется жюри):

quack/

  apps/web/          Next.js

  apps/api/          FastAPI

  data/              датасеты (§3.3)

  scripts/           seed.py, gen\_types.sh

  deploy/            docker-compose.yml, Caddyfile, .env.example

  docs/              product-logic.md, memory-architecture-quack.md, tech-stack.md, api-contract.md

  README.md

README по требованию кейса: задача, решение, стек, архитектура, запуск, тестовый сценарий и логин, роли, источники данных, AI/API, готовые компоненты (shadcn/ui, React Flow, KaTeX), ограничения. Техсправка — раздел README.

---

## 7\. Что решено сознательно против «обычного»

- **Не Celery** — ARQ покрывает всё на малой доле кода и без отдельного `beat`.  
- **Не Vercel AI SDK** — свой SSE, чтобы результаты инструментов шли типизированными событиями.  
- **Не платный провайдер и не привязка к одному** — OpenAI-совместимый клиент, провайдер меняется строкой в `.env`.  
- **Не внешние эмбеддинги** — локальная модель, задача крошечная.  
- **Не Aura / Neon / Upstash** — один compose на своём VPS, ноль cold start, ноль аккаунтов.  
- **Не WebSocket** — polling версии модели знаний; чат и так SSE.  
- **Не Python-функции для шаблонов** — JSON \+ sympy, генератор-функция только как исключение.  
- **Не `eval`** — sympy с ограниченным словарём.

## 8\. Открытые вопросы

1. Провайдер LLM и модели в двух слотах — после теста на фрагментах. `[B2, до вечера 17.09]`  
2. Лимиты выбранного провайдера в минуту и в день → значения rate-limit в конфиге. `[B2]`  
3. Ресурсы VPS: хватает ли на Neo4j \+ эмбеддинги; иначе эмбеддинги в `bulk` и `interactive` без модели. `[B3]`  
4. Tavily: регистрация ключа, проверка лимита. `[B3]`

