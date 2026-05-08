#!/usr/bin/env python3
"""Compute the mean image_vector across a version's docs and write it
to disk + populate `image_vector_centered` on every doc.

Mean-centering subtracts the index-wide average vector from every
embedding before kNN. The intuition: jina-clip-v2 produces vectors
that all share a "natural image" component (the average direction
points toward 'this looks like a 256x256 PNG'). Subtracting that
component leaves only the icon-specific direction, which often
discriminates better in retrieval.

Output:
    vectors/<version>_mean.json — the mean vector, used at query time.
    Also updates each indexed doc with `image_vector_centered`.

Usage:
    .venv-mcp/bin/python scripts/compute_mean_center.py --version v115.0.0
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

log = logging.getLogger("compute_mean_center")


async def fetch_all_vectors(
    http: httpx.AsyncClient,
    endpoint: str,
    api_key: str,
    index: str,
    version: str,
) -> list[tuple[str, list[float]]]:
    """Page through every doc for `version` and pull image_vector.

    Returns [(prop_name, vector), ...]. We use a Point In Time + sort
    on prop_name for deterministic pagination.
    """
    body = {
        "size": 200,
        "_source": ["prop_name", "image_vector"],
        "query": {"term": {"release_tag": version}},
        "sort": [{"prop_name": "asc"}],
    }
    out: list[tuple[str, list[float]]] = []
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
            vec = src.get("image_vector")
            if vec is None:
                continue
            out.append((src["prop_name"], vec))
        if len(hits) < body["size"]:
            break
        body["search_after"] = hits[-1]["sort"]
    return out


async def bulk_update_centered(
    http: httpx.AsyncClient,
    endpoint: str,
    api_key: str,
    index: str,
    version: str,
    centered_by_prop: dict[str, list[float]],
) -> tuple[int, int]:
    """Update each doc's image_vector_centered via _update_by_query."""
    ok = 0
    failed = 0
    for prop, centered in centered_by_prop.items():
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
                "source": "ctx._source.image_vector_centered = params.vec;",
                "params": {"vec": centered},
            },
        }
        r = await http.post(
            f"{endpoint.rstrip('/')}/{index}/_update_by_query?refresh=false",
            json=body,
            headers={"Authorization": f"ApiKey {api_key}"},
        )
        if r.status_code != 200:
            log.warning("update failed for %s: %s", prop, r.text[:200])
            failed += 1
            continue
        if r.json().get("updated", 0) == 0:
            log.warning("update matched no docs for %s", prop)
            failed += 1
            continue
        ok += 1
        if ok % 100 == 0:
            log.info("updated %d/%d", ok, len(centered_by_prop))
    return ok, failed


async def run(version: str) -> int:
    endpoint = os.environ["ELASTICSEARCH_ENDPOINT"]
    api_key = os.environ["ELASTICSEARCH_VECTOR_DB_API_KEY"]
    index = os.environ.get("ES_INDEX_NAME", "eui_icons")

    timeout = httpx.Timeout(60.0)
    async with httpx.AsyncClient(timeout=timeout) as http:
        log.info("fetching all image_vectors for %s …", version)
        rows = await fetch_all_vectors(http, endpoint, api_key, index, version)
        if not rows:
            log.error("no docs found for version %s", version)
            return 1
        log.info("got %d vectors", len(rows))

        # Compute mean per dimension. Stay pure-Python to avoid
        # numpy as a hard dep.
        dims = len(rows[0][1])
        sums = [0.0] * dims
        for _, vec in rows:
            for i, v in enumerate(vec):
                sums[i] += v
        n = len(rows)
        mean = [s / n for s in sums]
        log.info("mean vector computed (dims=%d, ||mean||²=%.4f)", dims, sum(m * m for m in mean))

        # Persist the mean for use at query time.
        out_dir = REPO_ROOT / "vectors"
        out_dir.mkdir(exist_ok=True)
        mean_path = out_dir / f"{version}_image_mean.json"
        mean_path.write_text(json.dumps({"version": version, "n_docs": n, "mean": mean}))
        log.info("wrote %s", mean_path)

        # Compute centered vectors and bulk-update.
        centered_by_prop: dict[str, list[float]] = {}
        for prop, vec in rows:
            centered_by_prop[prop] = [v - m for v, m in zip(vec, mean)]
        log.info("backfilling image_vector_centered for %d docs …", len(centered_by_prop))
        ok, failed = await bulk_update_centered(
            http, endpoint, api_key, index, version, centered_by_prop
        )
        log.info("done: updated=%d failed=%d", ok, failed)
        return 0 if failed == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--version", default="v115.0.0")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return asyncio.run(run(args.version))


if __name__ == "__main__":
    sys.exit(main())
