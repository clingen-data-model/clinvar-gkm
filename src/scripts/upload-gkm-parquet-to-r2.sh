#!/bin/bash
# Upload the ONE ClinVar-GKM Parquet set of the version line (R2_LINE, default v1/1.1/) to <line>parquet/.
#
# Parquet is derived from the JSON bundle and is not a release record (ADR 0008): one set, rebuilt every release
# from the newest dataset and overwritten in place. There is no Parquet in archives; past states are rebuilt from
# the monthly bundles. Layout:
#   <line>parquet/<section>.parquet
#   <line>parquet/manifest.json   build date, source release + dataset, builder ("BigQuery export" until
#                                 clinvar-gkm-parquet takes over), table-spec version (if known), schema version,
#                                 and every file with its size and sha256
# Each section is overwritten in place; afterwards any *.parquet (or other file) in parquet/ that is not in the
# local set is deleted (a renamed or dropped section), so there is no window with a missing file. The index is
# regenerated.
#
# Usage: ./upload-gkm-parquet-to-r2.sh <export_date> <dataset_version> <parquet_dir> [--dry-run] [--purge]
#
# --purge purges the CDN copy of <line>parquet/ (cached 1 day by the Parquet cache rule; ADR 0005).
# PARQUET_BUILDER and PARQUET_TABLE_SPEC_VERSION override the manifest's builder and table_spec_version.
set -euo pipefail

if [[ $# -lt 3 ]]; then
  sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 1
fi
EXPORT_DATE="$1"; DATASET_VERSION="$2"; PARQUET_DIR="$3"; shift 3
[[ "$EXPORT_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { echo "ERROR: bad date '${EXPORT_DATE}'" >&2; exit 1; }
DRY_RUN=false; PURGE=false
for arg in "$@"; do case "$arg" in
  --dry-run) DRY_RUN=true ;;
  --purge) PURGE=true ;;
  *) echo "ERROR: unknown arg '${arg}'" >&2; exit 1 ;;
esac; done
export DRY_RUN

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=r2-common.sh
. "${SCRIPT_DIR}/r2-common.sh"
SCHEMA_VERSION="$(sed -n 's/^SCHEMA_VERSION = "\(.*\)"$/\1/p' "${SCRIPT_DIR}/assemble-gkm-dicts.py")"
PQ="${R2_LINE}parquet/"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

echo "=== ClinVar-GKM Parquet upload -> ${PQ} (built from ${EXPORT_DATE}, ${DATASET_VERSION}) ==="
${DRY_RUN} && echo "  Mode: DRY RUN"
SECTIONS=()
if [[ -d "${PARQUET_DIR}" ]]; then
  for f in "${PARQUET_DIR}"/*.parquet; do [[ -f "$f" ]] && SECTIONS+=("$(basename "$f")"); done
fi
if [[ ${#SECTIONS[@]} -eq 0 ]]; then
  ${DRY_RUN} || { echo "ERROR: no *.parquet in ${PARQUET_DIR}" >&2; exit 1; }
  echo "  [dry-run] (no local Parquet in ${PARQUET_DIR}; would upload <section>.parquet + manifest.json)"
fi

echo "--- uploading ${#SECTIONS[@]} sections ---"
for f in "${SECTIONS[@]+"${SECTIONS[@]}"}"; do
  r2_put "${PARQUET_DIR}/${f}" "${PQ}${f}" "application/vnd.apache.parquet"
done

if [[ ${#SECTIONS[@]} -gt 0 ]]; then
  r2_layout parquet-manifest --dir "${PARQUET_DIR}" --release "${EXPORT_DATE}" \
    --dataset "clinvar_${EXPORT_DATE//-/_}_${DATASET_VERSION}" --schema-version "${SCHEMA_VERSION}" \
    --builder "${PARQUET_BUILDER:-BigQuery export}" \
    ${PARQUET_TABLE_SPEC_VERSION:+--table-spec-version "${PARQUET_TABLE_SPEC_VERSION}"} --out "${TMP}/manifest.json"
  r2_put "${TMP}/manifest.json" "${PQ}manifest.json" "application/json"
fi

# Remove files that are no longer produced (after the upload: no window with a missing file).
echo "--- removing stale files from ${PQ} ---"
removed=0
r2_listing "${PQ}" "${TMP}/parquet.txt"
while read -r _ _ _ key; do
  [[ -n "${key:-}" ]] || continue
  fn="${key#"${PQ}"}"
  [[ "${fn}" == "manifest.json" || -f "${PARQUET_DIR}/${fn}" ]] && continue
  [[ ${#SECTIONS[@]} -eq 0 ]] && continue
  r2_rm "${key}"; removed=$((removed + 1))
done < "${TMP}/parquet.txt"
echo "  ${removed} stale file(s) $(${DRY_RUN} && echo 'to remove' || echo 'removed')."

IDX=(); ${DRY_RUN} && IDX+=(--dry-run)
"${SCRIPT_DIR}/generate-r2-index.sh" "${IDX[@]+"${IDX[@]}"}"

${PURGE} && cf_purge prefixes "${PQ}"
echo "=== Parquet: ${R2_PUBLIC_URL}/${PQ} ==="
