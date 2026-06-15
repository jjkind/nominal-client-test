#!/usr/bin/env bash
set -euo pipefail

# Deletes Loki logs from the start of the current year through now.
# The Loki delete API uses "now" as the default end time when no end parameter is sent.

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

START_OF_YEAR="$(date -u +"%Y-01-01T00:00:00Z")"

# Loki delete requires a LogQL selector.
# This default deletes all streams that have an app label.
# Override it like:
#
#   LOKI_DELETE_QUERY='{app="fsae-telemetry"}' ./scripts/loki_delete.sh
#
if [ -n "${LOKI_DELETE_QUERY:-}" ]; then
  DELETE_QUERY="$LOKI_DELETE_QUERY"
else
  DELETE_QUERY='{app=~".+"}'
fi

echo "Preparing Loki delete request..."
echo "Loki base URL: $LOKI_BASE_URL"
echo "Delete URL:     $DELETE_URL"
echo "Delete query:  $DELETE_QUERY"
echo "Start time:    $START_OF_YEAR"
echo "End time:      now/default"
echo

read -r -p "This will delete matching Loki logs. Continue? Type DELETE to continue: " CONFIRM

if [ "$CONFIRM" != "DELETE" ]; then
  echo "Aborted."
  exit 0
fi

echo
echo "Submitting delete request..."

curl -sS -v -G -X POST "$DELETE_URL" \
  -u "$GRAFANA_LOKI_USER:$GRAFANA_LOKI_DELETE_TOKEN" \
  --data-urlencode "query=$DELETE_QUERY" \
  --data-urlencode "start=$START_OF_YEAR"

echo
echo
echo "Waiting 10 seconds before checking delete requests..."
sleep 10

POLL_INTERVAL_SECONDS="${LOKI_DELETE_POLL_INTERVAL_SECONDS:-10}"
MAX_CHECKS="${LOKI_DELETE_MAX_CHECKS:-60}"

echo
echo "Checking Loki delete requests until none remain..."
echo "Poll interval: ${POLL_INTERVAL_SECONDS}s"
echo "Max checks:    $MAX_CHECKS"
echo

for CHECK_NUMBER in $(seq 1 "$MAX_CHECKS"); do
  echo "Check $CHECK_NUMBER/$MAX_CHECKS..."

  RESPONSE="$(curl -sS "$DELETE_URL" \
    -u "$GRAFANA_LOKI_USER:$GRAFANA_LOKI_DELETE_TOKEN")"

  # Remove whitespace so we can reliably compare empty/null/[] responses.
  COMPACT_RESPONSE="$(printf '%s' "$RESPONSE" | tr -d '[:space:]')"

  if [ -z "$COMPACT_RESPONSE" ] || [ "$COMPACT_RESPONSE" = "null" ] || [ "$COMPACT_RESPONSE" = "[]" ]; then
    echo "No Loki delete requests remain."
    echo
    echo "Done."
    exit 0
  fi

  echo "Delete requests still present:"
  echo "$RESPONSE"
  echo

  if [ "$CHECK_NUMBER" -lt "$MAX_CHECKS" ]; then
    echo "Waiting ${POLL_INTERVAL_SECONDS}s before checking again..."
    sleep "$POLL_INTERVAL_SECONDS"
    echo
  fi
done

echo "Timed out waiting for Loki delete requests to clear."
echo "Last response:"
echo "$RESPONSE"
exit 1
```
