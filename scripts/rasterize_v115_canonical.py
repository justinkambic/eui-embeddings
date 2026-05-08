#!/usr/bin/env python3
"""Rasterize every v115 icon's canonical SVG to PNG via resvg.

Produces a parallel directory of PNGs that source the same EUI .tsx
asset files the index was built from. Used to build augmented
centroids from a CLEAN source (resvg) so they can be evaluated
against Playwright-rendered PNGs without train/test leakage.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import dotenv_values  # noqa: E402

env = dotenv_values(REPO_ROOT / ".env")
os.environ.update({k: v for k, v in env.items() if v})

from ingester.eui_repo import DEFAULT_LOCATION, EuiRepo  # noqa: E402
from ingester.extract_svg import extract_from_tsx, to_inline_svg  # noqa: E402
from ingester.parse_maps import parse_repo  # noqa: E402
from ingester.raster import rasterize_glyph, rasterize_token, resolve_chrome  # noqa: E402

log = logging.getLogger("rasterize_v115_canonical")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--version", default="v115.0.0")
    parser.add_argument("--out", type=Path,
                        default=REPO_ROOT / "reports" / "resvg_pngs_v115.0.0")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")

    repo = EuiRepo(Path(DEFAULT_LOCATION))
    repo.checkout(args.version)
    icons, tokens, _ = parse_repo(repo.location)

    # Tokens have a (shape, color) entry in EUI's TOKEN_MAP. The docs
    # page (and any real user paste) renders them as colored chips with
    # white glyphs — NOT as bare black-and-white shapes. Indexing them
    # as bare glyphs creates a massive train/test mismatch and is why
    # token icons (e.g., tokenBoolean) had been ranking poorly. Use
    # rasterize_token + the parsed chrome whenever a prop has a token
    # entry; fall back to rasterize_glyph for everything else.
    chrome_by_prop = {t.prop_name: resolve_chrome(t.color, t.shape) for t in tokens}

    args.out.mkdir(parents=True, exist_ok=True)
    ok = 0
    ok_token = 0
    failed = 0
    for ic in icons:
        asset_path = repo.assets_dir() / f"{ic.asset_filename}.tsx"
        if not asset_path.exists():
            continue
        try:
            tsx = asset_path.read_text(encoding="utf-8")
            inline = to_inline_svg(extract_from_tsx(tsx))
            chrome = chrome_by_prop.get(ic.prop_name)
            if chrome is not None:
                png = rasterize_token(inline, chrome)
                ok_token += 1
            else:
                png = rasterize_glyph(inline)
            (args.out / f"{ic.prop_name}.png").write_bytes(png)
            ok += 1
        except Exception as e:
            log.warning("skip %s: %s", ic.prop_name, e)
            failed += 1
    log.info(
        "done: ok=%d (tokens=%d) failed=%d -> %s",
        ok, ok_token, failed, args.out,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
