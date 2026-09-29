# ClinvarProposition

!!! warning "Draft"

    This data class is at a **draft** maturity level and may change significantly in future releases.

Any proposition type valid in ClinVar-GKM statements. Includes the GA4GH standard proposition types (pathogenicity, oncogenicity, clinical significance) and ClinVar-specific proposition types for submission categories not covered by the GA4GH specifications.

**JSON Schema:** [ClinvarProposition](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarProposition){ target=_blank }

**One of:**

- `VariantPathogenicityProposition`
- `VariantOncogenicityProposition`
- `VariantClinicalSignificanceProposition`
- [ClinvarRiskFactorProposition](ClinvarRiskFactorProposition.md)
- [ClinvarProtectiveProposition](ClinvarProtectiveProposition.md)
- [ClinvarDrugResponseProposition](ClinvarDrugResponseProposition.md)
- [ClinvarAffectsProposition](ClinvarAffectsProposition.md)
- [ClinvarAssociationProposition](ClinvarAssociationProposition.md)
- [ClinvarConfersSensitivityProposition](ClinvarConfersSensitivityProposition.md)
- [ClinvarOtherProposition](ClinvarOtherProposition.md)
- [ClinvarNotProvidedProposition](ClinvarNotProvidedProposition.md)
- [ClinvarConflictingDataFromSubmitterProposition](ClinvarConflictingDataFromSubmitterProposition.md)
- [ClinvarUndefinedProposition](ClinvarUndefinedProposition.md)

