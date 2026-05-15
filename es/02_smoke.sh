#!/usr/bin/env bash
# End-to-end smoke test:
#   1. Embed a known phrase via the inference endpoint.
#   2. Index a fake doc with that vector.
#   3. Run a kNN search using the same query vector.
#   4. Assert the fake doc comes back as the top hit.
#
# Cleans up the fake doc on success.

source "$(dirname "$0")/_lib.sh"

SMOKE_DOC_ID="__smoke@__"
QUERY="search icon"

log "embedding query via $INFERENCE_ID"
EMBED_BODY=$(printf '{"input":[%s]}' "$(printf '%s' "$QUERY" | python3 -c 'import sys, json; print(json.dumps(sys.stdin.read()))')")
EMBED_RESP=$(es_post "/_inference/embedding/$INFERENCE_ID" --data-binary "$EMBED_BODY")
VEC=$(echo "$EMBED_RESP" | python3 -c 'import sys, json; print(json.dumps(json.load(sys.stdin)["embeddings"][0]["embedding"]))')
DIM=$(echo "$VEC" | python3 -c 'import sys, json; print(len(json.load(sys.stdin)))')
[ "$DIM" = "1024" ] || die "expected 1024 dims, got $DIM"
ok "embedded query as ${DIM}-dim vector"

log "indexing fake smoke doc"
DOC=$(python3 -c "
import json, sys, os
vec = json.loads('$VEC')
print(json.dumps({
  'prop_name': '__smoke',
  'release_tag': '__',
  'release_major': 0,
  'image_vector': vec,
  'name_vector': vec,
}))
")
es_put "/$INDEX_NAME/_doc/$SMOKE_DOC_ID?refresh=wait_for" --data-binary "$DOC" >/dev/null
ok "indexed $SMOKE_DOC_ID"

log "running kNN over name_vector"
SEARCH_BODY=$(python3 -c "
import json
print(json.dumps({
  'knn': {
    'field': 'name_vector',
    'query_vector': json.loads('$VEC'),
    'k': 5,
    'num_candidates': 50
  },
  'fields': ['prop_name'],
  '_source': False
}))
")
SEARCH_RESP=$(es_post "/$INDEX_NAME/_search" --data-binary "$SEARCH_BODY")
TOP_NAME=$(echo "$SEARCH_RESP" | python3 -c 'import sys, json; d=json.load(sys.stdin); h=d["hits"]["hits"]; print(h[0]["fields"]["prop_name"][0] if h else "")')
[ "$TOP_NAME" = "__smoke" ] || die "expected top hit prop_name=__smoke, got '$TOP_NAME'. Full hits: $SEARCH_RESP"
ok "kNN top hit is __smoke (self-match) — pipeline is wired end-to-end"

log "cleaning up smoke doc"
es_delete "/$INDEX_NAME/_doc/$SMOKE_DOC_ID?refresh=wait_for" >/dev/null
ok "smoke complete"
