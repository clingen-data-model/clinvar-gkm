#!/bin/bash
#
# run-release.sh — end-to-end ClinVar-GKM release pipeline for a single release date.
#
# The clinvar-ingest pipeline (v2.7.0 and later) does everything before this script, for every release: it ingests
# the ClinVar XML, runs dataset_diff_on (the {S}.diff_* drivers) and variation_identity_incremental, exports the
# changed variations to gs://clinvar-gkm/<date>/dev/vi.jsonl.gz, and its Cloud Run job clinvar-ingest-vrsify
# translates that export with vrs-python into vi-vrs-python.jsonl.gz (+ vi-vrs-python.provenance.json). The
# procedures it calls (dataset_diff_on, variation_identity, variation_vrs_changed) still live in src/procedures/,
# but this script never runs them. It chains the four steps that turn that upstream output into published GKM output:
#
#   1. cloud vrsify check    src/scripts/check-cloud-vrsify.sh: stops unless upstream has finished, i.e.
#                            vi-vrs-python.jsonl.gz and its provenance exist and the provenance names the current
#                            vi.jsonl.gz (same md5 and size). Read-only; it fails at once rather than wait. It also
#                            runs before a --start-step 2 run, so every gkm_vrs load is checked.
#   2. vrs-to-bq             version stamp (gkm_pipeline_version), then src/scripts/vrs-to-bq-table.sh
#                            (Cloud Run transform of vi-vrs-python.jsonl.gz -> load gkm_vrs -> gkm_* procs)
#   3. release               publish to the version line R2_LINE (default v1/1.2/; layout in r2_layout.py):
#                            release-gkm-delta.sh --no-upload (build and strictly validate the DELTA) and
#                            release-gkm.sh --weekly --no-upload (build and strictly validate this release's
#                            weekly FULL), both with jsonschema-rs; a failure of either stops
#                            here, with R2 untouched,
#                            r2-rollover.sh (month/year rollover now that this release is posted),
#                            release-gkm.sh --weekly --start-step=3 (the weekly FULL -> weekly/),
#                            any due official monthly (a server-side copy of its ADR 0002 source
#                            release's weekly full, or a re-export, validated the same way, when that is
#                            gone), r2-rollover.sh
#                            again (drops the kept source candidate once the monthly is posted),
#                            release-gkm-delta.sh --start-step=3 (the weekly DELTA -> deltas/)
#   4. parquet               release-gkm-parquet.sh: gkm-bundle-parquet builds the one Parquet set from the
#                            weekly full step 3 published (on a --bootstrap-monthly release, from the line's
#                            checkpoint monthly), verifies it, and overwrites parquet/
#
# The gkm_vrs load in step 2 self-corrects between incremental and full: it carries the prior release's gkm_vrs
# forward and merges in the translated changed set, or replaces it when the translation is not the changed subset.
#
# --full-procs forces the gkm procs of step 2 full (GKS_FULL=true into vrs-to-bq-table.sh): every
# catvar/scv/rcv/vcv proc runs its full wrapper; the gkm_vrs load still follows the data. This is the weekly mode
# after 1.1.0 until ADR 0007 workstream 3 decides on the incremental gkm machinery (the incremental wrappers
# were seen to fall back to full silently).
#
# A NEW version line (a new MINOR, ADR 0009 §1/§5) starts with ONE checkpoint monthly and deltas forward. Step 3
# then refuses a normal release into a line that has no official monthly (its deltas would have no checkpoint_full),
# and --bootstrap-monthly=YYYY-MM starts the line instead: <date> must be the ADR 0002 source release of ClinVar's
# YYYY-MM monthly (checked against ClinVar's index and BigQuery, never guessed) and the line must be empty. It
# builds, validates (jsonschema-rs) and publishes <date>'s full as <line>clinvar-gkm_YYYY-MM.json.gz (+ 00-latest),
# and nothing else: no weekly full, and no delta (the previous release was built for the previous line, so that
# delta has no monthly to replay onto in this line). The next release's delta is the line's first; its
# baseline_release must be <date> (upload-gkm-delta-to-r2.sh refuses it otherwise). Step 4 still runs: with no
# weekly full, release-gkm-parquet.sh builds the line's first Parquet set from that checkpoint monthly.
#
# Steps 3 and 4 publish to the public R2 bucket. Use --dry-run to run everything but have the
# release steps only print what they would upload (no R2 writes) — use it for test runs.
# NOTE: --dry-run still writes the pipeline_version stamp and runs the procs in BigQuery; --dry-run only gates
# steps 3-4 / R2 upload.
#
# USAGE:
#   ./src/scripts/run-release.sh YYYY-MM-DD [--full-procs] [--dry-run] [--skip-parquet] [--start-step N]
#                                [--bootstrap-monthly=YYYY-MM]
#
#   --full-procs    the step-2 gkm procs full (the weekly mode); the gkm_vrs load stays data-driven
#   --dry-run       steps 3-4 (release scripts) run in dry-run: no R2 upload / no GCS writes
#   --skip-parquet  skip step 4, leaving parquet/ untouched: it keeps the previous set, and its manifest and
#                   the index keep saying which release that set was built from
#   --start-step N  begin at step N (1-4); default 1. 2 still runs the step-1 check first. --start-step 4 runs only
#                   the Parquet step for a release that is already published.
#   --bootstrap-monthly=YYYY-MM
#                   step 3 starts an EMPTY line (R2_LINE) with this checkpoint monthly (see above)

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
FULL_PROCS=false
DRY_RUN=false
SKIP_PARQUET=false
START_STEP=1
BOOTSTRAP_MONTH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --full-procs) FULL_PROCS=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    --skip-parquet) SKIP_PARQUET=true; shift ;;
    --start-step) START_STEP="${2:?--start-step needs a number}"; shift 2 ;;
    --start-step=*) START_STEP="${1#*=}"; shift ;;
    --bootstrap-monthly=*) BOOTSTRAP_MONTH="${1#*=}"; shift ;;
    -*) echo "ERROR: unknown flag: $1" >&2; exit 1 ;;
    *) if [[ -z "$DATE" ]]; then DATE="$1"; shift; else echo "ERROR: unexpected arg: $1" >&2; exit 1; fi ;;
  esac
