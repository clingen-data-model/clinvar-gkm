# ClinvarOtherProposition

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A proposition for ClinVar submissions classified as "other" that do not fit any standard or named classification category. ClinVar has stopped accepting new submissions with this classification, but historical submissions remain.

**JSON Schema:** [ClinvarOtherProposition](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarOtherProposition){ target=_blank }

Some ClinvarOtherProposition attributes are inherited from [ClinvarGermlineCustomProposition](ClinvarGermlineCustomProposition.md).

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 0..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string` | 0..1 | MUST be "ClinvarOtherProposition". |
| `name` | `string` | 0..1 | A primary name for the entity. |
| `description` | `string` | 0..1 | A free-text description of the Entity. |
| `aliases` | `string`[] (unordered) | 0..m | Alternative name(s) for the Entity. |
| `extensions` | [Extension](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/extension.html#extension){ target=_blank rel=noopener }[] (unordered) | 0..m | A list of extensions to the Entity, that allow for capture of information not directly supported by elements defined in the model. |
| `subject` | [MolecularVariation](https://va-spec.ga4gh.org/en/1.1.0/appendices/imported-models/molecular-variation.html#molecularvariation){ target=_blank rel=noopener } \| [CategoricalVariant](https://va-spec.ga4gh.org/en/1.1.0/appendices/imported-models/categorical-variant.html#categoricalvariant){ target=_blank rel=noopener } \| [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener } | 0..1 | A variant that is the subject of the Proposition. |
| `predicate` | `string` | 0..1 | The relationship the Proposition describes between the subject variant and object condition. MUST be "isClinvarOtherAssociationFor". |
| `object` | [Condition](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/domain-entities.html#condition){ target=_blank rel=noopener } \| [ConditionSet](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/domain-entities.html#conditionset){ target=_blank rel=noopener } \| [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener } | 0..1 | The condition for which the variant is associated. |
| `geneContextQualifier` | [MappableConcept](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/mappable-concept.html#mappableconcept){ target=_blank rel=noopener } \| [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener } | 0..1 | Reports a gene impacted by the variant, which may contribute to the association described in the Proposition. |
| `modeOfInheritanceQualifier` | [MappableConcept](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/mappable-concept.html#mappableconcept){ target=_blank rel=noopener } \| [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener } | 0..1 | Reports a pattern of inheritance expected for the effect of the variant. |
| `penetranceQualifier` | [MappableConcept](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/mappable-concept.html#mappableconcept){ target=_blank rel=noopener } \| [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener } | 0..1 | Reports the penetrance of the effect - the extent to which the variant impact is expressed by carriers. |

