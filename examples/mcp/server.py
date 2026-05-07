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
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent, TextContent


# 5 MB to match the sidecar's body cap. Anything larger is almost certainly
# not an icon screenshot anyway.
_MAX_IMAGE_BYTES = 5 * 1024 * 1024

BASE_URL = os.environ.get("ICON_SEARCH_BASE_URL", "http://127.0.0.1:4555")
EUI_DOCS_URL = "https://eui.elastic.co/docs/components/display/icons"

# We pull preview-render assets from this checkout via `git show <ref>:<path>`,
# which reads file contents at a specific tag without disturbing HEAD/working
# tree. The ingester maintains this clone; we just read from it.
EUI_REPO = (Path(__file__).resolve().parents[2] / ".cache" / "eui").resolve()

# Make ingester's raster + extractor available so we can render previews.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    from ingester.extract_svg import extract_from_tsx, to_inline_svg  # noqa: E402
    from ingester.raster import rasterize_glyph  # noqa: E402

    _RENDER_AVAILABLE = True
except Exception:  # pragma: no cover — graceful degrade
    _RENDER_AVAILABLE = False


mcp = FastMCP("eui-icons")


# --- preview rendering -----------------------------------------------------


def _git_show(ref: str, path: str) -> bytes | None:
    """Read `path` at `ref` from the ingester's EUI clone, without changing HEAD."""
    if not (EUI_REPO / ".git").exists():
        return None
    try:
        return subprocess.check_output(
            ["git", "-C", str(EUI_REPO), "show", f"{ref}:{path}"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None


@lru_cache(maxsize=8)
def _icon_map_for_version(version: str) -> dict[str, str]:
    """Parse typeToPathMap at `version` → {prop_name: asset_filename}.

    Uses git-show so we don't have to checkout (which would race with
    concurrent ingest runs sharing the same .cache/eui)."""
    candidates = (
        "packages/eui/src/components/icon/icon_map.ts",  # v95+
        "src/components/icon/icon_map.ts",                # v91-v94
    )
    for relpath in candidates:
        blob = _git_show(version, relpath)
        if blob is None:
            continue
        text = blob.decode("utf-8", errors="replace")
        # Match either:
        #   propName: 'asset_name',  (v91 form)
        #   propName: () => import('./assets/asset_name'),  (v115 form)
        out: dict[str, str] = {}
        rx = re.compile(
            r"^\s*([A-Za-z_]\w*)\s*:\s*"
            r"(?:['\"]([^'\"]+)['\"]|"
            r"\(\s*\)\s*=>\s*import\s*\(\s*['\"]\./assets/([^'\"]+)['\"]\s*\))",
            re.MULTILINE,
        )
        for m in rx.finditer(text):
            prop = m.group(1)
            asset = m.group(2) or m.group(3)
            if prop and asset:
                out[prop] = asset
        if out:
            return out
    return {}


def _asset_path_at_version(version: str, asset_filename: str) -> str | None:
    """Repo-relative path to the .tsx asset at the given version."""
    for relpath in (
        f"packages/eui/src/components/icon/assets/{asset_filename}.tsx",
        f"src/components/icon/assets/{asset_filename}.tsx",
    ):
        if _git_show(version, relpath) is not None:
            return relpath
    return None


@lru_cache(maxsize=512)
def _render_preview_b64(version: str, prop_name: str) -> str | None:
    """Render `prop_name`@`version` to a PNG and return base64 (no data: prefix).

    Returns None if anything in the chain fails (missing checkout, asset not
    found, raster error). The MCP tool falls back to text-only when this is
    None — preview images are nice-to-have, not load-bearing.
    """
    if not _RENDER_AVAILABLE:
        return None
    icon_map = _icon_map_for_version(version)
    asset = icon_map.get(prop_name)
    if not asset:
        return None
    relpath = _asset_path_at_version(version, asset)
    if not relpath:
        return None
    tsx_bytes = _git_show(version, relpath)
    if tsx_bytes is None:
        return None
    try:
        ext = extract_from_tsx(tsx_bytes.decode("utf-8", errors="replace"))
        png = rasterize_glyph(to_inline_svg(ext))
    except Exception:
        return None
    return base64.b64encode(png).decode("ascii")


# --- response formatting ---------------------------------------------------


def _format_hits_text(hits: list[dict[str, Any]]) -> str:
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
    lines.append("")
    lines.append(f"Browse all icons in EUI's docs: {EUI_DOCS_URL}")
    return "\n".join(lines)


def _build_response_blocks(
    hits: list[dict[str, Any]],
) -> list[TextContent | ImageContent]:
    """Compose the tool response: text summary + an inline preview image
    per hit (when we can render it). MCP clients that support image content
    will display the previews; clients that don't will still see the text."""
    blocks: list[TextContent | ImageContent] = [
        TextContent(type="text", text=_format_hits_text(hits)),
    ]
    for hit in hits:
        png_b64 = _render_preview_b64(hit["version"], hit["prop_name"])
        if png_b64:
            blocks.append(
                ImageContent(type="image", data=png_b64, mimeType="image/png")
            )
            blocks.append(
                TextContent(
                    type="text",
                    text=f"↑ `{hit['prop_name']}` ({hit['version']})",
                )
            )
    return blocks


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
) -> list[TextContent | ImageContent]:
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
    def err(msg: str) -> list[TextContent | ImageContent]:
        return [TextContent(type="text", text=msg)]

    provided = [n for n in (text, image_path, image_base64) if n]
    if len(provided) == 0:
        return err("Error: provide one of `text`, `image_path`, or `image_base64`.")
    if len(provided) > 1:
        return err(
            "Error: provide only ONE of `text`, `image_path`, or `image_base64`, "
            "not multiple."
        )
    if limit < 1 or limit > 50:
        return err("Error: `limit` must be between 1 and 50.")

    # Resolve image_path → image_base64 here, so the wire format to the
    # sidecar is uniform and we never ship ambiguous arg combinations.
    if image_path:
        try:
            p = Path(image_path).expanduser()
        except Exception as e:
            return err(f"Error: invalid `image_path` ({image_path!r}): {e}")
        if not p.exists():
            return err(f"Error: image_path does not exist: {p}")
        if not p.is_file():
            return err(f"Error: image_path is not a regular file: {p}")
        size = p.stat().st_size
        if size > _MAX_IMAGE_BYTES:
            return err(f"Error: image at {p} is {size} bytes; max is {_MAX_IMAGE_BYTES}.")
        try:
            data = p.read_bytes()
        except OSError as e:
            return err(f"Error: could not read {p}: {e}")
        image_base64 = base64.b64encode(data).decode("ascii")

    body: dict[str, Any] = {"limit": limit}
    if version:
        body["version"] = version
    body["query"] = text if text else {"image": image_base64}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.post(f"{BASE_URL}/api/icon-search", json=body)
        except (httpx.ConnectError, httpx.RequestError, httpx.TimeoutException) as e:
            return err(_connection_help(repr(e)))

    if r.status_code != 200:
        try:
            detail = r.json()
        except Exception:
            detail = r.text
        return err(f"icon-search error (HTTP {r.status_code}): {detail}")

    data = r.json()
    return _build_response_blocks(data.get("hits", []))


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
