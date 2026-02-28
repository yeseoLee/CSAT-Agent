UV ?= uv
DOCKER ?= docker
IMAGE ?= csat-agent:latest
PDF ?= data/problem.pdf
DATA_DIR ?= $(CURDIR)/data

.PHONY: help venv sync lock lint format format-check run docker-build docker-run docker-lint clean

help:
	@echo "Available targets:"
	@echo "  make venv         - Create .venv with uv"
	@echo "  make sync         - Sync dependencies (including dev group)"
	@echo "  make lock         - Generate/update uv.lock"
	@echo "  make lint         - Run ruff lint"
	@echo "  make format       - Auto-fix lint issues and format code"
	@echo "  make format-check - Validate formatting without changes"
	@echo "  make run PDF=...  - Run the agent locally"
	@echo "  make docker-build - Build docker image"
	@echo "  make docker-run   - Run container with mounted data directory"
	@echo "  make docker-lint  - Run lint inside docker"

venv:
	$(UV) venv .venv --python 3.12

sync: venv
	$(UV) sync --group dev

lock:
	$(UV) lock

lint:
	$(UV) run ruff check src

format:
	$(UV) run ruff check --fix src
	$(UV) run ruff format src

format-check:
	$(UV) run ruff check src
	$(UV) run ruff format --check src

run:
	$(UV) run python -m csat_agent.main "$(PDF)"

docker-build:
	$(DOCKER) build -t $(IMAGE) .

docker-run:
	$(DOCKER) run --rm -it -v "$(DATA_DIR):/app/data" $(IMAGE) "$(PDF)"

docker-lint:
	$(DOCKER) run --rm $(IMAGE) uv run ruff check src

clean:
	$(UV) cache clean