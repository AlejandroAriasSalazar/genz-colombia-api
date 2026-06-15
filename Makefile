.PHONY: install lint test migrate ingest run

install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements-dev.txt

lint:
	.venv/bin/ruff check app scripts tests alembic
	.venv/bin/ruff format --check app scripts tests alembic

test:
	.venv/bin/pytest --cov=app --cov-report=term-missing

migrate:
	.venv/bin/alembic upgrade head

ingest:
	.venv/bin/python -m scripts.manage ingest

run:
	.venv/bin/uvicorn app.main:app --reload --port 8000
