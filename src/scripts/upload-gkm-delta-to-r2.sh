#!/bin/bash

# Upload a ClinVar-GKM DELTA tree (bundle + manifest + Parquet) to Cloudflare R2.
# Runs after release-gkm-delta.sh has produced the delta bundle, manifest.json,
# and merged per-section delta Parquet.
#
# R2 layout written:
#   deltas/<YYYY-MMDD>/clinvar-gkm-delta_<YYYY-MMDD>.json.gz   — the delta bundle
#   deltas/<YYYY-MMDD>/manifest.json                          — per-release manifest
#   deltas/<YYYY-MMDD>/parquet/<section>.parquet              — per-section delta Parquet
#   deltas/00-latest/{clinvar-gkm-delta_00-latest.json.gz, manifest.json, parquet/*}
#
# Before upload it resolves manifest.checkpoint_full = the newest monthly FULL
# currently in datasets/ (clinvar-gkm_YYYY-MM.json.gz), so a consumer knows which
# full bundle this delta chain replays onto. Then regenerates index.json.
#
# Usage:
#   ./upload-gkm-delta-to-r2.sh <export_date> <delta_bundle> <manifest_file> [--parquet-dir=DIR] [--dry-run] [--purge] [--replace-sections]
#
# --replace-sections: after uploading this release's Parquet set, delete the dated parquet/ dir's *.parquet
# files that are not in --parquet-dir (stale sections from an earlier layout). For re-publishing a date.
#
# --purge: after upload, purge the CDN cache for this release's dated prefix. Only needed
# when RE-publishing an existing date (overwrite); requires CF_ZONE_ID + CF_PURGE_TOKEN
# (a zone-scoped token with Cache Purge). See ADR 0005.

set -e

# --- Positional arguments ---
if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <export_date> <delta_bundle> <manifest_file> [--parquet-dir=DIR] [--dry-run] [--purge] [--replace-sections]"
  echo "  export_date    ClinVar release date (YYYY-MM-DD)"
  echo "  delta_bundle   Local path to the assembled delta bundle (.json.gz)"
  echo "  manifest_file  Local path to manifest.json"
  exit 1
fi

EXPORT_DATE="$1"
DELTA_BUNDLE="$2"
MANIFEST_FILE="$3"
shift 3

# Validate date format
if ! [[ "$EXPORT_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  echo "ERROR: export_date must be YYYY-MM-DD format, got '${EXPORT_DATE}'"
  exit 1
fi

# --- Parse flags ---
DRY_RUN=false
PARQUET_DIR=""
PURGE=false
REPLACE_SECTIONS=false
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --purge) PURGE=true ;;
    --replace-sections) REPLACE_SECTIONS=true ;;
    --parquet-dir=*) PARQUET_DIR="${arg#--parquet-dir=}" ;;
    *)
      echo "ERROR: Unknown argument '${arg}'"
      echo "Usage: $0 <export_date> <delta_bundle> <manifest_file> [--parquet-dir=DIR] [--dry-run] [--purge] [--replace-sections]"
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
# Per-major release prefix (ADR 0004). Everything this script publishes lives under
# it (v1/deltas/…). Env-overridable; the r2_* helpers below prepend it, so call sites
# still pass bare deltas/… paths.
R2_PREFIX="${R2_PREFIX:-v1/}"

# --- CDN cache purge (optional; see ADR 0005) -----------------------------------------
# Routine releases write NEW dated keys, which aren't cached yet — no purge needed. Pass
# --purge ONLY when re-publishing/overwriting an already-cached dated prefix, so Cloudflare
# edge caches don't serve stale bytes until the (long) immutable Edge TTL expires. Requires
# a ZONE-scoped Cloudflare token with Cache Purge (the object-scoped r2 token cannot purge):
#   export CF_ZONE_ID=...  CF_PURGE_TOKEN=...
CF_PUBLIC_HOST="${CF_PUBLIC_HOST:-data.clinvar-gkm.org}"
CF_ZONE_ID="${CF_ZONE_ID:-}"
CF_PURGE_TOKEN="${CF_PURGE_TOKEN:-}"

