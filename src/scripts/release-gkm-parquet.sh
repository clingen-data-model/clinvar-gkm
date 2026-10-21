#!/bin/bash
# Rebuild the ONE ClinVar-GKM Parquet set from a dataset and publish it to <line>parquet/ (R2_LINE, default
# v1/1.1/), with parquet/manifest.json. Run every release, on the newest dataset (run-release.sh does this
# after the weekly delta). Parquet is derived from the bundle and is not kept per release (ADR 0008).
#
#   1. export-gkm-dicts.sh --parquet-only — the FULL dict tables (not the delta), typed Parquet to GCS
#   2. download the shards and merge them into one file per section (DuckDB)
#   3. upload-gkm-parquet-to-r2.sh       — overwrite parquet/, write manifest.json, drop stale sections, regenerate the index
#
# Usage: ./release-gkm-parquet.sh <export_date> <dataset_version> [--start-step=N] [--dry-run] [--no-upload] [--purge]
#
# --no-upload stops after step 2 and KEEPS the merged Parquet in STAGE_DIR (default /tmp), so it can be
# checked before publishing; resume with --start-step=3. The set is about 12 GB.
set -e
[[ $# -lt 2 ]] && { echo "Usage: $0 <export_date> <dataset_version> [--start-step=N] [--dry-run] [--no-upload] [--purge]"; exit 1; }
EXPORT_DATE="$1"; DATASET_VERSION="$2"; shift 2
[[ "$EXPORT_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { echo "ERROR: bad date '${EXPORT_DATE}'"; exit 1; }

DRY_RUN=false; START_STEP=1; NO_UPLOAD=false; PURGE=false
for arg in "$@"; do case "$arg" in
  --dry-run) DRY_RUN=true ;;
  --no-upload) NO_UPLOAD=true ;;
  --purge) PURGE=true ;;
  --start-step=*) START_STEP="${arg#--start-step=}" ;;
  *) echo "ERROR: unknown arg '${arg}'"; exit 1 ;;
esac; done
[[ "$START_STEP" =~ ^[1-3]$ ]] || { echo "ERROR: --start-step must be 1, 2, or 3, got '${START_STEP}'"; exit 1; }

GCS_BUCKET="clinvar-gkm"
GCS_PREFIX="gkm-latest"                                   # export-gkm-dicts.sh writes <prefix>-parquet
GCS_PARQUET_PATH="gs://${GCS_BUCKET}/${GCS_PREFIX}-parquet"
BQ_DATASET="clinvar_${EXPORT_DATE//-/_}_${DATASET_VERSION}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STAGE_DIR="${STAGE_DIR:-/tmp}"
PARQUET_DIR="${STAGE_DIR}/clinvar-gkm-parquet-latest-${EXPORT_DATE}"

echo "=== ClinVar-GKM latest Parquet from ${BQ_DATASET} -> ${PARQUET_DIR} ==="
$DRY_RUN && echo "  Mode: DRY RUN"

if (( START_STEP <= 1 )); then
  echo "=== [1/3] export typed Parquet ==="
  if $DRY_RUN; then
    echo "  [dry-run] export-gkm-dicts.sh ${BQ_DATASET} ${GCS_BUCKET} ${GCS_PREFIX} --parquet-only"
  else
    gsutil -m -q rm -r "${GCS_PARQUET_PATH}/" 2>/dev/null || true
    "${SCRIPT_DIR}/export-gkm-dicts.sh" "${BQ_DATASET}" "${GCS_BUCKET}" "${GCS_PREFIX}" --parquet-only
  fi
fi

if (( START_STEP <= 2 )); then
  echo "=== [2/3] download + merge shards ==="
  if $DRY_RUN; then
    echo "  [dry-run] download ${GCS_PARQUET_PATH}/ and merge into ${PARQUET_DIR}/<section>.parquet"
  else
    rm -rf "${PARQUET_DIR}"; mkdir -p "${PARQUET_DIR}/_gcs"
    gsutil -m cp "${GCS_PARQUET_PATH}/*.parquet" "${PARQUET_DIR}/_gcs/"
    for first in "${PARQUET_DIR}"/_gcs/*-000000000000.parquet; do
      [[ -f "$first" ]] || continue
      base="$(basename "$first" | sed 's/-000000000000\.parquet//')"
      echo "    ${base}"
      duckdb -c "COPY (SELECT * FROM read_parquet('${PARQUET_DIR}/_gcs/${base}-*.parquet')) TO '${PARQUET_DIR}/${base}.parquet' (FORMAT PARQUET, COMPRESSION SNAPPY);"
    done
    rm -rf "${PARQUET_DIR}/_gcs"
    echo "  $(find "${PARQUET_DIR}" -name '*.parquet' | wc -l | tr -d ' ') sections in ${PARQUET_DIR}/"
  fi
fi

if $NO_UPLOAD; then
  echo "=== [3/3] skipped (--no-upload); merged Parquet kept in ${PARQUET_DIR}/ ==="
  echo "  Publish later with: $0 ${EXPORT_DATE} ${DATASET_VERSION} --start-step=3"
  exit 0
fi

echo "=== [3/3] upload ==="
UPLOAD_ARGS=("${EXPORT_DATE}" "${DATASET_VERSION}" "${PARQUET_DIR}")
$DRY_RUN && UPLOAD_ARGS+=("--dry-run")
$PURGE && UPLOAD_ARGS+=("--purge")
"${SCRIPT_DIR}/upload-gkm-parquet-to-r2.sh" "${UPLOAD_ARGS[@]}"

if ! $DRY_RUN; then
  rm -rf "${PARQUET_DIR}"
  gsutil -m -q rm -r "${GCS_PARQUET_PATH}/" 2>/dev/null || true
fi
echo "=== latest Parquet from ${EXPORT_DATE} complete ==="
