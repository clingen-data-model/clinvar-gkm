#!/bin/bash
# Prune the BigQuery release datasets to what ADR 0014 retains. DRY RUN unless --apply.
#
# A release dataset (clinvar_<yyyy>_<mm>_<dd>_<version>) dated on or after the RETENTION FLOOR is left untouched.
# The floor is the earlier of two dates in the current line's public index.json:
#
#   - the source_release of the newest published monthly. The next monthly's source is a later dataset (ADR 0002),
#     and a new line starts from this one (ADR 0008, 1.2.0 D1).
#   - the baseline of the newest published delta: the newest dataset dated before latest_release. A re-run of that
#     release reads its gkm_dict_*, gkm_vrs and variation_identity tables.
#
# It only ever touches release datasets: names that match clinvar_<yyyy>_<mm>_<dd>_v<n>_<n>_<n> exactly. Every
# other dataset (clinvar_ingest, clinvar_curator*, scratch and _recon datasets, …) is skipped: its tables are never
# listed or changed, and the name is checked again before each drop.
#
# In every older release dataset the script drops the tables ADR 0014 calls working state (their content is in the
# published bundles) and keeps the build's own record:
#
#   drop   gkm_dict_*, gkm_vrs, the carried-forward intermediates (gkm_{rcv,vcv}_{classification_agg,priority_agg,
#          aggregate_contribution}, gkm_scv_condition_sets), the retired gkm_json outputs (gkm_catvar,
#          gkm_{scv,rcv,vcv}_statement), pre-rename gks_* tables, and temp_* / stg_* debug leftovers
#   keep   gkm_pipeline_version, gkm_change_log, gkm_scv_change_audit, delta_gkm_*, the changed-id sets, and every
#          table not named above: everything clinvar-ingest writes (the ingested tables, diff_*,
#          variation_identity / _loc / _hgvs / _xref) and one-offs this repo does not create
#
# It never deletes a dataset: the procedures take the newest existing dataset before a release as its baseline
# (clinvar_ingest.schema_on), so a missing dataset would silently widen the next delta.
#
# Usage: ./prune-release-datasets.sh [--apply]
#
#   --apply   drop the tables (default: print the plan; bq ls only, nothing is billed)
#
# A dropped table can be restored within its dataset's time-travel window (7 days by default), e.g.
#   bq cp <dataset>.<table>@-86400000 <dataset>.<table>      # the table as it was 24 h ago
set -euo pipefail

APPLY=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=true; shift ;;
    -h|--help) sed -n '2,34p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "ERROR: unknown argument '$1'" >&2; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=r2-common.sh
. "${SCRIPT_DIR}/r2-common.sh"
PROJECT_ID="${PROJECT_ID:-clingen-dev}"
export CLOUDSDK_CORE_PROJECT="${PROJECT_ID}"
DATE_RE='^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
RELEASE_DS_RE='^clinvar_[0-9]{4}_[0-9]{2}_[0-9]{2}_v[0-9]+_[0-9]+_[0-9]+$'

# Echo "drop" or "keep" for a table name (ADR 0014). Case patterns match the whole name, so gkm_dict_* does not
# match delta_gkm_dict_*.
table_action() {
  case "$1" in
    gkm_dict_*|gkm_vrs|gkm_scv_condition_sets \
      |gkm_rcv_classification_agg|gkm_rcv_priority_agg|gkm_rcv_aggregate_contribution \
      |gkm_vcv_classification_agg|gkm_vcv_priority_agg|gkm_vcv_aggregate_contribution \
      |gkm_catvar|gkm_scv_statement|gkm_rcv_statement|gkm_vcv_statement \
      |gks_*|temp_*|stg_*)
      echo drop ;;
    *) echo keep ;;
  esac
}

