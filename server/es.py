"""Elasticsearch client for the search server.

Intentionally separate from ingester/es_client.py — the server only needs
inference embedding and kNN search, not bulk indexing or retries.
"""

from __future__ import annotations

import base64

import httpx


class SearchClient:
    def __init__(self, endpoint: str, api_key: str, index: str, inference_id: str):
        self._http = httpx.AsyncClient(
            base_url=endpoint.rstrip("/"),
            headers={
                "Authorization": f"ApiKey {api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        self.index = index
        self.inference_id = inference_id

    async def aclose(self) -> None:
        await self._http.aclose()

    async def embed_text(self, text: str) -> list[float]:
        r = await self._http.post(
            f"/_inference/embedding/{self.inference_id}",
            json={"input": [text]},
        )
        r.raise_for_status()
        return r.json()["embeddings"][0]["embedding"]

    async def embed_image(self, png: bytes) -> list[float]:
        b64 = base64.b64encode(png).decode()
        r = await self._http.post(
            f"/_inference/embedding/{self.inference_id}",
            json={"input": [{
                "content": [{
                    "type": "image",
                    "format": "base64",
                    "value": f"data:image/png;base64,{b64}",
                }]
            }]},
        )
        r.raise_for_status()
        return r.json()["embeddings"][0]["embedding"]

    async def knn_search(
        self,
        vector: list[float],
        field: str,
        k: int = 100,
        version: str | None = None,
        limit: int = 12,
    ) -> list[dict]:
        knn: dict = {
            "field": field,
            "query_vector": vector,
            "k": k,
            "num_candidates": k * 2,
        }
        if version:
            knn["filter"] = {"term": {"release_tag": version}}

        r = await self._http.post(
            f"/{self.index}/_search",
            json={"knn": knn, "_source": ["prop_name", "release_tag"], "size": k},
        )
        r.raise_for_status()

        # Deduplicate by prop_name — multiple versions may match; keep highest score.
        seen: dict[str, dict] = {}
        for hit in r.json()["hits"]["hits"]:
            name = hit["_source"]["prop_name"]
            score = hit["_score"]
            if name not in seen or score > seen[name]["score"]:
                seen[name] = {
                    "prop_name": name,
                    "version": hit["_source"]["release_tag"],
                    "score": score,
                }

        ranked = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
        return ranked[:limit]

    async def indexed_versions(self) -> list[str]:
        r = await self._http.post(
            f"/{self.index}/_search",
            json={
                "size": 0,
                "aggs": {"versions": {"terms": {"field": "release_tag", "size": 50}}},
            },
        )
        r.raise_for_status()
        buckets = r.json()["aggregations"]["versions"]["buckets"]
        return sorted(b["key"] for b in buckets)
