#!/bin/bash
#
# check-scv-codings.sh — before run-release.sh exports anything: confirm that a release's built gkm_* tables carry
# the guideline codings the SCV statement profiles require (schema 1.3.0, ADR 0015), and, with --with-baseline, that
# the previous release's do too. Read-only.
#
# The bundle validation at publish holds every SCV to its profile, but only after the export, and it does not cover
# the VCV and RCV aggregate codings. This catches, before any export:
#   - a build against an outdated lookup (see check-clinsig-lookup.sh);
#   - SCVs or aggregates carried forward with the old codes by an incremental build;
#   - a delta whose baseline was built with the old codes (the first delta of a line must diff against a dataset
#     built with the line's procs, or nearly every SCV would show as changed).
#
# Counts, each of which must be 0:
#   old_codes             SCVs coded 'tier 1' ... 'tier 4', under 'SVC v4' or an '(AAC)' system, or not lower case
#   strength_system       SCVs whose strength is coded in another system than their classification
#   tier_name             somatic clinical impact SCVs whose coding name is not 'Tier I' ... 'Tier IV', and other
#                         SCVs whose coding has a name
#   aggregate_old_codes   VCV and RCV classification aggregates with the old codes
#
# USAGE:
#   ./src/scripts/check-scv-codings.sh YYYY-MM-DD [--with-baseline]
#
# ENV OVERRIDES:
#   PROJECT_ID   GCP project (default clingen-dev)

set -o errexit
set -o nounset
set -o pipefail

PROJECT_ID="${PROJECT_ID:-clingen-dev}"
export CLOUDSDK_CORE_PROJECT="${PROJECT_ID}"

DATE="${1:?Usage: $0 YYYY-MM-DD [--with-baseline]}"
if ! [[ "${DATE}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  echo "ERROR: invalid release date '${DATE}', expected YYYY-MM-DD" >&2
  exit 1
fi
WITH_BASELINE=false
case "${2:-}" in
  "") ;;
  --with-baseline) WITH_BASELINE=true ;;
  *) echo "ERROR: unknown argument '$2'" >&2; exit 1 ;;
esac

bq_csv() {
  bq query --project_id="${PROJECT_ID}" --use_legacy_sql=false --format=csv --max_rows=10 "$1"
}

# "schema_name,prev_release_date" of the release active on a date (prev_release_date may be empty).
release_on() {
  bq_csv "SELECT schema_name, prev_release_date FROM \`clinvar_ingest.schema_on\`(DATE '$1')" | sed -n 2p
}

release="$(release_on "${DATE}")" || true
DATASET="${release%%,*}"
PREV_DATE="${release#*,}"
[[ -n "${DATASET}" && "${DATASET}" != "${release}" ]] || {
  echo "ERROR: no release dataset for ${DATE} (clinvar_ingest.schema_on)" >&2
  exit 1
}
BASELINE=""
if ${WITH_BASELINE} && [[ -n "${PREV_DATE}" ]]; then
  BASELINE="$(release_on "${PREV_DATE}")" || true
  BASELINE="${BASELINE%%,*}"
  [[ -n "${BASELINE}" ]] || { echo "ERROR: no release dataset for the previous release ${PREV_DATE}" >&2; exit 1; }
fi

# Echo "name=count ..." for one dataset; return 1 when any count is not 0 (or the counts cannot be read).
check() {
  local S="$1" out header values name_field
  # A dataset built before 1.3.0 has no classification.primaryCoding.name, and the counts below need it.
  name_field="$(bq_csv "SELECT COUNT(*) AS n FROM \`${S}.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS\`
    WHERE table_name = 'gkm_dict_scv' AND field_path = 'classification.primaryCoding.name'" | sed -n 2p)" \
    || { echo "could not be read"; return 1; }
  [[ "${name_field}" == "1" ]] || { echo "built before schema 1.3.0 (gkm_dict_scv has no classification.primaryCoding.name)"; return 1; }
  out="$(bq_csv "
    SELECT
      (SELECT COUNTIF(REGEXP_CONTAINS(classification.primaryCoding.code, r'^tier [0-9]')
                      OR classification.primaryCoding.system = 'SVC v4'
                      OR STRPOS(classification.primaryCoding.system, '(AAC)') > 0
                      OR STRPOS(strength.primaryCoding.system, '(AAC)') > 0
                      OR classification.primaryCoding.code != LOWER(classification.primaryCoding.code))
       FROM \`${S}.gkm_dict_scv\`) AS old_codes,
      (SELECT COUNTIF(strength.primaryCoding.system != classification.primaryCoding.system)
       FROM \`${S}.gkm_dict_scv\`) AS strength_system,
      (SELECT COUNTIF(IF(STARTS_WITH(proposition, '#/propositionSomaticClinicalImpact/'),
                         classification.primaryCoding.name IS DISTINCT FROM
                           CASE classification.primaryCoding.code
                             WHEN 'tier i' THEN 'Tier I' WHEN 'tier ii' THEN 'Tier II'
                             WHEN 'tier iii' THEN 'Tier III' WHEN 'tier iv' THEN 'Tier IV' END,
                         classification.primaryCoding.name IS NOT NULL))
       FROM \`${S}.gkm_dict_scv\`) AS tier_name,
      (SELECT COUNTIF(REGEXP_CONTAINS(c.code, r'^tier [0-9]') OR c.system = 'SVC v4'
                      OR STRPOS(c.system, '(AAC)') > 0 OR c.code != LOWER(c.code))
       FROM (SELECT agg_classif_coding AS c FROM \`${S}.gkm_vcv_classification_agg\`
             UNION ALL SELECT agg_classif_coding FROM \`${S}.gkm_rcv_classification_agg\`)) AS aggregate_old_codes")" \
    || { echo "could not be read"; return 1; }
  header="$(printf '%s\n' "${out}" | sed -n 1p)"
  values="$(printf '%s\n' "${out}" | sed -n 2p)"
  [[ -n "${values}" ]] || { echo "could not be read"; return 1; }
  paste -d= <(tr ',' '\n' <<<"${header}") <(tr ',' '\n' <<<"${values}") | tr '\n' ' '
  echo
  [[ "${values}" =~ ^0(,0)*$ ]]
}

failed=false
targets=("${DATASET}")
if ${WITH_BASELINE}; then
  if [[ -n "${BASELINE}" ]]; then targets+=("${BASELINE}"); else echo "    ${DATE} has no previous release"; fi
fi
for S in "${targets[@]}"; do
  label="${S}"; [[ "${S}" == "${BASELINE}" && "${S}" != "${DATASET}" ]] && label="${S} (the delta's baseline)"
  if result="$(check "${S}")"; then
    echo "    ${label}: SCV profile codings OK (${result% })"
  else
    echo "ERROR: ${label}: ${result% }" >&2
    failed=true
  fi
done
if ${failed}; then
  echo "ERROR: rebuild with the current procs, against a lookup check-clinsig-lookup.sh passes, in full mode" \
    "(run-release.sh --full-procs); a delta's baseline must be built the same way." >&2
  exit 1
fi
