.PHONY: dev test e2e lint build

dev:
	docker compose -f infra/docker-compose.yml up -d --wait
	uv run --extra dev alembic -c apps/api/alembic.ini upgrade head
	npm run dev

test:
	uv run --extra dev pytest
	npm --prefix apps/web test

e2e:
	npm --prefix apps/web run e2e

lint:
	uv run --extra dev ruff check .
	uv run --extra dev mypy
	npm --prefix apps/web run lint
	npm --prefix apps/web run typecheck

build:
	npm --prefix apps/web run build
