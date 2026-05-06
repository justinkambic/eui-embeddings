"""EUI icon ingester.

Walks elastic/eui git tags, parses typeToPathMap and TOKEN_MAP per
version, rasterizes SVGs (raw glyph + programmatically chromed token)
to PNG via resvg, and POSTs to the Elasticsearch `_inference/embedding`
endpoint backed by Jina jina-clip-v2 via Elastic Inference Service.

See ../docs/PHASE_0_FINDINGS.md for the verified inference shape and
project-history/reference/eui-embeddings/architecture/revamp-plan.md
for the full design.
"""
