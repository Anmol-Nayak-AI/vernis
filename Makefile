.PHONY: install dev-api dev-web lint test test-backend test-frontend build migrate migration-check db-inspect performance backup restore-drill compose-up compose-down

install:
	cd backend && uv sync --extra test
	cd frontend && npm ci

dev-api:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

dev-web:
	cd frontend && npm run dev

lint:
	cd backend && uv run ruff check app tests alembic
	cd frontend && npm run typecheck

test: test-backend test-frontend

test-backend:
	cd backend && uv run pytest

test-frontend:
	cd frontend && npm test

build:
	cd frontend && npm run build

migrate:
	cd backend && uv run alembic upgrade head

migration-check:
	cd backend && uv run alembic upgrade head --sql > /tmp/vernis-alembic.sql

db-inspect:
	cd backend && uv run python -m scripts.inspect_database

performance:
	cd backend && uv run python -m scripts.performance_smoke

backup:
	./scripts/backup.sh

restore-drill:
	@test -n "$(BACKUP)" || (echo "Set BACKUP=backups/<timestamp>" && exit 2)
	./scripts/restore-drill.sh "$(BACKUP)" --confirm-scratch-reset

compose-up:
	docker compose up --build

compose-down:
	docker compose down
