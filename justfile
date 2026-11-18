set shell := ["bash", "-euo", "pipefail", "-c"]

brew_lib := env_var_or_default("BREW_LIB", "/opt/homebrew/lib")

default: check

setup:
    cd backend && uv sync
    cd web && pnpm install --frozen-lockfile

dev:
    just dev-api & just dev-web & wait

dev-api:
    cd backend && DYLD_FALLBACK_LIBRARY_PATH="${DYLD_FALLBACK_LIBRARY_PATH:-{{brew_lib}}}" uv run python -m automator.main

dev-web:
    cd web && pnpm dev

doctor:
    cd backend && DYLD_FALLBACK_LIBRARY_PATH="${DYLD_FALLBACK_LIBRARY_PATH:-{{brew_lib}}}" uv run python -m automator.doctor

fmt:
    cd backend && uv run ruff format . && uv run ruff check --fix .
    cd web && pnpm fmt

lint:
    python3 .claude/hooks/comment_scan.py backend web .claude scripts
    for script in scripts/*.sh; do bash -n "$script"; done
    if grep -HnE '^[[:space:]]*#' scripts/*.sh | grep -v ':1:#!'; then echo "shell scripts may only have a shebang comment"; exit 1; fi
    if command -v shellcheck >/dev/null; then shellcheck scripts/*.sh; else echo "shellcheck not installed, skipped"; fi
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
