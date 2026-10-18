#!/bin/bash
# republish-v1.sh — runbook driver for re-publishing EVERY /v1/ release in place (the 1.1.0 backfill:
# 4 monthly fulls + 00-latest, every Parquet set, 15 deltas). Run AFTER the 16 datasets are rebuilt and
# every gate in docs/superpowers/plans/2026-10-18-proposition-reorganization.md §6.4 passes. Every
# subcommand that writes to R2 is a separate, user-confirmed step; each honors --dry-run.
#
# Usage:
#   ./republish-v1.sh list
#   ./republish-v1.sh backup  [--dry-run]                 # copy v1/** -> v1/_backup/pre-1.1.0/** (server-side)
#   ./republish-v1.sh stage   <target|all>                # export + assemble + Parquet, NO upload (STAGE_DIR)
#   ./republish-v1.sh upload  <target|all> [--dry-run] [--purge]
#   ./republish-v1.sh index   [--dry-run]                 # regenerate v1/index.json + v1/feed.xml
#
# <target> is a monthly label (2026-07) or a delta date (2026-07-06); "all" runs fulls (month order),
# then deltas (date order), so 00-latest ends on the newest of each. upload passes --replace-sections,
# which deletes the dated dir's stale section files (e.g. the old var*-proposition.parquet) after the new
# set is uploaded. --purge purges each re-published dated path from the CDN (needs CF_ZONE_ID +
# CF_PURGE_TOKEN; ADR 0005). Staged files live in STAGE_DIR (default /tmp): a full is about 4.8 GB plus
# about 12 GB of Parquet, so stage + upload one full at a time when disk is short.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STAGE_DIR="${STAGE_DIR:-/tmp}"
export STAGE_DIR

# monthly label | source release date | dataset version (ADR 0002 mapping; matches the published index)
FULLS="
2026-07 2026-06-27 v2_5_0
2026-08 2026-08-04 v2_5_0
2026-09 2026-08-29 v2_6_0
2026-10 2026-09-28 v2_6_0
"
# delta release date | dataset version
DELTAS="
2026-07-06 v2_5_0
2026-07-15 v2_5_0
2026-07-20 v2_5_0
2026-07-27 v2_5_0
2026-08-04 v2_5_0
2026-08-08 v2_5_0
2026-08-16 v2_5_0
2026-08-22 v2_5_0
2026-08-29 v2_6_0
2026-09-05 v2_6_0
2026-09-13 v2_6_0
2026-09-23 v2_6_0
2026-09-28 v2_6_0
2026-10-04 v2_6_0
2026-10-11 v2_6_0
"

R2_BUCKET="clinvar-gkm"
R2_ENDPOINT="https://09208aa33790838db213a21f630c33e7.r2.cloudflarestorage.com"
R2_PROFILE="r2"
R2_PREFIX="${R2_PREFIX:-v1/}"
BACKUP_PREFIX="${R2_PREFIX}_backup/pre-1.1.0/"

CMD="${1:-}"; [[ $# -gt 0 ]] && shift
TARGET=""
DRY_RUN=false; PURGE=false
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --purge) PURGE=true ;;
    -*) echo "ERROR: unknown flag '${arg}'" >&2; exit 1 ;;
    *) TARGET="$arg" ;;
  esac
done

