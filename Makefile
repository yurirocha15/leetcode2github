format:
	isort .
	black --line-length 104 .

setup:
	pip install -e .[dev]
	pre-commit install

test-solutions:
	env PYTHONPATH=src pytest tests -s --verbose --cov=src --cov-report=html --cov-report=term-missing --suppress-no-test-exit-code

tree:
	tree -I "$(shell cat .gitignore | tr -s '\n' '|')"
