.PHONY: up down api worker-interactive worker-bulk seed test test-int types lint

up:
	docker compose -f deploy/docker-compose.yml up -d

down:
	docker compose -f deploy/docker-compose.yml down

api:
	cd apps/api && uv run uvicorn app.main:create_app --factory --reload

worker-interactive:
	cd apps/api && uv run arq app.workers.main.WorkerInteractive

worker-bulk:
	cd apps/api && uv run arq app.workers.main.WorkerBulk

seed:
	cd apps/api && uv run python ../../scripts/seed.py

test:
	cd apps/api && uv run pytest -m "not integration"

test-int:
	cd apps/api && uv run pytest

types:
	bash scripts/gen_types.sh

lint:
	cd apps/api && uv run ruff check . && uv run ruff format --check .