# --- Derived date components ---
YEAR="${EXPORT_DATE:0:4}"
MM="${EXPORT_DATE:5:2}"
DD="${EXPORT_DATE:8:2}"
MMDD="${MM}${DD}"                    # 0706
PREFIX="deltas/${YEAR}-${MMDD}"     # deltas/2026-0706
LATEST_PREFIX="deltas/00-latest"

DELTA_NAME="clinvar-gkm-delta_${YEAR}-${MMDD}.json.gz"
LATEST_DELTA_NAME="clinvar-gkm-delta_00-latest.json.gz"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# =====================================================================
# Helper functions (shared with upload-gkm-to-r2.sh)
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

r2_copy() {
  # Server-side (no-egress) copy that works across object sizes despite two R2 gaps:
  #   * multipart copy with default props calls GetObjectTagging (R2: NotImplemented)
  #   * single-part copy with --copy-props none sends x-amz-tagging-directive:REPLACE
  #     (R2: NotImplemented)
  # So: large objects (>=2GB) via `aws s3 cp --copy-props none` (multipart, no tag calls);
  # everything smaller via `aws s3api copy-object` (single CopyObject, no tag calls).
  # Delta artifacts are usually small (this hits the s3api path), but a large delta bundle
  # is handled correctly too.
  local src="${R2_PREFIX}$1" dest="${R2_PREFIX}$2"
  if $DRY_RUN; then
    echo "  [dry-run] copy: ${src} -> ${dest}"
    return
  fi
  local size
  size=$(aws s3api head-object --bucket "${R2_BUCKET}" --key "${src}" \
    --endpoint-url "${R2_ENDPOINT}" --profile "${R2_PROFILE}" \
    --query ContentLength --output text 2>/dev/null || echo 0)
  if [[ "${size}" -ge 2147483648 ]]; then
    aws s3 cp "s3://${R2_BUCKET}/${src}" "s3://${R2_BUCKET}/${dest}" \
      --endpoint-url "${R2_ENDPOINT}" --profile "${R2_PROFILE}" --copy-props none --quiet
  else
    aws s3api copy-object --bucket "${R2_BUCKET}" --key "${dest}" \
      --copy-source "${R2_BUCKET}/${src}" \
      --endpoint-url "${R2_ENDPOINT}" --profile "${R2_PROFILE}" >/dev/null
  fi
}

r2_ls() {
  local prefix="${R2_PREFIX}$1"
  aws s3 ls "s3://${R2_BUCKET}/${prefix}" \
    --endpoint-url "${R2_ENDPOINT}" \
    --profile "${R2_PROFILE}" \
    2>/dev/null | awk '{print $NF}' || true
}

r2_rm() {
  local key="${R2_PREFIX}$1"
  if $DRY_RUN; then
    echo "  [dry-run] delete: ${key}"
    return
  fi
  aws s3 rm "s3://${R2_BUCKET}/${key}" \
    --endpoint-url "${R2_ENDPOINT}" \
    --profile "${R2_PROFILE}" \
    --quiet
}

