#!/bin/bash
# Month and year rollover of a version line (R2_LINE, default v1/1.1/), NCBI-style. Run when a release is posted
# (run-release.sh runs it before and after the weekly uploads); the plan comes from r2_layout.py plan_rollover:
#
#   month rollover   the first release of a new month moves the finished month's deltas (bundle, .sha256,
#                    .manifest.json) from deltas/ into deltas/YYYY-MM/, and DELETES the finished month's weekly
#                    fulls. The newest of them is kept until the new month's official monthly is posted, because
#                    it is that monthly's ADR 0002 source candidate (the monthly is a server-side copy of it); the
#                    run after the monthly is posted deletes it. Past weeks are rebuilt from a monthly + deltas.
#   year rollover    the first release of a new year moves the prior year's monthlies (+ .sha256) to
#                    archive/YYYY/ and its delta folders deltas/YYYY-MM/ to archive/YYYY/deltas/YYYY-MM/.
#
# Idempotent: when the line already matches the layout for <release_date> the plan is empty. A move is a
# size-aware server-side copy, a size check, then a delete. Moved and deleted paths are purged from the CDN
# (they are cached as immutable). The index is regenerated when anything changed.
#
# Usage: ./r2-rollover.sh <release_date> [--dry-run] [--no-purge] [--listing FILE]
#
# --listing FILE plans against a saved listing (`aws s3 ls --recursive` output or "SIZE KEY" lines) instead of
# the live bucket; it implies --dry-run (used to test a year rollover on a synthetic listing).
set -euo pipefail

[[ $# -ge 1 ]] || { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
RELEASE="$1"; shift
[[ "$RELEASE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { echo "ERROR: release_date must be YYYY-MM-DD" >&2; exit 1; }
DRY_RUN=false; PURGE=true; LISTING=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --no-purge) PURGE=false; shift ;;
    --listing) LISTING="$2"; DRY_RUN=true; shift 2 ;;
    *) echo "ERROR: unknown argument '$1'" >&2; exit 1 ;;
  esac
done
export DRY_RUN

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=r2-common.sh
. "${SCRIPT_DIR}/r2-common.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

echo "=== rollover of ${R2_LINE} for release ${RELEASE} ==="
${DRY_RUN} && echo "  Mode: DRY RUN"
if [[ -n "${LISTING}" ]]; then cp "${LISTING}" "${TMP}/listing.txt"; else r2_listing "${R2_LINE}" "${TMP}/listing.txt"; fi
r2_layout rollover --listing "${TMP}/listing.txt" --line "${R2_LINE}" --release "${RELEASE}" > "${TMP}/plan.txt"

sed -n 's/^# /  note: /p' "${TMP}/plan.txt"
awk '$1 == "MOVE" {n++; b += $2} END {printf "  moves:   %d objects, %.2f GB\n", n, b / 1e9}' "${TMP}/plan.txt"
awk '$1 == "DELETE" {n++; b += $2} END {printf "  deletes: %d objects, %.2f GB\n", n, b / 1e9}' "${TMP}/plan.txt"
if ! grep -q -E '^(MOVE|DELETE) ' "${TMP}/plan.txt"; then
  echo "  nothing to do"; exit 0
fi

OLD_KEYS=()
while read -r op size a b; do
  case "${op}" in
    MOVE) r2_move "${a}" "${b}" "${size}"; OLD_KEYS+=("${a}") ;;
    DELETE) r2_rm "${a}"; OLD_KEYS+=("${a}") ;;
  esac
done < <(grep -E '^(MOVE|DELETE) ' "${TMP}/plan.txt")

[[ -n "${LISTING}" ]] && exit 0
IDX=(); ${DRY_RUN} && IDX+=(--dry-run)
"${SCRIPT_DIR}/generate-r2-index.sh" "${IDX[@]+"${IDX[@]}"}"
${PURGE} && cf_purge files "${OLD_KEYS[@]}"
echo "=== rollover complete ==="
