#!/usr/bin/env python3
"""Render every EUI icon to a PNG via the live docs page in headless Chromium.

The output PNGs simulate the "user pastes a screenshot of a real
browser-rendered icon" path, which is what the production search has to
serve. Compare with the canonical `quality_sweep.py` (which embeds the
resvg-rasterized SVG of each asset) to surface gaps where browser font
rendering / anti-aliasing / EUI's CSS color shifts the embedding away
from the indexed canonical.

Prereqs:
    .venv-mcp/bin/pip install playwright
    .venv-mcp/bin/playwright install chromium
    yarn workspace @elastic/eui-website start  # docs site at :3000

Usage:
    .venv-mcp/bin/python scripts/render_icons_playwright.py \
        --version v115.0.0 \
        --docs-url http://localhost:3000/docs/components/display/icons

Output:
    reports/playwright_pngs_<version>/<propName>.png

The companion `--png-dir` flag on quality_sweep.py consumes these PNGs.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from playwright.async_api import async_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]

log = logging.getLogger("render_icons_playwright")


async def render(docs_url: str, out_dir: Path, limit: int | None) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 1600, "height": 1000},
            # Higher DSF = more pixels per SVG. EUI icons are 16x16 by
            # default; at DSF=4 we capture 64x64 PNGs, closer to the
            # typical 50-200px crops users actually paste in.
            device_scale_factor=4,
        )
        page = await ctx.new_page()
        log.info("loading %s", docs_url)
        await page.goto(docs_url, wait_until="networkidle")

        # The page lazy-mounts the React grids; wait for at least one
        # icon cell to exist before scraping the rest.
        await page.wait_for_selector('[id^="icon-"]', timeout=30_000)

        # Grab every icon-cell id present in the DOM right now. As the
        # docs page is one route, this gives us all sections in a single
        # page-load (glyphs + logos + apps + ML + tokens + custom logos).
        ids: list[str] = await page.eval_on_selector_all(
            '[id^="icon-"]',
            "els => Array.from(new Set(els.map(e => e.id)))",
        )
        log.info("discovered %d icon cells in DOM", len(ids))
        if limit is not None:
            ids = ids[:limit]

        rendered = 0
        skipped = 0
        for cell_id in ids:
            prop = cell_id[len("icon-") :]
            png_path = out_dir / f"{prop}.png"

            # Scroll the cell into view (FlexGrid lays cells out lazily;
            # without scrolling we sometimes hit zero-pixel screenshots).
            cell = page.locator(f'[id="{cell_id}"]')
            await cell.scroll_into_view_if_needed()

            # Capture the SVG, but with white padding around it.
            #
            # Capturing the bare <svg> bounding box ranks differently
            # than what real users paste: a manual screenshot always
            # has whitespace around the icon, and that padding changes
            # how the icon-search-server's resize-fit-contain step lays
            # the icon onto the 256x256 input fed to jina-clip-v2.
            # Empirically, a 50%-padded capture of grokApp produces the
            # same rank-1 hit as a hand-pasted screenshot, while a
            # zero-padding capture produces a different (wrong) hit.
            svg = cell.locator("svg").first
            if await svg.count() == 0:
                log.warning("skip %s: no <svg> in cell", prop)
                skipped += 1
                continue
            box = await svg.bounding_box()
            if not box or box["width"] == 0 or box["height"] == 0:
                log.warning("skip %s: zero-pixel bounding box", prop)
                skipped += 1
                continue

            pad = max(box["width"], box["height"]) * 0.5
            clip = {
                "x": max(0.0, box["x"] - pad),
                "y": max(0.0, box["y"] - pad),
                "width": box["width"] + 2 * pad,
                "height": box["height"] + 2 * pad,
            }

            try:
                buf = await page.screenshot(clip=clip, type="png")
                png_path.write_bytes(buf)
                rendered += 1
            except Exception as e:
                log.warning("skip %s: %s", prop, e)
                skipped += 1

            if rendered % 50 == 0 and rendered > 0:
                log.info("rendered %d/%d", rendered, len(ids))

        log.info("done: rendered=%d skipped=%d -> %s", rendered, skipped, out_dir)

        await ctx.close()
        await browser.close()

    return 0 if skipped == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--version", default="v115.0.0")
    parser.add_argument(
        "--docs-url",
        default="http://localhost:3000/docs/components/display/icons",
    )
    parser.add_argument("--limit", type=int, default=None, help="cap N for testing")
    parser.add_argument(
        "--out-dir",
        default=None,
        help="defaults to reports/playwright_pngs_<version>",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    out_dir = Path(args.out_dir) if args.out_dir else (
        REPO_ROOT / "reports" / f"playwright_pngs_{args.version}"
    )
    return asyncio.run(render(args.docs_url, out_dir, args.limit))


if __name__ == "__main__":
    sys.exit(main())
