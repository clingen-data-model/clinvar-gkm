#!/bin/bash
# validate-proposition-conformance.sh — structural conformance check for the reshaped
# proposition data (CustomProposition model, va-spec 1.1.0-ballot). Runs BigQuery assertions
# over the SCV+RCV+VCV proposition dicts + the condition conceptType enum for a release.
#
# This is a STRUCTURAL gate (field mutual-exclusivity, discriminator correctness, no residual
# arrays, valid conceptType enum). A full JSON-Schema validation against schema/clinvar-gkm/json/*
# is a recommended follow-on (resolves clinvar + va-spec $refs; e.g. check-jsonschema over a sample).
#
# Usage: ./validate-proposition-conformance.sh <release_date> <dataset_version>   (project clingen-dev)
#        GKM_DATASET=<dataset> overrides the dataset name derived from the date + version.
# Exits non-zero if any reference field holds a bare id instead of a '#/' pointer (see the last check).
set -euo pipefail
DATE="${1:?release date YYYY-MM-DD}"; VER="${2:?dataset version e.g. v2_5_0}"
PROJECT="${CLOUDSDK_CORE_PROJECT:-clingen-dev}"
DS="${GKM_DATASET:-clinvar_${DATE//-/_}_${VER}}"

echo "=== proposition conformance: ${DS} ==="
bq query --project_id="$PROJECT" --use_legacy_sql=false --format=pretty --quiet "
WITH allp AS (
  SELECT value FROM \`${DS}.gkm_dict_proposition\`
  UNION ALL SELECT value FROM \`${DS}.gkm_dict_rcv_proposition\`
  UNION ALL SELECT value FROM \`${DS}.gkm_dict_vcv_proposition\`
)
SELECT
  COUNTIF(JSON_VALUE(value,'\$.subject') IS NULL) AS missing_subject_BAD,
  COUNTIF(JSON_QUERY(value,'\$.object') IS NULL) AS missing_object_BAD,
  COUNTIF(JSON_VALUE(value,'\$.type') IS NULL) AS missing_type_BAD,
  COUNTIF(JSON_TYPE(JSON_QUERY(value,'\$.object'))='array') AS object_array_BAD,
  COUNTIF(JSON_VALUE(value,'\$.customPropositionType') IS NOT NULL
       OR JSON_VALUE(value,'\$.subjectVariant') IS NOT NULL
       OR JSON_VALUE(value,'\$.objectCondition') IS NOT NULL
       OR JSON_VALUE(value,'\$.objectTumorType') IS NOT NULL) AS stale_field_BAD,
  COUNT(*) AS total
FROM allp"

echo "=== condition conceptType enum (must be only Condition/Phenotype/Disease/Trait/Absent) ==="
bq query --project_id="$PROJECT" --use_legacy_sql=false --format=pretty --quiet "
SELECT COUNTIF(conceptType NOT IN ('Condition','Phenotype','Disease','Trait','Absent')) AS invalid_conceptType_BAD,
       COUNT(*) AS total
FROM \`${DS}.gkm_dict_condition\`"

# --- Phase 2: proposition delivery-group reference integrity -------------------------------------
# Every statement/evidence-line proposition pointer is now group-qualified (#/<group>-proposition/<id>).
# The pointer's group prefix (computed proc-side) must equal the group recomputed from the referenced
# proposition row's raw gks type; no old #/proposition/ pointers may remain; no dangling ids.
echo "=== proposition reference integrity (group prefix == recomputed group; no old/dangling refs) ==="
bq query --project_id="$PROJECT" --use_legacy_sql=false --format=pretty --quiet "
WITH refs AS (
  SELECT proposition FROM \`${DS}.gkm_dict_scv\`
  UNION ALL SELECT proposition FROM \`${DS}.gkm_dict_rcv\`
  UNION ALL SELECT proposition FROM \`${DS}.gkm_dict_vcv\`
  UNION ALL SELECT targetProposition FROM \`${DS}.gkm_dict_evidence_line\`
),
props AS (
  SELECT key, JSON_VALUE(value,'\$.type') AS raw_type
  FROM \`${DS}.gkm_dict_proposition\`
  UNION ALL SELECT key, JSON_VALUE(value,'\$.type')
  FROM \`${DS}.gkm_dict_rcv_proposition\`
  UNION ALL SELECT key, JSON_VALUE(value,'\$.type')
  FROM \`${DS}.gkm_dict_vcv_proposition\`
),
parsed AS (
  SELECT
    (proposition LIKE '#/proposition/%') AS is_old,
    REGEXP_EXTRACT(proposition, r'^#/([a-z]+)-proposition/') AS ptr_group,
    REGEXP_EXTRACT(proposition, r'^#/[a-z]+-proposition/(.+)\$') AS ref_id
  FROM refs
)
SELECT
  COUNTIF(parsed.is_old) AS leftover_old_ref_BAD,
  COUNTIF(NOT parsed.is_old AND p.key IS NULL) AS dangling_ref_BAD,
  COUNTIF(NOT parsed.is_old AND p.key IS NOT NULL AND parsed.ptr_group != CASE
      WHEN p.raw_type LIKE 'Clinvar%' THEN 'varcustom'
      WHEN p.raw_type = 'VariantOncogenicityProposition' THEN 'vartumor'
      WHEN p.raw_type = 'VariantTherapeuticResponseProposition' THEN 'vartherapy'
      WHEN p.raw_type IN ('VariantPathogenicityProposition','VariantClinicalSignificanceProposition',
                          'VariantDiagnosticProposition','VariantPrognosticProposition') THEN 'varcond'
      ELSE 'UNKNOWN' END) AS misrouted_ref_BAD,
  COUNT(*) AS total_refs
FROM parsed LEFT JOIN props p ON p.key = parsed.ref_id"

# Every proposition's raw gks type must map to exactly one of the 4 delivery groups (total mapping).
echo "=== proposition group coverage (every prop maps to a known group) ==="
bq query --project_id="$PROJECT" --use_legacy_sql=false --format=pretty --quiet "
WITH allp AS (
  SELECT value FROM \`${DS}.gkm_dict_proposition\`
  UNION ALL SELECT value FROM \`${DS}.gkm_dict_rcv_proposition\`
  UNION ALL SELECT value FROM \`${DS}.gkm_dict_vcv_proposition\`)
SELECT COUNTIF(
    JSON_VALUE(value,'\$.type') NOT IN
      ('VariantOncogenicityProposition','VariantTherapeuticResponseProposition','VariantPathogenicityProposition',
       'VariantClinicalSignificanceProposition','VariantDiagnosticProposition','VariantPrognosticProposition')
    AND NOT JSON_VALUE(value,'\$.type') LIKE 'Clinvar%'
  ) AS unknown_group_BAD,
  COUNT(*) AS total
FROM allp"

echo "All *_BAD columns must be 0."

# --- Uniform '#/' references (hard gate) ---------------------------------------------------------
# Every field that points at another bundle record must be a '#/<section>/<id>' pointer, never a
# bare id. A bare id was a real regression (1.0.0 de-pointer: 7.47M VCV proposition objects and the
# vcv- ConceptSet members went bare). NOT checked, deliberately bare CURIEs: the submittedCondition /
# submittedConditionSet extension strings (condition, conditionSet, direct_match, normalized_match),
# which record what was submitted and matched rather than reference a record.
echo "=== reference fields hold '#/' pointers, never bare ids (FAILS the script on any bare value) ==="
REF_SQL="
WITH refs AS (
  SELECT 'proposition.subject' f, JSON_VALUE(value,'\$.subject') v FROM \`${DS}.gkm_dict_proposition\`
  UNION ALL SELECT 'proposition.subject', JSON_VALUE(value,'\$.subject') FROM \`${DS}.gkm_dict_rcv_proposition\`
  UNION ALL SELECT 'proposition.subject', JSON_VALUE(value,'\$.subject') FROM \`${DS}.gkm_dict_vcv_proposition\`
  UNION ALL SELECT 'proposition.object', JSON_VALUE(value,'\$.object') FROM \`${DS}.gkm_dict_proposition\`
  UNION ALL SELECT 'proposition.object', JSON_VALUE(value,'\$.object') FROM \`${DS}.gkm_dict_rcv_proposition\`
  UNION ALL SELECT 'proposition.object', JSON_VALUE(value,'\$.object') FROM \`${DS}.gkm_dict_vcv_proposition\`
  UNION ALL SELECT 'proposition.conditionQualifier', JSON_VALUE(value,'\$.conditionQualifier') FROM \`${DS}.gkm_dict_proposition\`
  UNION ALL SELECT 'proposition.conditionQualifier', JSON_VALUE(value,'\$.conditionQualifier') FROM \`${DS}.gkm_dict_rcv_proposition\`
  UNION ALL SELECT 'proposition.conditionQualifier', JSON_VALUE(value,'\$.conditionQualifier') FROM \`${DS}.gkm_dict_vcv_proposition\`
  UNION ALL SELECT 'conditionSet.concepts', c FROM \`${DS}.gkm_dict_condition_set\`, UNNEST(concepts) c
  UNION ALL SELECT 'therapyGroup.concepts', JSON_VALUE(c) FROM \`${DS}.gkm_dict_therapygroup\`, UNNEST(JSON_QUERY_ARRAY(value,'\$.concepts')) c
  UNION ALL SELECT 'variation.members', m FROM \`${DS}.gkm_dict_variation\`, UNNEST(members) m
  UNION ALL SELECT 'variation.constraints.allele', c.allele FROM \`${DS}.gkm_dict_variation\`, UNNEST(constraints) c
  UNION ALL SELECT 'variation.constraints.location', c.location FROM \`${DS}.gkm_dict_variation\`, UNNEST(constraints) c
  UNION ALL SELECT 'variation.clinvarGeneList.gene', g.gene FROM \`${DS}.gkm_dict_variation\`, UNNEST(extensions) e, UNNEST(e.value_gene_array) g
  UNION ALL SELECT 'allele.location', JSON_VALUE(value,'\$.location') FROM \`${DS}.gkm_dict_allele\`
  UNION ALL SELECT 'copyNumberCount.location', JSON_VALUE(value,'\$.location') FROM \`${DS}.gkm_dict_copy_number_count\`
  UNION ALL SELECT 'copyNumberChange.location', JSON_VALUE(value,'\$.location') FROM \`${DS}.gkm_dict_copy_number_change\`
  UNION ALL SELECT 'location.sequenceReference', JSON_VALUE(value,'\$.sequenceReference') FROM \`${DS}.gkm_dict_location\`
  UNION ALL SELECT 'scv.proposition', proposition FROM \`${DS}.gkm_dict_scv\`
  UNION ALL SELECT 'scv.contributions.contributor', c.contributor FROM \`${DS}.gkm_dict_scv\`, UNNEST(contributions) c
  UNION ALL SELECT 'scv.hasEvidenceLines', h FROM \`${DS}.gkm_dict_scv\`, UNNEST(hasEvidenceLines) h
  UNION ALL SELECT 'evidenceLine.targetProposition', targetProposition FROM \`${DS}.gkm_dict_evidence_line\`
  UNION ALL SELECT 'vcv.proposition', proposition FROM \`${DS}.gkm_dict_vcv\`
  UNION ALL SELECT 'vcv.hasEvidenceLines', h FROM \`${DS}.gkm_dict_vcv\`, UNNEST(hasEvidenceLines) h
  UNION ALL SELECT 'rcv.proposition', proposition FROM \`${DS}.gkm_dict_rcv\`
  UNION ALL SELECT 'rcv.hasEvidenceLines', h FROM \`${DS}.gkm_dict_rcv\`, UNNEST(hasEvidenceLines) h
  UNION ALL SELECT 'vcv_evidenceLine.hasEvidenceItems', h FROM \`${DS}.gkm_dict_vcv_evidence_line\`, UNNEST(hasEvidenceItems) h
  UNION ALL SELECT 'rcv_evidenceLine.hasEvidenceItems', h FROM \`${DS}.gkm_dict_rcv_evidence_line\`, UNNEST(hasEvidenceItems) h
)
SELECT f AS field,
  COUNTIF(NOT REGEXP_CONTAINS(v, r'^#/[A-Za-z][A-Za-z0-9_-]*/.')) AS bare_BAD,
  COUNT(*) AS total,
  IFNULL(ANY_VALUE(IF(NOT REGEXP_CONTAINS(v, r'^#/[A-Za-z][A-Za-z0-9_-]*/.'), v, NULL)), '') AS example_bare
FROM refs WHERE v IS NOT NULL
GROUP BY f ORDER BY f"
REF_OUT="$(bq query --project_id="$PROJECT" --use_legacy_sql=false --format=csv --max_rows=1000 --quiet "$REF_SQL")"
echo "$REF_OUT" | column -t -s,
BARE_TOTAL="$(echo "$REF_OUT" | awk -F, 'NR>1 {s+=$2} END {print s+0}')"
FIELDS_SEEN="$(echo "$REF_OUT" | awk 'NR>1' | wc -l | tr -d ' ')"
if [ "$FIELDS_SEEN" -eq 0 ]; then
  echo "FAIL: reference check returned no rows (query error or empty dataset ${DS})" >&2; exit 1
fi
if [ "$BARE_TOTAL" -ne 0 ]; then
  echo "FAIL: ${BARE_TOTAL} reference value(s) are bare ids, not '#/' pointers (see bare_BAD above)" >&2; exit 1
fi
echo "PASS: every reference field is a '#/' pointer."
