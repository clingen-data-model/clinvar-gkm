#!/bin/bash

# Backfill a historical monthly ClinVar-GKM release to Cloudflare R2.
#
# Use this script to upload past monthly releases that were not captured
# by the normal pipeline. It uploads directly to the monthly destination
# without updating the 00-latest pointer.
#
# Destination is derived from the export year vs. the current calendar year (all under v1/):
#   Current year:  v1/datasets/clinvar-gkm_{YYYY}-{MM}.json.gz
#   Prior year:    v1/archives/{YYYY}/clinvar-gkm_{YYYY}-{MM}.json.gz
#
# No Parquet: Parquet is derived and published only as the single latest set (ADR 0008), never per month.
#
# The 00-latest pointers are NOT updated — this is a backfill, not the
# most recent release. Run the normal upload-gkm-to-r2.sh for current releases.
#
# Usage:
#   ./backfill-monthly-to-r2.sh <export_date> <dataset_version> <bundle_file> [--dry-run] [--purge]
#
# Examples:
#   ./backfill-monthly-to-r2.sh 2026-03-29 v2_5_0 /tmp/clinvar-gkm-2026-03-29.json.gz
#   ./backfill-monthly-to-r2.sh 2025-11-28 v2_4_0 /tmp/clinvar-gkm-2025-11-28.json.gz --dry-run

set -e

# --- Positional arguments ---
if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <export_date> <dataset_version> <bundle_file> [--dry-run] [--purge]"
  echo "  export_date      ClinVar release date (YYYY-MM-DD)"
  echo "  dataset_version  Dataset version (e.g. v2_5_0)"
  echo "  bundle_file      Local path to the assembled bundle (.json.gz)"
  exit 1
fi

EXPORT_DATE="$1"
DATASET_VERSION="$2"
BUNDLE_FILE="$3"
shift 3

# Validate date format
if ! [[ "$EXPORT_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  echo "ERROR: export_date must be YYYY-MM-DD format, got '${EXPORT_DATE}'"
  exit 1
fi

# --- Parse flags ---
DRY_RUN=false
PURGE=false
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --purge) PURGE=true ;;
    *)
      echo "ERROR: Unknown argument '${arg}'"
      exit 1
      ;;
  esac
done

# --- R2 Configuration ---
R2_ACCOUNT_ID="09208aa33790838db213a21f630c33e7"
R2_BUCKET="clinvar-gkm"
R2_ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
R2_PROFILE="r2"
R2_PUBLIC_URL="${R2_PUBLIC_URL:-https://data.clinvar-gkm.org}"
# Per-major release prefix (ADR 0004) — matches the other uploaders + generate-r2-index.sh,
# so backfilled months land under v1/ (where the index generator looks), not the bucket root.
R2_PREFIX="${R2_PREFIX:-v1/}"

# --- CDN cache purge (optional; see ADR 0005) -----------------------------------------
# A first-time backfill writes a NEW dated key — no purge needed. Pass --purge ONLY when
# re-running a backfill over an already-published (and cached) month, so edge caches don't
# serve stale bytes until the (long) immutable Edge TTL expires. Requires a ZONE-scoped
# Cloudflare token with Cache Purge (the object-scoped r2 token cannot purge):
#   export CF_ZONE_ID=...  CF_PURGE_TOKEN=...
CF_PUBLIC_HOST="${CF_PUBLIC_HOST:-data.clinvar-gkm.org}"
CF_ZONE_ID="${CF_ZONE_ID:-}"
CF_PURGE_TOKEN="${CF_PURGE_TOKEN:-}"

# --- Derived date components ---
YEAR="${EXPORT_DATE:0:4}"
MM="${EXPORT_DATE:5:2}"
CURRENT_YEAR="$(date +%Y)"

# --- Filenames ---
MONTHLY_FILE="clinvar-gkm_${YEAR}-${MM}.json.gz"

# --- Destination ---
if [[ "$YEAR" == "$CURRENT_YEAR" ]]; then
  DEST="datasets/${MONTHLY_FILE}"
else
  DEST="archives/${YEAR}/${MONTHLY_FILE}"
fi

# =====================================================================
# Helper functions
# =====================================================================

