#!/bin/bash
# export-gkm-dicts.sh
# Export all GKS dictionary tables to GCS as NDJSON, the input of the bundle assembler.
#
# Usage: ./export-gkm-dicts.sh <dataset> <gcs_bucket> [prefix] [--delta]
#
# No Parquet: the one published Parquet set is built from the bundle by gkm-bundle-parquet
# (release-gkm-parquet.sh), never exported from BigQuery.
# Example: ./export-gkm-dicts.sh clinvar_2025_06_08 clinvar-gkm gkm-dicts

set -euo pipefail

# Parse positional args and flags
DATASET="${1:?Usage: $0 <dataset> <gcs_bucket> [prefix] [--delta]}"
BUCKET="${2:?Usage: $0 <dataset> <gcs_bucket> [prefix] [--delta]}"
PREFIX="${3:-gkm-dicts}"
DELTA=false
for arg in "$@"; do
  case "$arg" in
    --delta) DELTA=true ;;
  esac
done

src_table() {           # $1 = base dict table, e.g. gkm_dict_scv
  if $DELTA; then echo "delta_$1"; else echo "$1"; fi
}

GCS_PATH="gs://${BUCKET}/${PREFIX}"

echo "Exporting GKS dictionaries from ${DATASET}"

extract() {
  local table="$1"
  local basename="$2"
  # Use wildcard sharding to handle large tables
  # e.g., allele.ndjson.gz -> allele-*.ndjson.gz
  local sharded="${basename%.ndjson.gz}-*.ndjson.gz"
  echo "  Exporting ${table} -> ${sharded}"
  bq extract --destination_format NEWLINE_DELIMITED_JSON --compression GZIP \
    "${DATASET}.${table}" "${GCS_PATH}/${sharded}"
}

