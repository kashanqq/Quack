# Quack backend

Здесь находятся FastAPI-приложение (`app/`), тесты (`tests/`), миграции (`alembic/`), конфигурация Python (`pyproject.toml`) и `uv.lock`. Локальная инфраструктура расположена в `../deploy/`, общие команды — в корневом `../Makefile`.

## Локальный запуск

Нужны Python 3.12, uv и Docker Compose. Из корня репозитория:

```bash
docker compose -f deploy/docker-compose.yml up -d
cd backend
uv sync
uv run uvicorn app.main:create_app --factory --reload
```

Пример переменных окружения находится в `../deploy/.env.example`. Часть API, workers и seed-команд пока не реализована. Файлов `docs/tz/00-contracts.md` и `docs/tz/10-B3.md` в этом checkout сейчас нет.

`ssot/` содержит прежние копии архитектурных документов. Файл `ssot/memory-architecture-quack.md` сохранён здесь: корневого экземпляра сейчас нет. `graphify-out/` содержит старый граф с устаревшими абсолютными путями; перед использованием его нужно пересобрать из `backend/`.
