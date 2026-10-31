.PHONY: lint test check
lint:
	ruff check backend && ruff format --check backend
test:
	pytest
check: lint test
