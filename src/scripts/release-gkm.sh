#!/bin/bash

# Release a ClinVar-GKM monthly FULL bundle: export from BigQuery, assemble, upload to R2.
#
# Three steps:
#   1. export-gkm-dicts.sh --ndjson-only — export the dictionary tables to GCS as NDJSON
#   2. assemble-gkm-dicts.py             — assemble the NDJSON into a single JSON bundle
#   3. upload-gkm-to-r2.sh               — upload the bundle (+ .sha256 sidecar) to Cloudflare R2
#
# No Parquet: Parquet is a derived convenience, published only as the single latest set
# (release-gkm-parquet.sh), never per release.
#
# Usage:
#   ./release-gkm.sh <export_date> <dataset_version> [--start-step=N] [--keep-source] [--dry-run]
#                    [--month-label=YYYY-MM] [--no-upload]
#
# --no-upload stops after step 2 and KEEPS the staged bundle (no R2 write, no cleanup), so it can be
# validated before publishing; resume with --start-step=3. STAGE_DIR (default /tmp) sets where it is staged.
#
# Examples:
#   ./release-gkm.sh 2026-05-03 v2_5_0
#   ./release-gkm.sh 2026-05-03 v2_5_0 --dry-run
#   ./release-gkm.sh 2026-05-03 v2_5_0 --keep-source
#   ./release-gkm.sh 2026-05-03 v2_5_0 --start-step=2  # re-run from assemble step
#   ./release-gkm.sh 2026-05-03 v2_5_0 --start-step=3  # re-run upload only
#   ./release-gkm.sh 2026-05-03 v2_5_0 --no-upload     # stage only (export, assemble)

set -e

# --- Positional arguments ---
if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <export_date> <dataset_version> [--start-step=N] [--keep-source] [--dry-run] [--month-label=YYYY-MM] [--no-upload]"
  echo "  export_date      ClinVar release date (YYYY-MM-DD)"
  echo "  dataset_version  Dataset version (e.g. v2_5_0)"
  echo "  --start-step=N   Start at step N (1=export, 2=assemble, 3=upload)"
  echo "  --month-label=   Publish to this YYYY-MM monthly slot instead of export_date's month"
  echo "  --no-upload      Stop after step 2; keep the staged bundle (resume with --start-step=3)"
  exit 1
fi

EXPORT_DATE="$1"
DATASET_VERSION="$2"
shift 2

# Validate date format
if ! [[ "$EXPORT_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  echo "ERROR: export_date must be YYYY-MM-DD format, got '${EXPORT_DATE}'"
  exit 1
fi

# --- Parse flags ---
DRY_RUN=false
KEEP_SOURCE=false
START_STEP=1
MONTH_LABEL=""
NO_UPLOAD=false
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --keep-source) KEEP_SOURCE=true ;;
    --start-step=*) START_STEP="${arg#--start-step=}" ;;
    --month-label=*) MONTH_LABEL="${arg#--month-label=}" ;;
    --no-upload) NO_UPLOAD=true ;;
    *)
      echo "ERROR: Unknown argument '${arg}'"
      exit 1
      ;;
  esac
done

if ! [[ "$START_STEP" =~ ^[1-3]$ ]]; then
  echo "ERROR: --start-step must be 1, 2, or 3, got '${START_STEP}'"
  exit 1
fi

# --- Configuration ---
GCS_BUCKET="clinvar-gkm"
GCS_DICTS_PREFIX="gkm-dicts"
GCS_DICTS_PATH="gs://${GCS_BUCKET}/${GCS_DICTS_PREFIX}"
DATE_UNDERSCORED="${EXPORT_DATE//-/_}"
BQ_DATASET="clinvar_${DATE_UNDERSCORED}_${DATASET_VERSION}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
if [[ -x "${PROJECT_ROOT}/venv/3.12/bin/python3" ]]; then
  PYTHON="${PROJECT_ROOT}/venv/3.12/bin/python3"
else
  PYTHON="python3"
fi

STAGE_DIR="${STAGE_DIR:-/tmp}"
BUNDLE_FILE="${STAGE_DIR}/clinvar-gkm-${EXPORT_DATE}.json.gz"

