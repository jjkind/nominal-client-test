#!/usr/bin/env bash
set -euo pipefail

# Checks current Loki delete requests.
# Run this from the project root.

if [ ! -f ".env" ]; then
  echo "Missing .env file. Run this script from the project root."
  exit 1
fi

set -a
source .env
set +a

: "${GRAFANA_LOKI_PUSH_URL:?Missing GRAFANA_LOKI_PUSH_URL in .env}"
: "${GRAFANA_LOKI_USER:?Missing GRAFANA_LOKI_USER in .env}"
: "${GRAFANA_LOKI_DELETE_TOKEN:?Missing GRAFANA_LOKI_DELETE_TOKEN in .env}"

LOKI_BASE_URL="${GRAFANA_LOKI_PUSH_URL%/loki/api/v1/push}"
DELETE_URL="$LOKI_BASE_URL/loki/api/v1/delete"

echo "Checking Loki delete requests..."
echo "Delete URL: $DELETE_URL"
echo

RESPONSE="$(curl -sS "$DELETE_URL" \
  -u "$GRAFANA_LOKI_USER:$GRAFANA_LOKI_DELETE_TOKEN")"

COMPACT_RESPONSE="$(printf '%s' "$RESPONSE" | tr -d '[:space:]')"

if [ -z "$COMPACT_RESPONSE" ] || [ "$COMPACT_RESPONSE" = "null" ] || [ "$COMPACT_RESPONSE" = "[]" ]; then
  echo "No active Loki delete requests found."
  exit 0
fi

echo "Active Loki delete requests:"
echo

if command -v jq >/dev/null 2>&1; then
  echo "$RESPONSE" | jq .
else
  echo "$RESPONSE"
fi
```
