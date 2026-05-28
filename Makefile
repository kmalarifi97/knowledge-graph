# All real work runs inside Docker. The Makefile is the thin host-side
# entrypoint; no Python is invoked on the host.

.PHONY: build pipeline registry logical llm arbitrate validate test sh clean

build:
	docker compose build

# Full pipeline: sources -> arbitration (which calls the validator).
pipeline: build
	docker compose run --rm kg python -m pipeline

# Individual stages, useful when debugging one component.
registry: build
	docker compose run --rm kg python -m registry.registry

sync: build
	docker compose run --rm kg python -m registry.sync

sync-dry: build
	docker compose run --rm kg python -m registry.sync --dry-run

# Re-verify every anchor, including ones already marked verified.
# Catches the case where an over-confident seed assertion was wrong.
sync-all: build
	docker compose run --rm kg python -m registry.sync --all

logical: build
	docker compose run --rm kg python -m sources.logical

llm: build
	docker compose run --rm kg python -m sources.llm_extract

arbitrate: build
	docker compose run --rm kg python -m arbitration.arbitrate

validate: build
	docker compose run --rm kg python -m validator.dag candidates/logical.jsonl candidates/llm.jsonl

test: build
	docker compose run --rm kg pytest -q

sh: build
	docker compose run --rm kg bash

clean:
	rm -f candidates/*.jsonl arbitration/arbitrated.jsonl arbitration/review.jsonl