remove_stale_sections() {
  # --replace-sections only: after this release's Parquet set is uploaded to a DATED dir ($1, bare path,
  # trailing slash), delete every *.parquet there that is not in the local set ($2). Dated dirs are never
  # wiped otherwise, so a republish that renames sections (1.1.0: the four var*-proposition tables ->
  # proposition*) would leave the old files beside the new ones, and generate-r2-index.sh lists sections
  # from the R2 listing. Upload-then-delete leaves no window with missing files. Honors DRY_RUN.
  $REPLACE_SECTIONS || return 0
  local dated_dir="$1" local_dir="$2" fn removed=0
  while IFS= read -r fn; do
    [[ "$fn" == *.parquet ]] || continue
    [[ -f "${local_dir}/${fn}" ]] && continue
    echo "  stale section: ${dated_dir}${fn}"
    r2_rm "${dated_dir}${fn}"
    (( removed++ )) || true
  done < <(r2_ls "${dated_dir}")
  echo "  ${removed} stale section file(s) $($DRY_RUN && echo 'to remove' || echo 'removed') from ${dated_dir}"
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

echo "=== ClinVar-GKM DELTA Upload ==="
echo "  Release date:  ${EXPORT_DATE}"
echo "  Delta prefix:  ${PREFIX}/"
echo "  Delta bundle:  ${DELTA_NAME}"
$DRY_RUN && echo "  Mode:          DRY RUN"
echo ""

# --- Check local artifacts (skip strict checks in dry-run — orchestrator does not
#     produce them when dry-running the earlier steps) ---
if ! $DRY_RUN; then
  if [[ ! -f "${DELTA_BUNDLE}" ]]; then
    echo "ERROR: delta bundle not found at ${DELTA_BUNDLE}"; exit 1
  fi
  if [[ ! -f "${MANIFEST_FILE}" ]]; then
    echo "ERROR: manifest not found at ${MANIFEST_FILE}"; exit 1
  fi
fi

# --- (a) Resolve checkpoint_full from current R2 monthly state ------------------------
echo "--- Resolving checkpoint_full (newest monthly FULL in datasets/) ---"
CHECKPOINT_FILE=""
while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  # Keep only clinvar-gkm_YYYY-MM.json.gz (monthly full); exclude 00-latest + weekly.
  [[ "$f" == *"00-latest"* ]] && continue
  [[ "$f" =~ ^clinvar-gkm_[0-9]{4}-[0-9]{2}\.json\.gz$ ]] || continue
  # lexically-last wins (YYYY-MM sorts chronologically)
  if [[ -z "$CHECKPOINT_FILE" || "$f" > "$CHECKPOINT_FILE" ]]; then
    CHECKPOINT_FILE="$f"
  fi
done < <(r2_ls "datasets/clinvar-gkm_")

if [[ -n "$CHECKPOINT_FILE" ]]; then
  # Path is written into the manifest and resolved by consumers as base_url + path,
  # so it must carry the same ${R2_PREFIX} the full bundle is published under.
  CHECKPOINT_PATH="${R2_PREFIX}datasets/${CHECKPOINT_FILE}"
  CHECKPOINT_RELEASE="${CHECKPOINT_FILE#clinvar-gkm_}"   # 2026-06.json.gz
  CHECKPOINT_RELEASE="${CHECKPOINT_RELEASE%.json.gz}"     # 2026-06
  echo "  checkpoint_full = ${CHECKPOINT_PATH} (release ${CHECKPOINT_RELEASE})"
  if $DRY_RUN; then
    echo "  [dry-run] would patch manifest.checkpoint_full = {path, release}"
  else
    "${PYTHON:-python3}" -c '
import json, sys
path, cp_path, cp_rel = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path) as fh:
    d = json.load(fh)
d["checkpoint_full"] = {"path": cp_path, "release": cp_rel}
with open(path, "w") as fh:
    json.dump(d, fh, indent=2)
' "${MANIFEST_FILE}" "${CHECKPOINT_PATH}" "${CHECKPOINT_RELEASE}"
    echo "  patched manifest.checkpoint_full"
  fi
else
  echo "  WARNING: no monthly FULL found in datasets/ — checkpoint_full stays null"
  echo "           (expected on the initial rollout; the first delta bootstraps from itself)"
fi
echo ""

# --- (b) Upload the delta tree --------------------------------------------------------
echo "--- Uploading delta tree to ${PREFIX}/ ---"
r2_upload "${DELTA_BUNDLE}" "${PREFIX}/${DELTA_NAME}"
r2_upload "${MANIFEST_FILE}" "${PREFIX}/manifest.json" "application/json"

