.PHONY: up down api worker-interactive worker-bulk seed test test-int types lint

up:
	docker compose -f deploy/docker-compose.yml up -d

down:
	docker compose -f deploy/docker-compose.yml down

api:
	cd backend && uv run uvicorn app.main:create_app --factory --reload

worker-interactive:
	cd backend && uv run arq app.workers.main.WorkerInteractive

worker-bulk:
	cd backend && uv run arq app.workers.main.WorkerBulk

seed:
	cd backend && uv run python ../scripts/seed.py

test:
	cd backend && uv run pytest -m "not integration"

test-int:
	cd backend && uv run pytest

types:
	bash scripts/gen_types.sh

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