# --- retention floor, from the line's index.json ---------------------------------------------------------------
INDEX_URL="${R2_PUBLIC_URL}/${R2_LINE}index.json"
read -r LATEST MONTHLY_SRC < <(curl -sf --max-time 60 "${INDEX_URL}" | "${R2_PYTHON}" -c '
import json, sys
j = json.load(sys.stdin)
srcs = [m.get("source_release") or "" for m in j.get("datasets", {}).get("monthly", [])]
print(j.get("latest_release") or "-", max(srcs) if srcs else "-")
') || { echo "ERROR: cannot read ${INDEX_URL}" >&2; exit 1; }
[[ "${LATEST}" =~ ${DATE_RE} ]] || { echo "ERROR: no latest_release in ${INDEX_URL}" >&2; exit 1; }
[[ "${MONTHLY_SRC}" =~ ${DATE_RE} ]] || { echo "ERROR: no monthly source_release in ${INDEX_URL}" >&2; exit 1; }

# "date<TAB>dataset" for every release dataset, oldest first.
DATASETS="$(bq ls --project_id="${PROJECT_ID}" --max_results=100000 \
  | awk '{print $1}' \
  | grep -E "${RELEASE_DS_RE}" \
  | sed -E 's/^(clinvar_([0-9]{4})_([0-9]{2})_([0-9]{2})_.*)$/\2-\3-\4	\1/' \
  | sort)" || { echo "ERROR: cannot list datasets in ${PROJECT_ID}" >&2; exit 1; }
cut -f1 <<< "${DATASETS}" | grep -qx "${LATEST}" \
  || { echo "ERROR: no dataset for latest_release ${LATEST}; refusing to plan" >&2; exit 1; }
cut -f1 <<< "${DATASETS}" | grep -qx "${MONTHLY_SRC}" \
  || { echo "ERROR: no dataset for monthly source_release ${MONTHLY_SRC}; refusing to plan" >&2; exit 1; }
BASELINE="$(cut -f1 <<< "${DATASETS}" | awk -v l="${LATEST}" '$0 < l' | tail -n1)"
[[ "${BASELINE}" =~ ${DATE_RE} ]] || { echo "ERROR: no dataset before ${LATEST}; refusing to plan" >&2; exit 1; }
FLOOR="${MONTHLY_SRC}"; [[ "${BASELINE}" < "${FLOOR}" ]] && FLOOR="${BASELINE}"

echo "=== prune release datasets (${PROJECT_ID}, line ${R2_LINE}) ==="
${APPLY} || echo "  Mode: DRY RUN (nothing is dropped; pass --apply)"
echo "  latest_release ${LATEST} (baseline ${BASELINE}), newest monthly source ${MONTHLY_SRC}"
echo "  Retention floor ${FLOOR}: datasets dated on or after it are untouched:"
awk -F'\t' -v f="${FLOOR}" '$1 >= f {print "    " $2}' <<< "${DATASETS}"

# --- plan (and drop) below the floor ----------------------------------------------------------------------------
TOTAL_DROP=0; FAILED=0
while IFS=$'\t' read -r d ds; do
  [[ "${d}" < "${FLOOR}" ]] || continue
  [[ "${ds}" =~ ${RELEASE_DS_RE} ]] || { echo "ERROR: '${ds}' is not a release dataset; skipped" >&2; continue; }
  tables="$(bq ls --project_id="${PROJECT_ID}" --max_results=100000 --format=json "${ds}" \
    | "${R2_PYTHON}" -c 'import json, sys; [print(t["tableReference"]["tableId"]) for t in json.load(sys.stdin)]')" \
    || { echo "ERROR: cannot list ${ds}" >&2; FAILED=$((FAILED + 1)); continue; }
  drops=()
  while IFS= read -r t; do
    [[ -n "${t}" && "$(table_action "${t}")" == drop ]] && drops+=("${t}")
  done <<< "${tables}"
  [[ ${#drops[@]} -gt 0 ]] || continue
  echo "  ${ds}: drop ${#drops[@]}"
  for t in "${drops[@]}"; do
    if ${APPLY}; then
      [[ "${ds}" =~ ${RELEASE_DS_RE} ]] || { echo "ERROR: refusing to drop from '${ds}'" >&2; exit 1; }
      bq rm -f -t "${PROJECT_ID}:${ds}.${t}" >/dev/null \
        || { echo "    FAILED ${t}" >&2; FAILED=$((FAILED + 1)); continue; }
      echo "    dropped ${t}"
    else
      echo "    ${t}"
    fi
  done
  TOTAL_DROP=$((TOTAL_DROP + ${#drops[@]}))
done <<< "${DATASETS}"

if ${APPLY}; then echo "=== dropped ${TOTAL_DROP} tables, ${FAILED} failures ==="; else
  echo "=== plan: ${TOTAL_DROP} tables to drop (dry run) ==="; fi
[[ ${FAILED} -eq 0 ]]