done

if [[ -z "$DATE" ]]; then
  echo "Usage: $0 YYYY-MM-DD [--full-procs] [--dry-run] [--skip-parquet] [--start-step N] [--bootstrap-monthly=YYYY-MM]" >&2
  exit 1
fi

if ! [[ "${START_STEP}" =~ ^[1-4]$ ]]; then
  echo "ERROR: --start-step must be 1-4, got '${START_STEP}'" >&2
  exit 1
fi
if [[ -n "${BOOTSTRAP_MONTH}" ]] && ! [[ "${BOOTSTRAP_MONTH}" =~ ^[0-9]{4}-[0-9]{2}$ ]]; then
  echo "ERROR: --bootstrap-monthly must be YYYY-MM, got '${BOOTSTRAP_MONTH}'" >&2
  exit 1
fi

# Step 3 assembles the bundles, and orjson sets their layout. Check now, not hours in: the active python3 may be an
# environment without it.
if (( START_STEP <= 3 )); then
  ASSEMBLE_PYTHON="python3"; [[ -x "${REPO_ROOT}/venv/3.12/bin/python3" ]] && ASSEMBLE_PYTHON="${REPO_ROOT}/venv/3.12/bin/python3"
  "${ASSEMBLE_PYTHON}" -c 'import orjson' 2>/dev/null || {
    echo "ERROR: ${ASSEMBLE_PYTHON} ($(command -v "${ASSEMBLE_PYTHON}")) has no orjson, which sets the bundle layout. pip install orjson there, or run step 3 from another environment." >&2
    exit 1
  }
  # Step 3 validates the delta and every full strictly (rs engine) before upload; same reasoning.
  $DRY_RUN || "${SCRIPT_DIR}/validate-bundle.sh" --check-setup --engine rs
fi
echo "=== run-release ${DATE} (full-procs=${FULL_PROCS}, dry-run=${DRY_RUN}, skip-parquet=${SKIP_PARQUET}, start-step=${START_STEP}${BOOTSTRAP_MONTH:+, bootstrap-monthly=${BOOTSTRAP_MONTH}}, project=${PROJECT_ID}) ==="

# --- Step 1: check the upstream cloud vrsify output ---------------------------------------
# clinvar-ingest has run the diff, variation_identity, the vi.jsonl.gz export and the translation. Runs before every
# gkm_vrs load (also on --start-step 2), so nothing loads a translation of a stale export.
if (( START_STEP <= 2 )); then
  echo ">>> [1/4] check-cloud-vrsify.sh (vi-vrs-python.jsonl.gz must be the translation of the current vi.jsonl.gz)"
  "${REPO_ROOT}/src/scripts/check-cloud-vrsify.sh" "${DATE}"
fi