usage() { sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

# Echo the matching "label date version" (full) or "date version" (delta) rows for TARGET.
fulls_for() { echo "$FULLS" | awk -v t="$1" 'NF==3 && (t=="all" || $1==t)'; }
deltas_for() { echo "$DELTAS" | awk -v t="$1" 'NF==2 && (t=="all" || $1==t)'; }

require_target() {
  [[ -n "$TARGET" ]] || { echo "ERROR: ${CMD} needs a target (see: $0 list)" >&2; exit 1; }
  if [[ -z "$(fulls_for "$TARGET")$(deltas_for "$TARGET")" ]]; then
    echo "ERROR: unknown target '${TARGET}' (see: $0 list)" >&2; exit 1
  fi
}

aws_r2() { aws --endpoint-url "${R2_ENDPOINT}" --profile "${R2_PROFILE}" "$@"; }

backup() {
  # Size-aware server-side copy (.claude/rules/scripts.md): >=2 GB via `s3 cp --copy-props none`,
  # smaller via `s3api copy-object` (R2 lacks GetObjectTagging / x-amz-tagging-directive).
  local n=0 bytes=0 size key rest
  echo "=== backup: s3://${R2_BUCKET}/${R2_PREFIX} -> s3://${R2_BUCKET}/${BACKUP_PREFIX} ==="
  while read -r _ _ size key; do
    [[ -n "${key:-}" ]] || continue
    rest="${key#"${R2_PREFIX}"}"
    [[ "$rest" == _backup/* ]] && continue
    n=$((n + 1)); bytes=$((bytes + size))
    if $DRY_RUN; then echo "  [dry-run] copy ${key} -> ${BACKUP_PREFIX}${rest} (${size} B)"; continue; fi
    if [[ "$size" -ge 2147483648 ]]; then
      aws_r2 s3 cp "s3://${R2_BUCKET}/${key}" "s3://${R2_BUCKET}/${BACKUP_PREFIX}${rest}" --copy-props none --quiet
    else
      aws_r2 s3api copy-object --bucket "${R2_BUCKET}" --key "${BACKUP_PREFIX}${rest}" \
        --copy-source "${R2_BUCKET}/${key}" >/dev/null
    fi
  done < <(aws_r2 s3 ls "s3://${R2_BUCKET}/${R2_PREFIX}" --recursive)
  if $DRY_RUN; then echo "  ${n} objects, ${bytes} bytes would be copied."
  else echo "  ${n} objects, ${bytes} bytes copied."; fi
}

stage() {
  require_target
  local label date ver
  while read -r label date ver; do
    [[ -n "$label" ]] || continue
    echo "=== stage full ${label} (from ${date}, ${ver}) -> ${STAGE_DIR} ==="
    "${SCRIPT_DIR}/release-gkm.sh" "$date" "$ver" "--month-label=${label}" --no-upload
  done < <(fulls_for "$TARGET")
  while read -r date ver; do
    [[ -n "$date" ]] || continue
    echo "=== stage delta ${date} (${ver}) -> ${STAGE_DIR} ==="
    "${SCRIPT_DIR}/release-gkm-delta.sh" "$date" "$ver" --no-upload
  done < <(deltas_for "$TARGET")
}

upload() {
  require_target
  local flags=(--replace-sections) label date ver
  $DRY_RUN && flags+=(--dry-run)
  $PURGE && flags+=(--purge)
  while read -r label date ver; do
    [[ -n "$label" ]] || continue
    local bundle="${STAGE_DIR}/clinvar-gkm-${date}.json.gz" pq="${STAGE_DIR}/clinvar-gkm-${date}-parquet"
    $DRY_RUN || [[ -f "$bundle" && -d "$pq" ]] || { echo "ERROR: ${label} not staged (${bundle}, ${pq}/)" >&2; exit 1; }
    echo "=== upload full ${label} ==="
    "${SCRIPT_DIR}/upload-gkm-to-r2.sh" "$date" "$ver" "$bundle" "--parquet-dir=${pq}" \
      "--month-label=${label}" "${flags[@]}"
  done < <(fulls_for "$TARGET")
  while read -r date ver; do
    [[ -n "$date" ]] || continue
    local bundle="${STAGE_DIR}/clinvar-gkm-delta-${date}.json.gz"
    local manifest="${STAGE_DIR}/clinvar-gkm-delta-${date}-manifest.json"
    local pq="${STAGE_DIR}/clinvar-gkm-delta-${date}-parquet"
    $DRY_RUN || [[ -f "$bundle" && -f "$manifest" ]] || { echo "ERROR: delta ${date} not staged (${bundle}, ${manifest})" >&2; exit 1; }
    echo "=== upload delta ${date} ==="
    "${SCRIPT_DIR}/upload-gkm-delta-to-r2.sh" "$date" "$bundle" "$manifest" "--parquet-dir=${pq}" "${flags[@]}"
  done < <(deltas_for "$TARGET")
}

case "$CMD" in
  list)
    echo "fulls (label  source  version):"; echo "$FULLS" | awk 'NF' | sed 's/^/  /'
    echo "deltas (date  version):"; echo "$DELTAS" | awk 'NF' | sed 's/^/  /' ;;
  backup) backup ;;
  stage) stage ;;
  upload) upload ;;
  index)
    args=(); $DRY_RUN && args+=(--dry-run)
    "${SCRIPT_DIR}/generate-r2-index.sh" "${args[@]+"${args[@]}"}" ;;
  *) usage ;;
esac
