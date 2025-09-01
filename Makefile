.PHONY: install test lint type run

install:
	pip install -e .

test:
	pytest

lint:
	ruff .

type:
	mypy ally

run:
	ally web
