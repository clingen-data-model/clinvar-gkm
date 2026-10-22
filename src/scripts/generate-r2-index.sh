#!/bin/bash
# Regenerate a version line's index.json + feed.xml, and the bucket-root index.json, from the CURRENT R2 state.
#
# Called by every uploader, so the published index is consistent whichever ran last. The layout and the JSON
# shape are defined in r2_layout.py (see its docstring). Per line (<line>index.json):
#   monthly        official monthlies, each with sha256 (from its .sha256 sidecar) and source_release, the weekly
#                  release it was built from (ADR 0002); latest = the 00-latest copy and which monthly it equals
#   weekly         the current month's weekly fulls + the 00-latest_weekly copy
#   deltas         every delta of the current year (current month at deltas/, earlier months in deltas/YYYY-MM/)
#   archive        prior years: monthlies and deltas
#   parquet        the one Parquet set, from parquet/manifest.json
# The root index.json lists the version lines (status, schema, superseded_by, index, feed).
#
# source_release is not in the bundle, so the generator carries it forward from the line's previous index.json;
# an uploader that posts a monthly passes --source YYYY-MM=YYYY-MM-DD for it (republish passes the whole table).
#
# Usage:
#   ./generate-r2-index.sh [--dry-run] [--line v1/1.1/] [--source YYYY-MM=YYYY-MM-DD]... [--no-root]
#   ./generate-r2-index.sh --listing FILE [--sidecars DIR] ...   # offline, from a saved listing; implies --dry-run
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LINE_ARG=""; LISTING=""; SIDECARS=""; NO_ROOT=false; SOURCES=()
DRY_RUN=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --line) LINE_ARG="$2"; shift 2 ;;
    --line=*) LINE_ARG="${1#*=}"; shift ;;
    --source) SOURCES+=(--source "$2"); shift 2 ;;
    --source=*) SOURCES+=(--source "${1#*=}"); shift ;;
    --listing) LISTING="$2"; DRY_RUN=true; shift 2 ;;
    --sidecars) SIDECARS="$2"; shift 2 ;;
    --no-root) NO_ROOT=true; shift ;;
    *) echo "ERROR: unknown argument '$1'" >&2; exit 1 ;;
  esac
done
export DRY_RUN
# shellcheck source=r2-common.sh
. "${SCRIPT_DIR}/r2-common.sh"
[[ -n "${LINE_ARG}" ]] && R2_LINE="${LINE_ARG}"
[[ "${R2_LINE}" == */ ]] || R2_LINE="${R2_LINE}/"
SCHEMA_VERSION="${SCHEMA_VERSION:-$(sed -n 's/^SCHEMA_VERSION = "\(.*\)"$/\1/p' "${SCRIPT_DIR}/assemble-gkm-dicts.py")}"

TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

echo "--- Generating ${R2_LINE}index.json + ${R2_LINE}feed.xml$(${NO_ROOT} || echo ' + root index.json') ---"
if [[ -n "${LISTING}" ]]; then
  cp "${LISTING}" "${TMP}/listing.txt"
else
  r2_listing "${R2_LINE}" "${TMP}/listing.txt"
  SIDECARS="${TMP}/mirror"
  r2_mirror_small "${R2_LINE}" "${SIDECARS}"
fi

r2_layout index --listing "${TMP}/listing.txt" --line "${R2_LINE}" ${SIDECARS:+--sidecars "${SIDECARS}"} \
  --schema-version "${SCHEMA_VERSION}" --out-index "${TMP}/index.json" --out-feed "${TMP}/feed.xml" \
  "${SOURCES[@]+"${SOURCES[@]}"}"
r2_layout root --schema-version "${SCHEMA_VERSION}" --out "${TMP}/root.json"

r2_put "${TMP}/index.json" "${R2_LINE}index.json" "application/json"
r2_put "${TMP}/feed.xml" "${R2_LINE}feed.xml" "application/atom+xml"
${NO_ROOT} || r2_put "${TMP}/root.json" "index.json" "application/json"

if ${DRY_RUN}; then
  KEEP="${INDEX_OUT_DIR:-${TMPDIR:-/tmp}/clinvar-gkm-index-dry-run}/${R2_LINE}"
  mkdir -p "${KEEP}"
  cp "${TMP}/index.json" "${TMP}/feed.xml" "${KEEP}"
  cp "${TMP}/root.json" "${KEEP%"${R2_LINE}"}root-index.json"
  echo "  [dry-run] generated files kept in ${KEEP}"
fi
