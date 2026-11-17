#!/bin/bash
# Build the ONE ClinVar-GKM Parquet set from a release's published weekly full and publish it to <line>parquet/
# (R2_LINE, default v1/1.2/), with parquet/manifest.json. Run every release, on the newest release (stage 6 of
# run-release.sh). Parquet is derived from the bundle and is not kept per release (ADR 0008).
#
#   1. gkm-bundle-parquet build           the default tables, from the published weekly full
#   2. gkm-bundle-parquet verify          id sets and values against the bundle, then the round trip to its records
#   3. upload-gkm-parquet-to-r2.sh        overwrite parquet/, write manifest.json, drop stale files, regenerate the index
#
# This is the only way the published Parquet is made: BigQuery exports no Parquet. The tool reads the weekly full
# from its public URL and checks it against the sha256 in the published .sha256 sidecar, which this script
# downloads first (it stops if the sidecar is missing). The tables are the tool's generated default for the
# bundle schema (no column set): --bundle-schema is the schema's w3id URL for the assembler's SCHEMA_VERSION, and
# --version-property schema_version names the root property that holds the bundle's version.
#
# Usage: ./release-gkm-parquet.sh <export_date> <dataset_version> [--start-step=N] [--dry-run] [--no-upload] [--purge]
#
# --no-upload stops after step 2 and KEEPS the build in STAGE_DIR (default /tmp), so it can be checked before
# publishing; resume with --start-step=3. --dry-run prints the commands it would run, and reads and uploads
# nothing. A build needs about 25 GB free (the set is about 12 GB). PARQUET_MEMORY_LIMIT sets DuckDB's limit
# (default: the tool's). PARQUET_TOOL_CMD replaces the pinned tool command, e.g. to test an unpublished checkout:
#   PARQUET_TOOL_CMD="uvx --from /path/to/gkm-bundle-parquet gkm-bundle-parquet" (split on spaces).
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
export DRY_RUN

# The output bytes depend on the tool version, so a change of table layout is a deliberate bump of this pin.
PARQUET_TOOL=(uvx "gkm-bundle-parquet@2.0.0")
[[ -n "${PARQUET_TOOL_CMD:-}" ]] && read -r -a PARQUET_TOOL <<< "${PARQUET_TOOL_CMD}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=r2-common.sh
. "${SCRIPT_DIR}/r2-common.sh"
SCHEMA_VERSION="$(sed -n 's/^SCHEMA_VERSION = "\(.*\)"$/\1/p' "${SCRIPT_DIR}/assemble-gkm-dicts.py")"
[[ "${SCHEMA_VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
  echo "ERROR: no SCHEMA_VERSION in ${SCRIPT_DIR}/assemble-gkm-dicts.py (got '${SCHEMA_VERSION}')"; exit 1; }
BUNDLE_SCHEMA="https://w3id.org/clingen/schema/clinvar-gkm/${SCHEMA_VERSION}/clinvar-gkm-bundle.schema.json"
STAGE_DIR="${STAGE_DIR:-/tmp}"
PARQUET_DIR="${STAGE_DIR}/clinvar-gkm-parquet-latest-${EXPORT_DATE}"
WORK_DIR="${PARQUET_DIR}.work"
MMDD="${EXPORT_DATE:5:2}${EXPORT_DATE:8:2}"
FULL_URL="${R2_PUBLIC_URL}/${R2_LINE}weekly/clinvar-gkm_${EXPORT_DATE:0:4}-${MMDD}.json.gz"
MEMORY_ARGS=(); [[ -n "${PARQUET_MEMORY_LIMIT:-}" ]] && MEMORY_ARGS=(--memory-limit "${PARQUET_MEMORY_LIMIT}")

echo "=== ClinVar-GKM Parquet (${PARQUET_TOOL[*]}, schema ${SCHEMA_VERSION}) from ${FULL_URL} -> ${PARQUET_DIR} ==="
$DRY_RUN && echo "  Mode: DRY RUN"

# The weekly full's sha256, from its published sidecar (`sha256sum -c` format). Steps 1 and 2 read the full.
if (( START_STEP <= 2 )); then
  if $DRY_RUN; then
    FULL_SHA256="<sha256 from ${FULL_URL}.sha256>"
  else
    FULL_SHA256="$(curl -fsSL "${FULL_URL}.sha256" | awk '{print $1; exit}')" || FULL_SHA256=""
    [[ "${FULL_SHA256}" =~ ^[0-9a-f]{64}$ ]] || {
      echo "ERROR: ${FULL_URL}.sha256 is missing or malformed; is the ${EXPORT_DATE} weekly full published?"; exit 1; }
  fi
  BUNDLE_ARGS=(--full "${FULL_URL}" --sha256 "${FULL_SHA256}" --bundle-schema "${BUNDLE_SCHEMA}"
    --version-property schema_version)
fi

# Print a command (--dry-run) or run it.
run_tool() {
  if $DRY_RUN; then echo "  [dry-run] ${PARQUET_TOOL[*]} $*"; else "${PARQUET_TOOL[@]}" "$@"; fi
}

if (( START_STEP <= 1 )); then
  echo "=== [1/3] build ==="
  $DRY_RUN || rm -rf "${PARQUET_DIR}" "${WORK_DIR}"
  run_tool build "${BUNDLE_ARGS[@]}" --out "${PARQUET_DIR}" --work-dir "${WORK_DIR}" ${MEMORY_ARGS[@]+"${MEMORY_ARGS[@]}"}
fi

if (( START_STEP <= 2 )); then
  echo "=== [2/3] verify ==="
  run_tool verify "${PARQUET_DIR}" --bundle-recompute "${BUNDLE_ARGS[@]}" --work-dir "${WORK_DIR}" \
    ${MEMORY_ARGS[@]+"${MEMORY_ARGS[@]}"}
  run_tool verify "${PARQUET_DIR}" --roundtrip --work-dir "${WORK_DIR}" ${MEMORY_ARGS[@]+"${MEMORY_ARGS[@]}"}
  $DRY_RUN || rm -rf "${WORK_DIR}"
fi

if $NO_UPLOAD; then
  echo "=== [3/3] skipped (--no-upload); the verified build is kept in ${PARQUET_DIR}/ ==="
  echo "  Publish later with: $0 ${EXPORT_DATE} ${DATASET_VERSION} --start-step=3"
  exit 0
fi

echo "=== [3/3] upload ==="
UPLOAD_ARGS=("${EXPORT_DATE}" "${DATASET_VERSION}" "${PARQUET_DIR}")
$DRY_RUN && UPLOAD_ARGS+=("--dry-run")
$PURGE && UPLOAD_ARGS+=("--purge")
"${SCRIPT_DIR}/upload-gkm-parquet-to-r2.sh" "${UPLOAD_ARGS[@]}"

$DRY_RUN || rm -rf "${PARQUET_DIR}"
echo "=== latest Parquet from ${EXPORT_DATE} complete ==="
