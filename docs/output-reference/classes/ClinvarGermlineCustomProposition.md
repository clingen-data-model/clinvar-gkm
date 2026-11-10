# ClinvarGermlineCustomProposition

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A custom proposition type for ClinVar germline submissions that do not have a corresponding GA4GH VA-Spec proposition type. Includes ClinVar submission categories such as "risk factor", "protective", "drug response", "affects", "association", "confers sensitivity", "other", "not provided", and "conflicting data from submitters". These custom proposition types are used to represent variant-condition associations in ClinVar. No name, description, aliases or extensions.

**JSON Schema:** [ClinvarGermlineCustomProposition](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarGermlineCustomProposition){ target=_blank }

Some ClinvarGermlineCustomProposition attributes are inherited from [SubjectVariantProposition](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/entities/subject-variant-proposition.html#subjectvariantproposition){ target=_blank rel=noopener }, `ClinvarGermlineCustomPropositionProperties`.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 0..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string` | 1..1 | The name of the class that is instantiated by a data object representing the Entity. |
| `subject` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/variation/<id>` | 1..1 | The variant, a '#/variation/<id>' pointer into this bundle. |
| `predicate` | `string` | 1..1 | The relationship declared to hold between the subject and the object of the Proposition. |
| `object` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/condition/<id>` or `#/conditionSet/<id>` | 1..1 | The condition the variant is associated with, a '#/condition/<id>' or '#/conditionSet/<id>' pointer into this bundle. |
| `geneContextQualifier` | [ClinvarGeneContextQualifier](ClinvarGeneContextQualifier.md) | 0..1 | Reports a gene impacted by the variant, which may contribute to the association described in the Proposition (SCV propositions only). |
| `modeOfInheritanceQualifier` | [ClinvarModeOfInheritanceQualifier](ClinvarModeOfInheritanceQualifier.md) | 0..1 | Reports a pattern of inheritance expected for the effect of the variant (SCV propositions only). |
| `penetranceQualifier` | [ClinvarPenetranceQualifier](ClinvarPenetranceQualifier.md) | 0..1 | Reports the penetrance of the effect - the extent to which the variant impact is expressed by carriers (SCV propositions only). |

**Not used by ClinVar-GKM:** `name`, `description`, `aliases`, `extensions`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