# --- Step 2: version stamp, then transform -> load gkm_vrs -> gkm_* procs ------------------
# audit_stamp = full git describe (provenance, always). gate_key = last commit touching the
# build-relevant paths (only advances when build logic changes; docs-only commits don't).
# gate_key is ALWAYS the honest plain build-path hash: --full-procs forces the procs full THIS week via an explicit
# flag propagated below, not by poisoning the gate, so next week's normal run can resume incremental.
if (( START_STEP <= 2 )); then
  AUDIT_STAMP="$(git -C "${REPO_ROOT}" describe --tags --always --dirty)"
  GATE_KEY="$(git -C "${REPO_ROOT}" log -1 --format=%H -- src/procedures src/scripts)"
  # These values are spliced into a single-quoted SQL literal below; a stray single quote
  # would break out of it. Abort rather than emit malformed SQL.
  case "${AUDIT_STAMP}${GATE_KEY}" in *\'*) echo "ERROR: version stamp contains a single quote" >&2; exit 1;; esac
  echo ">>> [2/4] stamping pipeline_version audit=${AUDIT_STAMP} gate=${GATE_KEY}"
  bq query --project_id="${PROJECT_ID}" --use_legacy_sql=false \
    "CALL \`clinvar_ingest.gkm_pipeline_version\`(DATE '${DATE}', '${AUDIT_STAMP}', '${GATE_KEY}')"

  echo ">>> [2/4] vrs-to-bq-table.sh (transform, load gkm_vrs, run gkm_* procs)"
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
R2_LINE="${R2_LINE:-v1/1.2/}"
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
# An empty line is started by --bootstrap-monthly (bootstrap_line). Every failure here is non-fatal to the delta.
publish_due_monthly_fulls() {
  local latest_pub month cv_dt src_date src_key
  latest_pub="$(r2_latest_published_month)" || true
  if [[ -z "${latest_pub}" ]]; then
    echo "    monthly trigger: no monthly in ${R2_LINE} yet; skipping (start a new line with --bootstrap-monthly)"
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
      echo ">>> [3/4] ClinVar monthly ${month} (released ${cv_dt}) -> copy of the ${src_date} weekly full"
      "${REPO_ROOT}/src/scripts/upload-gkm-to-r2.sh" "${up_args[@]}" \
        || echo "WARNING: monthly ${month} copy from ${src_key} failed; continuing" >&2
    else
      echo ">>> [3/4] ClinVar monthly ${month} (released ${cv_dt}) -> re-export from ${src_date} (no weekly full)"
      local full_args=("${src_date}" "${DATASET_VERSION}" "--month-label=${month}")
      $DRY_RUN && full_args+=("--dry-run")
      "${REPO_ROOT}/src/scripts/release-gkm.sh" "${full_args[@]}" \
        || echo "WARNING: monthly ${month} from ${src_date} failed; continuing" >&2
    fi
  done < <(clinvar_monthlies)
}

# The line's state from a read-only listing: empty | started | broken (r2_layout.py line_state).
r2_line_state() {
  local tmp rc=0
  tmp="$(mktemp)"
  r2_listing "${R2_LINE}" "${tmp}" && r2_layout line-state --listing "${tmp}" --line "${R2_LINE}" || rc=$?
  rm -f "${tmp}"
  return "${rc}"
}

# Start an empty line with ONE checkpoint monthly: this release's full, published as the official monthly
# BOOTSTRAP_MONTH. Refuses unless ClinVar has published that monthly and this release is its ADR 0002 source (the
# newest GKM-built release before ClinVar's datetime), so the label is never guessed.
bootstrap_line() {
  local cv_dt src_date
  cv_dt="$(clinvar_monthlies | awk -F '\t' -v m="${BOOTSTRAP_MONTH}" '$1 == m {print $2}')"
  if [[ -z "${cv_dt}" ]]; then
    echo "ERROR: ClinVar has not published ClinVarVCVRelease_${BOOTSTRAP_MONTH} (${CLINVAR_XML_INDEX})" >&2
    exit 1
  fi
  src_date="$(resolve_source_date "${cv_dt}")" || true
  if [[ "${src_date}" != "${DATE}" ]]; then
    echo "ERROR: the ADR 0002 source of the ${BOOTSTRAP_MONTH} monthly (ClinVar released ${cv_dt}) is" \
      "'${src_date:-none}', not ${DATE}" >&2
    exit 1
  fi
  echo ">>> [3/4] bootstrap ${R2_LINE}: checkpoint monthly ${BOOTSTRAP_MONTH} <- ${DATE} (ClinVar released ${cv_dt})"
  "${REPO_ROOT}/src/scripts/release-gkm.sh" "${REL_ARGS[@]}" "--month-label=${BOOTSTRAP_MONTH}" --no-upload
  "${REPO_ROOT}/src/scripts/release-gkm.sh" "${REL_ARGS[@]}" "--month-label=${BOOTSTRAP_MONTH}" --start-step=3
  echo "    ${R2_LINE} started. No weekly full and no delta for ${DATE}: the next release's delta is the line's"
  echo "    first, with baseline_release ${DATE}."
}

