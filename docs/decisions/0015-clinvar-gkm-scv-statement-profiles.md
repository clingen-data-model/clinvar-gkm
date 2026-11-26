# 0015 — ClinVar-GKM SCV statement profiles modelled on the VA-Spec community profiles

- **Status:** Accepted
- **Date:** 2026-11-24
- **Decided:** 2026-11-24 (maintainer)

## Context

VA-Spec publishes community statement profiles for three guidelines: ACMG 2015 (`VariantPathogenicityStatement`),
CCV 2022 (`VariantOncogenicityStatement`) and AMP/ASCO/CAP 2017 (`VariantClinicalSignificanceStatement`). Each fixes
the classification codes and their system, the strengths, and the direction per classification, and requires
`specifiedBy`. They are intentionally strict, and they are not ClinVar-GKM's to change.

Until 1.3.0, ClinVar-GKM's SCV statements were held only to `ClinvarScvStatement`, which allows any coding. Measured
against the community profiles, the 2026-11 full release failed in several ways:

- 400,832 pathogenicity, 139 oncogenicity and 149 clinical significance SCVs have no `specifiedBy`: ClinVar does
  not require an assertion method.
- ClinVar accepts classifications the 2015 guidelines do not define: the SVCv4 VUS sub-tiers (265 SCVs) and the
  combined labels `Benign/Likely benign` and `Pathogenic/Likely pathogenic` (203).
- The low-penetrance and risk-allele strengths (641 SCVs) are coded under the ClinGen 2024 recommendations, where
  their classifications are defined, not under ACMG 2015.
- Every clinical significance SCV (1,752) failed on its coding: the source lookup coded the tiers `tier 1` … `tier 4`
  under the misnamed system `AMP/ASCO/CAP (AAC) Guidelines, 2017`, and `classification.name` is ClinVar's label
  (`Tier I - Strong`), not the canonical `Tier I`.

Some of these are ClinVar's data and cannot be changed. Others were ClinVar-GKM's own coding errors.

## Decision

1. **Three ClinVar-GKM profiles**, `ClinvarScvPathogenicityStatement`, `ClinvarScvOncogenicityStatement` and
   `ClinvarScvClinicalSignificanceStatement`. Each is a `ClinvarScvStatement` plus the community profile's
   classification, strength and direction rules, restated (a `$ref` to the community profile could not be
   relaxed), minus the documented differences.
2. **Selection by proposition section.** An SCV carries no statement-type field. The section its `proposition`
   points into is its statement type, so the bundle schema picks the profile from it. SCVs in
   `propositionClinvarCustom` stay on `ClinvarScvStatement`.
3. **Fix ClinVar-GKM's coding errors at the source** (`clinvar_clinsig_types`, clinvar-ingest-bq-tools):
   `tier 1` … `tier 4` → `tier i` … `tier iv`; `AMP/ASCO/CAP (AAC) Guidelines, 2017` → `AMP/ASCO/CAP Guidelines,
   2017`; the VUS sub-tiers' system `SVC v4` → `ACMG/AMP/CAP/ClinGen SVCv4.0` (short name SVCv4), with their
   strengths `high`, `mid`, `low` in the same system; and `pathogenic/Likely pathogenic` →
   `pathogenic/likely pathogenic`. A strength is always coded in its classification's system.
4. **The canonical tier name is on the coding.** A clinical significance SCV's `classification.primaryCoding.name`
   is `Tier I` … `Tier IV`. `classification.name` stays ClinVar's label: how a classification is named for display
   is the data producer's choice.
5. **The remaining differences are documented, not hidden:**
   - `specifiedBy` is optional in all three profiles.
   - ACMG 2015: the SVCv4 VUS sub-tiers and their strengths, ClinVar's combined labels, and low-penetrance and
     risk-allele strengths under ClinGen 2024 are allowed.
   - AMP/ASCO/CAP 2017: the canonical tier name is on `primaryCoding.name`, not `classification.name`.

   The [Community Profiles](../profiles/community-profiles.md) page compares each rule. Each profile's description
   names its differences. `src/scripts/community-profile-conformance.py`, run by hand on each monthly full release,
   counts the SCVs that do not conform to each unchanged community profile, by reason, and refreshes the counts on
   that page.

## Consequences

- **Schema 1.3.0**, a MINOR release of corrections (the 1.1.0 release policy): the new profiles make some records
  that 1.2.0 allowed invalid. Codes change for consumers filtering on `tier 1` or `SVC v4`. The release notes and
  the changelog say so.
- Four new classes: the three profiles and `ClinvarClassificationCoding`, the SCV classification's coding, which
  allows a `name`.
- 1.3.0 is built **in full**: the incremental mode would carry unchanged SCVs forward with their old codes. The
  first 1.3.0 delta must be built against a dataset rebuilt with the 1.3.0 procedures.
- The source lookup is shared with the live 1.2 line, so it is changed in BigQuery only at the 1.3.0 cut-over.
- The VCV and RCV aggregates are unchanged in shape. They take their codings from the same lookup by label, so
  single-label aggregates pick up the corrected codes.
- Both validators (jsonschema-rs and the gkm-toolkit) now load the community profile schemas, and the rs registry
  refuses to fetch a `$ref` over the network.

## Alternatives considered

- **Change the community profiles** (for example, make `specifiedBy` optional in VA-Spec): rejected. The profiles
  are intentionally defined, and an implementation that does not conform should show where and why.
- **Validate SCVs against the community profiles directly**: impossible, since the profiles reject data ClinVar
  holds.
- **Document the differences only, with no ClinVar-GKM profiles**: rejected. Nothing would enforce the rules
  ClinVar-GKM does meet, and coding errors like `tier 1` would go unnoticed.