PARQUET_SECTIONS=()
if [[ -n "${PARQUET_DIR}" && -d "${PARQUET_DIR}" ]]; then
  for parquet_file in "${PARQUET_DIR}"/*.parquet; do
    [[ -f "$parquet_file" ]] || continue
    section="$(basename "${parquet_file}" .parquet)"
    PARQUET_SECTIONS+=("$section")
    r2_upload "${parquet_file}" "${PREFIX}/parquet/${section}.parquet" \
      "application/vnd.apache.parquet"
  done
  echo "  ${#PARQUET_SECTIONS[@]} Parquet sections uploaded."
  remove_stale_sections "${PREFIX}/parquet/" "${PARQUET_DIR}"
elif $DRY_RUN; then
  echo "  [dry-run] (no local Parquet dir; would upload ${R2_PREFIX}${PREFIX}/parquet/<section>.parquet)"
else
  echo "  (no Parquet dir found, skipping)"
fi
echo ""

# --- (c) Refresh deltas/00-latest/ (server-side copy of the three artifact kinds) -----
echo "--- Refreshing ${LATEST_PREFIX}/ ---"
r2_copy "${PREFIX}/${DELTA_NAME}" "${LATEST_PREFIX}/${LATEST_DELTA_NAME}"
r2_copy "${PREFIX}/manifest.json" "${LATEST_PREFIX}/manifest.json"
# Clear stale sections from 00-latest/parquet/ before copying THIS release's sections.
# The delta's per-section parquet set varies release to release, so without a wipe a section
# from a prior release (that had no changes this release) would linger in 00-latest/parquet/
# alongside the current sections and misrepresent the latest delta. The bundle + manifest are
# single files (cleanly overwritten by r2_copy above), so only parquet/ needs this.
if $DRY_RUN; then
  echo "  [dry-run] clear ${R2_PREFIX}${LATEST_PREFIX}/parquet/ (drop stale prior-release sections)"
else
  aws s3 rm "s3://${R2_BUCKET}/${R2_PREFIX}${LATEST_PREFIX}/parquet/" --recursive \
    --endpoint-url "${R2_ENDPOINT}" --profile "${R2_PROFILE}" --quiet 2>/dev/null || true
fi
if [[ ${#PARQUET_SECTIONS[@]} -gt 0 ]]; then
  for section in "${PARQUET_SECTIONS[@]}"; do
    r2_copy "${PREFIX}/parquet/${section}.parquet" "${LATEST_PREFIX}/parquet/${section}.parquet"
  done
elif $DRY_RUN; then
  echo "  [dry-run] (would copy ${R2_PREFIX}${PREFIX}/parquet/<section>.parquet -> ${R2_PREFIX}${LATEST_PREFIX}/parquet/)"
fi
echo ""

# --- (d) Regenerate index.json --------------------------------------------------------
INDEX_ARGS=()
$DRY_RUN && INDEX_ARGS+=("--dry-run")
"${SCRIPT_DIR}/generate-r2-index.sh" "${INDEX_ARGS[@]}"

# --- (e) Purge CDN cache for the re-published dated prefix (--purge only) --------------
# index.json + deltas/00-latest/ are on a short Edge TTL (they self-refresh), so only the
# immutable dated prefix needs purging when a same-date delta is re-published.
cf_purge "${CF_PUBLIC_HOST}/${R2_PREFIX}${PREFIX}/"

# --- Summary --------------------------------------------------------------------------
echo ""
echo "=== Delta Upload Complete ==="
echo "  Delta:   ${R2_PUBLIC_URL}/${R2_PREFIX}${PREFIX}/${DELTA_NAME}"
echo "  Manifest:${R2_PUBLIC_URL}/${R2_PREFIX}${PREFIX}/manifest.json"
echo "  Latest:  ${R2_PUBLIC_URL}/${R2_PREFIX}${LATEST_PREFIX}/${LATEST_DELTA_NAME}"
echo "  Index:   ${R2_PUBLIC_URL}/index.json"
