#!/bin/bash
# Upload a ClinVar-GKM weekly DELTA (bundle + .sha256 sidecar + manifest) to its place in the version line
# (R2_LINE, default v1/1.1/; layout in r2_layout.py):
#
#   <line>deltas/clinvar-gkm-delta_YYYY-MMDD.json.gz (+ .sha256, + .manifest.json)   the line's current month
#   <line>deltas/YYYY-MM/clinvar-gkm-delta_YYYY-MMDD.*                               an earlier month this year
#
# The current month is the month of the newest release in the line (or this one, if newer); CURRENT_MONTH=YYYY-MM
# overrides it (a republish of past deltas sets it to the final month, so nothing has to move afterwards).
#
# Before the upload the manifest is completed (r2_layout.py patch-manifest):
#   checkpoint_full  the newest official monthly whose source_release <= this delta's baseline_release, i.e. the
#                    full a consumer replays this delta (and the ones after it) onto: {path, release, month,
#                    sha256}, where release is the monthly's source_release (a date) and month its YYYY-MM label
#                    (r2_layout.checkpoint_for). Monthlies are therefore uploaded before the deltas that follow them.
#   sha256, bundle   the bundle's sha256, name, path and size
#   schema_version   the bundle's own schema_version
# and the chain is checked: baseline_release must equal the release of the newest delta before this one in the
# line (refused otherwise; --allow-gap overrides). The index is regenerated.
#
# Usage: ./upload-gkm-delta-to-r2.sh <export_date> <delta_bundle> <manifest_file> [--dry-run] [--purge] [--allow-gap]
#
# --dry-run completes a COPY of the manifest (prints its checkpoint) and writes nothing to R2.
# --purge purges the CDN copy of the paths written; only needed when overwriting an existing delta.
set -euo pipefail

if [[ $# -lt 3 ]]; then
  sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'; exit 1
fi
EXPORT_DATE="$1"; DELTA_BUNDLE="$2"; MANIFEST_FILE="$3"; shift 3
[[ "$EXPORT_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { echo "ERROR: export_date must be YYYY-MM-DD, got '${EXPORT_DATE}'" >&2; exit 1; }

DRY_RUN=false; PURGE=false; ALLOW_GAP=false
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --purge) PURGE=true ;;
    --allow-gap) ALLOW_GAP=true ;;
    *) echo "ERROR: unknown argument '${arg}'" >&2; exit 1 ;;
  esac
done
export DRY_RUN

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=r2-common.sh
. "${SCRIPT_DIR}/r2-common.sh"

COMPACT="${EXPORT_DATE:0:4}-${EXPORT_DATE:5:2}${EXPORT_DATE:8:2}"
NAME="clinvar-gkm-delta_${COMPACT}.json.gz"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

echo "=== ClinVar-GKM DELTA upload ${EXPORT_DATE} (${R2_LINE}) ==="
${DRY_RUN} && echo "  Mode: DRY RUN"
HAVE_LOCAL=true
if [[ ! -f "${DELTA_BUNDLE}" || ! -f "${MANIFEST_FILE}" ]]; then
  ${DRY_RUN} || { echo "ERROR: delta bundle or manifest missing (${DELTA_BUNDLE}, ${MANIFEST_FILE})" >&2; exit 1; }
  HAVE_LOCAL=false
fi

r2_listing "${R2_LINE}" "${TMP}/listing.txt"
DIR="$(r2_layout delta-dir --listing "${TMP}/listing.txt" --line "${R2_LINE}" --release "${EXPORT_DATE}" \
  ${CURRENT_MONTH:+--current-month "${CURRENT_MONTH}"})"
KEY="${DIR}${NAME}"
MAN_KEY="${DIR}clinvar-gkm-delta_${COMPACT}.manifest.json"
# The newest delta in the line before this one (any folder): this delta's baseline must be its release.
PREV="$(awk '{print $4}' "${TMP}/listing.txt" \
  | sed -n 's|.*/clinvar-gkm-delta_\([0-9]\{4\}\)-\([0-9]\{2\}\)\([0-9]\{2\}\)\.json\.gz$|\1-\2-\3|p' \
  | awk -v d="${EXPORT_DATE}" '$0 < d' | sort | tail -n1)"
echo "  Folder:   ${DIR}"
echo "  Previous: ${PREV:-none (first delta of the line)}"

if ${HAVE_LOCAL}; then
  r2_cat "${R2_LINE}index.json" > "${TMP}/index.json" || : > "${TMP}/index.json"
  MAN="${MANIFEST_FILE}"
  if ${DRY_RUN}; then cp "${MANIFEST_FILE}" "${TMP}/manifest.json"; MAN="${TMP}/manifest.json"; fi
  PATCH_ARGS=(--manifest "${MAN}" --bundle "${DELTA_BUNDLE}" --index "${TMP}/index.json" --dir "${DIR}")
  [[ -n "${PREV}" ]] && PATCH_ARGS+=(--previous-release "${PREV}")
  ${ALLOW_GAP} && PATCH_ARGS+=(--allow-gap)
  echo "--- completing the manifest (checkpoint_full, sha256, schema_version) ---"
  SUMMARY="$(r2_layout patch-manifest "${PATCH_ARGS[@]}")"
  echo "  ${SUMMARY}"
  SHA="$("${R2_PYTHON}" -c 'import json,sys; print(json.load(open(sys.argv[1]))["sha256"])' "${MAN}")"
else
  echo "  [dry-run] no local bundle/manifest: would complete the manifest and check the chain against ${PREV:-none}"
  MAN="${MANIFEST_FILE}"
  SHA="0000000000000000000000000000000000000000000000000000000000000000"
fi

echo "--- uploading ---"
r2_put "${DELTA_BUNDLE}" "${KEY}"
r2_put_sidecar "${SHA}" "${KEY}"
r2_put "${MAN}" "${MAN_KEY}" "application/json"

IDX=(); ${DRY_RUN} && IDX+=(--dry-run)
"${SCRIPT_DIR}/generate-r2-index.sh" "${IDX[@]+"${IDX[@]}"}"

${PURGE} && cf_purge files "${KEY}" "${KEY}.sha256" "${MAN_KEY}"

echo "=== DELTA upload complete: ${R2_PUBLIC_URL}/${KEY} ==="
