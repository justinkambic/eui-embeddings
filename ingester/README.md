# ingester

Walks `elastic/eui` git tags, extracts each icon and token's SVG, rasterizes
to PNG (raw glyph + programmatically chromed token), and writes vectors to
Elasticsearch via the `_inference/embedding` endpoint backed by `jina-clip-v2`
through Elastic Inference Service.

## Status

Phase 1 scaffold. The CLI prints a stub message; real implementation lands in
Phase 3.

## Quick reference

```bash
# Verify the cluster + inference path (Phase 0; already done)
make verify

# Set up the inference endpoint and index (Phase 2)
make seed

# Ingest a specific tag (Phase 3)
make ingest VERSION=v115.0.0

# Background trickle ingestion at a configurable pace (Phase 3)
make ingest-trickle FROM=v92.0.0 TO=v114.0.0 PACE=10m
```

## Design

See `../docs/PHASE_0_FINDINGS.md` and
`~/git/justinkambic/project-history/reference/eui-embeddings/architecture/revamp-plan.md`.

## Env vars

The ingester reads `.env` at the repo root:

| Var | Required | Notes |
|---|---|---|
| `ELASTICSEARCH_ENDPOINT` | yes | Cloud cluster URL |
| `ELASTICSEARCH_VECTOR_DB_API_KEY` | yes | API key for the new v9.4 cluster |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | no | Optional; if set, ingester emits OTel spans |
