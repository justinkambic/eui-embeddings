#!/usr/bin/env python3
"""Backfill `description` text + `description_vector` onto existing
docs in the eui_icons index.

Reads a JSON map of {prop_name: description}, embeds each via jina
text inference, and runs an `update_by_query`-style _bulk update
against docs matching `(prop_name, release_tag)`.

Existing image_vector / name_vector fields are untouched; this is
purely additive.

Usage:
    .venv-mcp/bin/python scripts/backfill_descriptions.py \
        --version v115.0.0 \
        --descriptions descriptions/v115.0.0_seed.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import dotenv_values  # noqa: E402

env = dotenv_values(REPO_ROOT / ".env")
os.environ.update({k: v for k, v in env.items() if v})

from ingester.es_client import EsClient, EsConfig  # noqa: E402

log = logging.getLogger("backfill_descriptions")


async def update_doc(
    http: httpx.AsyncClient,
    es_endpoint: str,
    api_key: str,
    index: str,
    prop_name: str,
    version: str,
    description: str,
    description_vector: list[float],
) -> tuple[str, bool, str]:
    body = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"prop_name": prop_name}},
                    {"term": {"release_tag": version}},
                ]
            }
        },
        "script": {
            "source": (
                "ctx._source.description = params.desc; "
                "ctx._source.description_vector = params.vec;"
            ),
            "params": {"desc": description, "vec": description_vector},
        },
    }
    r = await http.post(
        f"{es_endpoint.rstrip('/')}/{index}/_update_by_query?refresh=true",
        json=body,
        headers={"Authorization": f"ApiKey {api_key}"},
    )
    if r.status_code != 200:
        return prop_name, False, f"HTTP {r.status_code}: {r.text[:200]}"
    body = r.json()
    updated = body.get("updated", 0)
    if updated == 0:
        return prop_name, False, "no docs matched (prop+version not in index?)"
    return prop_name, True, f"updated {updated}"


async def run(version: str, descriptions_file: Path) -> int:
    cfg = EsConfig(
        endpoint=os.environ["ELASTICSEARCH_ENDPOINT"],
        api_key=os.environ["ELASTICSEARCH_VECTOR_DB_API_KEY"],
    )
    es = EsClient(cfg)

    raw = json.loads(descriptions_file.read_text())
    descriptions = {k: v for k, v in raw.items() if not k.startswith("_")}
    log.info("loaded %d descriptions from %s", len(descriptions), descriptions_file)

    prop_names = list(descriptions.keys())
    texts = [descriptions[p] for p in prop_names]

    log.info("embedding %d descriptions via jina text inference", len(texts))
    vectors: list[list[float]] = []
    # EIS caps `input` at 16 items per call, so any larger batch HTTP-400s.
    batch = 16
    for i in range(0, len(texts), batch):
        chunk = texts[i : i + batch]
        vecs = await es.embed_texts(chunk)
        if len(vecs) != len(chunk):
            log.error(
                "embedding count mismatch: requested %d got %d", len(chunk), len(vecs)
            )
            await es.aclose()
            return 1
        vectors.extend(vecs)
        log.info("embedded %d/%d", i + len(chunk), len(texts))

    timeout = httpx.Timeout(60.0)
    async with httpx.AsyncClient(timeout=timeout) as http:
        try:
            ok = 0
            failed: list[tuple[str, str]] = []
            for prop, text, vec in zip(prop_names, texts, vectors):
                p, success, detail = await update_doc(
                    http,
                    cfg.endpoint,
                    cfg.api_key,
                    cfg.index_name,
                    prop,
                    version,
                    text,
                    vec,
                )
                if success:
                    ok += 1
                    log.info("ok %s — %s", p, detail)
                else:
                    failed.append((p, detail))
                    log.warning("FAILED %s — %s", p, detail)
        finally:
            await es.aclose()

    log.info("done: %d updated, %d failed", ok, len(failed))
    return 0 if not failed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--version", default="v115.0.0")
    parser.add_argument(
        "--descriptions",
        type=Path,
        default=REPO_ROOT / "descriptions" / "v115.0.0_seed.json",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    return asyncio.run(run(args.version, args.descriptions))


if __name__ == "__main__":
    sys.exit(main())
