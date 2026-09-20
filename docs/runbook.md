# Runbook: релиз, отказы, восстановление, откат

Фаза 5, §22 «Release/runbook минимум». Документ для того, кто выкатывает и
дежурит, а не для читателя архитектуры. Всё, что здесь описано, проверяется
командами из репозитория; ничего не требует доступа к чужим системам.

Обозначения: `<>` — значение, которое подставляет оператор. Ключи, пароли и
пути к секретам в этот файл не попадают и попадать не должны.

## 1. Что такое «выкачено»

Релиз считается выполненным, если одновременно:

1. `https://<DOMAIN>/health` отвечает `200`;
2. в ответе `version` равен точному SHA коммита `main`, который выкатывали;
3. `status` = `ok`, а не `degraded`.

`status=degraded` с кодом 200 — это **не** успешный smoke: код 200 сохранён
для совместимости, а решение о годности релиза принимает деплой-workflow,
который сверяет и `version`, и `status`.

## 2. Предрелизная проверка (10 минут)

```bash
make lint                       # ruff check + format
make test                       # юнит-тесты
make test-int                   # нужны живые PG, Neo4j, Redis
cd backend && uv run --frozen pytest -m phase5
cd backend && uv run --frozen python ../scripts/seed.py --validate
make types                      # схема фронта совпадает с OpenAPI
```

Переменные для `make test-int`:

```
TEST_DATABASE_URL=postgresql+asyncpg://<user>:<pass>@127.0.0.1:5432/quack_test
TEST_NEO4J_URI=bolt://127.0.0.1:7687
TEST_NEO4J_USER=neo4j
TEST_NEO4J_PASSWORD=<pass>
```

Интеграционные тесты **очищают граф** (`MATCH (n) DETACH DELETE n`). После
них локальную базу нужно пересидировать: `make seed`. На продакшене
интеграционные тесты не запускаются никогда.

Отдельно, один раз перед защитой: живой чек-лист провайдера
`backend/docs/tz/checklists/phase5-live.md` и отчёт качества наблюдателя
`backend/docs/tz/checklists/phase5-observer-eval.md`. Тесты без ключа не
доказывают, что провайдер работает.

## 3. Деплой

Выкатывает workflow `.github/workflows/deploy.yml` по push в `main`. Он:

- требует **все** секреты `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`,
  `VPS_KNOWN_HOSTS`, `DOMAIN`. Неполный набор — ошибка, а не пропуск;
- при полностью пустом наборе пропускает деплой и **говорит об этом**.
  «CI зелёный, деплой пропущен» — это не выполненный деплой (§22);
- подключается по SSH со `StrictHostKeyChecking=yes` и известными хостами;
- проверяет, что на сервере ровно тот SHA, что выкатывается;
- отказывается работать, если в `deploy/.env` остались примерные значения
  или адреса `localhost`;
- поднимает compose, прогоняет `alembic upgrade head` и проверяет
  `https://<DOMAIN>/health` — и `status`, и `version`.

Ручной деплой того же самого:

```bash
ssh <user>@<host>
cd /opt/quack && git pull --ff-only origin main
compose="docker compose --env-file deploy/.env -f deploy/docker-compose.yml \
  -f deploy/docker-compose.prod.yml --profile prod"
$compose config --quiet
$compose up -d --build
$compose exec -T api alembic upgrade head
curl -fsS https://<DOMAIN>/health
```

Наружу открыты только 80 и 443 (Caddy). PostgreSQL, Neo4j и Redis host-портов
не публикуют — в `docker-compose.prod.yml` они сброшены через `ports: !reset []`.

### Гонка миграций

`api` запускается двумя uvicorn-воркерами, но `alembic upgrade head` в его
команде — один процесс до старта воркеров, и это единственное место, где
миграции применяются. Реплики API не поднимаются параллельно; если когда-то
понадобятся, миграции нужно вынести в отдельный одноразовый сервис, а не
оставлять их в команде каждой реплики.

## 4. Миграции и данные

Фаза 5 добавляет `0004_phase5`: поля жизненного цикла в `job_outbox` и
частичный индекс `events (student_id, id) WHERE processed_at IS NULL`.

Миграция expand-only: все новые поля с server default, ни одно старое не
удаляется и не меняет тип. Предыдущая версия приложения продолжает работать
на новой схеме — это то, что позволяет откатить образ без отката схемы.

Backfill смотрит только на то, что старые строки реально говорили:
`enqueued_at IS NOT NULL` → `enqueued` (доставка была), иначе → `pending`.
`succeeded` не выставляется никому: доставка не доказывает выполнение.

Перед схемными изменениями — бэкап:

```bash
$compose exec -T postgres pg_dump -U <user> -d <db> --format=custom > <path>/pg-<sha>.dump
$compose exec -T neo4j neo4j-admin database dump neo4j --to-path=/backups
$compose exec -T redis redis-cli BGSAVE
```

Проверять восстановление нужно на копии, в изолированном окружении, а не на
продакшене. Куда кладутся дампы и кто их хранит — операторское решение; путь
и ключи в репозиторий не попадают.

**`docker compose down -v` не является частью обновления.** Эта команда сносит
тома с данными учеников.

## 5. Поведение при отказах

