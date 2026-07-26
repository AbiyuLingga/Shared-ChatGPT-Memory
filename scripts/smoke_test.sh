#!/usr/bin/env bash
set -euo pipefail
: "${SMOKE_TOKEN:?Set SMOKE_TOKEN to the configured Action API key}"
base_url="${SMOKE_BASE_URL:-http://localhost:8000}"
curl --fail --silent "$base_url/health" >/dev/null
curl --fail --silent -X POST "$base_url/v1/memories/search" \
  -H "Authorization: Bearer $SMOKE_TOKEN" -H 'Content-Type: application/json' \
  --data '{"query":"smoke marker"}' >/dev/null
echo "Basic authenticated smoke checks passed. Use the manual checklist for add/update/delete."
