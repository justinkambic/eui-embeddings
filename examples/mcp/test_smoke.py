#!/usr/bin/env python3
"""Smoke-test the MCP server end-to-end without a real AI client.

Spawns server.py over stdio and exercises both tools, asserting the
sidecar is reachable and responses contain expected fields. Skip this if
the sidecar isn't running — the assertion error message will say so.

Usage:
    .venv-mcp/bin/python examples/mcp/test_smoke.py
"""

from __future__ import annotations

import asyncio
import base64
import io
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


HERE = Path(__file__).resolve().parent


async def run_smoke() -> int:
    server_py = HERE / "server.py"
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_py)],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. Tools listed?
            tools = await session.list_tools()
            tool_names = {t.name for t in tools.tools}
            print(f"[ok] tools advertised: {sorted(tool_names)}")
            assert "icon_search" in tool_names, "icon_search not registered"
            assert "icon_versions" in tool_names, "icon_versions not registered"

            # 2. icon_versions
            res = await session.call_tool("icon_versions", {})
            text_blocks = [c.text for c in res.content if hasattr(c, "text")]
            joined = "\n".join(text_blocks)
            print(f"[icon_versions] response:\n{joined}\n")
            if "Could not reach" in joined:
                print("[skip] sidecar not running — start it and retry.")
                return 1
            assert "v115" in joined or "v91" in joined, "expected at least one indexed version"

            # 3. icon_search by text
            res = await session.call_tool(
                "icon_search",
                {"text": "warning triangle", "limit": 3, "version": "v115.0.0"},
            )
            text = "\n".join(c.text for c in res.content if hasattr(c, "text"))
            print(f"[icon_search text='warning triangle']:\n{text}\n")
            assert "warning" in text.lower(), "expected 'warning' to appear in matches"

            # 4. icon_search by image (canonical search.png if available)
            search_png = Path("/tmp/indexed_search.png")
            if not search_png.exists():
                # Generate one on the fly via the ingester's raster
                sys.path.insert(0, str(HERE.parent.parent))
                from ingester.extract_svg import extract_from_tsx, to_inline_svg
                from ingester.raster import rasterize_glyph

                tsx = Path(
                    ".cache/eui/packages/eui/src/components/icon/assets/search.tsx"
                ).read_text()
                png = rasterize_glyph(to_inline_svg(extract_from_tsx(tsx)))
                search_png.write_bytes(png)
            b64 = base64.b64encode(search_png.read_bytes()).decode()
            res = await session.call_tool(
                "icon_search",
                {"image_base64": b64, "limit": 3, "version": "v115.0.0"},
            )
            text = "\n".join(c.text for c in res.content if hasattr(c, "text"))
            print(f"[icon_search image=search.png]:\n{text}\n")
            assert "search" in text.lower(), "expected 'search' to appear in matches"

            # 5. Validation errors (negative case)
            res = await session.call_tool("icon_search", {})
            text = "\n".join(c.text for c in res.content if hasattr(c, "text"))
            print(f"[icon_search no-args]: {text}")
            assert "either" in text.lower() and "text" in text.lower(), "expected helpful error"

    print("\n[ok] smoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run_smoke()))