r2_upload() {
  local src="$1" dest="${R2_PREFIX}$2" content_type="${3:-application/gzip}"
  if $DRY_RUN; then
    echo "  [dry-run] upload: ${dest}"
    return
  fi
  aws s3 cp "$src" "s3://${R2_BUCKET}/${dest}" \
    --endpoint-url "${R2_ENDPOINT}" \
    --profile "${R2_PROFILE}" \
    --content-type "${content_type}" \
    --quiet
}

r2_ls() {
  local prefix="$1"
  aws s3 ls "s3://${R2_BUCKET}/${prefix}" \
    --endpoint-url "${R2_ENDPOINT}" \
    --profile "${R2_PROFILE}" \
    2>/dev/null | awk '{print $NF}' || true
}

r2_ls_with_size() {
  local prefix="$1"
  aws s3 ls "s3://${R2_BUCKET}/${prefix}" \
    --endpoint-url "${R2_ENDPOINT}" \
    --profile "${R2_PROFILE}" \
    2>/dev/null | awk '/\.json\.gz$/ {print $3, $4}' || true
}

cf_purge() {
  # Purge CDN-cached copies of the given host-relative prefixes (args: "host/path" each).
  # No-op unless --purge was passed; honors DRY_RUN; never fatal (always returns 0).
  $PURGE || return 0
  if $DRY_RUN; then
    local p
    for p in "$@"; do echo "  [dry-run] purge: ${p}"; done
    return 0
  fi
  if [[ -z "$CF_ZONE_ID" || -z "$CF_PURGE_TOKEN" ]]; then
    echo "  WARNING: --purge set but CF_ZONE_ID/CF_PURGE_TOKEN not set — skipping CDN purge."
    echo "           Overwritten paths may serve stale from cache until Edge TTL expiry."
    return 0
  fi
  local prefixes="" p
  for p in "$@"; do
    [[ -n "$prefixes" ]] && prefixes+=","
    prefixes+="\"${p}\""
  done
  echo "  Purging CDN cache: $*"
  if curl -fsS -X POST \
      "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/purge_cache" \
      -H "Authorization: Bearer ${CF_PURGE_TOKEN}" \
      -H "Content-Type: application/json" \
      --data "{\"prefixes\":[${prefixes}]}" >/dev/null 2>&1; then
    echo "  Purge requested."
  else
    echo "  WARNING: CDN purge request failed (continuing)."
  fi
}

# =====================================================================
# Main
# =====================================================================

echo "=== ClinVar-GKM Backfill Monthly ==="
echo "  Release date:  ${EXPORT_DATE}"
echo "  Version:       ${DATASET_VERSION}"
echo "  Monthly file:  ${MONTHLY_FILE}"
echo "  Destination:   ${DEST}"
if $DRY_RUN; then
  echo "  Mode:          DRY RUN"
fi
echo ""

# --- Check bundle file ---
echo "Checking bundle: ${BUNDLE_FILE}"
if ! $DRY_RUN && [[ ! -f "${BUNDLE_FILE}" ]]; then
  echo "ERROR: Bundle file not found at ${BUNDLE_FILE}"
  exit 1
fi
echo ""

# --- Upload monthly file ---
echo "--- Uploading monthly release ---"
echo "  ${DEST}"
r2_upload "${BUNDLE_FILE}" "${DEST}"
echo ""

# --- Regenerate index.json via the shared delta-aware generator ---
# (Do NOT inline an index builder here — it would write the retired weekly-schema index and
#  clobber the deltas-aware index.json. generate-r2-index.sh reflects current R2 state:
#  monthly fulls + archives + deltas.)
echo "--- Regenerating index.json ---"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INDEX_ARGS=()
$DRY_RUN && INDEX_ARGS+=("--dry-run")
"${SCRIPT_DIR}/generate-r2-index.sh" "${INDEX_ARGS[@]}"

# --- Purge CDN cache for the re-published dated paths (--purge only) ---
# Only needed when re-running a backfill over an already-published (cached) month.
cf_purge "${CF_PUBLIC_HOST}/${R2_PREFIX}${DEST}"

# --- Summary ---
echo ""
echo "=== Backfill Complete ==="
echo "  Monthly: ${R2_PUBLIC_URL}/${R2_PREFIX}${DEST}"
echo "  Index:   ${R2_PUBLIC_URL}/index.json"
