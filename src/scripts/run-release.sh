#!/bin/bash
#
# run-release.sh — end-to-end ClinVar-GKM release pipeline for a single release date.
#
# Chains the five stages that turn an ingested ClinVar release into published GKS output:
# Stage 0 (dataset_diff_on) runs ahead of stage 1 to build the {S}.diff_* drivers, and a
# version stamp (gkm_pipeline_version) is written between stages 3 and 4.
#
#   1. variation_identity   BigQuery CALL   (incremental by default; full with --full)
#   2. export-vi-to-gcs      src/scripts/export-vi-table-to-gcs.sh   -> gs://.../vi.jsonl.gz
#   3. vrsify                src/vrsify/vrsify.sh   (external vrs-python; needs local services)
#   4. vrs-to-bq             src/scripts/vrs-to-bq-table.sh
#                            (Cloud Run transform -> load gkm_vrs -> gkm_* procs)
#   5. release               publish to the version line R2_LINE (default v1/1.1/; layout in r2_layout.py):
#                            r2-rollover.sh (month/year rollover now that this release is posted),
#                            release-gkm.sh --weekly (this release's weekly FULL -> weekly/),
#                            any due official monthly (a server-side copy of its ADR 0002 source
#                            release's weekly full, or a re-export when that is gone), r2-rollover.sh
#                            again (drops the kept source candidate once the monthly is posted),
#                            release-gkm-delta.sh (the weekly DELTA -> deltas/), then
#                            release-gkm-parquet.sh (the one Parquet set -> parquet/, overwritten)
#
# Stages 1 and 2 are incremental by default (recompute only changed variations, carry the
# rest forward). Stage 4 self-corrects between incremental and full loads. --full forces a
# full rebuild across stages 1-2 AND forces the incremental gks procs (catvar + scv) full
# in Stage 4 (propagated as GKS_FULL to vrs-to-bq-table.sh) — REQUIRED after any version-invalidating change (the
# variation_identity transform, or the vrsify pin in src/vrsify/requirements.txt). The
# version-stamp gate written between stages 3 and 4 is always the honest plain build-path
# hash, even on --full, so a --full release still leaves a valid baseline for next week's
# normal run to resume incremental from.
#
# --full-procs forces ONLY the gkm procs of Stage 4 full (GKS_FULL=true into vrs-to-bq-table.sh): every
# catvar/scv/rcv/vcv proc runs its full wrapper. Stages 1-3 (variation_identity, export, vrsify) and the
# gkm_vrs load stay incremental, so only the ~changed variations are re-normalized. This is the weekly mode
# after 1.1.0 until ADR 0007 workstream 3 decides on the incremental gkm machinery (the incremental wrappers
# were seen to fall back to full silently). --full implies it.
#
# Stage 5 publishes to the public R2 bucket. Use --dry-run to run everything but have the
# release stage only print what it would upload (no R2 writes) — use it for test runs.
# NOTE: --dry-run still writes the pipeline_version stamp to BigQuery; --dry-run only gates
# Stage 5 / R2 upload.
#
# USAGE:
#   ./src/scripts/run-release.sh YYYY-MM-DD [--full | --full-procs] [--dry-run] [--start-step N]
#
#   --full          full rebuild of stages 1-2 and every gkm proc in stage 4 (reseed the baseline);
#                   the version-stamp gate is unaffected, so next week resumes incremental
#   --full-procs    only the stage-4 gkm procs full; variation_identity, export, vrsify and the
#                   gkm_vrs load stay incremental
#   --dry-run       stage 5 (release scripts) runs in dry-run: no R2 upload / no GCS writes
#   --start-step N  begin at stage N (1-5); default 1. Stage 3 (vrsify) needs the local
#                   SeqRepo/UTA/gene-norm services — see src/vrsify/README.md.
#
# NOTE: stage 3 cannot run in CI/headless environments; run it on a host with the
# variation-normalizer service topology, or use --start-step to run the BigQuery-side
# stages separately from vrsify.

set -o errexit
set -o nounset
set -o pipefail

PROJECT_ID="${PROJECT_ID:-clingen-dev}"
# Keep gcloud/bq defaulting to the same project so the bq wrapper does not prepend a
# mismatched --project_id (a wrong gcloud default can wedge bq on status polling).
export CLOUDSDK_CORE_PROJECT="${PROJECT_ID}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

DATE=""
FULL=false
FULL_PROCS=false
DRY_RUN=false
START_STEP=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --full) FULL=true; shift ;;
    --full-procs) FULL_PROCS=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    --start-step) START_STEP="${2:?--start-step needs a number}"; shift 2 ;;
    --start-step=*) START_STEP="${1#*=}"; shift ;;
    -*) echo "ERROR: unknown flag: $1" >&2; exit 1 ;;
    *) if [[ -z "$DATE" ]]; then DATE="$1"; shift; else echo "ERROR: unexpected arg: $1" >&2; exit 1; fi ;;
  esac
