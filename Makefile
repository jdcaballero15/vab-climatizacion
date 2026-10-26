.DEFAULT_GOAL := help
.PHONY: help up down logs test lint fmt stories-validate stories-index stories-sync-dry hooks-install hooks-test seed

help: ## Lista los comandos
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

up: ## Levanta el entorno local (db, minio, mailpit, backend)
	docker compose up -d --build

down: ## Baja el entorno local
	docker compose down

logs: ## Sigue los logs del backend
	docker compose logs -f backend

test: ## Corre los tests del backend
	cd backend && python -m pytest

lint: ## Lint y chequeo de tipos del backend
	cd backend && ruff check . && ruff format --check . && mypy app

seed: ## Genera datos de prueba ficticios en una base vacía (requiere SEED_PASSWORD)
	cd backend && python -m app.demo_data

fmt: ## Formatea el backend
	cd backend && ruff check --fix . && ruff format .

stories-validate: ## Valida el formato de las historias de usuario
	python3 scripts/validate_stories.py

stories-index: ## Regenera docs/stories/INDEX.md
	python3 scripts/validate_stories.py --write-index

stories-sync-dry: ## Muestra qué issues crearía o actualizaría la sincronización
	python3 scripts/sync_stories.py --dry-run

hooks-install: ## Instala pre-commit (formato, lint, gitleaks, historias)
	pip install pre-commit && pre-commit install

hooks-test: ## Verifica que los guardas de Claude Code sigan bloqueando
	bash .claude/hooks/test_guards.sh
