.PHONY: sync format lint format-check typecheck test secrets check

sync:
	uv sync --frozen

format:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff check .

format-check:
	uv run ruff format --check .

typecheck:
	uv run mypy

test:
	uv run pytest --cov

secrets:
	@if git grep -nIE '(BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,})' -- . ':!uv.lock'; then echo "Potential secret found"; exit 1; else echo "No high-confidence secret patterns found"; fi

check: format-check lint typecheck test secrets