done

if [[ -z "$DATE" ]]; then
  echo "Usage: $0 YYYY-MM-DD [--full | --full-procs] [--dry-run] [--start-step N]" >&2
  exit 1
fi

$FULL && FULL_PROCS=true   # --full implies the procs full
echo "=== run-release ${DATE} (full=${FULL}, full-procs=${FULL_PROCS}, dry-run=${DRY_RUN}, start-step=${START_STEP}, project=${PROJECT_ID}) ==="

# --- Stage 0: dataset diff (produces {S}.diff_* — drivers for all incremental procs) ----
# Idempotent (CREATE OR REPLACE). On the first release it emits a warning and writes no
# diff tables, which correctly makes the incremental guards fall back to a full rebuild.
if (( START_STEP <= 1 )); then
  echo ">>> [0/5] dataset_diff_on (build {S}.diff_* drivers)"
  bq query --project_id="${PROJECT_ID}" --use_legacy_sql=false \
    "CALL \`clinvar_ingest.dataset_diff_on\`(DATE '${DATE}')"
fi

# --- Stage 1: variation_identity -------------------------------------------------------
if (( START_STEP <= 1 )); then
  if $FULL; then
    echo ">>> [1/5] variation_identity (FULL rebuild)"
    bq query --project_id="${PROJECT_ID}" --use_legacy_sql=false \
      "CALL \`clinvar_ingest.variation_identity\`(DATE '${DATE}', FALSE)"
  else
    echo ">>> [1/5] variation_identity_incremental"
    bq query --project_id="${PROJECT_ID}" --use_legacy_sql=false \
      "CALL \`clinvar_ingest.variation_identity_incremental\`(DATE '${DATE}', FALSE)"
  fi
fi

# --- Stage 2: export variation_identity to GCS -----------------------------------------
if (( START_STEP <= 2 )); then
  echo ">>> [2/5] export-vi-table-to-gcs.sh"
  if $FULL; then
    "${REPO_ROOT}/src/scripts/export-vi-table-to-gcs.sh" "${DATE}" --full
  else
    "${REPO_ROOT}/src/scripts/export-vi-table-to-gcs.sh" "${DATE}"
  fi
fi

# --- Stage 3: vrsify (external vrs-python) ---------------------------------------------
if (( START_STEP <= 3 )); then
  echo ">>> [3/5] vrsify.sh (vrs-python; requires local SeqRepo/UTA/gene-norm services)"
  "${REPO_ROOT}/src/vrsify/vrsify.sh" "${DATE}"
fi

# --- Version stamp: record provenance + the carry-forward gate key -----------------------
# audit_stamp = full git describe (provenance, always). gate_key = last commit touching the
# build-relevant paths (only advances when build logic changes; docs-only commits don't).
# gate_key is ALWAYS the honest plain build-path hash, even on --full: a forced full rebuild
# this week must still leave a valid baseline so next week's normal run can resume
# incremental via a matching gate. --full forces catvar full THIS week via an explicit flag
# propagated into Stage 4 below, not by poisoning the gate.
if (( START_STEP <= 4 )); then
  AUDIT_STAMP="$(git -C "${REPO_ROOT}" describe --tags --always --dirty)"
  GATE_KEY="$(git -C "${REPO_ROOT}" log -1 --format=%H -- src/procedures src/scripts src/vrsify)"
  # These values are spliced into a single-quoted SQL literal below; a stray single quote
  # would break out of it. Abort rather than emit malformed SQL.
  case "${AUDIT_STAMP}${GATE_KEY}" in *\'*) echo "ERROR: version stamp contains a single quote" >&2; exit 1;; esac
  echo ">>> stamping pipeline_version audit=${AUDIT_STAMP} gate=${GATE_KEY}"
  bq query --project_id="${PROJECT_ID}" --use_legacy_sql=false \
    "CALL \`clinvar_ingest.gkm_pipeline_version\`(DATE '${DATE}', '${AUDIT_STAMP}', '${GATE_KEY}')"
fi

# --- Stage 4: transform -> load gkm_vrs -> gkm_* procs ---------------------------------
if (( START_STEP <= 4 )); then
  echo ">>> [4/5] vrs-to-bq-table.sh (transform, load gkm_vrs, run gkm_* procs)"
  # GKS_FULL forces the full proc wrappers; it does not change the gkm_vrs load (that follows the data).
  GKS_FULL="${FULL_PROCS}" "${REPO_ROOT}/src/scripts/vrs-to-bq-table.sh" "${DATE}"
fi

