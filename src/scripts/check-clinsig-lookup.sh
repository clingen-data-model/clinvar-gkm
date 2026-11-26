#!/bin/bash
#
# check-clinsig-lookup.sh — before run-release.sh builds anything: confirm that the shared classification lookup
# clinvar_ingest.clinvar_clinsig_types carries the guideline codings the SCV statement profiles require (schema
# 1.3.0, ADR 0015). The lookup is maintained in clinvar-ingest-bq-tools
# (scripts/dataset-preparation/00-setup-translation-tables.sql) and applied to BigQuery by hand, so a build can run
# against an outdated copy: the procs would then write the old codes, and only the bundle validation at publish
# would notice, after the whole build. Read-only.
#
# Fails on any row with:
#   - a classification code that is not lower case ('pathogenic/Likely pathogenic')
#   - a retired system name ('SVC v4', 'AMP/ASCO/CAP (AAC) Guidelines, 2017')
#   - a somatic clinical impact code other than 'tier i' ... 'tier iv', or a system other than AMP/ASCO/CAP 2017
#   - a VUS sub-tier (vus-h, vus-m, vus-l) not under 'ACMG/AMP/CAP/ClinGen SVCv4.0', or without a strength
# and when any of those rows is missing.
#
# USAGE:
#   ./src/scripts/check-clinsig-lookup.sh
#
# ENV OVERRIDES:
#   PROJECT_ID       GCP project (default clingen-dev)
#   CLINSIG_LOOKUP   the lookup table (default clinvar_ingest.clinvar_clinsig_types)

set -o errexit
set -o nounset
set -o pipefail

PROJECT_ID="${PROJECT_ID:-clingen-dev}"
export CLOUDSDK_CORE_PROJECT="${PROJECT_ID}"
LOOKUP="${CLINSIG_LOOKUP:-clinvar_ingest.clinvar_clinsig_types}"

QUERY="
WITH clinsig AS (SELECT * FROM \`${LOOKUP}\`),
row_problems AS (
  SELECT FORMAT('%s %s: %s', proposition_type, code, CASE
      WHEN classification_code != LOWER(classification_code)
        THEN FORMAT('classification code %T is not lower case', classification_code)
      WHEN code_system = 'SVC v4' OR STRPOS(code_system, '(AAC)') > 0
        THEN FORMAT('retired system name %T', code_system)
      WHEN proposition_type = 'sci' AND classification_code NOT IN ('tier i', 'tier ii', 'tier iii', 'tier iv')
        THEN FORMAT('classification code %T is not tier i ... tier iv', classification_code)
      WHEN proposition_type = 'sci' AND code_system != 'AMP/ASCO/CAP Guidelines, 2017'
        THEN FORMAT('system %T is not AMP/ASCO/CAP Guidelines, 2017', code_system)
      WHEN code IN ('vus-h', 'vus-m', 'vus-l') AND code_system != 'ACMG/AMP/CAP/ClinGen SVCv4.0'
        THEN FORMAT('system %T is not ACMG/AMP/CAP/ClinGen SVCv4.0', code_system)
      WHEN code IN ('vus-h', 'vus-m', 'vus-l') AND strength_code IS NULL
        THEN 'no strength'
    END) AS problem
  FROM clinsig
),
missing AS (
  SELECT FORMAT('%s %s: missing', want.proposition_type, want.classification_code) AS problem
  FROM UNNEST([
    STRUCT('sci' AS proposition_type, 'tier i' AS classification_code), ('sci', 'tier ii'), ('sci', 'tier iii'),
    ('sci', 'tier iv'), ('path', 'vus-high'), ('path', 'vus-mid'), ('path', 'vus-low'),
    ('path', 'pathogenic/likely pathogenic')
  ]) AS want
  LEFT JOIN clinsig USING (proposition_type, classification_code)
  WHERE clinsig.code IS NULL
)
SELECT problem FROM row_problems WHERE problem IS NOT NULL
UNION ALL SELECT problem FROM missing
ORDER BY problem
"

echo "    checking ${LOOKUP} for the SCV statement profile codings"
out="$(bq query --project_id="${PROJECT_ID}" --use_legacy_sql=false --format=csv --max_rows=1000 "${QUERY}")" || {
  echo "ERROR: could not read ${LOOKUP}" >&2
  exit 1
}
problems="$(printf '%s\n' "${out}" | grep -v -x -e 'problem' -e '' || true)"
if [[ -n "${problems}" ]]; then
  echo "ERROR: ${LOOKUP} does not carry the codings the SCV statement profiles require:" >&2
  printf '%s\n' "${problems}" | sed 's/^/    /' >&2
  echo "Apply the clinvar_clinsig_types statements of clinvar-ingest-bq-tools'" \
    "scripts/dataset-preparation/00-setup-translation-tables.sql (main) to BigQuery first." >&2
  exit 1
fi
echo "    ${LOOKUP} carries the profile codings"
