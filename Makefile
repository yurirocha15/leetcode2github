format:
	black .
	isort .

get-question:
	python scripts/leetcode_tools.py get-question $(ID)
	make format

lint:
	env PYTHONPATH=src pytest src --flake8 --mypy

setup:
	python -m pip install -r requirements.txt
	pre-commit install
	python scripts/leetcode_tools.py download-client

re-login:
	python scripts/leetcode_tools.py relogin

test-solutions:
	env PYTHONPATH=src pytest src -s --verbose --cov=src --cov-report=html --cov-report=term-missing --suppress-no-test-exit-code

tree:
	tree -I "$(shell cat .gitignore | tr -s '\n' '|')"