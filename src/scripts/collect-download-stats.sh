#!/bin/bash

# Collect one UTC day of per-path download statistics for data.clinvar-gkm.org.
#
# Queries Cloudflare GraphQL Analytics (httpRequestsAdaptiveGroups) for the zone and
# writes one CSV row per (path, status):
#
#   date,path,status,requests,bytes,distinct_clients
#
# Privacy: client IPs are fetched only to count distinct clients per row. They are
# held in memory, never written to disk, the CSV, BigQuery or the log.
#
# The Free plan keeps about 31 days ("4w3d") of data, so a day older than that cannot
# be collected. Counts come from Cloudflare's adaptive sampling and are estimates.
#
# Credentials (never printed): CF_ANALYTICS_TOKEN (Zone > Analytics > Read on
# clinvar-gkm.org) and CF_ZONE_ID, from the environment (CI) or, when either is unset,
# from ${CF_ENV_FILE:-~/.config/clinvar-gkm/cloudflare.env}.
# Optional CF_EXCLUDE_IPS: comma- or space-separated IPs to leave out (maintainers).
#
# Usage:
#   ./collect-download-stats.sh [--date YYYY-MM-DD] [--out FILE] [--bq]
#
#   --date  UTC day to collect (default: yesterday, UTC)
#   --out   CSV path (default: ./download-stats_<date>.csv)
#   --bq    also load the rows into ${BQ_TABLE:-clingen-dev:clinvar_ingest.gkm_download_stats},
#           creating the table if needed and replacing any rows already loaded for that date

set -euo pipefail

HOST="data.clinvar-gkm.org"
GRAPHQL_URL="https://api.cloudflare.com/client/v4/graphql"
LIMIT=9999
RETENTION_DAYS=31
BQ_TABLE="${BQ_TABLE:-clingen-dev:clinvar_ingest.gkm_download_stats}"

usage() {
  echo "Usage: $0 [--date YYYY-MM-DD] [--out FILE] [--bq]" >&2
  exit 1
}

# --- Portable date helpers (GNU date on CI, BSD date on macOS) ---
is_gnu_date() { date --version >/dev/null 2>&1; }

# date_shift YYYY-MM-DD +N|-N  -> YYYY-MM-DD
date_shift() {
  if is_gnu_date; then
    date -u -d "$1 $2 day" +%F
  else
    date -u -j -v"$2"d -f %Y-%m-%d "$1" +%F
  fi
}

# date_epoch YYYY-MM-DD -> seconds at 00:00:00 UTC
date_epoch() {
  if is_gnu_date; then
    date -u -d "$1" +%s
  else
    date -u -j -f "%Y-%m-%d %H:%M:%S" "$1 00:00:00" +%s
  fi
}

# --- Parse flags ---
DAY=""
OUT=""
LOAD_BQ=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --date) [[ $# -ge 2 ]] || usage; DAY="$2"; shift 2 ;;
    --date=*) DAY="${1#--date=}"; shift ;;
    --out) [[ $# -ge 2 ]] || usage; OUT="$2"; shift 2 ;;
    --out=*) OUT="${1#--out=}"; shift ;;
    --bq) LOAD_BQ=true; shift ;;
    -h|--help) usage ;;
    *) echo "ERROR: unknown argument '$1'" >&2; usage ;;
  esac
done

