#!/usr/bin/env bash
# Create (idempotent) the eui_icons index. If it already exists we leave it
# alone — the ingester writes new docs without depending on a destructive
# re-index.

source "$(dirname "$0")/_lib.sh"

BODY_FILE="$(dirname "$0")/index_mapping.json"
[ -f "$BODY_FILE" ] || die "missing $BODY_FILE"

CODE="$(es_head "/$INDEX_NAME")"
case "$CODE" in
  200)
    ok "index $INDEX_NAME already exists; leaving as-is"
    exit 0
    ;;
  404)
    log "creating $INDEX_NAME"
    es_put "/$INDEX_NAME" --data-binary "@$BODY_FILE" >/dev/null
    ok "created $INDEX_NAME"
    ;;
  *)
    die "unexpected HEAD /$INDEX_NAME response: $CODE"
    ;;
esac
