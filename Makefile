format:
	isort .
	black --line-length 104 .

get-all-submissions:
	python scripts/leet2git.py get-all-submissions
	make format

get-question:
	python scripts/leet2git.py get-question $(ID)
	make format

remove-question:
	python scripts/leet2git.py remove-question $(ID)

setup:
	python -m pip install -r requirements.txt
	pre-commit install

submit-question:
	python scripts/leet2git.py submit-question $(ID)

test-solutions:
	env PYTHONPATH=src pytest tests -s --verbose --cov=src --cov-report=html --cov-report=term-missing --suppress-no-test-exit-code

tree:
	tree -I "$(shell cat .gitignore | tr -s '\n' '|')"
