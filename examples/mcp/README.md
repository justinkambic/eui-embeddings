# Legacy MCP server (reference)

The original `mcp_server.py` (kept at `legacy/mcp_server.py`) was a Model
Context Protocol wrapper around the FastAPI `/search` endpoint. It is not part
of the Revamp v2 demo.

If we want to surface the new vector search via MCP later (Phase 7+), the
right move is a small new MCP server that talks to the Express sidecar at
`packages/icon-search-server/` (in the EUI fork branch), not a port of the
original. This file is a placeholder so the path exists.
