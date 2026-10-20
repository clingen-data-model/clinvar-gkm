#!/bin/bash
# export-gkm-dicts.sh
# Export all GKS dictionary tables to GCS as NDJSON and/or Parquet
#
# Usage: ./export-gkm-dicts.sh <dataset> <gcs_bucket> [prefix] [--parquet-only] [--delta]
# Example: ./export-gkm-dicts.sh clinvar_2025_06_08 clinvar-gkm gkm-dicts
# Example: ./export-gkm-dicts.sh clinvar_2025_06_08 clinvar-gkm gkm-dicts --parquet-only

set -euo pipefail

# Parse positional args and flags
DATASET="${1:?Usage: $0 <dataset> <gcs_bucket> [prefix] [--parquet-only] [--delta]}"
BUCKET="${2:?Usage: $0 <dataset> <gcs_bucket> [prefix] [--parquet-only] [--delta]}"
PREFIX="${3:-gkm-dicts}"
PARQUET_ONLY=false
DELTA=false
for arg in "$@"; do
  case "$arg" in
    --parquet-only) PARQUET_ONLY=true ;;
    --delta) DELTA=true ;;
  esac
done

src_table() {           # $1 = base dict table, e.g. gkm_dict_scv
  if $DELTA; then echo "delta_$1"; else echo "$1"; fi
}

GCS_PATH="gs://${BUCKET}/${PREFIX}"
PARQUET_PREFIX="${PREFIX}-parquet"
GCS_PARQUET_PATH="gs://${BUCKET}/${PARQUET_PREFIX}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCHEMA_DIR="${SCRIPT_DIR}/parquet-schemas"

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

