#!/usr/bin/env bash
# Create (idempotent) the multimodal embedding inference endpoint backed by
# jina-clip-v2 via Elastic Inference Service.
#
# If the endpoint already exists we validate it matches what we expect; if
# it diverges, we delete and recreate.

source "$(dirname "$0")/_lib.sh"

BODY_FILE="$(dirname "$0")/inference_endpoint.json"
[ -f "$BODY_FILE" ] || die "missing $BODY_FILE"

PATH_BASE="/_inference/embedding/$INFERENCE_ID"

EXISTING="$(es_get "$PATH_BASE" 2>/dev/null || true)"

if [ -n "$EXISTING" ] && echo "$EXISTING" | grep -q '"task_type"'; then
  log "endpoint $INFERENCE_ID exists; checking model_id..."
  MODEL_ID="$(echo "$EXISTING" | python3 -c 'import sys,json; print(json.load(sys.stdin)["endpoints"][0]["service_settings"]["model_id"])' 2>/dev/null \
            || echo "$EXISTING" | python3 -c 'import sys,json; print(json.load(sys.stdin)["service_settings"]["model_id"])' 2>/dev/null \
            || echo "")"
  if [ "$MODEL_ID" = "jina-clip-v2" ]; then
    ok "endpoint $INFERENCE_ID already correctly configured (model_id=$MODEL_ID)"
    exit 0
  fi
  log "endpoint exists but model_id=$MODEL_ID; recreating"
  es_delete "$PATH_BASE" >/dev/null
fi

log "creating $INFERENCE_ID with jina-clip-v2 via EIS"
es_put "$PATH_BASE" --data-binary "@$BODY_FILE" >/dev/null
ok "created $INFERENCE_ID"
