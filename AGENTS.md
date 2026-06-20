# Repository Guidelines

## Project Overview

`leet2git` is a Python CLI that synchronizes LeetCode problems and accepted submissions into a local Git repository. The package uses a `src/` layout and exposes the `leet2git` console command from `leet2git.leet2git:leet2git`.

## Setup

- Use Python 3.11 or newer.
- Install the package for local development with `uv sync --extra dev` or `make setup-dev`.
- Install only runtime dependencies with `uv sync` or `make setup`.
- The CLI reads browser cookies for LeetCode through `browser-cookie3`; do not add tests or scripts that require real user cookies unless the user explicitly asks.

## Common Commands

- `make format`: run Ruff format and Ruff autofix through `uv`.
- `make lint`: run Ruff and ty through `uv`.
- `make utest`: run tests under `tests` with coverage.
- `uv run pytest tests -s --verbose`: useful focused test command while developing tests.

## Code Style

- Follow the Ruff configuration in `pyproject.toml` and keep types friendly to `ty`.
- Keep compatibility with the supported Python versions declared in `pyproject.toml`.
- Prefer the existing Click command patterns in `src/leet2git/leet2git.py`.
- Keep user-facing CLI messages concise and actionable.
- Avoid broad refactors when fixing a narrow behavior; this codebase has several small modules with clear responsibilities.

## Architecture Notes

- `leet2git.py`: Click command entry points and command orchestration.
- `config_manager.py`: Pydantic config models plus platform-specific config/data paths via `platformdirs`.
- `leetcode_client.py`: async-first LeetCode HTTP/session interactions using `httpx`, with sync wrappers for the Click CLI.
- `question_db.py`: Pydantic question metadata models and local pickle-backed storage.
- `file_handler.py`, `default_handler.py`, `python_handler.py`: file generation and language-specific behavior.
- `readme_handler.py`: generated README updates for target solution repositories.
- `my_utils.py`: shared helpers used by commands.

## Testing Guidance

- Add tests under `tests/` for new behavior. The current test tree is minimal, so prefer focused unit tests around pure helpers or isolated file operations.
- Mock network calls, browser cookie access, editor launches, and LeetCode responses.
- Use temporary directories for generated repositories, config files, question databases, and README output.
- When changing CLI behavior, test with Click's testing utilities where practical.
- Preserve compatibility with existing pickle-backed question databases when changing `QuestionData`, `IdTitleMap`, or `QuestionDB.load`.
- Keep `ConfigManager.config` returning a plain dictionary unless the surrounding command/file-handler code is migrated together.
- When changing LeetCode request shapes, keep unit tests on `httpx.MockTransport` and run a live smoke check against public unauthenticated endpoints such as GraphQL `questionData` and `/api/problems/all/`.

## Safety Notes

- Do not commit real LeetCode cookies, generated user configs, local question databases, or downloaded solutions from a user's personal repository.
- Be careful with `leet2git reset --hard` and delete paths. Confirm behavior in tests with temporary directories before changing deletion logic.
- `ConfigManager.reset_config` opens an editor via `click.edit`; mock it in automated tests.