# --- Monthly-full trigger helpers (ClinVar authoritative index) -----------------------
# The monthly full bundle is anchored to ClinVar's own monthly cadence, not our weekly
# release cadence. ClinVar publishes ClinVarVCVRelease_YYYY-MM.xml.gz at the FTP index
# early each month; its appearance is the ONLY signal we use (we never ingest that XML).
# Our monthly full for YYYY-MM = the most recent of OUR builds with release date strictly
# before ClinVar's monthly Released datetime, re-exported into the YYYY-MM slot (label from
# ClinVar, content from our build). See docs/superpowers/specs/2026-08-24-clinvar-index-
# monthly-trigger-design.md.
CLINVAR_XML_INDEX="https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/"
R2_LINE="${R2_LINE:-v1/1.1/}"
export R2_LINE
# shellcheck source=r2-common.sh
. "${REPO_ROOT}/src/scripts/r2-common.sh"

# Emit "YYYY-MM<TAB>YYYY-MM-DD HH:MM:SS" per ClinVar monthly release, ascending. Parses the
# autoindex: after tag-strip the fields are filename, size, released-date, released-time,
# modified-date, modified-time. Excludes the sibling .xml.gz.md5 rows.
clinvar_monthlies() {
  curl -sf --max-time 60 "${CLINVAR_XML_INDEX}" 2>/dev/null \
    | sed -E 's/<[^>]+>/ /g' \
    | tr -s ' ' \
    | awk '$1 ~ /^ClinVarVCVRelease_[0-9]{4}-[0-9]{2}\.xml\.gz$/ {
             print substr($1, 19, 7) "\t" $3 " " $4 }' \
    | sort -u
}

# Echo the newest YYYY-MM already published as an official monthly in the line (top level or archive/YYYY/),
# or empty. (Before the v1/1.1/ layout this listed the retired bucket-root datasets/ and always came back empty.)
r2_latest_published_month() {
  aws_r2 s3 ls "s3://${R2_BUCKET}/${R2_LINE}" --recursive 2>/dev/null \
    | awk '{print $4}' \
    | sed -n -E "s#^${R2_LINE}(archive/[0-9]{4}/)?clinvar-gkm_([0-9]{4}-[0-9]{2})\.json\.gz\$#\2#p" \
    | sort | tail -n1
}

# True if the dataset carries the published GKM product (marker table present). The GKM era
# began 2026-06-27; older raw clinvar_ingest datasets have no gkm_dict_* tables to export.
# bq show is location-agnostic (INFORMATION_SCHEMA queries need the dataset's region).
dataset_is_gkm_capable() {
  bq show --project_id="${PROJECT_ID}" --format=none "$1.gkm_pipeline_version" >/dev/null 2>&1
}

# Echo the newest GKM-capable dataset date (YYYY-MM-DD) with release date strictly before the
# cutoff datetime's DATE, or empty. Walks newest-first, skipping raw datasets not yet GKM-built
# (date-strict "<" implements "before that datetime" — ClinVar monthlies land ~00:07 early
# month, so a same-date weekly collision is unlikely).
resolve_source_date() {
  local cutoff_date="${1:0:10}" d
  while IFS= read -r d; do
    [[ -n "${d}" ]] || continue
    if dataset_is_gkm_capable "clinvar_${d//-/_}_${DATASET_VERSION}"; then echo "${d}"; return 0; fi
  done < <(
    bq ls --project_id="${PROJECT_ID}" --max_results=100000 2>/dev/null \
      | awk '{print $1}' \
      | grep -E "^clinvar_[0-9]{4}_[0-9]{2}_[0-9]{2}_${DATASET_VERSION}$" \
      | sed -E 's/^clinvar_([0-9]{4})_([0-9]{2})_([0-9]{2})_.*/\1-\2-\3/' \
      | awk -v c="${cutoff_date}" '$0 < c' \
      | sort -r
  )
}

