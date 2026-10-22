#!/bin/bash
# Backfill a past official monthly ClinVar-GKM bundle into the version line (R2_LINE, default v1/1.1/).
#
# A thin wrapper over upload-gkm-to-r2.sh --month-label, which already does what a backfill needs:
#   * a month of the line's current year goes to <line>clinvar-gkm_YYYY-MM.json.gz, a prior year's month to
#     <line>archive/YYYY/clinvar-gkm_YYYY-MM.json.gz (each + .sha256);
#   * clinvar-gkm_00-latest.json.gz is repointed only when the month is the newest monthly (never by a backfill
#     of an older month);
#   * the index records the month's source_release (<export_date>).
# No Parquet: Parquet is one derived set per line (ADR 0008), never per month.
#
# Usage:
#   ./backfill-monthly-to-r2.sh <export_date> <dataset_version> <bundle_file> [--month-label=YYYY-MM] [--dry-run] [--purge]
#
# --month-label defaults to <export_date>'s month; ADR 0002 labels a monthly by ClinVar's month, which is often
# the month AFTER its source release (e.g. 2026-10 <- 2026-09-28), so pass it explicitly.
set -euo pipefail
if [[ $# -lt 3 ]]; then
  sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 1
fi
EXPORT_DATE="$1"; DATASET_VERSION="$2"; BUNDLE_FILE="$3"; shift 3
LABEL="${EXPORT_DATE:0:7}"; PASS=()
for arg in "$@"; do
  case "$arg" in
    --month-label=*) LABEL="${arg#--month-label=}" ;;
    --dry-run|--purge) PASS+=("$arg") ;;
    *) echo "ERROR: unknown argument '${arg}'" >&2; exit 1 ;;
  esac
done
exec "$(cd "$(dirname "$0")" && pwd)/upload-gkm-to-r2.sh" "${EXPORT_DATE}" "${DATASET_VERSION}" "${BUNDLE_FILE}" \
  "--month-label=${LABEL}" "${PASS[@]+"${PASS[@]}"}"
