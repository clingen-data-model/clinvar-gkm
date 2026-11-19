#!/bin/bash
# Freeze a superseded version line (ADR 0008 (b), (c); maintainer decision 2026-11-18). DRY RUN unless --apply.
#
# Run after the new line is published and r2_layout.LINES marks <line> frozen with superseded_by (the code on the
# release branch). The plan comes from r2_layout.py plan_freeze:
#
#   delete   every weekly full (weekly/, 00-latest_weekly included): weekly fulls are not records (ADR 0009 §4)
#            parquet/: a frozen line has no Parquet (ADR 0008 (e)); --keep-parquet defers this
#   keep     the monthlies, the 00-latest copy, archive/YYYY/, and every delta (bundle, .sha256, manifest) where the
#            line's last rollover left it. Bytes and paths do not change.
#   write    <line>MANIFEST.json (every kept bundle and delta manifest: key, size, sha256) and <line>README.txt,
#            then regenerate <line>index.json + feed.xml (status frozen, superseded_by, from LINES) and the root
#            index.json, then purge the deleted paths from the CDN.
#   verify   re-list the line and check it against MANIFEST.json and both indexes (r2_layout.py verify-frozen).
#
# The plan refuses to run while it reports a PROBLEM (an unexpected key, a bundle without a sha256 sidecar, a
# monthly with no known source_release). Re-running after a successful freeze deletes nothing; it only rewrites
# MANIFEST.json, README.txt and the indexes.
#
# Usage: ./r2-freeze-line.sh <line> [--apply] [--keep-parquet] [--no-purge] [--listing FILE [--sidecars DIR]]
#
#   <line>          e.g. v1/1.1/
#   --apply         make the changes (default: print the plan and write the files to a local folder only)
#   --keep-parquet  keep parquet/ (until the new line publishes its own Parquet); freeze again without it later
#   --listing FILE  plan against a saved listing (`aws s3 ls --recursive` output or "SIZE KEY" lines); implies the
#                   dry run. --sidecars DIR is a local mirror of the line's sidecars, delta manifests and index.json.
set -euo pipefail

[[ $# -ge 1 ]] || { sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
LINE="$1"; shift
[[ "${LINE}" == */ ]] || LINE="${LINE}/"
[[ "${LINE}" =~ ^v[0-9]+/[0-9]+\.[0-9]+/$ ]] || { echo "ERROR: line must look like v1/1.1/, got '${LINE}'" >&2; exit 1; }
APPLY=false; KEEP_PARQUET=false; PURGE=true; LISTING=""; SIDECARS=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=true; shift ;;
    --keep-parquet) KEEP_PARQUET=true; shift ;;
    --no-purge) PURGE=false; shift ;;
    --listing) LISTING="$2"; shift 2 ;;
    --sidecars) SIDECARS="$2"; shift 2 ;;
    *) echo "ERROR: unknown argument '$1'" >&2; exit 1 ;;
  esac
done
[[ -n "${LISTING}" ]] && APPLY=false
DRY_RUN=true; ${APPLY} && DRY_RUN=false
export DRY_RUN

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=r2-common.sh
. "${SCRIPT_DIR}/r2-common.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
OUT="${FREEZE_OUT_DIR:-${TMPDIR:-/tmp}/clinvar-gkm-freeze}"
FREEZE_ARGS=(); ${KEEP_PARQUET} && FREEZE_ARGS+=(--keep-parquet)

echo "=== freeze ${LINE} ==="
${DRY_RUN} && echo "  Mode: DRY RUN (nothing on R2 changes; pass --apply)"
if [[ -n "${LISTING}" ]]; then
  cp "${LISTING}" "${TMP}/listing.txt"
else
  r2_listing "${LINE}" "${TMP}/listing.txt"
  SIDECARS="${TMP}/mirror"
  mkdir -p "${SIDECARS}"
  # Read-only: the sha256 sidecars, the delta manifests (hashed for MANIFEST.json) and the line's index.json.
  aws_r2 s3 cp "s3://${R2_BUCKET}/${LINE}" "${SIDECARS}/" --recursive --quiet --exclude "*" \
    --include "*.sha256" --include "*.manifest.json" --include "index.json" --exclude "weekly/*" --exclude "parquet/*"
fi

r2_layout freeze --listing "${TMP}/listing.txt" --line "${LINE}" ${SIDECARS:+--sidecars "${SIDECARS}"} \
  --out-dir "${TMP}/out" "${FREEZE_ARGS[@]+"${FREEZE_ARGS[@]}"}" > "${TMP}/plan.txt"

sed -n 's/^# /  note: /p' "${TMP}/plan.txt" | grep -v 'note: PROBLEM' || true
sed -n 's/^# PROBLEM /  PROBLEM: /p' "${TMP}/plan.txt"
awk '$1 == "DELETE" {n++; b += $2} END {printf "  deletes: %d objects, %.2f GB\n", n, b / 1e9}' "${TMP}/plan.txt"
awk '$1 == "DELETE" { k = $3; sub("/[^/]*$", "/", k); c[k]++ } END { for (k in c) printf "    %-40s %d\n", k, c[k] }' \
  "${TMP}/plan.txt" | sort
mkdir -p "${OUT}"
cp -R "${TMP}/out/." "${OUT}/"
echo "  MANIFEST.json and README.txt written to ${OUT}/${LINE}"

if grep -q '^# PROBLEM ' "${TMP}/plan.txt"; then
  ${DRY_RUN} && { echo "  a real run would refuse: fix the PROBLEMs first"; exit 0; }
  echo "ERROR: refusing to freeze ${LINE}: fix the PROBLEMs above" >&2; exit 1
fi
${DRY_RUN} && grep '^DELETE ' "${TMP}/plan.txt" | sed 's/^DELETE [0-9]* /  [dry-run] delete: /'
${DRY_RUN} && { echo "  [dry-run] upload: ${LINE}MANIFEST.json, ${LINE}README.txt; regenerate ${LINE}index.json, feed.xml, root index.json"; exit 0; }

OLD_KEYS=()
while read -r op _ key; do
  [[ "${op}" == "DELETE" ]] || continue
  r2_rm "${key}"; OLD_KEYS+=("${key}")
done < "${TMP}/plan.txt"
r2_put "${TMP}/out/${LINE}MANIFEST.json" "${LINE}MANIFEST.json" "application/json"
r2_put "${TMP}/out/${LINE}README.txt" "${LINE}README.txt" "text/plain"
"${SCRIPT_DIR}/generate-r2-index.sh" --line "${LINE}"
${PURGE} && cf_purge files "${OLD_KEYS[@]+"${OLD_KEYS[@]}"}"

echo "--- verify ---"
r2_listing "${LINE}" "${TMP}/after.txt"
r2_cat "${LINE}index.json" > "${TMP}/index.json"
r2_cat "index.json" > "${TMP}/root.json"
r2_layout verify-frozen --listing "${TMP}/after.txt" --line "${LINE}" --manifest "${TMP}/out/${LINE}MANIFEST.json" \
  --index "${TMP}/index.json" --root "${TMP}/root.json" "${FREEZE_ARGS[@]+"${FREEZE_ARGS[@]}"}"
echo "=== ${LINE} frozen ==="
