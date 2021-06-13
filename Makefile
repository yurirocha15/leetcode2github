format:
	isort .
	black --line-length 104 .

setup:
	pip install -e .

setup-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test-solutions:
	env PYTHONPATH=src pytest tests -s --verbose --cov=src --cov-report=html --cov-report=term-missing --suppress-no-test-exit-code

tree:
	tree -I "$(shell cat .gitignore | tr -s '\n' '|')"
