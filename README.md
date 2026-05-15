# EUI Embeddings

Multimodal vector search over [Elastic UI](https://github.com/elastic/eui) icons.
Paste an image of an icon (or type a description), get back the closest EUI
icons with version-aware filtering.

This repo houses the **ingester** that walks `elastic/eui` git tags from `v91`
forward, rasterizes each icon's SVG (raw glyph + programmatically chromed
token), and writes vectors to an Elasticsearch cluster running on Elastic
Cloud. The actual search UX lives in a development branch on a fork of
`elastic/eui` (see `feat/icon-vector-search` in `~/git/justinkambic/eui`),
which injects an `<IconSearch />` MDX component into the docs Icons page.

## Status

🚧 In active rebuild. The legacy stack (FastAPI + Playwright + Next.js +
HuggingFace CLIP) lives under `legacy/` for migration reference. The new
stack uses **Jina `jina-clip-v2` via Elastic Inference Service** for both
text and image embeddings — no separate inference service required.

See:
- `docs/PHASE_0_FINDINGS.md` — verified inference path on the v9.4 cluster.
- `~/git/justinkambic/project-history/reference/eui-embeddings/architecture/revamp-plan.md` —
  the active architecture plan and phased schedule.
- `~/git/justinkambic/project-history/reference/eui-embeddings/architecture/legacy-snapshot.md` —
  what existed before the rebuild and why we changed it.

## Layout

```
ingester/        Python package that walks EUI tags and writes vectors to ES.
es/              Bash + JSON to create the inference endpoint, index, smoke test.
examples/mcp/    Reference for re-adding MCP support (Phase 7+).
docs/            Active runbooks and Phase findings.
legacy/          Legacy stack (FastAPI, Playwright, Next.js, GCP YAMLs). Kept
                 for migration reference, not used by the new arch.
```

## Quick start

```bash
# 1. Copy env template, fill in cluster URL + API key.
cp .env.example .env
$EDITOR .env

# 2. Verify the cluster is reachable.
make verify

# 3. (Phase 2) Set up the inference endpoint and index.
make seed

# 4. (Phase 3) Ingest a single EUI version.
make ingest VERSION=v115.0.0

# 5. (Phase 3) Background trickle backfill of older versions.
make ingest-trickle FROM=v92.0.0 TO=v114.0.0 PACE=10m
```

`make help` lists every target.

## Architecture (one paragraph)

ES holds one index `eui_icons` keyed by `${prop_name}@${release_tag}#${kind}`,
where `kind ∈ {glyph, token}`. The `kind: glyph` doc is the raw EUI SVG
rasterized to PNG; `kind: token` is the same glyph composited onto a colored
shape derived from `TOKEN_MAP` in EUI's source — both rasterized via `resvg`,
no Playwright. Both vectors come from `jina-clip-v2` via the EIS inference
endpoint (1024d, cosine). At search time the EUI fork's `<IconSearch />`
component routes the query to the right `kind` based on either a UI toggle
or a small classifier, applies the version filter (default = the version
the docs are built against), and reorders the standard EUI icon grid by
similarity score. See the revamp plan for the full picture.

## License

[Apache 2.0](LICENSE.txt).
