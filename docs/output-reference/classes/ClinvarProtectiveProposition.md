# ClinvarProtectiveProposition

!!! warning "Draft"

    This data class is at a **draft** maturity level and may change significantly in future releases.

A custom proposition describing the protective role of a variant against a condition. Used for ClinVar submissions classified as "protective". ClinVar has stopped accepting new submissions with this classification, but historical submissions remain.

**JSON Schema:** [ClinvarProtectiveProposition](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarProtectiveProposition){ target=_blank }

Some ClinvarProtectiveProposition attributes are inherited from [ClinvarGermlineCustomProposition](ClinvarGermlineCustomProposition.md).

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 0..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string` | 0..1 | MUST be "ClinvarProtectiveProposition". |
| `name` | `string` | 0..1 | A primary name for the entity. |
| `description` | `string` | 0..1 | A free-text description of the Entity. |
| `aliases` | `string`[] (unordered) | 0..m | Alternative name(s) for the Entity. |
| `extensions` | `Extension`[] (unordered) | 0..m | A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model. |
| `subject` | `MolecularVariation` \| `CategoricalVariant` \| `iriReference` | 0..1 | A variant that is the subject of the Proposition. |
| `predicate` | `string` | 0..1 | The relationship the Proposition describes between the subject variant and object condition. MUST be "isProtectiveFor". |
| `object` | `Condition` \| `ConditionSet` \| `iriReference` | 0..1 | The condition for which the variant is associated. |
| `geneContextQualifier` | `MappableConcept` \| `iriReference` | 0..1 | Reports a gene impacted by the variant, which may contribute to the association described in the Proposition. |
| `modeOfInheritanceQualifier` | `MappableConcept` \| `iriReference` | 0..1 | Reports a pattern of inheritance expected for the effect of the variant. |
| `penetranceQualifier` | `MappableConcept` \| `iriReference` | 0..1 | Reports the penetrance of the effect - the extent to which the variant impact is expressed by carriers. |