TODAY="$(date -u +%F)"
[[ -n "$DAY" ]] || DAY="$(date_shift "$TODAY" -1)"
if [[ ! "$DAY" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  echo "ERROR: --date must be YYYY-MM-DD (got '${DAY}')" >&2; exit 1
fi
if [[ ! "$DAY" < "$TODAY" ]]; then
  echo "ERROR: ${DAY} is not a complete UTC day yet (today is ${TODAY})" >&2; exit 1
fi
AGE_DAYS=$(( ( $(date_epoch "$TODAY") - $(date_epoch "$DAY") ) / 86400 ))
if (( AGE_DAYS > RETENTION_DAYS )); then
  echo "ERROR: ${DAY} is ${AGE_DAYS} days ago; Cloudflare keeps about ${RETENTION_DAYS} days" >&2; exit 1
fi
NEXT_DAY="$(date_shift "$DAY" +1)"
[[ -n "$OUT" ]] || OUT="./download-stats_${DAY}.csv"

# --- Credentials ---
if [[ -z "${CF_ANALYTICS_TOKEN:-}" || -z "${CF_ZONE_ID:-}" ]]; then
  ENV_FILE="${CF_ENV_FILE:-${HOME}/.config/clinvar-gkm/cloudflare.env}"
  if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    . "$ENV_FILE"
  fi
fi
if [[ -z "${CF_ANALYTICS_TOKEN:-}" || -z "${CF_ZONE_ID:-}" ]]; then
  echo "ERROR: CF_ANALYTICS_TOKEN and CF_ZONE_ID must be set (environment or env file)" >&2; exit 1
fi

# JSON array of IPs to exclude; empty array = exclude nothing.
EXCLUDE_JSON="$(printf '%s' "${CF_EXCLUDE_IPS:-}" | tr -s ', ' '\n' | jq -R . | jq -sc 'map(select(length > 0))')"

# GraphQL variables ($z, $a, ...) are literal, not shell expansions.
# shellcheck disable=SC2016
QUERY='query($z:String!,$a:Time!,$b:Time!,$x:[string]){viewer{zones(filter:{zoneTag:$z}){httpRequestsAdaptiveGroups(limit:'"${LIMIT}"',filter:{datetime_geq:$a,datetime_lt:$b,clientRequestHTTPHost:"'"${HOST}"'",clientIP_notin:$x}){count sum{edgeResponseBytes} dimensions{clientRequestPath edgeResponseStatus clientIP}}}}}'

# fetch_groups FROM TO -> JSON array of raw groups (includes clientIP; stdout only).
# The token goes to curl on stdin (-K -), so it never appears in the process list.
fetch_groups() {
  local from="$1" to="$2" body resp errors
  body="$(jq -nc --arg q "$QUERY" --arg z "$CF_ZONE_ID" --arg a "$from" --arg b "$to" \
    --argjson x "$EXCLUDE_JSON" '{query:$q, variables:{z:$z, a:$a, b:$b, x:$x}}')"
  resp="$(printf 'header = "Authorization: Bearer %s"\n' "$CF_ANALYTICS_TOKEN" \
    | curl -sS --fail-with-body -K - -H 'Content-Type: application/json' \
        --data "$body" "$GRAPHQL_URL")" || {
    echo "ERROR: Cloudflare GraphQL request failed" >&2; return 1; }
  errors="$(jq -r '(.errors // [])[] | .message' <<< "$resp")"
  if [[ -n "$errors" ]]; then
    # Error messages can quote the zone id; redact it.
    echo "ERROR: Cloudflare GraphQL: ${errors//${CF_ZONE_ID}/<zone>}" >&2
    return 1
  fi
  jq -c '.data.viewer.zones[0].httpRequestsAdaptiveGroups // []' <<< "$resp"
}

echo "--- Collecting ${HOST} downloads for ${DAY} (UTC) ---" >&2
GROUPS_JSON="$(fetch_groups "${DAY}T00:00:00Z" "${NEXT_DAY}T00:00:00Z")"

# A full page means the day had more groups than one query returns: re-query by hour.
if [[ "$(jq 'length' <<< "$GROUPS_JSON")" -ge "$LIMIT" ]]; then
  echo "  ${LIMIT}+ groups for the day; querying hour by hour" >&2
  GROUPS_JSON="[]"
  for h in 00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23; do
    if [[ "$h" == "23" ]]; then
      to="${NEXT_DAY}T00:00:00Z"
    else
      to="${DAY}T$(printf '%02d' $((10#$h + 1))):00:00Z"
    fi
    hour_json="$(fetch_groups "${DAY}T${h}:00:00Z" "$to")"
    if [[ "$(jq 'length' <<< "$hour_json")" -ge "$LIMIT" ]]; then
      echo "ERROR: hour ${h} alone returned ${LIMIT}+ groups; results would be truncated" >&2; exit 1
    fi
    GROUPS_JSON="$(jq -c --argjson h "$hour_json" '. + $h' <<< "$GROUPS_JSON")"
  done
fi

# Aggregate to (path, status). clientIP is used only inside this jq program.
{
  echo "date,path,status,requests,bytes,distinct_clients"
  jq -r --arg d "$DAY" '
    group_by([.dimensions.clientRequestPath, .dimensions.edgeResponseStatus])
    | map({
        path: .[0].dimensions.clientRequestPath,
        status: .[0].dimensions.edgeResponseStatus,
        requests: (map(.count) | add),
        bytes: (map(.sum.edgeResponseBytes) | add),
        clients: (map(.dimensions.clientIP) | unique | length)
      })
    | sort_by(.path, .status)[]
    | [$d, .path, .status, .requests, .bytes, .clients] | @csv' <<< "$GROUPS_JSON"
} > "$OUT"
GROUPS_JSON=""

ROWS=$(( $(wc -l < "$OUT") - 1 ))
TOTALS="$(awk -F, 'NR > 1 {r += $4; b += $5} END {printf "%d requests, %.2f GB", r, b / 1e9}' "$OUT")"
echo "  wrote ${OUT}: ${ROWS} rows, ${TOTALS}" >&2

# --- Optional BigQuery load ---
if $LOAD_BQ; then
  BQ_PROJECT="${BQ_TABLE%%:*}"
  BQ_SQL_TABLE="${BQ_TABLE/:/.}"
  echo "--- Loading into ${BQ_TABLE} ---" >&2
  if ! bq --project_id="$BQ_PROJECT" show "$BQ_TABLE" >/dev/null 2>&1; then
    bq --project_id="$BQ_PROJECT" mk --table \
      --description "Daily per-path download counts for ${HOST} (collect-download-stats.sh). No IPs." \
      "$BQ_TABLE" \
      date:DATE,path:STRING,status:INTEGER,requests:INTEGER,bytes:INTEGER,distinct_clients:INTEGER
  fi
  # Re-running a day replaces its rows instead of duplicating them.
  bq --project_id="$BQ_PROJECT" query --use_legacy_sql=false --quiet \
    "DELETE FROM \`${BQ_SQL_TABLE}\` WHERE date = DATE '${DAY}'" >/dev/null
  if (( ROWS > 0 )); then
    bq --project_id="$BQ_PROJECT" load --source_format=CSV --skip_leading_rows=1 \
      "$BQ_TABLE" "$OUT"
  fi
  echo "  loaded ${ROWS} rows for ${DAY}" >&2
fi
