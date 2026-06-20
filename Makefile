format:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff check .
	uv run ty check src

setup:
	uv sync

setup-dev:
	uv sync --extra dev

utest:
	uv run pytest tests -s --verbose --cov=src --cov-report=html --cov-report=term-missing --suppress-no-test-exit-code

build:
	uv run python -m build

tree:
	tree -I "$(shell cat .gitignore | tr -s '\n' '|')"
