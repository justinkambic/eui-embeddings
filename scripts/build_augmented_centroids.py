#!/usr/bin/env python3
"""Build augmented per-icon centroids.

For each indexed v115 icon:
  1. Take the rendered Playwright PNG (or fall back to the canonical
     resvg PNG by re-rasterizing the SVG) as the source.
  2. Generate K padded variants via the same _tta_variants() helper
     used at query time.
  3. Embed all K variants.
  4. Mean-pool the K embeddings into a single "augmented centroid"
     vector and write to image_vector_aug_centroid on the doc.

The hypothesis: averaging across naturally-cropped variants smooths
out per-rendering noise, so the icon's stored representation is
robust to whatever framing the user pastes. Symmetric to query-time
TTA but applied once at index time, with no inference cost per query.

Usage:
    .venv-mcp/bin/python scripts/build_augmented_centroids.py \
        --version v115.0.0 --png-dir reports/playwright_pngs_v115.0.0
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import dotenv_values  # noqa: E402

env = dotenv_values(REPO_ROOT / ".env")
os.environ.update({k: v for k, v in env.items() if v})

from ingester.es_client import EsClient, EsConfig  # noqa: E402
from scripts.quality_sweep import _tta_variants  # noqa: E402

log = logging.getLogger("build_augmented_centroids")


async def fetch_props_and_assets(
    http: httpx.AsyncClient,
    endpoint: str,
    api_key: str,
    index: str,
    version: str,
) -> list[tuple[str, str]]:
    body: dict[str, Any] = {
        "size": 200,
        "_source": ["prop_name", "asset_filename"],
        "query": {"term": {"release_tag": version}},
        "sort": [{"prop_name": "asc"}],
    }
    out: list[tuple[str, str]] = []
    while True:
        r = await http.post(
            f"{endpoint.rstrip('/')}/{index}/_search",
            json=body,
            headers={"Authorization": f"ApiKey {api_key}"},
        )
        r.raise_for_status()
        hits = r.json()["hits"]["hits"]
        if not hits:
            break
        for h in hits:
            src = h["_source"]
            out.append((src["prop_name"], src.get("asset_filename") or ""))
        if len(hits) < body["size"]:
            break
        body["search_after"] = hits[-1]["sort"]
    return out


async def update_centroid(
    http: httpx.AsyncClient,
    endpoint: str,
    api_key: str,
    index: str,
    version: str,
    prop: str,
    centroid: list[float],
) -> bool:
    body = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"prop_name": prop}},
                    {"term": {"release_tag": version}},
                ]
            }
        },
        "script": {
            "source": "ctx._source.image_vector_aug_centroid = params.vec;",
            "params": {"vec": centroid},
        },
    }
    r = await http.post(
        f"{endpoint.rstrip('/')}/{index}/_update_by_query?refresh=false",
        json=body,
        headers={"Authorization": f"ApiKey {api_key}"},
    )
    return r.status_code == 200 and r.json().get("updated", 0) > 0


async def run(version: str, png_dir: Path) -> int:
    cfg = EsConfig(
        endpoint=os.environ["ELASTICSEARCH_ENDPOINT"],
        api_key=os.environ["ELASTICSEARCH_VECTOR_DB_API_KEY"],
    )
    es = EsClient(cfg)

    timeout = httpx.Timeout(60.0)
    async with httpx.AsyncClient(timeout=timeout) as http:
        log.info("fetching prop list for %s …", version)
        props = await fetch_props_and_assets(
            http, cfg.endpoint, cfg.api_key, cfg.index_name, version
        )
        log.info("got %d props", len(props))

        ok = 0
        skipped_no_png = 0
        failed = 0
        try:
            for prop, _asset in props:
                src_png = png_dir / f"{prop}.png"
                if not src_png.exists():
                    skipped_no_png += 1
                    continue
                raw = src_png.read_bytes()
                variants = _tta_variants(raw)
                vecs = await es.embed_pngs(variants)
                if len(vecs) != len(variants):
                    log.warning("%s: embed mismatch", prop)
                    failed += 1
                    continue
                dim = len(vecs[0])
                centroid = [
                    sum(v[i] for v in vecs) / len(vecs) for i in range(dim)
                ]
                ok_update = await update_centroid(
                    http, cfg.endpoint, cfg.api_key, cfg.index_name, version, prop, centroid
                )
                if ok_update:
                    ok += 1
                else:
                    failed += 1
                if (ok + failed) % 50 == 0:
                    log.info("processed %d / %d (ok=%d failed=%d)",
                             ok + failed, len(props) - skipped_no_png, ok, failed)
        finally:
            await es.aclose()

        log.info(
            "done: ok=%d skipped_no_png=%d failed=%d", ok, skipped_no_png, failed
        )
    return 0 if failed == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--version", default="v115.0.0")
    parser.add_argument(
        "--png-dir",
        type=Path,
        default=REPO_ROOT / "reports" / "playwright_pngs_v115.0.0",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("ingester").setLevel(logging.WARNING)

    return asyncio.run(run(args.version, args.png_dir))


if __name__ == "__main__":
    sys.exit(main())