| Что упало | Что видит ученик | Что происходит внутри |
|---|---|---|
| LLM | Чат — `503 llm_unavailable` до первого токена; тексты — сохранённая версия с пометкой `saved_version` | Задачи паркуются в `waiting_dependency`, попытки не тратятся |
| Neo4j | Ответ на задачу принят, оценка выдана, `projection_status="pending"`; сеты — `availability.mode="static"`, прогноз не показывается | События остаются `processed_at IS NULL`, `recover_graph_events` догоняет |
| Redis | Кэш — промах; графовые мутации откладываются (fail-closed) | Намерения задач остаются в Postgres, `outbox_replay` доставит |
| Поиск | Кэш и «пол» программ с явной пометкой | `/health.checks.search` = `down` из последней записанной ошибки |
| PostgreSQL | `500 internal` | Восстановление невозможно без базы — это единственная действительно жёсткая зависимость |

Ни один ответ `2xx` не уходит раньше коммита: транзакция закрывается в
middleware между обработчиком и отправкой ответа, а сбой коммита даёт `500`,
а не ложное «принято».

Ни одна авария не теряет уже принятый ответ ученика.

### Диагностика

```sql
-- что стоит в очереди и чего ждёт
select status, dependency, count(*), min(not_before)
from job_outbox where status in
  ('pending','enqueued','running','waiting_dependency')
group by 1,2 order by 1,2;

-- окончательно провалившиеся задачи (их разбирает человек)
select id, fn_name, attempts, last_error_code, updated_at
from job_outbox where status='failed' order by updated_at desc limit 20;

-- долг графа: сколько событий и с какого момента
select count(*), min(ingested_at) from events where processed_at is null
and type in ('task.answered','diagnostic.completed','mock.completed',
             'observation.extracted','misconception.canonized',
             'misconception.personal_created','misconception.disputed',
             'misconception.undisputed');
```

То же самое без SQL: `GET /health` отдаёт `graph_pending` и `jobs_pending`,
когда они не нули.

### Ручное вмешательство

Восстановление запускается само: при старте bulk-воркера и по крону каждые
10 минут (`outbox_replay`) и 10 минут со сдвигом (`recovery_sweep`). Публичного
HTTP-эндпоинта для этого нет и быть не должно (§10).

Если нужно подтолкнуть конкретного ученика:

```bash
$compose exec -T worker-bulk python -c "
import asyncio
from arq.connections import RedisSettings, create_pool
from app.config import settings
async def main():
    pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    await pool.enqueue_job('recover_graph_events', request_id='manual',
        student_id='<student_id>', through_event_id=<event_id>,
        _queue_name='bulk', _job_id='graph-recover:<student_id>')
asyncio.run(main())"
```

Отравленное событие (`recovery_blocked` в логах, `job.failed` в событиях)
**не пропускается** простановкой `processed_at`: события за ним зависят от
его состояния. Разбирается причина, чинится, восстановление повторяется.

## 6. Откат

1. Схема совместима (обычный случай, т.к. миграция expand-only) — откатить
   образ на предыдущий SHA, схему не трогать.
2. Схема несовместима — восстановить проверенный бэкап, зафиксировать границу
   событий (максимальный `events.id` в бэкапе) и согласовать окно потерь.
   Произвольный `alembic downgrade` при живых новых `job_outbox`-намерениях
   недопустим: их поля просто исчезнут.
3. Массовое удаление событий, графа или томов откатом не является.

## 7. Демо

```bash
cd backend
uv run --frozen python ../scripts/seed.py            # обычный seed
uv run --frozen python ../scripts/seed.py --demo     # два демо-аккаунта
uv run --frozen python ../scripts/seed.py --demo-check
```

`--demo` идемпотентен: сверяет фактическое состояние и ничего не дублирует,
не сбрасывает работу жюри и не создаёт вторых ответов. `--demo-check` только
читает и печатает готовность (аккаунты, анкета, сохранённые программы,
выведенный конфликт, кэши, очереди); пароли он не печатает.

Сброс чистого аккаунта — отдельная команда, не часть seed:

```bash
uv run --frozen python ../scripts/seed.py --reset-clean
```

Учётные данные обоих аккаунтов — в `data/demo/manifest.json`. Это специально
заведённые тестовые аккаунты; ничего кроме них публиковать нельзя.

Прогрев ставит задачи фазы 4 через тот же долговечный outbox. Если воркер не
поднят, задачи не теряются — они лежат в `job_outbox` и уйдут в очередь при
старте. Проверять готовность текстов нужно по `--demo-check`, а не по факту
запуска команды.

Замер из шести задач запускается параметром `n_tasks=6` в запросе на старт
замера. Глобальный `diag_max` не понижается: это изменило бы продукт для всех,
а не для демо.

## 8. Чего этот файл не обещает

- Круглосуточного мониторинга нет. Есть структурные JSON-логи и SQL-запросы
  выше плюс обязательная предрелизная проверка оператором. Порог тревоги по
  остатку кредитов LLM, канал и ответственный не выдуманы — это D11.
- `exactly-once` между PostgreSQL, Neo4j и Redis не обещается. Гарантия —
  доставка «хотя бы один раз» с идемпотентными эффектами.
- Полная перестройка графа новой версией экстрактора в фазу 5 не входит.
