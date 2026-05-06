# EUI Embeddings — Revamp v2
#
# All targets read .env automatically. Use `make help` to list everything.

SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

# Load .env if present (supports values with spaces). Variables become
# available to make targets and to commands invoked by them.
ifneq (,$(wildcard .env))
include .env
export
endif

PYTHON ?= python3
INGESTER_PYTHON ?= $(PYTHON) -m ingester

.PHONY: help verify seed ingest ingest-trickle demo \
        ingester-install ingester-test \
        clean-pycache

help:  ## Show this help.
	@grep -E '^[a-zA-Z0-9_-]+:.*##' Makefile | awk -F':.*##' '{printf "  %-20s %s\n", $$1, $$2}'

# === Phase 0 ===

verify:  ## Ping the configured ES cluster.
	@if [ -z "$$ELASTICSEARCH_ENDPOINT" ]; then echo "ELASTICSEARCH_ENDPOINT not set; copy .env.example to .env first." >&2; exit 1; fi
	@curl -sS -H "Authorization: ApiKey $$ELASTICSEARCH_VECTOR_DB_API_KEY" \
	    "$$ELASTICSEARCH_ENDPOINT" \
	    | python3 -c 'import sys,json; d=json.load(sys.stdin); print("ok:", d.get("cluster_name"), d.get("version", {}).get("number"))'

# === Phase 2 (es/ scripts land here) ===

seed: seed-inference seed-index seed-smoke  ## Create inference endpoint, index, and smoke-test.

seed-inference:  ## (Phase 2) Create the eui-icon-encoder inference endpoint.
	@bash es/00_create_inference.sh

seed-index:  ## (Phase 2) Create the eui_icons index.
	@bash es/01_create_index.sh

seed-smoke:  ## (Phase 2) Index a fake doc and run a kNN search.
	@bash es/02_smoke.sh

# === Phase 3 (ingester) ===

ingester-install:  ## Install ingester deps into the active venv.
	@$(PYTHON) -m pip install -r ingester/requirements.txt

ingester-test:  ## Run ingester unit tests (Phase 3+).
	@$(PYTHON) -m pytest ingester/ -q

ingest:  ## (Phase 3) Ingest a single EUI version. Use VERSION=vXX.Y.Z.
	@if [ -z "$(VERSION)" ]; then echo "Usage: make ingest VERSION=v115.0.0" >&2; exit 1; fi
	@$(INGESTER_PYTHON) run --version "$(VERSION)"

ingest-trickle:  ## (Phase 3) Background backfill at PACE between versions. Use FROM=, TO=, PACE=10m.
	@if [ -z "$(FROM)" ] || [ -z "$(TO)" ]; then echo "Usage: make ingest-trickle FROM=v92.0.0 TO=v114.0.0 PACE=10m" >&2; exit 1; fi
	@$(INGESTER_PYTHON) trickle --from "$(FROM)" --to "$(TO)" --pace "$(PACE)"

# === Phase 5 ===

demo:  ## (Phase 5) Seed + ingest latest + open browser. Stub for now.
	@echo "make demo: not yet implemented (Phase 5)."

# === Housekeeping ===

clean-pycache:  ## Remove __pycache__ trees.
	@find . -name __pycache__ -type d -prune -exec rm -rf {} +
