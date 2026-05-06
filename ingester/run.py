"""Single-version ingestion: walk an EUI tag, embed every icon, write to ES.

Entry point: `python -m ingester run --version v115.0.0`.

Flow:
1. Open/clone EUI under .cache/eui, fetch tags, checkout the requested tag.
2. Parse typeToPathMap for that version (one entry per <EuiIcon type=...> name).
3. Build a render plan per entry — one doc per (prop_name, release_tag).
4. Skip plans whose doc id already exists.
5. Rasterize the bare SVG to a deterministic black-on-white PNG.
6. Batch-embed PNGs and prop names via _inference (concurrent, bounded).
7. Bulk-index in batches of N.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .es_client import EsClient, EsConfig
from .eui_repo import EuiRepo, DEFAULT_LOCATION, DEFAULT_REPO_URL
from .extract_svg import extract_from_tsx, to_inline_svg
from .parse_maps import IconEntry, parse_repo
from .raster import rasterize_glyph
from .util import doc_id, humanize_prop, major_from_tag


log = logging.getLogger("ingester")


# --- planning ---------------------------------------------------------------


@dataclass
class RenderPlan:
    prop_name: str
    asset_filename: str
    asset_path: Path

    def doc_id(self, release_tag: str) -> str:
        return doc_id(self.prop_name, release_tag)


def build_plans(icons: list[IconEntry], assets_dir: Path) -> list[RenderPlan]:
    plans: list[RenderPlan] = []
    for ic in icons:
        asset_path = assets_dir / f"{ic.asset_filename}.tsx"
        if not asset_path.exists():
            log.warning("missing asset for prop=%s expected=%s", ic.prop_name, asset_path)
            continue
        plans.append(
            RenderPlan(
                prop_name=ic.prop_name,
                asset_filename=ic.asset_filename,
                asset_path=asset_path,
            )
        )
    return plans


# --- rendering --------------------------------------------------------------


def render_png(plan: RenderPlan) -> bytes:
    tsx = plan.asset_path.read_text(encoding="utf-8")
    inline = to_inline_svg(extract_from_tsx(tsx))
    return rasterize_glyph(inline)


def text_for_plan(plan: RenderPlan) -> str:
    """Synthesize the text input we embed into name_vector."""
    return f"{humanize_prop(plan.prop_name)} icon"


# --- embedding + indexing ---------------------------------------------------


@dataclass
class IngestStats:
    plans_total: int = 0
    plans_skipped: int = 0
    plans_indexed: int = 0
    plans_render_failed: int = 0
    bulk_failures: int = 0
    duration_s: float = 0.0
    render_errors: list[str] = field(default_factory=list)


async def _bulk_embed(es: EsClient, pngs: list[bytes], texts: list[str], batch_size: int) -> tuple[list[list[float]], list[list[float]]]:
    """Embed pngs and texts in parallel chunks of `batch_size`."""
    async def embed_pngs_chunk(chunk: list[bytes]) -> list[list[float]]:
        return await es.embed_pngs(chunk)

    async def embed_texts_chunk(chunk: list[str]) -> list[list[float]]:
        return await es.embed_texts(chunk)

    png_chunks = [pngs[i : i + batch_size] for i in range(0, len(pngs), batch_size)]
    text_chunks = [texts[i : i + batch_size] for i in range(0, len(texts), batch_size)]

    png_tasks = [embed_pngs_chunk(c) for c in png_chunks]
    text_tasks = [embed_texts_chunk(c) for c in text_chunks]

    # Run image and text embedding concurrently. Each batch is one HTTP call.
    png_results, text_results = await asyncio.gather(
        asyncio.gather(*png_tasks),
        asyncio.gather(*text_tasks),
    )

    image_vectors = [v for chunk in png_results for v in chunk]
    name_vectors = [v for chunk in text_results for v in chunk]
    return image_vectors, name_vectors


async def ingest_version(
    *,
    version: str,
    es: EsClient,
    repo: EuiRepo,
    force: bool = False,
    limit: int | None = None,
    batch_size: int = 16,
    bulk_size: int = 64,
) -> IngestStats:
    started = time.monotonic()
    stats = IngestStats()

    log.info("checking out %s", version)
    repo.checkout(version)
    released_at = repo.commit_date(version)

    icons, _tokens, paths = parse_repo(repo.location)
    log.info("%s: layout=%s, icons=%d", version, paths.layout, len(icons))

    plans = build_plans(icons, repo.assets_dir())
    if limit is not None:
        plans = plans[:limit]
    stats.plans_total = len(plans)

    if not force:
        log.info("checking which docs already exist (skip-if-exists pre-pass)")
        existing = await asyncio.gather(*(es.doc_exists(p.doc_id(version)) for p in plans))
        new_plans = [p for p, e in zip(plans, existing) if not e]
        stats.plans_skipped = len(plans) - len(new_plans)
        plans = new_plans
        log.info("%d/%d plans already indexed; %d to ingest", stats.plans_skipped, stats.plans_total, len(plans))
    else:
        log.info("--force: re-ingesting all %d plans", len(plans))

    if not plans:
        stats.duration_s = time.monotonic() - started
        return stats

    log.info("rasterizing %d PNGs", len(plans))
    rendered: list[tuple[RenderPlan, bytes]] = []
    for p in plans:
        try:
            rendered.append((p, render_png(p)))
        except Exception as e:
            stats.plans_render_failed += 1
            msg = f"{p.prop_name} ({p.asset_filename}.tsx): {type(e).__name__}: {e}"
            stats.render_errors.append(msg)
            log.warning("render failed: %s", msg)
    if not rendered:
        log.warning("no plans rendered successfully; nothing to index")
        stats.duration_s = time.monotonic() - started
        return stats
    plans = [r[0] for r in rendered]
    pngs = [r[1] for r in rendered]
    texts = [text_for_plan(p) for p in plans]

    log.info("embedding via _inference (batch_size=%d)", batch_size)
    image_vectors, name_vectors = await _bulk_embed(es, pngs, texts, batch_size)
    if len(image_vectors) != len(plans) or len(name_vectors) != len(plans):
        raise RuntimeError(
            f"vector count mismatch: plans={len(plans)} image={len(image_vectors)} name={len(name_vectors)}"
        )

    release_major = major_from_tag(version)
    docs: list[tuple[str, dict]] = []
    for plan, iv, nv in zip(plans, image_vectors, name_vectors):
        source: dict[str, Any] = {
            "prop_name": plan.prop_name,
            "release_tag": version,
            "release_major": release_major,
            "released_at": released_at,
            "asset_filename": plan.asset_filename,
            "asset_path": str(plan.asset_path.relative_to(repo.location)),
            "image_vector": iv,
            "name_vector": nv,
        }
        docs.append((plan.doc_id(version), source))

    log.info("bulk-indexing %d docs (bulk_size=%d)", len(docs), bulk_size)
    for i in range(0, len(docs), bulk_size):
        chunk = docs[i : i + bulk_size]
        # On the last chunk, refresh=wait_for so subsequent runs see the writes.
        is_last = i + bulk_size >= len(docs)
        result = await es.bulk_index(chunk, refresh="wait_for" if is_last else "false")
        if result.get("errors"):
            stats.bulk_failures += sum(
                1 for item in result.get("items", []) if "error" in item.get("index", {})
            )

    stats.plans_indexed = len(docs)
    stats.duration_s = time.monotonic() - started
    return stats


# --- state file -------------------------------------------------------------


STATE_DIR = Path("ingester/state")


def _state_path(version: str) -> Path:
    safe = version.replace("/", "_")
    return STATE_DIR / f"{safe}.json"


def write_state(version: str, stats: IngestStats) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    _state_path(version).write_text(
        json.dumps(
            {
                "version": version,
                "plans_total": stats.plans_total,
                "plans_skipped": stats.plans_skipped,
                "plans_indexed": stats.plans_indexed,
                "plans_render_failed": stats.plans_render_failed,
                "bulk_failures": stats.bulk_failures,
                "duration_s": round(stats.duration_s, 3),
                "render_errors": stats.render_errors,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


# --- CLI --------------------------------------------------------------------


def _make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser("ingester", description="EUI icon ingester")
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="ingest a single EUI tag")
    run.add_argument("--version", required=True, help="EUI tag, e.g. v115.0.0")
    run.add_argument("--force", action="store_true", help="re-ingest even if docs exist")
    run.add_argument("--limit", type=int, default=None, help="stop after N plans")
    run.add_argument("--batch-size", type=int, default=16,
                     help="items per _inference call. EIS jina-clip-v2 enforces a max of 16.")
    run.add_argument("--bulk-size", type=int, default=64)

    trickle = sub.add_parser("trickle", help="background backfill across a tag range")
    trickle.add_argument("--from", dest="from_tag", required=True)
    trickle.add_argument("--to", dest="to_tag", required=True)
    trickle.add_argument("--pace", default="10m", help="sleep between versions, e.g. 30s, 5m, 1h")
    trickle.add_argument("--majors-only", action="store_true", help="only ingest .0.0 tags")

    return p


def _pace_to_seconds(pace: str) -> int:
    pace = pace.strip()
    if pace.endswith("h"):
        return int(pace[:-1]) * 3600
    if pace.endswith("m"):
        return int(pace[:-1]) * 60
    if pace.endswith("s"):
        return int(pace[:-1])
    return int(pace)


async def _cmd_run(args: argparse.Namespace) -> int:
    cfg = EsConfig(
        endpoint=os.environ["ELASTICSEARCH_ENDPOINT"],
        api_key=os.environ["ELASTICSEARCH_VECTOR_DB_API_KEY"],
    )
    es = EsClient(cfg)
    # Always use our own cache; never disturb the user's eui fork.
    repo = EuiRepo.open_or_clone(
        DEFAULT_LOCATION,
        os.environ.get("EUI_REPO", DEFAULT_REPO_URL),
    )
    repo.fetch_tags()

    try:
        stats = await ingest_version(
            version=args.version,
            es=es,
            repo=repo,
            force=args.force,
            limit=args.limit,
            batch_size=args.batch_size,
            bulk_size=args.bulk_size,
        )
        write_state(args.version, stats)
        log.info(
            "done %s in %.1fs: indexed=%d skipped=%d total=%d render_failed=%d bulk_failures=%d",
            args.version,
            stats.duration_s,
            stats.plans_indexed,
            stats.plans_skipped,
            stats.plans_total,
            stats.plans_render_failed,
            stats.bulk_failures,
        )
        return 0 if stats.bulk_failures == 0 else 1
    finally:
        await es.aclose()


async def _cmd_trickle(args: argparse.Namespace) -> int:
    cfg = EsConfig(
        endpoint=os.environ["ELASTICSEARCH_ENDPOINT"],
        api_key=os.environ["ELASTICSEARCH_VECTOR_DB_API_KEY"],
    )
    repo = EuiRepo.open_or_clone(
        DEFAULT_LOCATION,
        os.environ.get("EUI_REPO", DEFAULT_REPO_URL),
    )
    repo.fetch_tags()

    from .util import major_from_tag as _major

    pattern = "v*.*.*"
    tags = repo.list_tags(pattern)

    def _key(t: str) -> tuple[int, int, int]:
        import re

        m = re.match(r"v(\d+)\.(\d+)\.(\d+)", t)
        return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (0, 0, 0)

    sorted_tags = sorted(tags, key=_key)
    lo = _key(args.from_tag)
    hi = _key(args.to_tag)
    in_range = [t for t in sorted_tags if lo <= _key(t) <= hi]
    if args.majors_only:
        in_range = [t for t in in_range if t.endswith(".0.0")]
    log.info("trickle plan: %d versions, pace=%s", len(in_range), args.pace)

    pace_s = _pace_to_seconds(args.pace)

    rc = 0
    es = EsClient(cfg)
    try:
        for i, tag in enumerate(in_range):
            log.info("[%d/%d] %s", i + 1, len(in_range), tag)
            try:
                stats = await ingest_version(version=tag, es=es, repo=repo)
                write_state(tag, stats)
            except Exception as e:
                log.exception("trickle: failed on %s: %s", tag, e)
                rc = 1
            if i + 1 < len(in_range):
                log.info("sleeping %ds before next version", pace_s)
                await asyncio.sleep(pace_s)
    finally:
        await es.aclose()
    return rc


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # httpx is chatty; suppress per-request INFO logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    parser = _make_parser()
    args = parser.parse_args(argv)
    if args.cmd == "run":
        return asyncio.run(_cmd_run(args))
    if args.cmd == "trickle":
        return asyncio.run(_cmd_trickle(args))
    parser.error(f"unknown command {args.cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