extract_ndjson_where() {
  # NDJSON export of a dict table filtered by a WHERE predicate. `bq extract` cannot
  # filter, so this uses EXPORT DATA; the sharded output shape matches extract().
  local table="$1"
  local basename="$2"
  local where="$3"
  local sharded="${basename%.ndjson.gz}-*.ndjson.gz"
  echo "  Exporting ${table} -> ${sharded} (NDJSON via EXPORT DATA, WHERE ${where})"
  bq query --use_legacy_sql=false --nouse_cache \
    "EXPORT DATA OPTIONS(
      uri='${GCS_PATH}/${sharded}',
      format='JSON',
      compression='GZIP',
      overwrite=true
    ) AS
    SELECT * FROM \`${DATASET}.${table}\` WHERE ${where}"
}

export_variation_ndjson() {
  # variation is the only passthrough dict with native INT64 columns (constraints.copies and
  # extensions.value_coding). Both `bq extract` and `EXPORT DATA` serialize INT64 as a QUOTED
  # STRING in JSON (precision-safety), which makes copies a string and breaks cat-vrs
  # CopyCountConstraint (oneOf[integer, Range]). Render those two columns via TO_JSON so INT64
  # emits as a JSON number; the assembler's strip_empty (runs before the value_* collapse)
  # still drops the null value_<type> variants. No other section has native INT64.
  local table="$1"
  local sharded="variation-*.ndjson.gz"
  echo "  Exporting ${table} -> ${sharded} (NDJSON via EXPORT DATA, TO_JSON int-safe)"
  bq query --use_legacy_sql=false --nouse_cache \
    "EXPORT DATA OPTIONS(
      uri='${GCS_PATH}/${sharded}',
      format='JSON',
      compression='GZIP',
      overwrite=true
    ) AS
    SELECT * REPLACE(TO_JSON(constraints) AS constraints, TO_JSON(extensions) AS extensions)
    FROM \`${DATASET}.${table}\`"
}

# Proposition sections (1.1.0, by meaning): the 3 per-level proposition dicts are delivered as the 4
# sections below. A row's section is clinvar_ingest.gkm_proposition_section(type), the ONE canonical
# mapping (src/procedures/gkm-proposition-section-func.sql) the statement procs use for their pointers.
# The function raises on an unmapped type, so the export fails loudly instead of dropping rows.
PROP_SECTIONS="propositionPathogenicity propositionOncogenicity propositionSomaticClinicalImpact propositionClinvarCustom"
# shellcheck disable=SC2016  # literal BigQuery backticks, not command substitution
PROP_SECTION_FN='`clinvar_ingest.gkm_proposition_section`'

# Belt and braces before any proposition export: every proposition row maps to one of PROP_SECTIONS, so
# the exported sections sum to the three dicts' total (a new section added to the function but not to
# PROP_SECTIONS would otherwise be dropped silently). Delta-aware via src_table.
assert_proposition_sections() {
  local in_list="" section
  for section in ${PROP_SECTIONS}; do in_list="${in_list:+${in_list},}'${section}'"; done
  echo "  Asserting every proposition maps to one of: ${PROP_SECTIONS}"
  bq query --use_legacy_sql=false --nouse_cache --quiet \
    "ASSERT (
      SELECT COUNTIF(${PROP_SECTION_FN}(JSON_VALUE(value, '\$.type')) IN (${in_list})) = COUNT(*)
      FROM (
        SELECT value FROM \`${DATASET}.$(src_table gkm_dict_proposition)\`
        UNION ALL SELECT value FROM \`${DATASET}.$(src_table gkm_dict_rcv_proposition)\`
        UNION ALL SELECT value FROM \`${DATASET}.$(src_table gkm_dict_vcv_proposition)\`
      )
    ) AS 'proposition rows map to a section outside PROP_SECTIONS'"
}

# Extension value collapse (conformance): the pipeline stores typed extension values as `value_<type>`
# (value_string, value_boolean, value_submitted_condition, ...) so gkm_json_proc can nullify-by-type and
# drop them; the va-spec bundle wants a single polymorphic `value`. This recursive JS UDF renames the one
# populated `value_*` key (JSON_STRIP_NULLS already dropped the rest) to `value` in every extension object
# (any object with a `name` sibling), at any nesting depth. The gkm_dict_* tables keep `value_*`; only the
# bundle export is collapsed. Prepend ${COLLAPSE_UDF} to any query that uses collapse_ext_values(...).
COLLAPSE_UDF=$(cat <<'SQL'
CREATE TEMP FUNCTION collapse_ext_values(j STRING)
RETURNS STRING
LANGUAGE js AS r"""
  if (j == null) return null;
  function walk(o){
    if (Array.isArray(o)){ for (const x of o) walk(x); return; }
    if (o && typeof o === "object"){
      if ("name" in o){ for (const k of Object.keys(o)){ if (k.indexOf("value_")===0){ o["value"]=o[k]; delete o[k]; } } }
      for (const k of Object.keys(o)) walk(o[k]);
    }
  }
  const p = JSON.parse(j); walk(p); return JSON.stringify(p);
""";
SQL
)

export_proposition_section_ndjson() {
  local section="$1"
  local sharded="${section}-*.ndjson.gz"
  echo "  Exporting proposition section ${section} -> ${sharded} (NDJSON via EXPORT DATA)"
  bq query --use_legacy_sql=false --nouse_cache \
    "${COLLAPSE_UDF}
    EXPORT DATA OPTIONS(
      uri='${GCS_PATH}/${sharded}',
      format='JSON',
      compression='GZIP',
      overwrite=true
    ) AS
    SELECT key, SAFE.PARSE_JSON(collapse_ext_values(TO_JSON_STRING(value))) AS value FROM (
      SELECT key, value FROM \`${DATASET}.$(src_table gkm_dict_proposition)\`
      UNION ALL SELECT key, value FROM \`${DATASET}.$(src_table gkm_dict_rcv_proposition)\`
      UNION ALL SELECT key, value FROM \`${DATASET}.$(src_table gkm_dict_vcv_proposition)\`
    ) WHERE ${PROP_SECTION_FN}(JSON_VALUE(value, '\$.type')) = '${section}'"
}

# NDJSON export of a passthrough dict table with its `extensions` column value-collapsed for the bundle.
export_ndjson_ext_collapse() {
  local table="$1"
  local basename="$2"
  local sharded="${basename%.ndjson.gz}-*.ndjson.gz"
  echo "  Exporting ${table} -> ${sharded} (NDJSON via EXPORT DATA, extensions collapsed)"
  bq query --use_legacy_sql=false --nouse_cache \
    "${COLLAPSE_UDF}
    EXPORT DATA OPTIONS(
      uri='${GCS_PATH}/${sharded}',
      format='JSON',
      compression='GZIP',
      overwrite=true
    ) AS
    SELECT * REPLACE(
      SAFE.PARSE_JSON(collapse_ext_values(
        TO_JSON_STRING(JSON_STRIP_NULLS(TO_JSON(extensions), remove_empty => TRUE)))) AS extensions)
    FROM \`${DATASET}.${table}\`"
}

assert_proposition_sections

echo "Exporting NDJSON files to ${GCS_PATH}"

# Cat-VRS dictionaries (from gkm_catvar_proc)
extract "$(src_table gkm_dict_sequence_reference)" sequenceReference.ndjson.gz
extract "$(src_table gkm_dict_location)" location.ndjson.gz
extract "$(src_table gkm_dict_allele)" allele.ndjson.gz
extract "$(src_table gkm_dict_copy_number_count)" copyNumberCount.ndjson.gz
extract "$(src_table gkm_dict_copy_number_change)" copyNumberChange.ndjson.gz
extract "$(src_table gkm_dict_gene)" gene.ndjson.gz
export_variation_ndjson "$(src_table gkm_dict_variation)"

# Condition dictionaries (from gkm_scv_condition_proc)
extract "$(src_table gkm_dict_condition)" condition.ndjson.gz
# conditionSet: drop single-member sets (va-spec ConceptSet minItems:2). A one-concept
# set is just that condition — every producer references the lone member directly as
# #/condition/, never the set (0 of ~2.96M proposition.object refs point at a
# <=1-concept set), so single-member sets are unreferenced orphans. Mirrors conditionSet.sql.
extract_ndjson_where "$(src_table gkm_dict_condition_set)" conditionSet.ndjson.gz "ARRAY_LENGTH(concepts) > 1"

# Therapy dictionaries (from gkm_scv_statement_proc) — content-addressed dedup; the
# therapeutic proposition `object` references these via #/therapy/ and #/therapyGroup/.
extract "$(src_table gkm_dict_therapy)" therapy.ndjson.gz
extract "$(src_table gkm_dict_therapygroup)" therapyGroup.ndjson.gz

# SCV dictionaries (from gkm_scv_statement_proc)
extract "$(src_table gkm_dict_submitter)" submitter.ndjson.gz
export_ndjson_ext_collapse "$(src_table gkm_dict_evidence_line)" evidenceLine.ndjson.gz

# Proposition sections (1.1.0, by meaning): the 3 per-level proposition dicts are split into the
# PROP_SECTIONS by the canonical function. Delta-aware: the helper reads
# $(src_table gkm_dict_*proposition), so --delta mode emits proposition deltas split the same way
# (build-delta-manifest.py resolves each changed key to its section with the same function).
for section in ${PROP_SECTIONS}; do
  export_proposition_section_ndjson "${section}"
done

# VCV/RCV evidence line dictionaries (propositions handled by the section split above)
extract "$(src_table gkm_dict_vcv_evidence_line)" vcv_evidenceLine.ndjson.gz
extract "$(src_table gkm_dict_rcv_evidence_line)" rcv_evidenceLine.ndjson.gz

# Statement outputs
export_ndjson_ext_collapse "$(src_table gkm_dict_scv)" scv.ndjson.gz
extract "$(src_table gkm_dict_vcv)" vcv.ndjson.gz
extract "$(src_table gkm_dict_rcv)" rcv.ndjson.gz

echo "Done."
echo "  NDJSON:  ${GCS_PATH}/"
