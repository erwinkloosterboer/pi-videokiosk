.PHONY: lint test install run

lint:
	python3 -m ruff check src tests
	python3 -m ruff format --check src tests

test:
	python3 -m pytest tests -v

install:
	pip install -r requirements.txt
	pip install pytest ruff

run:
	$(if $(wildcard venv/bin/python),venv/bin/python -m src,python3 -m src)
