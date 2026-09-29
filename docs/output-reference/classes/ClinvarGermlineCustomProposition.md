# ClinvarGermlineCustomProposition

!!! warning "Draft"

    This data class is at a **draft** maturity level and may change significantly in future releases.

A custom proposition type for ClinVar germline submissions that do not have a corresponding GA4GH VA-Spec proposition type. Includes ClinVar submission categories such as "risk factor", "protective", "drug response", "affects", "association", "confers sensitivity", "other", "not provided", and "conflicting data from submitters". These custom proposition types are used to represent variant-condition associations in Clin

**JSON Schema:** [ClinvarGermlineCustomProposition](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarGermlineCustomProposition){ target=_blank }

Some ClinvarGermlineCustomProposition attributes are inherited from `SubjectVariantProposition`, `ClinvarGermlineCustomPropositionProperties`.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 0..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string` | 0..1 | The name of the class that is instantiated by a data object representing the Entity. |
| `name` | `string` | 0..1 | A primary name for the entity. |
| `description` | `string` | 0..1 | A free-text description of the Entity. |
| `aliases` | `string`[] (unordered) | 0..m | Alternative name(s) for the Entity. |
| `extensions` | `Extension`[] (unordered) | 0..m | A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model. |
| `subject` | `MolecularVariation` \| `CategoricalVariant` \| `iriReference` | 0..1 | A variant that is the subject of the Proposition. |
| `predicate` | `string` | 0..1 | The relationship declared to hold between the subject and the object of the Proposition. |
| `object` | `Condition` \| `ConditionSet` \| `iriReference` | 0..1 | The condition for which the variant is associated. |
| `geneContextQualifier` | `MappableConcept` \| `iriReference` | 0..1 | Reports a gene impacted by the variant, which may contribute to the association described in the Proposition. |
| `modeOfInheritanceQualifier` | `MappableConcept` \| `iriReference` | 0..1 | Reports a pattern of inheritance expected for the effect of the variant. |
| `penetranceQualifier` | `MappableConcept` \| `iriReference` | 0..1 | Reports the penetrance of the effect - the extent to which the variant impact is expressed by carriers. |

