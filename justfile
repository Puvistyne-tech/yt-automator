set shell := ["bash", "-euo", "pipefail", "-c"]

default: check

setup:
    cd backend && uv sync
    cd web && pnpm install --frozen-lockfile

dev:
    just dev-api & just dev-web & wait

dev-api:
    cd backend && uv run python -m automator.main

dev-web:
    cd web && pnpm dev

fmt:
    cd backend && uv run ruff format . && uv run ruff check --fix .
    cd web && pnpm fmt

lint:
    python3 .claude/hooks/comment_scan.py backend web .claude scripts
    cd backend && uv run ruff format --check . && uv run ruff check .
    cd web && pnpm lint

typecheck:
    cd backend && uv run mypy
    cd web && pnpm typecheck

test:
    cd backend && uv run pytest
    cd web && pnpm test

test-backend *args:
    cd backend && uv run pytest {{args}}

test-web *args:
    cd web && pnpm exec vitest run {{args}}

check: lint typecheck test
