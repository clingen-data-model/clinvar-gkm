# ClinvarNotProvidedProposition

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.0/appendices/maturity_model.html){ target=_blank rel=noopener }.

A proposition for ClinVar submissions where the submitter did not provide a clinical classification. These submissions still carry variant-condition associations but lack a formal pathogenicity or clinical significance assessment.

**JSON Schema:** [ClinvarNotProvidedProposition](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarNotProvidedProposition){ target=_blank }

Some ClinvarNotProvidedProposition attributes are inherited from [ClinvarGermlineCustomProposition](ClinvarGermlineCustomProposition.md).

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 0..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string` | 0..1 | MUST be "ClinvarNotProvidedProposition". |
| `name` | `string` | 0..1 | A primary name for the entity. |
| `description` | `string` | 0..1 | A free-text description of the Entity. |
| `aliases` | `string`[] (unordered) | 0..m | Alternative name(s) for the Entity. |
| `extensions` | `Extension`[] (unordered) | 0..m | A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model. |
| `subject` | `MolecularVariation` \| `CategoricalVariant` \| `iriReference` | 0..1 | A variant that is the subject of the Proposition. |
| `predicate` | `string` | 0..1 | The relationship the Proposition describes between the subject variant and object condition. MUST be "hasNoProvidedClassificationFor". |
| `object` | `Condition` \| `ConditionSet` \| `iriReference` | 0..1 | The condition for which the variant is associated. |
| `geneContextQualifier` | `MappableConcept` \| `iriReference` | 0..1 | Reports a gene impacted by the variant, which may contribute to the association described in the Proposition. |
| `modeOfInheritanceQualifier` | `MappableConcept` \| `iriReference` | 0..1 | Reports a pattern of inheritance expected for the effect of the variant. |
| `penetranceQualifier` | `MappableConcept` \| `iriReference` | 0..1 | Reports the penetrance of the effect - the extent to which the variant impact is expressed by carriers. |

