.PHONY: api-dev web-dev db-up db-down migrate test lint typecheck

api-dev:
	cd apps/api && uvicorn fluxmed.main:app --app-dir src --reload

web-dev:
	cd apps/web && npm run dev

db-up:
	docker compose up -d db

db-down:
	docker compose down

migrate:
	cd apps/api && alembic upgrade head

test:
	cd apps/api && pytest -q
	cd apps/web && npm test

lint:
	cd apps/api && ruff check src tests
	cd apps/web && npm run lint

typecheck:
	cd apps/api && mypy src
	cd apps/web && npm run typecheck
