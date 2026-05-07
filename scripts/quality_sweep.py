#!/usr/bin/env python3
"""Quality sweep: canonical self-paste over an entire EUI version.

For every icon in v115 (or whatever --version flag we're given), we:
  1. Rasterize the canonical SVG to PNG via the same pipeline used at ingest.
  2. Embed via _inference/embedding/eui-icon-encoder.
  3. Run kNN against image_vector with the version filter.
  4. Look up the rank of the icon's own asset_filename in the result list.

The "self-rank" answer treats EUI's icon-name aliases (e.g. submodule →
merge) as equivalent. If you paste merge and the top hit is submodule
(same SVG, different prop name), that's still rank 1.

Output: reports/quality_<version>_<timestamp>/{report.json, report.md}.

This is read-only against ES — no document writes, no index mutations.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import io
import json
import logging
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import dotenv_values  # noqa: E402

env = dotenv_values(REPO_ROOT / ".env")
os.environ.update({k: v for k, v in env.items() if v})

from ingester.es_client import EsClient, EsConfig  # noqa: E402
from ingester.eui_repo import DEFAULT_LOCATION, EuiRepo  # noqa: E402
from ingester.extract_svg import extract_from_tsx, to_inline_svg  # noqa: E402
from ingester.parse_maps import parse_repo  # noqa: E402
from ingester.raster import rasterize_glyph  # noqa: E402


log = logging.getLogger("quality_sweep")


# --- types ------------------------------------------------------------------


@dataclass
class IconResult:
    prop_name: str
    asset_filename: str
    rank: int  # 1-based; -1 = not found in top-K
    self_score: float | None  # score of any alias-equivalent doc in results
    top_hit: str | None
    top_score: float | None
    score_gap: float | None  # top_score - self_score (positive = ranked below top)
    competitors: list[tuple[str, float]] = field(default_factory=list)  # top-3 winners (excl. self/aliases)
    aliases_for_this_asset: list[str] = field(default_factory=list)
    error: str | None = None


# --- helpers ----------------------------------------------------------------


async def _knn_search(
    http: httpx.AsyncClient,
    es_endpoint: str,
    api_key: str,
    index: str,
    field: str,
    vector: list[float],
    version: str,
    k: int = 50,
) -> list[dict[str, Any]]:
    body = {
        "size": k,
        "_source": ["prop_name", "release_tag", "asset_filename"],
        "knn": {
            "field": field,
            "query_vector": vector,
            "k": k,
            "num_candidates": max(200, k * 4),
            "filter": [{"term": {"release_tag": version}}],
        },
    }
    r = await http.post(
        f"{es_endpoint.rstrip('/')}/{index}/_search",
        json=body,
        headers={"Authorization": f"ApiKey {api_key}"},
    )
    r.raise_for_status()
    data = r.json()
    return [
        {
            "_id": h["_id"],
            "prop_name": h["_source"]["prop_name"],
            "asset_filename": h["_source"].get("asset_filename"),
            "score": h["_score"],
        }
        for h in data["hits"]["hits"]
    ]




def _normalize_for_query(png: bytes, size: int = 256) -> bytes:
    """Python (Pillow) equivalent of the sidecar's `normalizeQueryImage`.

    The icon-search-server pre-processes user-pasted images via Sharp:
    `flatten({background:'#ffffff'}).resize(256, 256, {fit:'contain',
    background:'#ffffff', kernel:'lanczos3'})`. This function mirrors
    that so the sweep query path matches the production query path.

    Lanczos and exact pixel values won't be byte-identical with Sharp,
    but the high-level behavior (composite alpha onto white, fit-
    contain into 256x256 with white letterbox, lanczos resample) is
    the same — close enough that the resulting embeddings cluster the
    same way.
    """
    from PIL import Image

    im = Image.open(io.BytesIO(png))
    # Step 1: composite onto white if any alpha channel.
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    # Step 2: fit-contain into size×size, lanczos.
    im.thumbnail((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (size, size), (255, 255, 255))
    canvas.paste(im, ((size - im.width) // 2, (size - im.height) // 2))
    out = io.BytesIO()
    canvas.save(out, format="PNG", optimize=True)
    return out.getvalue()


async def _sidecar_search(
    http: httpx.AsyncClient,
    sidecar_url: str,
    png: bytes,
    version: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Run the sidecar's /api/icon-search end-to-end.

    Going through the sidecar (instead of calling ES `_inference`
    directly with raw PNG bytes) routes the query through the same
    Sharp `flatten + resize-fit-contain` normalization the real UI
    uses. Without this, the test sees a different embedding than
    production, and the recorded ranks are noise.
    """
    body = {
        "limit": limit,
        "version": version,
        "query": {"image": base64.b64encode(png).decode("ascii")},
    }
    r = await http.post(f"{sidecar_url.rstrip('/')}/api/icon-search", json=body)
    r.raise_for_status()
    hits = r.json().get("hits") or []
    # Match the shape `_knn_search` returns so downstream code is shared.
    return [
        {
            "_id": None,
            "prop_name": h["prop_name"],
            "asset_filename": h.get("asset_filename"),
            "score": h["score"],
        }
        for h in hits
    ]