echo "=== ClinVar-GKM Release Pipeline (monthly full bundle) ==="
echo "  Release date:  ${EXPORT_DATE}"
echo "  Version:       ${DATASET_VERSION}"
echo "  BQ dataset:    ${BQ_DATASET}"
echo "  GCS dicts:     ${GCS_DICTS_PATH}/"
echo "  Bundle:        ${BUNDLE_FILE}"
$DRY_RUN && echo "  Mode:          DRY RUN"
$KEEP_SOURCE && echo "  Keep source:   YES"
$NO_UPLOAD && echo "  Upload:        NO (stage only)"
[[ "$START_STEP" -gt 1 ]] && echo "  Start step:    ${START_STEP}"
echo ""

# =====================================================================
# Step 1: Export dictionary tables from BigQuery to GCS (NDJSON only)
# =====================================================================

if [[ "$START_STEP" -le 1 ]]; then
  echo "=== Step 1/3: Exporting dictionary tables ==="
  if $DRY_RUN; then
    echo "  [dry-run] Would clear ${GCS_DICTS_PATH}/, then run: export-gkm-dicts.sh ${BQ_DATASET} ${GCS_BUCKET} ${GCS_DICTS_PREFIX} --ndjson-only"
  else
    # Clear gkm-dicts before export to ensure no stale shards from a prior run
    echo "  Clearing ${GCS_DICTS_PATH}/ ..."
    gsutil -m -q rm -r "${GCS_DICTS_PATH}/" 2>/dev/null || true
    "${SCRIPT_DIR}/export-gkm-dicts.sh" "${BQ_DATASET}" "${GCS_BUCKET}" "${GCS_DICTS_PREFIX}" --ndjson-only
  fi
  echo ""
else
  echo "=== Step 1/3: Skipped (--start-step=${START_STEP}) ==="
  echo ""
fi

# =====================================================================
# Step 2: Assemble NDJSON into a single JSON bundle
# =====================================================================

if [[ "$START_STEP" -le 2 ]]; then
  echo "=== Step 2/3: Assembling bundle ==="
  ASSEMBLE_ARGS=("${GCS_DICTS_PATH}/" "${EXPORT_DATE}")
  if $KEEP_SOURCE; then
    ASSEMBLE_ARGS+=("--keep-source")
  fi
  ASSEMBLE_ARGS+=("--output" "${BUNDLE_FILE}")

  if $DRY_RUN; then
    echo "  [dry-run] Would run: ${PYTHON} assemble-gkm-dicts.py ${ASSEMBLE_ARGS[*]}"
  else
    "${PYTHON}" "${SCRIPT_DIR}/assemble-gkm-dicts.py" "${ASSEMBLE_ARGS[@]}"
  fi
  echo ""
else
  echo "=== Step 2/3: Skipped (--start-step=${START_STEP}) ==="
  echo ""
fi

# =====================================================================
# Step 3: Upload the bundle to Cloudflare R2
# =====================================================================

if $NO_UPLOAD; then
  echo "=== Step 3/3: Skipped (--no-upload); staged bundle kept ==="
  echo "  Bundle:  ${BUNDLE_FILE}"
  echo "  Publish later with: $0 ${EXPORT_DATE} ${DATASET_VERSION} --start-step=3${MONTH_LABEL:+ --month-label=${MONTH_LABEL}}"
  exit 0
fi

echo "=== Step 3/3: Uploading to R2 ==="
UPLOAD_ARGS=("${EXPORT_DATE}" "${DATASET_VERSION}" "${BUNDLE_FILE}")
if $DRY_RUN; then
  UPLOAD_ARGS+=("--dry-run")
fi
if [[ -n "${MONTH_LABEL}" ]]; then
  UPLOAD_ARGS+=("--month-label=${MONTH_LABEL}")
fi

"${SCRIPT_DIR}/upload-gkm-to-r2.sh" "${UPLOAD_ARGS[@]}"

# --- Cleanup ---
if ! $DRY_RUN; then
  rm -f "${BUNDLE_FILE}"
fi
