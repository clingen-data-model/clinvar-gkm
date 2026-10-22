-- ============================================================================
-- gkm_proposition_section(prop_type) — the ONE proposition type -> bundle section mapping
-- ============================================================================
-- Propositions are delivered in four sections grouped by meaning (1.1.0, ADR 0006). Every
-- consumer calls this function instead of carrying its own copy of the mapping:
--   * the 8 statement / evidence-line pointer sites (`#/<section>/<id>`) in
--     gkm-scv-statement-proc.sql, gkm-rcv-statement-proc.sql and gkm-vcv-statement-proc.sql;
--   * the NDJSON proposition export and the Parquet proposition template
--     (src/scripts/export-gkm-dicts.sh, src/scripts/parquet-schemas/proposition.sql);
--   * the delta manifest (src/scripts/build-delta-manifest.py);
--   * the reference-integrity validator (src/scripts/validate-proposition-conformance.sh).
--
-- The custom list is EXPLICIT (not LIKE 'Clinvar%'): a new upstream type raises here and fails
-- the build, the export and the validator, instead of landing in a section whose schema rejects
-- it. A NULL type raises too. Callers pass the RESOLVED type the proposition record carries
-- (RCV/VCV: IFNULL(cpt.gks_type, 'ClinvarUndefinedProposition'), as the dict build does).
--
-- Deploy before the procs that call it (it is part of the run-release.sh gate_key, being under
-- src/procedures/):
--   bq query --use_legacy_sql=false < src/procedures/gkm-proposition-section-func.sql
-- ============================================================================
CREATE OR REPLACE FUNCTION `clinvar_ingest.gkm_proposition_section`(prop_type STRING) AS (
  CASE
    WHEN prop_type = 'VariantPathogenicityProposition' THEN 'propositionPathogenicity'
    WHEN prop_type = 'VariantOncogenicityProposition' THEN 'propositionOncogenicity'
    WHEN prop_type IN ('VariantClinicalSignificanceProposition', 'VariantDiagnosticProposition',
                       'VariantPrognosticProposition', 'VariantTherapeuticResponseProposition')
      THEN 'propositionSomaticClinicalImpact'
    WHEN prop_type IN ('ClinvarNotProvidedProposition', 'ClinvarDrugResponseProposition',
                       'ClinvarOtherProposition', 'ClinvarRiskFactorProposition',
                       'ClinvarAssociationProposition', 'ClinvarAffectsProposition',
                       'ClinvarConflictingDataFromSubmitterProposition', 'ClinvarProtectiveProposition',
                       'ClinvarConfersSensitivityProposition', 'ClinvarUndefinedProposition')
      THEN 'propositionClinvarCustom'
    ELSE ERROR(FORMAT('unmapped proposition type for section mapping: %t', prop_type))
  END
);