# Publish an official monthly for any ClinVar monthly strictly NEWER than the latest already in the line (the
# bound keeps this cheap and stops it from re-touching history). Normally 0 or 1 per run. The monthly is a
# server-side copy of its source release's weekly full when that is still in weekly/ (r2-rollover.sh keeps the
# newest weekly full of the finished month until this happens); otherwise it is re-exported from BigQuery.
# Bootstrap (empty line) is a manual step (republish-v1.sh). Every failure here is non-fatal to the delta.
publish_due_monthly_fulls() {
  local latest_pub month cv_dt src_date src_key
  latest_pub="$(r2_latest_published_month)" || true
  if [[ -z "${latest_pub}" ]]; then
    echo "    monthly trigger: no monthly in ${R2_LINE} yet; skipping (bootstrap is republish-v1.sh)"
    return 0
  fi
  while IFS=$'\t' read -r month cv_dt; do
    [[ -n "${month}" ]] || continue
    [[ "${month}" > "${latest_pub}" ]] || continue
    src_date="$(resolve_source_date "${cv_dt}")" || true
    if [[ -z "${src_date}" ]]; then
      echo "    monthly ${month}: no GKM-built release before ${cv_dt} yet; will retry next run"
      continue
    fi
    src_key="${R2_LINE}weekly/clinvar-gkm_${src_date:0:4}-${src_date:5:2}${src_date:8:2}.json.gz"
    local up_args=("${src_date}" "${DATASET_VERSION}" "-" "--month-label=${month}" "--from-weekly")
    $DRY_RUN && up_args+=("--dry-run")
    if [[ -n "$(r2_size "${src_key}")" ]]; then
      echo ">>> [5/5] ClinVar monthly ${month} (released ${cv_dt}) -> copy of the ${src_date} weekly full"
      "${REPO_ROOT}/src/scripts/upload-gkm-to-r2.sh" "${up_args[@]}" \
        || echo "WARNING: monthly ${month} copy from ${src_key} failed; continuing" >&2
    else
      echo ">>> [5/5] ClinVar monthly ${month} (released ${cv_dt}) -> re-export from ${src_date} (no weekly full)"
      local full_args=("${src_date}" "${DATASET_VERSION}" "--month-label=${month}")
      $DRY_RUN && full_args+=("--dry-run")
      "${REPO_ROOT}/src/scripts/release-gkm.sh" "${full_args[@]}" \
        || echo "WARNING: monthly ${month} from ${src_date} failed; continuing" >&2
    fi
  done < <(clinvar_monthlies)
}

# --- Stage 5: publish to the version line ------------------------------------------------
if (( START_STEP <= 5 )); then
  echo ">>> [5/5] release to ${R2_LINE} (rollover, weekly full, monthly, delta, Parquet)"
  # release-gkm.sh needs the dataset version (e.g. v2_5_0); derive it from the dataset name.
  DATE_US="${DATE//-/_}"
  DATASET_ID="$(bq ls --project_id="${PROJECT_ID}" --max_results=10000 \
    | awk '{$1=$1; print}' | grep "^clinvar_${DATE_US}_" | head -n 1)"
  if [[ -z "${DATASET_ID}" ]]; then
    echo "ERROR: no dataset found matching clinvar_${DATE_US}_* in ${PROJECT_ID}" >&2
    exit 1
  fi
  DATASET_VERSION="${DATASET_ID#clinvar_"${DATE_US}"_}"
  echo "    dataset=${DATASET_ID} version=${DATASET_VERSION}"

  REL_ARGS=("${DATE}" "${DATASET_VERSION}"); $DRY_RUN && REL_ARGS+=("--dry-run")
  ROLL_ARGS=("${DATE}"); $DRY_RUN && ROLL_ARGS+=("--dry-run")

  # Month/year rollover first: posting this release may start a new month (or year).
  echo ">>> [5/5] rollover for ${DATE}"
  "${REPO_ROOT}/src/scripts/r2-rollover.sh" "${ROLL_ARGS[@]}"

  # This release's weekly FULL. Non-fatal: the delta is the record; a monthly whose source weekly full is
  # missing is re-exported instead.
  echo ">>> [5/5] publishing weekly FULL for ${DATE}"
  "${REPO_ROOT}/src/scripts/release-gkm.sh" "${REL_ARGS[@]}" --weekly \
    || echo "WARNING: weekly FULL ${DATE} failed; continuing to the monthly trigger and the delta" >&2

  # Official monthly, BEFORE the delta, so the delta's checkpoint_full can resolve to it.
  publish_due_monthly_fulls

  # Drop the finished month's kept weekly full once the new month's monthly is posted.
  "${REPO_ROOT}/src/scripts/r2-rollover.sh" "${ROLL_ARGS[@]}"

  echo ">>> [5/5] publishing weekly DELTA for ${DATE}"
  "${REPO_ROOT}/src/scripts/release-gkm-delta.sh" "${REL_ARGS[@]}"

  # The one Parquet set (parquet/) is rebuilt from THIS release's dataset, the newest JSON state. Non-fatal:
  # the bundles are the record; parquet/manifest.json says which release the set was built from.
  echo ">>> [5/5] rebuilding the Parquet set from ${DATE}"
  # --purge clears the CDN copy of parquet/ (cached 1 day by the Parquet cache rule).
  "${REPO_ROOT}/src/scripts/release-gkm-parquet.sh" "${REL_ARGS[@]}" --purge \
    || echo "WARNING: Parquet rebuild from ${DATE} failed; parquet/ still holds the previous set" >&2
fi

echo "=== run-release ${DATE} complete ==="
