#!/bin/bash
# Upload a ClinVar-GKM FULL bundle to its place in the version line (R2_LINE, default v1/1.1/; layout in
# r2_layout.py). Two kinds of full, NCBI-style:
#
#   --weekly                 the weekly full of <export_date>:
#                              <line>weekly/clinvar-gkm_YYYY-MMDD.json.gz (+ .sha256)
#                              <line>weekly/clinvar-gkm_00-latest_weekly.json.gz (+ .sha256), when it is the newest
#   --month-label=YYYY-MM    the official monthly (ADR 0002: <export_date> is its source release):
#                              <line>clinvar-gkm_YYYY-MM.json.gz (+ .sha256), or <line>archive/YYYY/ for a prior year
#                              <line>clinvar-gkm_00-latest.json.gz (+ .sha256), when it is the newest monthly
#     --from-weekly          make the monthly a server-side copy of weekly/clinvar-gkm_<export_date>.json.gz
#                            (no local bundle; pass "-" as bundle_file). Fails if that weekly full is not in R2.
#
# Without --weekly or --month-label the bundle is the monthly of <export_date>'s month (the old behaviour; prefer
# an explicit --month-label). Each .sha256 sidecar is in `sha256sum -c` format. A weekly full older than the line's
# current month is refused (finished months keep no weekly fulls). Month and year rollover are not done here:
# run-release.sh runs r2-rollover.sh. The index is regenerated, recording the monthly's source_release.
#
# Usage:
#   ./upload-gkm-to-r2.sh <export_date> <dataset_version> <bundle_file|-> [--weekly | --month-label=YYYY-MM
#                         [--from-weekly]] [--dry-run] [--purge]
#
# --purge purges the CDN copy of the dated path written; only needed when overwriting an existing dated file.
set -euo pipefail

if [[ $# -lt 3 ]]; then
  sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 1
fi
EXPORT_DATE="$1"; DATASET_VERSION="$2"; BUNDLE_FILE="$3"; shift 3
[[ "$EXPORT_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { echo "ERROR: export_date must be YYYY-MM-DD, got '${EXPORT_DATE}'" >&2; exit 1; }

DRY_RUN=false; PURGE=false; WEEKLY=false; FROM_WEEKLY=false; MONTH_LABEL=""
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --purge) PURGE=true ;;
    --weekly) WEEKLY=true ;;
    --from-weekly) FROM_WEEKLY=true ;;
    --month-label=*) MONTH_LABEL="${arg#--month-label=}" ;;
    *) echo "ERROR: unknown argument '${arg}'" >&2; exit 1 ;;
  esac
done
if [[ -n "${MONTH_LABEL}" ]] && ! [[ "${MONTH_LABEL}" =~ ^[0-9]{4}-[0-9]{2}$ ]]; then
  echo "ERROR: --month-label must be YYYY-MM, got '${MONTH_LABEL}'" >&2; exit 1
fi
if ${WEEKLY} && { [[ -n "${MONTH_LABEL}" ]] || ${FROM_WEEKLY}; }; then
  echo "ERROR: --weekly cannot be combined with --month-label / --from-weekly" >&2; exit 1
fi
${WEEKLY} || [[ -n "${MONTH_LABEL}" ]] || MONTH_LABEL="${EXPORT_DATE:0:7}"
export DRY_RUN

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=r2-common.sh
. "${SCRIPT_DIR}/r2-common.sh"

COMPACT="${EXPORT_DATE:0:4}-${EXPORT_DATE:5:2}${EXPORT_DATE:8:2}"
WEEKLY_KEY="${R2_LINE}weekly/clinvar-gkm_${COMPACT}.json.gz"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

echo "=== ClinVar-GKM FULL upload (${R2_LINE}) ==="
echo "  Release:  ${EXPORT_DATE} (${DATASET_VERSION})"
if ${WEEKLY}; then echo "  Kind:     weekly full"; else echo "  Kind:     monthly ${MONTH_LABEL}$(${FROM_WEEKLY} && echo ' (copy of the weekly full)')"; fi
${DRY_RUN} && echo "  Mode:     DRY RUN"

if ! ${FROM_WEEKLY} && ! ${DRY_RUN} && [[ ! -f "${BUNDLE_FILE}" ]]; then
  echo "ERROR: bundle not found: ${BUNDLE_FILE}" >&2; exit 1
fi

r2_listing "${R2_LINE}" "${TMP}/listing.txt"
CUR_MONTH="$(r2_layout current-month --listing "${TMP}/listing.txt" --line "${R2_LINE}")"

local_sha() {
  if [[ -f "${BUNDLE_FILE}" ]]; then shasum -a 256 "${BUNDLE_FILE}" | awk '{print $1}'
  else echo "0000000000000000000000000000000000000000000000000000000000000000"; fi
}

INDEX_ARGS=(); ${DRY_RUN} && INDEX_ARGS+=(--dry-run)
PURGE_KEYS=()

