# ClinvarConflictingDataFromSubmitterProposition

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A proposition for ClinVar submissions where the submitter's data conflicts with other submitters' data for the same variant-condition pair. Used for submissions classified as "conflicting data from submitters".

**JSON Schema:** [ClinvarConflictingDataFromSubmitterProposition](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarConflictingDataFromSubmitterProposition){ target=_blank }

Some ClinvarConflictingDataFromSubmitterProposition attributes are inherited from [ClinvarGermlineCustomProposition](ClinvarGermlineCustomProposition.md).

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 1..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string`<br>`ClinvarConflictingDataFromSubmitterProposition` | 1..1 | MUST be "ClinvarConflictingDataFromSubmitterProposition". |
| `subject` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/variation/<id>` | 1..1 | The variant, a '#/variation/<id>' pointer into this bundle. |
| `predicate` | `string`<br>`isConflictingDataFromSubmittersFor` | 1..1 | The relationship the Proposition describes between the subject variant and object condition. MUST be "isConflictingDataFromSubmittersFor". |
| `object` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/condition/<id>` or `#/conditionSet/<id>` | 1..1 | The condition the variant is associated with, a '#/condition/<id>' or '#/conditionSet/<id>' pointer into this bundle. |
| `geneContextQualifier` | [ClinvarGeneContextQualifier](ClinvarGeneContextQualifier.md) | 0..1 | Reports a gene impacted by the variant, which may contribute to the association described in the Proposition (SCV propositions only). |
| `modeOfInheritanceQualifier` | [ClinvarModeOfInheritanceQualifier](ClinvarModeOfInheritanceQualifier.md) | 0..1 | Reports a pattern of inheritance expected for the effect of the variant (SCV propositions only). |
| `penetranceQualifier` | [ClinvarPenetranceQualifier](ClinvarPenetranceQualifier.md) | 0..1 | Reports the penetrance of the effect - the extent to which the variant impact is expressed by carriers (SCV propositions only). |

**Not used by ClinVar-GKM:** `name`, `description`, `aliases`, `extensions`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

