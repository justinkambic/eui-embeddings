#!/usr/bin/env bash
# Shared helpers for es/*.sh scripts. Source me, don't run me.

set -euo pipefail

# Load .env from repo root (one level up from es/).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [ -f "$REPO_ROOT/.env" ]; then
  set -o allexport
  # shellcheck source=/dev/null
  . "$REPO_ROOT/.env"
  set +o allexport
fi

: "${ELASTICSEARCH_ENDPOINT:?ELASTICSEARCH_ENDPOINT not set in .env}"
: "${ELASTICSEARCH_VECTOR_DB_API_KEY:?ELASTICSEARCH_VECTOR_DB_API_KEY not set in .env}"

ES_BASE="${ELASTICSEARCH_ENDPOINT%/}"
ES_AUTH="Authorization: ApiKey $ELASTICSEARCH_VECTOR_DB_API_KEY"

# Names used across scripts. Keep in sync with revamp-plan.md §3.1.
INFERENCE_ID="${INFERENCE_ID:-eui-icon-encoder}"
INDEX_NAME="${INDEX_NAME:-eui_icons}"

# Wrappers around curl that fail loudly. Pass path + optional curl args.
es_get()    { curl -sS -fS -X GET    -H "$ES_AUTH" "$ES_BASE$1" "${@:2}"; }
es_put()    { curl -sS -fS -X PUT    -H "$ES_AUTH" -H "Content-Type: application/json" "$ES_BASE$1" "${@:2}"; }
es_post()   { curl -sS -fS -X POST   -H "$ES_AUTH" -H "Content-Type: application/json" "$ES_BASE$1" "${@:2}"; }
es_delete() { curl -sS    -X DELETE -H "$ES_AUTH" "$ES_BASE$1" "${@:2}"; }
es_head()   { curl -sS -o /dev/null -w "%{http_code}" -X HEAD -H "$ES_AUTH" "$ES_BASE$1"; }

log() { printf "\033[1;36m[es]\033[0m %s\n" "$*" >&2; }
ok()  { printf "\033[1;32m[ok]\033[0m %s\n"  "$*" >&2; }
die() { printf "\033[1;31m[err]\033[0m %s\n" "$*" >&2; exit 1; }
