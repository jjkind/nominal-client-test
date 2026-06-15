#!/usr/bin/env bash
set -euo pipefail

# Cancels all active Loki delete requests.
# Run from the project root.
#
# Optional:
#   FORCE_LOKI_DELETE_CANCEL=true ./scripts/loki_delete_cancel_all.sh
#
# Use force=true only if Loki says the request is already partially processed
# and you still want to cancel the remaining work.

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

echo "Checking active Loki delete requests..."
echo "Delete URL: $DELETE_URL"
echo

RESPONSE_FILE="$(mktemp)"

HTTP_STATUS="$(
  curl -sS -o "$RESPONSE_FILE" -w "%{http_code}" "$DELETE_URL" \
    -u "$GRAFANA_LOKI_USER:$GRAFANA_LOKI_DELETE_TOKEN"
)"

if [ "$HTTP_STATUS" != "200" ]; then
  echo "Failed to list Loki delete requests."
  echo "HTTP status: $HTTP_STATUS"
  echo "Response body:"
  cat "$RESPONSE_FILE"
  echo
  rm -f "$RESPONSE_FILE"
  exit 1
fi

RESPONSE="$(cat "$RESPONSE_FILE")"
rm -f "$RESPONSE_FILE"

COMPACT_RESPONSE="$(printf '%s' "$RESPONSE" | tr -d '[:space:]')"

if [ -z "$COMPACT_RESPONSE" ] || [ "$COMPACT_RESPONSE" = "null" ] || [ "$COMPACT_RESPONSE" = "[]" ]; then
  echo "No active Loki delete requests found."
  exit 0
fi

echo "Active Loki delete requests:"
echo

if command -v jq >/dev/null 2>&1; then
  echo "$RESPONSE" | jq .
  REQUEST_IDS="$(echo "$RESPONSE" | jq -r '.[] | .request_id // empty')"
else
  echo "$RESPONSE"
  echo
  echo "jq not found. Falling back to python3 for request_id parsing..."

  if ! command -v python3 >/dev/null 2>&1; then
    echo "Neither jq nor python3 is available. Cannot parse request IDs."
    exit 1
  fi

  REQUEST_IDS="$(
    python3 -c '
import json
import sys

data = json.load(sys.stdin)
if data is None:
    sys.exit(0)

for item in data:
    request_id = item.get("request_id")
    if request_id:
        print(request_id)
' <<< "$RESPONSE"
  )"
fi

if [ -z "${REQUEST_IDS:-}" ]; then
  echo "No request_id values found in Loki delete response."
  exit 0
fi

echo
echo "The following delete request IDs will be cancelled:"
echo "$REQUEST_IDS"
echo

read -r -p "Type CANCEL to cancel all listed delete requests: " CONFIRM

if [ "$CONFIRM" != "CANCEL" ]; then
  echo "Aborted."
  exit 0
fi

echo

FORCE_QUERY_PARAM=""

if [ "${FORCE_LOKI_DELETE_CANCEL:-false}" = "true" ]; then
  FORCE_QUERY_PARAM="&force=true"
  echo "Force cancellation enabled."
  echo
fi

FAILED_COUNT=0
CANCELLED_COUNT=0

while IFS= read -r REQUEST_ID; do
  if [ -z "$REQUEST_ID" ]; then
    continue
  fi

  echo "Cancelling delete request: $REQUEST_ID"

  CANCEL_RESPONSE_FILE="$(mktemp)"

  CANCEL_HTTP_STATUS="$(
    curl -sS -o "$CANCEL_RESPONSE_FILE" -w "%{http_code}" \
      -X DELETE "${DELETE_URL}?request_id=${REQUEST_ID}${FORCE_QUERY_PARAM}" \
      -u "$GRAFANA_LOKI_USER:$GRAFANA_LOKI_DELETE_TOKEN"
  )"

  if [ "$CANCEL_HTTP_STATUS" = "204" ] || [ "$CANCEL_HTTP_STATUS" = "200" ]; then
    echo "Cancelled: $REQUEST_ID"
    CANCELLED_COUNT=$((CANCELLED_COUNT + 1))
  else
    echo "Failed to cancel: $REQUEST_ID"
    echo "HTTP status: $CANCEL_HTTP_STATUS"

    if [ -s "$CANCEL_RESPONSE_FILE" ]; then
      echo "Response body:"
      cat "$CANCEL_RESPONSE_FILE"
      echo
    fi

    FAILED_COUNT=$((FAILED_COUNT + 1))
  fi

  rm -f "$CANCEL_RESPONSE_FILE"
  echo
done <<< "$REQUEST_IDS"

echo "Cancellation summary:"
echo "Cancelled: $CANCELLED_COUNT"
echo "Failed:    $FAILED_COUNT"
echo

echo "Checking remaining Loki delete requests..."
FINAL_RESPONSE="$(curl -sS "$DELETE_URL" \
  -u "$GRAFANA_LOKI_USER:$GRAFANA_LOKI_DELETE_TOKEN")"

FINAL_COMPACT_RESPONSE="$(printf '%s' "$FINAL_RESPONSE" | tr -d '[:space:]')"

if [ -z "$FINAL_COMPACT_RESPONSE" ] || [ "$FINAL_COMPACT_RESPONSE" = "null" ] || [ "$FINAL_COMPACT_RESPONSE" = "[]" ]; then
  echo "No active Loki delete requests remain."
else
  echo "Remaining Loki delete requests:"
  if command -v jq >/dev/null 2>&1; then
    echo "$FINAL_RESPONSE" | jq .
  else
    echo "$FINAL_RESPONSE"
  fi
fi

if [ "$FAILED_COUNT" -gt 0 ]; then
  exit 1
fi

echo
echo "Done."
```