async def process_icon(
    *,
    prop_name: str,
    asset_filename: str,
    asset_path: Path,
    version: str,
    es: EsClient,
    http: httpx.AsyncClient,
    asset_to_props: dict[str, list[str]],
    embed_sem: asyncio.Semaphore,
    knn_sem: asyncio.Semaphore,
    png_dir: Path | None = None,
    sidecar_url: str | None = None,
    normalize: bool = False,
) -> IconResult:
    aliases = [p for p in asset_to_props.get(asset_filename, []) if p != prop_name]
    try:
        if png_dir is not None:
            # Use the pre-rendered (Playwright) PNG so we test against
            # actual browser-rendered pixels instead of the resvg
            # round-trip of the same SVG that's already indexed.
            #
            # Aliases share an asset, but the docs page typically only
            # renders one cell per asset. If the prop's own PNG is
            # missing, fall back to any alias PNG that exists.
            png_path = png_dir / f"{prop_name}.png"
            if not png_path.exists():
                for alias in aliases:
                    alt = png_dir / f"{alias}.png"
                    if alt.exists():
                        png_path = alt
                        break
            if not png_path.exists():
                # Skip rather than error: there's no PNG to test, but
                # this isn't a code/pipeline failure. Mark with a
                # distinct sentinel rank so reports can separate
                # "skipped (no PNG)" from "errored".
                return IconResult(
                    prop_name, asset_filename, -2, None, None, None, None,
                    aliases_for_this_asset=aliases,
                    error="skipped: no pre-rendered PNG (icon not on docs page)",
                )
            png = png_path.read_bytes()
        else:
            tsx = asset_path.read_text(encoding="utf-8")
            inline = to_inline_svg(extract_from_tsx(tsx))
            png = rasterize_glyph(inline)

        if sidecar_url is not None:
            # Real-user path: sidecar runs Sharp normalize before
            # embedding. We share the embed_sem to keep concurrency
            # bounded.
            async with embed_sem:
                hits = await _sidecar_search(http, sidecar_url, png, version, limit=50)
        else:
            if normalize:
                # Mirror the sidecar's Sharp normalize so the embedding
                # input matches what real users hit. Otherwise the test
                # is bit-for-bit faithful to a query mode no one runs.
                png = _normalize_for_query(png)
            async with embed_sem:
                vecs = await es.embed_pngs([png])
            if not vecs:
                return IconResult(prop_name, asset_filename, -1, None, None, None, None,
                                  aliases_for_this_asset=aliases, error="no embedding returned")

            async with knn_sem:
                hits = await _knn_search(
                    http,
                    es.cfg.endpoint,
                    es.cfg.api_key,
                    es.cfg.index_name,
                    "image_vector",
                    vecs[0],
                    version,
                    k=50,
                )

        # Find the rank of any doc whose asset_filename matches ours
        # (alias-aware matching).
        rank = -1
        self_score: float | None = None
        for i, h in enumerate(hits):
            if h["asset_filename"] == asset_filename:
                rank = i + 1
                self_score = h["score"]
                break

        top_hit = hits[0]["prop_name"] if hits else None
        top_score = hits[0]["score"] if hits else None
        gap = (top_score - self_score) if (top_score is not None and self_score is not None) else None

        # Top-3 competitors: hits whose asset_filename != ours, in order.
        competitors: list[tuple[str, float]] = []
        for h in hits:
            if h["asset_filename"] != asset_filename and len(competitors) < 3:
                competitors.append((h["prop_name"], h["score"]))

        return IconResult(
            prop_name=prop_name,
            asset_filename=asset_filename,
            rank=rank,
            self_score=self_score,
            top_hit=top_hit,
            top_score=top_score,
            score_gap=gap,
            competitors=competitors,
            aliases_for_this_asset=aliases,
        )
    except Exception as e:
        log.exception("failed processing %s", prop_name)
        return IconResult(
            prop_name=prop_name,
            asset_filename=asset_filename,
            rank=-1,
            self_score=None,
            top_hit=None,
            top_score=None,
            score_gap=None,
            aliases_for_this_asset=aliases,
            error=f"{type(e).__name__}: {e}",
        )


# --- report writers ---------------------------------------------------------


