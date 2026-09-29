# Propositions

A proposition defines what a statement asserts — the relationship between a variant and a condition. Each proposition follows the subject-predicate-object pattern from the GA4GH [VA-Spec](https://va-spec.ga4gh.org/) specification:

- **Subject** (`subject`) — a reference to a ClinVar variation via `#/variation/clinvar:{id}`
- **Predicate** — the relationship type (e.g., `isCausalFor`, `isOncogenicFor`)
- **Object** (`object`) — a condition, disease, or phenotype

The [ClinvarProposition](ClinvarProposition.md) union type encompasses all 13 proposition types valid in ClinVar-GKM.

---

## Proposition Types

ClinVar-GKM uses 13 proposition types: 3 from the GA4GH VA-Spec standard and 10 defined specifically for ClinVar submission categories. The 10 ClinVar-specific types are **open subtypes of the VA-Spec `SubjectVariantProposition` base** — each carries its own real `type` name (the former `CustomProposition` + `customPropositionType` model is retired).

### GA4GH Standard Types

These types are defined in the [VA-Spec](https://va-spec.ga4gh.org/) and used directly:

| Code | Type | Predicate | Description |
| --- | --- | --- | --- |
| `PATH` | VariantPathogenicityProposition | `isCausalFor` | Germline pathogenicity/benignity |
| `ONCO` | VariantOncogenicityProposition | `isOncogenicFor` | Oncogenicity classification |
| `SCI` | VariantClinicalSignificanceProposition | `hasClinicalSignificanceFor` | Somatic clinical impact |

### ClinVar-Specific Types

These types handle ClinVar submission categories not covered by the GA4GH specifications. Several are no longer accepted as new submissions by ClinVar, but historical submissions remain in the dataset.

| Code | Type | Predicate | Description |
| --- | --- | --- | --- |
| `RF` | [ClinvarRiskFactorProposition](ClinvarRiskFactorProposition.md) | `isRiskFactorFor` | Risk factor |
| `PROT` | [ClinvarProtectiveProposition](ClinvarProtectiveProposition.md) | `isProtectiveFor` | Protective |
| `DR` | [ClinvarDrugResponseProposition](ClinvarDrugResponseProposition.md) | `hasDrugResponseFor` | Drug response |
| `AFF` | [ClinvarAffectsProposition](ClinvarAffectsProposition.md) | `hasAffectFor` | Affects |
| `ASSOC` | [ClinvarAssociationProposition](ClinvarAssociationProposition.md) | `isAssociatedWith` | Association |
| `CS` | [ClinvarConfersSensitivityProposition](ClinvarConfersSensitivityProposition.md) | `confersSensitivityFor` | Confers sensitivity |
| `OTH` | [ClinvarOtherProposition](ClinvarOtherProposition.md) | `isClinvarOtherAssociationFor` | Other |
| `NP` | [ClinvarNotProvidedProposition](ClinvarNotProvidedProposition.md) | `hasNoProvidedClassificationFor` | Not provided |
| `CONF` | [ClinvarConflictingDataFromSubmitterProposition](ClinvarConflictingDataFromSubmitterProposition.md) | `isConflictingDataFromSubmittersFor` | Conflicting data (germline only) |
| `UNDEF` | [ClinvarUndefinedProposition](ClinvarUndefinedProposition.md) | `isClinvarUndefinedAssociationFor` | Fallback for a classification that maps to no defined type |

---

## Somatic Evidence Line Propositions

Somatic clinical impact (SCI) statements carry evidence lines with their own target propositions. These 3 types appear only on [ClinvarSomaticEvidenceLine](ClinvarSomaticEvidenceLine.md) objects, not as top-level statement propositions:

| Code | Type | Predicates |
| --- | --- | --- |
| `TR` | VariantTherapeuticResponseProposition | `predictsSensitivityTo`, `predictsResistanceTo` |
| `DIAG` | VariantDiagnosticProposition | `isDiagnosticInclusionCriterionFor`, `isDiagnosticExclusionCriterionFor` |
| `PROG` | VariantPrognosticProposition | `associatedWithBetterOutcomeFor`, `associatedWithWorseOutcomeFor` |

---

## Inherited Attributes

All ClinVar proposition types are subtypes of the VA-Spec `SubjectVariantProposition` (the ClinVar-specific types via the open `ClinvarGermlineCustomProposition` base; the standard types via VA-Spec's `GeneticContextVariantProposition`). Common attributes:

- `subject` — the variant being classified (`MolecularVariation` \| `CategoricalVariant` \| `iriReference`)
- `object` — the associated `Condition`, `ConditionSet`, tumor type, or therapy
- `geneContextQualifier` — the gene impacted by the variant
- `alleleOriginQualifier` — germline, somatic, or mosaic origin

See the individual class pages for the complete information model including all inherited fields.
