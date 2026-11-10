# Propositions

A proposition defines what a statement asserts — the relationship between a variant and a condition. Each proposition follows the subject-predicate-object pattern from the GA4GH [VA-Spec](https://va-spec.ga4gh.org/) specification:

- **Subject** (`subject`) — a reference to a ClinVar variation via `#/variation/clinvar:{id}`
- **Predicate** — the relationship type (e.g., `isCausalFor`, `isOncogenicFor`)
- **Object** (`object`) — a condition, disease, or phenotype, as a `#/condition/` or `#/conditionSet/` reference (a therapy for therapeutic response)

Each proposition section points at its ClinVar profiles, which narrow the VA-Spec proposition classes to what the pipeline writes: `subject`, `object`, and `conditionQualifier` are pointers limited to the sections they may target, the qualifiers are ClinVar qualifier classes, and none carries `name`, `description`, `aliases`, `extensions`, or `alleleOriginQualifier`.

---

## Proposition Types

ClinVar-GKM uses 13 proposition types: 3 from the GA4GH VA-Spec standard and 10 defined specifically for ClinVar submission categories. The 10 ClinVar-specific types are **open subtypes of the VA-Spec `SubjectVariantProposition` base** — each carries its own real `type` name (the former `CustomProposition` + `customPropositionType` model is retired).

### GA4GH Standard Types

These types are defined in the [VA-Spec](https://va-spec.ga4gh.org/). Records keep the VA-Spec `type` name and validate against a ClinVar profile of it:

| Code | Type | ClinVar Profile | Predicate | Description |
| --- | --- | --- | --- | --- |
| `PATH` | VariantPathogenicityProposition | [ClinvarVariantPathogenicityProposition](ClinvarVariantPathogenicityProposition.md) | `isCausalFor` | Germline pathogenicity/benignity |
| `ONCO` | VariantOncogenicityProposition | [ClinvarVariantOncogenicityProposition](ClinvarVariantOncogenicityProposition.md) | `isOncogenicFor` | Oncogenicity classification |
| `SCI` | VariantClinicalSignificanceProposition | [ClinvarVariantClinicalSignificanceProposition](ClinvarVariantClinicalSignificanceProposition.md) | `hasClinicalSignificanceFor` | Somatic clinical impact |

### ClinVar-Specific Types

These types handle ClinVar submission categories not covered by the GA4GH specifications. Several are no longer accepted as new submissions by ClinVar, but historical submissions remain in the dataset.

| Code | Type | Predicate | Description |
| --- | --- | --- | --- |
| `RF` | [ClinvarRiskFactorProposition](ClinvarRiskFactorProposition.md) | `isRiskFactorFor` | Risk factor |
| `PROTECT` | [ClinvarProtectiveProposition](ClinvarProtectiveProposition.md) | `isProtectiveFor` | Protective |
| `DR` | [ClinvarDrugResponseProposition](ClinvarDrugResponseProposition.md) | `hasDrugResponseFor` | Drug response |
| `AFF` | [ClinvarAffectsProposition](ClinvarAffectsProposition.md) | `hasAffectFor` | Affects |
| `ASSOC` | [ClinvarAssociationProposition](ClinvarAssociationProposition.md) | `isAssociatedWith` | Association |
| `CS` | [ClinvarConfersSensitivityProposition](ClinvarConfersSensitivityProposition.md) | `confersSensitivityFor` | Confers sensitivity |
| `OTH` | [ClinvarOtherProposition](ClinvarOtherProposition.md) | `isClinvarOtherAssociationFor` | Other |
| `NP` | [ClinvarNotProvidedProposition](ClinvarNotProvidedProposition.md) | `hasNoProvidedClassificationFor` | Not provided |
| `CDFS` | [ClinvarConflictingDataFromSubmitterProposition](ClinvarConflictingDataFromSubmitterProposition.md) | `isConflictingDataFromSubmittersFor` | Conflicting data (germline only) |
| `UNDEF` | [ClinvarUndefinedProposition](ClinvarUndefinedProposition.md) | `isClinvarUndefinedAssociationFor` | Fallback for a classification that maps to no defined type |

---

## Somatic Evidence Line Propositions

Somatic clinical impact (SCI) statements carry evidence lines with their own target propositions. These 3 types are targeted only by the `targetProposition` of a [ClinvarSomaticEvidenceLine](ClinvarSomaticEvidenceLine.md), never by a statement's `proposition`:

| Code | Type | ClinVar Profile | Predicates |
| --- | --- | --- | --- |
| `TR` | VariantTherapeuticResponseProposition | [ClinvarVariantTherapeuticResponseProposition](ClinvarVariantTherapeuticResponseProposition.md) | `predictsSensitivityTo`, `predictsResistanceTo` |
| `DIAG` | VariantDiagnosticProposition | [ClinvarVariantDiagnosticProposition](ClinvarVariantDiagnosticProposition.md) | `isDiagnosticInclusionCriterionFor`, `isDiagnosticExclusionCriterionFor` |
| `PROG` | VariantPrognosticProposition | [ClinvarVariantPrognosticProposition](ClinvarVariantPrognosticProposition.md) | `associatedWithBetterOutcomeFor`, `associatedWithWorseOutcomeFor` |

---

## Bundle Sections

Since 1.1.0, propositions are delivered in four bundle sections grouped by **meaning**. A proposition's
section depends only on its `type`, at every level (SCV, VCV, RCV). The Parquet tables have the same names.

| Section | Types |
| --- | --- |
| `propositionPathogenicity` | `PATH` |
| `propositionOncogenicity` | `ONCO` |
| `propositionSomaticClinicalImpact` | `SCI`, `DIAG`, `PROG`, `TR` |
| `propositionClinvarCustom` | `RF`, `PROTECT`, `DR`, `AFF`, `ASSOC`, `CS`, `OTH`, `NP`, `CDFS`, `UNDEF` |

Statements and evidence lines point at the section: `#/propositionPathogenicity/SCV001234567-PATH`.

---

## Common Attributes

All ClinVar proposition types are subtypes of the VA-Spec `SubjectVariantProposition` (the ClinVar-specific types via the open `ClinvarGermlineCustomProposition` base; the standard types via VA-Spec's `GeneticContextVariantProposition`). Their ClinVar profiles allow these attributes:

- `subject` — the variant being classified, a `#/variation/` pointer
- `object` — the asserted object, a pointer: a `#/condition/` or `#/conditionSet/` for most types; a `#/therapy/` or `#/therapyGroup/` for `VariantTherapeuticResponseProposition` (drug therapies are content-addressed and deduplicated into the `therapy` / `therapyGroup` bundle sections)
- `conditionQualifier` — for `VariantTherapeuticResponseProposition` only, the `#/condition/` or `#/conditionSet/` the therapeutic response is asserted in (since `object` carries the therapy)
- `geneContextQualifier` — the gene impacted by the variant, embedded as a [ClinvarGeneContextQualifier](ClinvarGeneContextQualifier.md). Its `geneContextSource` extension may only be `submittedSymbolMatches`, `submittedSymbolDiffers`, `inferredFromVariant` or `submittedNotNormalized`. Every ClinVar proposition profile types the qualifier this way, including the profiles of the VA-Spec types.
- `modeOfInheritanceQualifier` — the submitted mode of inheritance, as a [ClinvarModeOfInheritanceQualifier](ClinvarModeOfInheritanceQualifier.md). Allowed on pathogenicity and the ClinVar-specific types only.
- `penetranceQualifier` — `low` or `risk`, derived from a low-penetrance or risk-allele classification, as a [ClinvarPenetranceQualifier](ClinvarPenetranceQualifier.md). Allowed on pathogenicity and the ClinVar-specific types only.

The qualifiers appear on SCV propositions only; VCV and RCV propositions carry none. No ClinVar proposition carries `alleleOriginQualifier`.

See the individual class pages for the complete information model including all inherited fields.