def _aggregate(results: list[IconResult]) -> dict[str, Any]:
    n = len(results)
    skipped = sum(1 for r in results if r.rank == -2)
    errored = sum(1 for r in results if r.error is not None and r.rank != -2)
    evaluated = n - skipped
    in_topk = lambda k: sum(1 for r in results if r.rank > 0 and r.rank <= k)
    not_found = sum(1 for r in results if r.rank == -1 and r.error is None)
    return {
        "total": n,
        "skipped": skipped,
        "evaluated": evaluated,
        "errored": errored,
        "ranked_top_1": in_topk(1),
        "ranked_top_3": in_topk(3),
        "ranked_top_10": in_topk(10),
        "ranked_top_50": in_topk(50),
        "not_in_top_50": not_found,
    }


def _problem_icons(results: list[IconResult]) -> list[IconResult]:
    """Icons that don't rank top-1 and aren't trivially aliased away."""
    out = []
    for r in results:
        if r.rank == -2:
            continue  # skipped (no PNG)
        if r.error is not None:
            continue
        if r.rank == 1:
            continue
        out.append(r)
    out.sort(key=lambda r: (r.rank if r.rank > 0 else 9999, -(r.score_gap or 0)))
    return out


def write_reports(results: list[IconResult], version: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": _aggregate(results),
        "results": [
            {
                "prop_name": r.prop_name,
                "asset_filename": r.asset_filename,
                "rank": r.rank,
                "self_score": r.self_score,
                "top_hit": r.top_hit,
                "top_score": r.top_score,
                "score_gap": r.score_gap,
                "competitors": [{"prop_name": p, "score": s} for p, s in r.competitors],
                "aliases_for_this_asset": r.aliases_for_this_asset,
                "error": r.error,
            }
            for r in results
        ],
    }
    (out_dir / "report.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    summary = payload["summary"]
    md_lines = [
        f"# Quality sweep — {version}",
        "",
        f"_Generated {payload['generated_at']}_",
        "",
        "## Summary",
        "",
        f"- Total icons in index: **{summary['total']}**",
        f"- Skipped (no PNG to test against): **{summary['skipped']}**",
        f"- Evaluated: **{summary['evaluated']}**",
        f"- Errored: **{summary['errored']}**",
        f"- Top-1 (correct icon ranks #1): **{summary['ranked_top_1']}** "
        f"({summary['ranked_top_1'] / max(summary['evaluated'], 1):.1%} of evaluated)",
        f"- Top-3: **{summary['ranked_top_3']}** "
        f"({summary['ranked_top_3'] / max(summary['evaluated'], 1):.1%} of evaluated)",
        f"- Top-10: **{summary['ranked_top_10']}** "
        f"({summary['ranked_top_10'] / max(summary['evaluated'], 1):.1%} of evaluated)",
        f"- Not found in top-50: **{summary['not_in_top_50']}**",
        "",
        "## Problem icons (rank > 1, sorted by rank then score gap)",
        "",
        "| Rank | Prop | Top hit | Δscore | Closest competitors |",
        "|---|---|---|---|---|",
    ]
    for r in _problem_icons(results)[:80]:
        comp = ", ".join(f"`{p}` {s:.3f}" for p, s in r.competitors[:3])
        gap = f"{r.score_gap:.3f}" if r.score_gap is not None else "-"
        md_lines.append(
            f"| {r.rank if r.rank > 0 else '50+'} | `{r.prop_name}` | `{r.top_hit or '-'}` | {gap} | {comp} |"
        )

    md_lines += [
        "",
        "## Errors",
        "",
    ]
    errs = [r for r in results if r.error and r.rank != -2]
    if not errs:
        md_lines.append("_None._")
    else:
        for r in errs:
            md_lines.append(f"- `{r.prop_name}`: {r.error}")

    (out_dir / "report.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")


# --- main -------------------------------------------------------------------


async def run(
    version: str,
    limit: int | None,
    png_dir: Path | None = None,
    sidecar_url: str | None = None,
    normalize: bool = False,
) -> int:
    cfg = EsConfig(
        endpoint=os.environ["ELASTICSEARCH_ENDPOINT"],
        api_key=os.environ["ELASTICSEARCH_VECTOR_DB_API_KEY"],
    )
    es = EsClient(cfg)

    repo = EuiRepo(Path(DEFAULT_LOCATION))
    log.info("checking out %s", version)
    repo.checkout(version)

    icons, _tokens, paths = parse_repo(repo.location)
    log.info("loaded %d icons from %s (layout=%s)", len(icons), version, paths.layout)

    asset_to_props: dict[str, list[str]] = defaultdict(list)
    for ic in icons:
        asset_to_props[ic.asset_filename].append(ic.prop_name)

    plans: list[tuple[str, str, Path]] = []
    for ic in icons:
        asset_path = repo.assets_dir() / f"{ic.asset_filename}.tsx"
        if asset_path.exists():
            plans.append((ic.prop_name, ic.asset_filename, asset_path))
        else:
            log.warning("missing asset for %s (%s)", ic.prop_name, ic.asset_filename)

    if limit is not None:
        plans = plans[:limit]
    log.info("running self-paste sweep over %d icons", len(plans))

    embed_sem = asyncio.Semaphore(4)
    knn_sem = asyncio.Semaphore(8)

    timeout = httpx.Timeout(60.0)
    async with httpx.AsyncClient(timeout=timeout) as http:
        try:
            tasks = [
                process_icon(
                    prop_name=p,
                    asset_filename=a,
                    asset_path=path,
                    version=version,
                    es=es,
                    http=http,
                    asset_to_props=asset_to_props,
                    embed_sem=embed_sem,
                    knn_sem=knn_sem,
                    png_dir=png_dir,
                    sidecar_url=sidecar_url,
                    normalize=normalize,
                )
                for (p, a, path) in plans
            ]
            results: list[IconResult] = []
            started = time.monotonic()
            for i, fut in enumerate(asyncio.as_completed(tasks), 1):
                r = await fut
                results.append(r)
                if i % 50 == 0 or i == len(tasks):
                    elapsed = time.monotonic() - started
                    log.info(
                        "[%d/%d] elapsed=%.1fs, in-flight failures so far=%d",
                        i, len(tasks), elapsed, sum(1 for x in results if x.error is not None),
                    )
        finally:
            await es.aclose()

    # Stable order: by prop_name
    results.sort(key=lambda r: r.prop_name)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = REPO_ROOT / "reports" / f"quality_{version}_{ts}"
    write_reports(results, version, out_dir)
    log.info("wrote report to %s", out_dir)

    s = _aggregate(results)
    base = max(s["evaluated"], 1)
    print()
    print(f"=== Quality sweep summary ({version}) ===")
    print(f"  total in index: {s['total']}")
    print(f"  skipped (no PNG): {s['skipped']}")
    print(f"  evaluated: {s['evaluated']}")
    print(f"  top-1: {s['ranked_top_1']} ({s['ranked_top_1'] / base:.1%})")
    print(f"  top-3: {s['ranked_top_3']} ({s['ranked_top_3'] / base:.1%})")
    print(f"  top-10: {s['ranked_top_10']} ({s['ranked_top_10'] / base:.1%})")
    print(f"  errored: {s['errored']}")
    print(f"  report: {out_dir}/report.md")
    return 0 if s["errored"] == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Self-paste quality sweep over a single EUI version")
    parser.add_argument("--version", default="v115.0.0", help="EUI tag to sweep (default v115.0.0)")
    parser.add_argument("--limit", type=int, default=None, help="cap to N icons (for testing)")
    parser.add_argument(
        "--png-dir",
        default=None,
        help=(
            "directory of <propName>.png files to use as the query "
            "image (e.g. reports/playwright_pngs_v115.0.0). When unset, "
            "rasterizes the canonical SVG via resvg (the original "
            "self-paste sweep)."
        ),
    )
    parser.add_argument(
        "--normalize",
        action="store_true",
        help=(
            "Pre-normalize each PNG with the Pillow equivalent of the "
            "sidecar's Sharp pipeline (flatten alpha onto white, fit-"
            "contain into 256x256, lanczos) before sending to ES. Use "
            "this with --png-dir to make the test path match what real "
            "users hit. Without it, the sweep sends raw PNG bytes to "
            "ES, which inflates accuracy."
        ),
    )
    parser.add_argument(
        "--via-sidecar",
        nargs="?",
        const="http://127.0.0.1:4555",
        default=None,
        metavar="URL",
        help=(
            "Route embedding + kNN through the icon-search-server "
            "sidecar at URL (default http://127.0.0.1:4555). This is "
            "the path real users hit, so the sweep result reflects "
            "actual end-to-end accuracy including the Sharp normalize "
            "step. Without this flag we send raw PNGs straight to ES, "
            "which inflates accuracy because the index was built on "
            "the same raw bytes."
        ),
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("ingester").setLevel(logging.WARNING)

    png_dir = Path(args.png_dir) if args.png_dir else None
    if png_dir is not None and not png_dir.is_dir():
        log.error("--png-dir does not exist or is not a directory: %s", png_dir)
        return 2
    return asyncio.run(
        run(
            args.version,
            args.limit,
            png_dir=png_dir,
            sidecar_url=args.via_sidecar,
            normalize=args.normalize,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
