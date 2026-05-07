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

import base64
import os
from pathlib import Path
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP


# 5 MB to match the sidecar's body cap. Anything larger is almost certainly
# not an icon screenshot anyway.
_MAX_IMAGE_BYTES = 5 * 1024 * 1024

BASE_URL = os.environ.get("ICON_SEARCH_BASE_URL", "http://127.0.0.1:4555")

# Where the docs page that knows how to anchor-link to individual icons lives.
# Defaults to the local Docusaurus dev server (the only place that supports
# the `#icon-<propName>` anchors today). Override with ICON_DOCS_BASE_URL once
# upstream EUI docs ship the same anchor scheme.
ICON_DOCS_BASE_URL = os.environ.get(
    "ICON_DOCS_BASE_URL",
    "http://localhost:3000/docs/components/display/icons",
)


mcp = FastMCP("eui-icons")


# --- response formatting ---------------------------------------------------


def _docs_link(prop_name: str) -> str:
    return f"{ICON_DOCS_BASE_URL}#icon-{prop_name}"


def _format_hits_text(hits: list[dict[str, Any]]) -> str:
    if not hits:
        return "No matching icons found."
    lines = [
        f"Top {len(hits)} matches (click the link to see the icon rendered in EUI's docs):",
        "",
        "| # | prop | score | version | preview | aliases |",
        "|---|---|---|---|---|---|",
    ]
    for i, hit in enumerate(hits, 1):
        prop = hit["prop_name"]
        score = hit["score"]
        version = hit["version"]
        aliases = hit.get("aliases") or []
        alias_cell = ", ".join(f"`{a}`" for a in aliases) if aliases else ""
        lines.append(
            f"| {i} | `{prop}` | {score:.3f} | {version} | "
            f"[view]({_docs_link(prop)}) | {alias_cell} |"
        )
    lines.append("")
    lines.append(f'Best match: `<EuiIcon type="{hits[0]["prop_name"]}" />` '
                 f'— see it: {_docs_link(hits[0]["prop_name"])}')
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
    image_path: str | None = None,
    image_base64: str | None = None,
    version: str | None = None,
    limit: int = 8,
) -> str:
    """Search EUI icons by text description or by image.

    Provide exactly ONE of `text`, `image_path`, or `image_base64`.

    PREFER `image_path` when the image is on disk (e.g. when the user
    pastes an image into chat — the AI client typically attaches it as a
    file path). It is more reliable than passing 7-100 KB of base64
    through tool-call argument serialization, where the bytes can get
    mangled in transit.

    Args:
        text: Free-text description, e.g. "search icon", "warning triangle",
            "trash can".
        image_path: Absolute or working-directory-relative path to an image
            file (PNG/JPG/WebP/GIF) to search for. The MCP server reads,
            base64-encodes, and forwards to the sidecar. 5 MB max.
        image_base64: Base64-encoded image bytes. A `data:image/...;base64,`
            prefix is OK. Use this only when the image is not available
            on disk (rare).
        version: EUI release tag to search against (e.g. "v115.0.0"). When
            omitted, searches across all indexed versions.
        limit: Number of top hits to return (1..50). Defaults to 8.
    """
    provided = [n for n in (text, image_path, image_base64) if n]
    if len(provided) == 0:
        return "Error: provide one of `text`, `image_path`, or `image_base64`."
    if len(provided) > 1:
        return (
            "Error: provide only ONE of `text`, `image_path`, or `image_base64`, "
            "not multiple."
        )
    if limit < 1 or limit > 50:
        return "Error: `limit` must be between 1 and 50."

    # Resolve image_path → image_base64 here, so the wire format to the
    # sidecar is uniform and we never ship ambiguous arg combinations.
    if image_path:
        try:
            p = Path(image_path).expanduser()
        except Exception as e:
            return f"Error: invalid `image_path` ({image_path!r}): {e}"
        if not p.exists():
            return f"Error: image_path does not exist: {p}"
        if not p.is_file():
            return f"Error: image_path is not a regular file: {p}"
        size = p.stat().st_size
        if size > _MAX_IMAGE_BYTES:
            return f"Error: image at {p} is {size} bytes; max is {_MAX_IMAGE_BYTES}."
        try:
            data = p.read_bytes()
        except OSError as e:
            return f"Error: could not read {p}: {e}"
        image_base64 = base64.b64encode(data).decode("ascii")

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
    return _format_hits_text(data.get("hits", []))


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