extract_parquet_typed() {
  # Export via EXPORT DATA using a SQL schema file from parquet-schemas/.
  # Schema files define typed columns, FK cleanup, and data column.
  # The {DATASET} placeholder is substituted with the target dataset.
  local basename="$1"
  local sql_file="$2"
  local sharded="${basename%.parquet}-*.parquet"
  local schema_path="${SCHEMA_DIR}/${sql_file}"
  if [[ ! -f "${schema_path}" ]]; then
    echo "  ERROR: Schema file not found: ${schema_path}" >&2
    return 1
  fi
  local sql
  sql=$(<"${schema_path}")
  sql="${sql//\{DATASET\}/${DATASET}}"
  if $DELTA; then
    # Typed-Parquet can't use src_table() (the table name is embedded inside the schema SQL,
    # not passed as a CLI arg). Every {DATASET}.gkm_dict_* table a parquet-schemas/*.sql
    # references (the proposition files reference several) has a delta_gkm_dict_* counterpart,
    # and no schema file uses "gkm_dict_" in any alias/column/literal, so rewriting every
    # qualified reference is safe. Invariant future schema authors must preserve.
    sql="${sql//.gkm_dict_/.delta_gkm_dict_}"
  fi
  echo "  Exporting ${sql_file%.sql} -> ${sharded} (Parquet via EXPORT DATA)"
  # ${COLLAPSE_UDF} makes collapse_ext_values(...) (the extension value_xxx -> value collapse),
  # is_blank(...) (all-null placeholder test) and bundle_cleanup(...) available to every schema file.
  bq query --use_legacy_sql=false --nouse_cache \
    "${COLLAPSE_UDF}
    EXPORT DATA OPTIONS(
      uri='${GCS_PARQUET_PATH}/${sharded}',
      format='PARQUET',
      compression='SNAPPY',
      overwrite=true
    ) AS
    ${sql}"
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
# It also defines:
#   is_blank(x)        TRUE when x is NULL or holds only nulls / empty arrays / empty structs at every depth
#                      (what JSON_STRIP_NULLS remove_empty drops). Typed-Parquet schema files use it to drop
#                      all-null placeholder structs and array elements the bundle does not carry.
#   bundle_cleanup(j)  the assembler's exact record cleanup (gkm_json_cleanup.py strip_empty, then the
#                      value_* collapse) for KV `data`/`value` columns, which the bundle cleans only in the
#                      assembler. Unlike JSON_STRIP_NULLS it KEEPS list elements, so a VRS Range [null, n]
#                      keeps its null bound (JSON_STRIP_NULLS would turn it into [n]).
COLLAPSE_UDF=$(cat <<'SQL'
CREATE TEMP FUNCTION is_blank(x ANY TYPE) AS (
  JSON_TYPE(JSON_STRIP_NULLS(TO_JSON(x), remove_empty => TRUE)) = 'null');
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
CREATE TEMP FUNCTION bundle_cleanup(j STRING)
RETURNS STRING
LANGUAGE js AS r"""
  if (j == null) return null;
  function strip(v){
    if (Array.isArray(v)) return v.map(strip);
    if (v && typeof v === "object"){
      const o = {};
      for (const k of Object.keys(v)){
        const s = strip(v[k]);
        if (!(s === null || (typeof s === "object" && Object.keys(s).length === 0))) o[k] = s;
      }
      return o;
    }
    return v;
  }
  function walk(o){
    if (Array.isArray(o)){ for (const x of o) walk(x); return; }
    if (o && typeof o === "object"){
      if ("name" in o){ for (const k of Object.keys(o)){ if (k.indexOf("value_")===0){ o["value"]=o[k]; delete o[k]; } } }
      for (const k of Object.keys(o)) walk(o[k]);
    }
  }
  const p = strip(JSON.parse(j)); walk(p); return JSON.stringify(p);
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

if ! $PARQUET_ONLY; then
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
fi

echo ""
echo "Exporting Parquet files to ${GCS_PARQUET_PATH}"

# Cat-VRS (typed columns extracted from KV JSON values)
extract_parquet_typed sequenceReference.parquet sequenceReference.sql
extract_parquet_typed location.parquet location.sql
extract_parquet_typed allele.parquet allele.sql
extract_parquet_typed copyNumberCount.parquet copyNumberCount.sql
extract_parquet_typed copyNumberChange.parquet copyNumberChange.sql
extract_parquet_typed gene.parquet gene.sql
extract_parquet_typed variation.parquet variation.sql

# Conditions
extract_parquet_typed condition.parquet condition.sql
extract_parquet_typed conditionSet.parquet conditionSet.sql

# Therapies (key/value JSON dicts -> two string columns key,value). Typed export casts the
# JSON `value` to a STRING (TO_JSON_STRING); a raw bq extract can't export a JSON column.
extract_parquet_typed therapy.parquet therapy.sql
extract_parquet_typed therapyGroup.parquet therapyGroup.sql

# SCV
extract_parquet_typed submitter.parquet submitter.sql
extract_parquet_typed evidenceLine.parquet evidenceLine.sql

# Proposition delivery groups (Phase 2): 4 typed group tables replace the 3 per-level tables.
extract_parquet_typed varcond-proposition.parquet varcond-proposition.sql
extract_parquet_typed vartumor-proposition.parquet vartumor-proposition.sql
extract_parquet_typed vartherapy-proposition.parquet vartherapy-proposition.sql
extract_parquet_typed varcustom-proposition.parquet varcustom-proposition.sql

# VCV/RCV evidence lines
extract_parquet_typed vcv_evidenceLine.parquet vcv_evidenceLine.sql
extract_parquet_typed rcv_evidenceLine.parquet rcv_evidenceLine.sql

# Statements
extract_parquet_typed scv.parquet scv.sql
extract_parquet_typed vcv.parquet vcv.sql
extract_parquet_typed rcv.parquet rcv.sql

echo "Done."
if ! $PARQUET_ONLY; then
  echo "  NDJSON:  ${GCS_PATH}/"
fi
echo "  Parquet: ${GCS_PARQUET_PATH}/"
