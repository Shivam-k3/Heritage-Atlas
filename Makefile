.PHONY: lint format typecheck test check
lint:
	ruff check backend scripts && ruff format --check backend scripts
format:
	ruff check --fix backend scripts && ruff format backend scripts
typecheck:
	mypy
test:
	pytest backend/tests -q
check: lint typecheck test