if ${WEEKLY}; then
  if [[ -n "${CUR_MONTH}" && "${EXPORT_DATE:0:7}" < "${CUR_MONTH}" ]]; then
    echo "ERROR: ${EXPORT_DATE} is before the line's current month ${CUR_MONTH}; finished months keep no weekly fulls" >&2
    exit 1
  fi
  NEWEST_WEEKLY="$(awk '{print $4}' "${TMP}/listing.txt" \
    | sed -n "s|^${R2_LINE}weekly/clinvar-gkm_\([0-9]\{4\}-[0-9]\{4\}\)\.json\.gz$|\1|p" | sort | tail -n1)"
  SHA="$(local_sha)"
  echo "--- weekly full -> ${WEEKLY_KEY} ---"
  r2_put "${BUNDLE_FILE}" "${WEEKLY_KEY}"
  r2_put_sidecar "${SHA}" "${WEEKLY_KEY}"
  if [[ -z "${NEWEST_WEEKLY}" || ! "${COMPACT}" < "${NEWEST_WEEKLY}" ]]; then
    LATEST_KEY="${R2_LINE}weekly/clinvar-gkm_00-latest_weekly.json.gz"
    echo "--- ${LATEST_KEY} (server-side copy) ---"
    r2_copy "${WEEKLY_KEY}" "${LATEST_KEY}" "$( [[ -f "${BUNDLE_FILE}" ]] && wc -c < "${BUNDLE_FILE}" | tr -d ' ' )"
    r2_put_sidecar "${SHA}" "${LATEST_KEY}"
  else
    echo "  (not the newest weekly full: ${NEWEST_WEEKLY} is newer; 00-latest_weekly unchanged)"
  fi
  echo "  sha256: ${SHA}"
  PURGE_KEYS+=("${WEEKLY_KEY}" "${WEEKLY_KEY}.sha256")
else
  YEAR_NOW="${CUR_MONTH:-${MONTH_LABEL}}"; YEAR_NOW="${YEAR_NOW:0:4}"
  if [[ "${MONTH_LABEL:0:4}" < "${YEAR_NOW}" ]]; then DIR="${R2_LINE}archive/${MONTH_LABEL:0:4}/"; else DIR="${R2_LINE}"; fi
  MONTHLY_KEY="${DIR}clinvar-gkm_${MONTH_LABEL}.json.gz"
  NEWEST_MONTHLY="$(awk '{print $4}' "${TMP}/listing.txt" \
    | sed -n "s|^${R2_LINE}clinvar-gkm_\([0-9]\{4\}-[0-9]\{2\}\)\.json\.gz$|\1|p" | sort | tail -n1)"
  echo "--- monthly ${MONTH_LABEL} -> ${MONTHLY_KEY} (source release ${EXPORT_DATE}) ---"
  if ${FROM_WEEKLY}; then
    SIZE="$(awk -v k="${WEEKLY_KEY}" '$4 == k {print $3}' "${TMP}/listing.txt")"
    [[ -n "${SIZE}" ]] || { echo "ERROR: ${WEEKLY_KEY} is not in R2; re-export instead (release-gkm.sh --month-label)" >&2; exit 2; }
    SHA="$(r2_cat "${WEEKLY_KEY}.sha256" | awk '{print $1; exit}' || true)"
    [[ "${SHA}" =~ ^[0-9a-f]{64}$ ]] || { echo "ERROR: ${WEEKLY_KEY}.sha256 missing or malformed" >&2; exit 2; }
    r2_copy "${WEEKLY_KEY}" "${MONTHLY_KEY}" "${SIZE}"
    if ! ${DRY_RUN}; then
      GOT="$(r2_size "${MONTHLY_KEY}")"
      [[ "${GOT}" == "${SIZE}" ]] || { echo "ERROR: ${MONTHLY_KEY} is ${GOT:-missing} B, expected ${SIZE}" >&2; exit 1; }
    fi
  else
    SHA="$(local_sha)"
    SIZE=""; [[ -f "${BUNDLE_FILE}" ]] && SIZE="$(wc -c < "${BUNDLE_FILE}" | tr -d ' ')"
    r2_put "${BUNDLE_FILE}" "${MONTHLY_KEY}"
  fi
  r2_put_sidecar "${SHA}" "${MONTHLY_KEY}"
  if [[ "${DIR}" == "${R2_LINE}" ]] && [[ -z "${NEWEST_MONTHLY}" || ! "${MONTH_LABEL}" < "${NEWEST_MONTHLY}" ]]; then
    LATEST_KEY="${R2_LINE}clinvar-gkm_00-latest.json.gz"
    echo "--- ${LATEST_KEY} (server-side copy) ---"
    r2_copy "${MONTHLY_KEY}" "${LATEST_KEY}" "${SIZE}"
    r2_put_sidecar "${SHA}" "${LATEST_KEY}"
  else
    echo "  (not the newest monthly: ${NEWEST_MONTHLY} is newer; 00-latest unchanged)"
  fi
  echo "  sha256: ${SHA}"
  INDEX_ARGS+=(--source "${MONTH_LABEL}=${EXPORT_DATE}")
  PURGE_KEYS+=("${MONTHLY_KEY}" "${MONTHLY_KEY}.sha256")
fi

if [[ -f "${SCRIPT_DIR}/r2-readme.txt" ]]; then
  r2_put "${SCRIPT_DIR}/r2-readme.txt" "${R2_LINE}README.txt" "text/plain"
fi

"${SCRIPT_DIR}/generate-r2-index.sh" "${INDEX_ARGS[@]}"

${PURGE} && cf_purge files "${PURGE_KEYS[@]}"

echo "=== FULL upload complete: ${R2_PUBLIC_URL}/${PURGE_KEYS[0]} ==="
