# Phase 0 — Inference path verification

**Date:** 2026-05-06
**Cluster:** v9.4.0 (Elastic Cloud Hosted, build 2e8528e9 from 2026-04-30)
**Outcome:** ✅ Pass. Multimodal `embedding` task type with `jina-clip-v2` works via EIS-bundled `elastic` service. No external Jina API key needed.

## What's available

`GET /_inference/_services` confirms:

- **`elastic` service** supports task types: `text_embedding`, `sparse_embedding`, `rerank`, `completion`, `chat_completion`, **`embedding`**.
  Required setting: `model_id`. No `api_key` required (EIS-bundled).
- **`jinaai` service** supports task types: `text_embedding`, `rerank`, **`embedding`**.
  Required settings: `api_key` (sensitive), `model_id`. Optional: `similarity`, `dimensions`, `embedding_type`, `rate_limit.requests_per_minute`.

We use the `elastic` service throughout (no key plumbing).

## Endpoint configuration

```http
PUT /_inference/embedding/eui-icon-encoder
{
  "service": "elastic",
  "service_settings": { "model_id": "jina-clip-v2" }
}
```

Server returns:
```json
{
  "inference_id": "eui-icon-encoder",
  "task_type": "embedding",
  "service": "elastic",
  "service_settings": {
    "model_id": "jina-clip-v2",
    "similarity": "cosine",
    "dimensions": 1024
  },
  "chunking_settings": { "strategy": "sentence", "max_chunk_size": 250, "sentence_overlap": 1 }
}
```

So defaults are: **1024 dimensions, cosine similarity, sentence chunking.** We don't need to override any of these.

## Request/response shape

### Text (shorthand)
```http
POST /_inference/embedding/eui-icon-encoder
{ "input": ["search icon"] }
```

Returns: `{"embeddings": [{"embedding": [<1024 floats>]}]}`.

### Image (or any multimodal)
```http
POST /_inference/embedding/eui-icon-encoder
{
  "input": [
    {
      "content": [
        { "type": "image", "format": "base64", "value": "data:image/png;base64,<b64>" }
      ]
    }
  ]
}
```

Returns: `{"embeddings": [{"embedding": [<1024 floats>]}]}`.

### Constraint: one item per `content` group

For the `elastic` service, **each `content` array must contain exactly one item**. Mixing text and image into a single content group fails:

```
Field [content] must contain a single item for [elastic] service.
[content] object with multiple items found at $.input.content[1]
```

This means we cannot emit a single fused vector for `"name + rendered image"` per icon in one call. Workaround: two separate `_inference` calls per icon (one text, one image), stored as `name_vector` and `image_vector`. Same for queries.

The `input` array itself can contain multiple groups (each their own embedding). So **batching at the group level is supported**: send N groups in one POST, get N vectors back. We'll batch at index time.

## Implications for the plan

1. **Use `service: "elastic"`, `model_id: "jina-clip-v2"`, defaults otherwise.** No API key, no dimension/similarity override needed.
2. **Two inference calls per doc** — text and image are separate. Already what the plan said; just re-confirmed by the constraint.
3. **Bulk strategy:** the ingester batches a group's worth of (text or image) inputs per POST. Pure-text batches and pure-image batches both work. Reasonable batch size: 32–64 items (TBD by latency profiling in Phase 3).
4. **The `text_embedding` shorthand `"input": ["..."]` works** — can use it for text-only batches without the structured form.

## Source references

- `~/git/justinkambic/elasticsearch/server/src/main/java/org/elasticsearch/inference/InferenceStringGroup.java` — defines the `content` field and the per-group structure. The doc comment in this file is the canonical example of the multimodal shape:
  ```
  "input": {
    "content": [
      {"type": "text", "format": "text", "value": "text input"},
      {"type": "image", "format": "base64", "value": "data:image/png;base64,..."}
    ]
  }
  ```
  (The two-items-per-content example in the source comment is for providers that *do* support fused multi-input groups; the `elastic` service rejects it.)
- `~/git/justinkambic/elasticsearch/server/src/main/java/org/elasticsearch/inference/InferenceString.java` — defines `type ∈ {text, image}` and `format ∈ {text, base64}`.

## Status

Phase 0 ✅ pass. Proceeding to Phase 1 (repo cleanup + skeleton).
