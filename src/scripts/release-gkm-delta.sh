#!/bin/bash
# Release the per-release GKS DELTA: export delta_<dict> tables, assemble a delta bundle,
# build manifest.json, upload the delta (bundle + manifest + .sha256 sidecar) to R2.
#
# No Parquet: Parquet is a derived convenience, published only as the single latest set
# (release-gkm-parquet.sh), never per delta.
#
# Usage: ./release-gkm-delta.sh <export_date> <dataset_version> [--start-step=N] [--dry-run] [--no-upload]
#   steps: 1=export, 2=assemble, 3=manifest + upload
#
# --no-upload builds the manifest in step 3 but skips the R2 upload and KEEPS the staged bundle and
# manifest (no cleanup), so they can be validated first; publish with upload-gkm-delta-to-r2.sh (or
# re-run with --start-step=3). STAGE_DIR (default /tmp) sets where they are staged.
set -e
[[ $# -lt 2 ]] && { echo "Usage: $0 <export_date> <dataset_version> [--start-step=N] [--dry-run] [--no-upload]"; exit 1; }
EXPORT_DATE="$1"; DATASET_VERSION="$2"; shift 2
[[ "$EXPORT_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { echo "ERROR: bad date '${EXPORT_DATE}'"; exit 1; }

DRY_RUN=false; START_STEP=1; NO_UPLOAD=false
for arg in "$@"; do case "$arg" in
  --dry-run) DRY_RUN=true ;;
  --no-upload) NO_UPLOAD=true ;;
  --start-step=*) START_STEP="${arg#--start-step=}" ;;
  *) echo "ERROR: unknown arg '${arg}'"; exit 1 ;;
esac; done
if ! [[ "$START_STEP" =~ ^[1-3]$ ]]; then
  echo "ERROR: --start-step must be 1, 2, or 3, got '${START_STEP}'"; exit 1
fi

GCS_BUCKET="clinvar-gkm"
GCS_DELTAS_PREFIX="gkm-deltas"
GCS_DELTAS_PATH="gs://${GCS_BUCKET}/${GCS_DELTAS_PREFIX}"
DATE_US="${EXPORT_DATE//-/_}"
BQ_DATASET="clinvar_${DATE_US}_${DATASET_VERSION}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PYTHON="python3"; [[ -x "${PROJECT_ROOT}/venv/3.12/bin/python3" ]] && PYTHON="${PROJECT_ROOT}/venv/3.12/bin/python3"

STAGE_DIR="${STAGE_DIR:-/tmp}"
DELTA_BUNDLE="${STAGE_DIR}/clinvar-gkm-delta-${EXPORT_DATE}.json.gz"
MANIFEST_FILE="${STAGE_DIR}/clinvar-gkm-delta-${EXPORT_DATE}-manifest.json"

echo "=== ClinVar-GKM DELTA release ${EXPORT_DATE} (dataset ${BQ_DATASET}) ==="
$DRY_RUN && echo "  Mode: DRY RUN"

# Step 1: export delta tables -> GCS (NDJSON only)
if (( START_STEP <= 1 )); then
  echo "=== [1/3] export delta tables ==="
  if $DRY_RUN; then
    echo "  [dry-run] export-gkm-dicts.sh ${BQ_DATASET} ${GCS_BUCKET} ${GCS_DELTAS_PREFIX} --delta --ndjson-only"
  else
    gsutil -m -q rm -r "${GCS_DELTAS_PATH}/" 2>/dev/null || true
    "${SCRIPT_DIR}/export-gkm-dicts.sh" "${BQ_DATASET}" "${GCS_BUCKET}" "${GCS_DELTAS_PREFIX}" --delta --ndjson-only
  fi
fi

# Step 2: assemble delta NDJSON -> delta bundle (with cleanup)
if (( START_STEP <= 2 )); then
  echo "=== [2/3] assemble delta bundle ==="
  if $DRY_RUN; then
    echo "  [dry-run] assemble-gkm-dicts.py ${GCS_DELTAS_PATH}/ ${EXPORT_DATE} --output ${DELTA_BUNDLE}"
  else
    "${PYTHON}" "${SCRIPT_DIR}/assemble-gkm-dicts.py" "${GCS_DELTAS_PATH}/" "${EXPORT_DATE}" --output "${DELTA_BUNDLE}"
  fi
fi

# Step 3: build manifest + upload delta tree
if (( START_STEP <= 3 )); then
  echo "=== [3/3] manifest + upload ==="
  MANIFEST_ARGS=("${EXPORT_DATE}" "${DATASET_VERSION}" "${MANIFEST_FILE}")
  if $DRY_RUN; then
    echo "  [dry-run] build-delta-manifest.py ${MANIFEST_ARGS[*]}"
  else
    "${PYTHON}" "${SCRIPT_DIR}/build-delta-manifest.py" "${MANIFEST_ARGS[@]}"
  fi
  if $NO_UPLOAD; then
    echo "  Upload skipped (--no-upload); staged artifacts kept:"
    echo "    ${DELTA_BUNDLE}"; echo "    ${MANIFEST_FILE}"
    exit 0
  fi
  UPLOAD_ARGS=("${EXPORT_DATE}" "${DELTA_BUNDLE}" "${MANIFEST_FILE}")
  $DRY_RUN && UPLOAD_ARGS+=("--dry-run")
  "${SCRIPT_DIR}/upload-gkm-delta-to-r2.sh" "${UPLOAD_ARGS[@]}"
fi

if ! $DRY_RUN; then rm -f "${DELTA_BUNDLE}" "${MANIFEST_FILE}"; fi
echo "=== DELTA release ${EXPORT_DATE} complete ==="