# --- Steps 3 and 4 need the dataset version (e.g. v2_5_0); derive it from the dataset name. ---
if (( START_STEP <= 4 )); then
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
fi

# --- Step 3: publish to the version line -------------------------------------------------
if (( START_STEP <= 3 )); then
  echo ">>> [3/4] release to ${R2_LINE} (rollover, weekly full, monthly, delta)"
  ROLL_ARGS=("${DATE}"); $DRY_RUN && ROLL_ARGS+=("--dry-run")

  # A new line starts with one checkpoint monthly (--bootstrap-monthly); every other release needs one in the line.
  LINE_STATE="$(r2_line_state)"
  echo "    ${R2_LINE} is ${LINE_STATE}"
  if [[ -n "${BOOTSTRAP_MONTH}" ]]; then
    [[ "${LINE_STATE}" == "empty" ]] || {
      echo "ERROR: --bootstrap-monthly starts an EMPTY line; ${R2_LINE} is ${LINE_STATE}" >&2; exit 1; }
    bootstrap_line
  elif [[ "${LINE_STATE}" != "started" ]]; then
    echo "ERROR: ${R2_LINE} has no official monthly (${LINE_STATE}). Start the line with" \
      "--bootstrap-monthly=YYYY-MM on its checkpoint release, or set R2_LINE to the line you mean." >&2
    exit 1
  fi
fi

if (( START_STEP <= 3 )) && [[ -z "${BOOTSTRAP_MONTH}" ]]; then
  # Build and strictly validate the delta and this release's weekly full before anything on R2 changes: a failure
  # here stops the release with the line untouched. The delta is uploaded below, after the monthly its
  # checkpoint_full may resolve to; the full right after the rollover.
  echo ">>> [3/4] building and validating the weekly DELTA for ${DATE}"
  "${REPO_ROOT}/src/scripts/release-gkm-delta.sh" "${REL_ARGS[@]}" --no-upload
  echo ">>> [3/4] building and validating the weekly FULL for ${DATE}"
  "${REPO_ROOT}/src/scripts/release-gkm.sh" "${REL_ARGS[@]}" --weekly --no-upload

  # Month/year rollover first: posting this release may start a new month (or year).
  echo ">>> [3/4] rollover for ${DATE}"
  "${REPO_ROOT}/src/scripts/r2-rollover.sh" "${ROLL_ARGS[@]}"

  # This release's weekly FULL, validated above. A failed upload is non-fatal: the delta is the record; a monthly
  # whose source weekly full is missing is re-exported (and validated) instead.
  echo ">>> [3/4] publishing weekly FULL for ${DATE}"
  "${REPO_ROOT}/src/scripts/release-gkm.sh" "${REL_ARGS[@]}" --weekly --start-step=3 \
    || echo "WARNING: weekly FULL ${DATE} upload failed; continuing to the monthly trigger and the delta" >&2

  # Official monthly, BEFORE the delta, so the delta's checkpoint_full can resolve to it.
  publish_due_monthly_fulls

  # Drop the finished month's kept weekly full once the new month's monthly is posted.
  "${REPO_ROOT}/src/scripts/r2-rollover.sh" "${ROLL_ARGS[@]}"

  echo ">>> [3/4] publishing weekly DELTA for ${DATE}"
  "${REPO_ROOT}/src/scripts/release-gkm-delta.sh" "${REL_ARGS[@]}" --start-step=3
fi

# --- Step 4: the one Parquet set (parquet/) ------------------------------------------------
# Built from THIS release's weekly full, so it runs only after step 3 has uploaded it. A --bootstrap-monthly release
# has no weekly full, and release-gkm-parquet.sh reads the checkpoint monthly the line's index.json lists for this
# release instead. If neither is published (e.g. the weekly full's upload failed), this step stops. Non-fatal after
# step 3: the bundles are the record, and parquet/manifest.json says which release the set was built from. Fatal
# when it is the only step asked for.
if (( START_STEP <= 4 )); then
  if $SKIP_PARQUET; then
    echo ">>> [4/4] --skip-parquet: parquet/ still holds the previous set"
  else
    echo ">>> [4/4] rebuilding the Parquet set from ${DATE}"
    # --purge clears the CDN copy of parquet/ (cached 1 day by the Parquet cache rule).
    "${REPO_ROOT}/src/scripts/release-gkm-parquet.sh" "${REL_ARGS[@]}" --purge || {
      echo "WARNING: Parquet rebuild from ${DATE} failed; parquet/ still holds the previous set" >&2
      (( START_STEP < 4 )) || exit 1
    }
  fi
fi

echo "=== run-release ${DATE} complete ==="
