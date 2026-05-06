"""Async Elasticsearch client used by the ingester.

Wraps just what we need: inference embeddings, doc-exists checks, and bulk
indexing. Uses httpx for async HTTP — we deliberately avoid the official
elasticsearch-py client because (a) we only need a few endpoints, (b) httpx
gives us first-class async, and (c) we want to control batching and
concurrency precisely.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import random
from dataclasses import dataclass
from typing import Iterable

import httpx


_log = logging.getLogger("ingester.es_client")


@dataclass(frozen=True)
class EsConfig:
    endpoint: str
    api_key: str
    inference_id: str = "eui-icon-encoder"
    index_name: str = "eui_icons"
    request_timeout_s: float = 120.0
    inference_concurrency: int = 4
    inference_max_retries: int = 5
    inference_retry_base_delay_s: float = 1.0


class EsError(RuntimeError):
    """Raised on non-2xx responses; .body has the parsed response body if any."""

    def __init__(self, message: str, *, status: int | None = None, body: object = None):
        super().__init__(message)
        self.status = status
        self.body = body


_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _backoff(base: float, attempt: int) -> float:
    """Exponential backoff with full jitter."""
    return random.uniform(0, base * (2 ** (attempt - 1)))


class EsClient:
    """Thin async wrapper around the inference + bulk-index endpoints we use."""

    def __init__(self, cfg: EsConfig):
        self.cfg = cfg
        self._client = httpx.AsyncClient(
            base_url=cfg.endpoint.rstrip("/"),
            headers={
                "Authorization": f"ApiKey {cfg.api_key}",
                "Content-Type": "application/json",
            },
            timeout=cfg.request_timeout_s,
            http2=False,
        )
        self._inference_sem = asyncio.Semaphore(cfg.inference_concurrency)

    async def aclose(self) -> None:
        await self._client.aclose()

    # --- inference --------------------------------------------------------

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Batch embed plain text inputs. Uses the shorthand `input: [str, ...]`."""
        if not texts:
            return []
        body = {"input": list(texts)}
        return await self._embed("text", body)

    async def embed_pngs(self, pngs: list[bytes]) -> list[list[float]]:
        """Batch embed PNG byte sequences. Each PNG is base64-encoded and wrapped in
        the structured `content` form that the `elastic` service requires for
        non-text inputs."""
        if not pngs:
            return []
        body = {
            "input": [
                {
                    "content": [
                        {
                            "type": "image",
                            "format": "base64",
                            "value": "data:image/png;base64," + base64.b64encode(png).decode(),
                        }
                    ]
                }
                for png in pngs
            ]
        }
        return await self._embed("image", body)

    async def _embed(self, kind_label: str, body: dict) -> list[list[float]]:
        path = f"/_inference/embedding/{self.cfg.inference_id}"
        attempt = 0
        last_err: Exception | None = None
        async with self._inference_sem:
            while attempt < self.cfg.inference_max_retries:
                attempt += 1
                try:
                    r = await self._client.post(path, json=body)
                except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.RemoteProtocolError) as e:
                    last_err = e
                    delay = _backoff(self.cfg.inference_retry_base_delay_s, attempt)
                    _log.warning(
                        "_inference %s transport error (attempt %d/%d): %s; retrying in %.1fs",
                        kind_label, attempt, self.cfg.inference_max_retries, e, delay,
                    )
                    await asyncio.sleep(delay)
                    continue

                if r.status_code in _RETRYABLE_STATUS:
                    delay = _backoff(self.cfg.inference_retry_base_delay_s, attempt)
                    _log.warning(
                        "_inference %s HTTP %d (attempt %d/%d); retrying in %.1fs",
                        kind_label, r.status_code, attempt, self.cfg.inference_max_retries, delay,
                    )
                    await asyncio.sleep(delay)
                    continue

                if r.status_code >= 400:
                    try:
                        err_body = r.json()
                    except Exception:
                        err_body = r.text
                    raise EsError(
                        f"_inference {kind_label} call failed (HTTP {r.status_code})",
                        status=r.status_code,
                        body=err_body,
                    )

                data = r.json()
                embeddings = data.get("embeddings", [])
                return [e["embedding"] for e in embeddings]

        # Out of retries.
        raise EsError(
            f"_inference {kind_label} call failed after {self.cfg.inference_max_retries} retries",
            body=str(last_err) if last_err else None,
        )

    # --- index ops --------------------------------------------------------

    async def doc_exists(self, doc_id: str) -> bool:
        r = await self._client.head(f"/{self.cfg.index_name}/_doc/{doc_id}")
        if r.status_code == 200:
            return True
        if r.status_code == 404:
            return False
        raise EsError(
            f"unexpected HEAD /{self.cfg.index_name}/_doc/{doc_id}: {r.status_code}",
            status=r.status_code,
        )

    async def bulk_index(self, docs: Iterable[tuple[str, dict]], *, refresh: str = "false") -> dict:
        """Bulk-index `(doc_id, source)` pairs into the configured index.

        Returns the parsed _bulk response. Raises EsError on transport-level
        failures; per-item failures show up under `items[*].error` in the body
        — caller is responsible for inspecting and retrying.
        """
        lines = []
        for doc_id, source in docs:
            lines.append(json.dumps({"index": {"_index": self.cfg.index_name, "_id": doc_id}}))
            lines.append(json.dumps(source))
        if not lines:
            return {"took": 0, "errors": False, "items": []}

        ndjson = "\n".join(lines) + "\n"
        r = await self._client.post(
            "/_bulk",
            params={"refresh": refresh},
            content=ndjson,
            headers={"Content-Type": "application/x-ndjson"},
        )
        if r.status_code >= 400:
            try:
                err_body = r.json()
            except Exception:
                err_body = r.text
            raise EsError(
                f"_bulk failed (HTTP {r.status_code})",
                status=r.status_code,
                body=err_body,
            )
        return r.json()

    async def count(self, query: dict | None = None) -> int:
        """Return the doc count for the configured index, optionally filtered."""
        body: dict = {"query": query} if query else {}
        r = await self._client.post(f"/{self.cfg.index_name}/_count", json=body)
        if r.status_code >= 400:
            try:
                err_body = r.json()
            except Exception:
                err_body = r.text
            raise EsError(f"_count failed (HTTP {r.status_code})", status=r.status_code, body=err_body)
        return r.json().get("count", 0)
