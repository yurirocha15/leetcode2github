format:
	isort .
	black .

lint:
	env PYTHONPATH=src pytest src --pylint --flake8 --mypy

setup:
	pip install -e .

setup-dev:
	make setup
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

utest:
	env PYTHONPATH=src pytest tests -s --verbose --cov=src --cov-report=html --cov-report=term-missing --suppress-no-test-exit-code

tree:
	tree -I "$(shell cat .gitignore | tr -s '\n' '|')"
