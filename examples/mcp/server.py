#!/usr/bin/env python3
"""MCP server exposing EUI icon search to AI assistants.

Wraps the icon-search-server sidecar (which holds the privileged ES API
key) so AI assistants can call icon_search as a tool. The intended user
flow:

    1. User pastes a screenshot of an icon into their AI chat (Claude
       Code, Cursor, etc.).
    2. The assistant sees the image and calls the `icon_search` tool
       with the image bytes as base64.
    3. This server forwards to the local icon-search-server sidecar.
    4. The assistant gets back a ranked list with EUI prop names and
       inserts something like `<EuiIcon type="search" />` in the user's
       code.

Configure your assistant's MCP client to launch this script over stdio.
For Claude Code, see claude_code_config.example.json next to this file.

The server only talks to the local sidecar at
$ICON_SEARCH_BASE_URL (default http://127.0.0.1:4555). It does NOT have
direct Elasticsearch access — that's intentional; the sidecar holds the
key and applies rate limits.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = os.environ.get("ICON_SEARCH_BASE_URL", "http://127.0.0.1:4555")

mcp = FastMCP("eui-icons")


def _format_hits(hits: list[dict[str, Any]]) -> str:
    if not hits:
        return "No matching icons found."
    lines = [f"Top {len(hits)} matches:"]
    for i, hit in enumerate(hits, 1):
        prop = hit["prop_name"]
        score = hit["score"]
        version = hit["version"]
        aliases = hit.get("aliases") or []
        alias_str = f" — also: {', '.join(f'`{a}`' for a in aliases)}" if aliases else ""
        lines.append(f"{i}. `{prop}` (score {score:.3f}, {version}){alias_str}")
    lines.append("")
    lines.append(f'Best match: `<EuiIcon type="{hits[0]["prop_name"]}" />`')
    return "\n".join(lines)


def _connection_help(detail: str) -> str:
    return (
        f"Could not reach the icon-search server at {BASE_URL}: {detail}.\n"
        "Start it with `yarn workspace @elastic/icon-search-server start` "
        "in the eui worktree, or set ICON_SEARCH_BASE_URL to a different sidecar."
    )


@mcp.tool()
async def icon_search(
    text: str | None = None,
    image_base64: str | None = None,
    version: str | None = None,
    limit: int = 8,
) -> str:
    """Search EUI icons by text description or by image.

    Provide either `text` or `image_base64` (not both). The image must be
    base64-encoded PNG/JPG/WebP bytes; a `data:image/...;base64,` prefix
    is OK and will be stripped. Returns a markdown-formatted ranked list
    with EUI prop names ready to drop into `<EuiIcon type="..." />`.

    Args:
        text: Free-text description, e.g. "search icon", "warning triangle",
            "trash can". Used when no image is supplied.
        image_base64: Base64-encoded image of the icon to find.
        version: EUI release tag to search against (e.g. "v115.0.0"). When
            omitted, searches across all indexed versions.
        limit: Number of top hits to return (1..50). Defaults to 8.
    """
    if not text and not image_base64:
        return "Error: provide either `text` or `image_base64`."
    if text and image_base64:
        return "Error: provide only one of `text` or `image_base64`, not both."
    if limit < 1 or limit > 50:
        return "Error: `limit` must be between 1 and 50."

    body: dict[str, Any] = {"limit": limit}
    if version:
        body["version"] = version
    body["query"] = text if text else {"image": image_base64}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.post(f"{BASE_URL}/api/icon-search", json=body)
        except (httpx.ConnectError, httpx.RequestError, httpx.TimeoutException) as e:
            return _connection_help(repr(e))

    if r.status_code != 200:
        try:
            detail = r.json()
        except Exception:
            detail = r.text
        return f"icon-search error (HTTP {r.status_code}): {detail}"

    data = r.json()
    return _format_hits(data.get("hits", []))


@mcp.tool()
async def icon_versions() -> str:
    """List the EUI release tags currently indexed and searchable.

    Use this to confirm which version filter to pass to `icon_search`.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(f"{BASE_URL}/api/versions")
        except (httpx.ConnectError, httpx.RequestError, httpx.TimeoutException) as e:
            return _connection_help(repr(e))

    if r.status_code != 200:
        return f"icon-search error (HTTP {r.status_code}): {r.text}"
    versions = r.json().get("versions") or []
    if not versions:
        return "No versions indexed yet. Run the ingester first."
    return "Indexed EUI versions:\n" + "\n".join(f"- {v}" for v in versions)


def main() -> None:
    # FastMCP's run() handles stdio transport.
    mcp.run()


if __name__ == "__main__":
    main()
