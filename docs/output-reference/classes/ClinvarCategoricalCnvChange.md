# ClinvarCategoricalCnvChange

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.0/appendices/maturity_model.html){ target=_blank rel=noopener }.

A ClinVar copy number variant with a qualitative change indication (gain or loss). Uses a DefiningLocationConstraint with a CopyChangeConstraint from Cat-VRS CategoricalCnv.

**JSON Schema:** [ClinvarCategoricalCnvChange](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarCategoricalCnvChange){ target=_blank }

Some ClinvarCategoricalCnvChange attributes are inherited from [CategoricalCnv](https://cat-vrs.ga4gh.org/en/latest/concepts/Recipes/CategoricalCnv.html#categoricalcnv){ target=_blank rel=noopener }, `ClinvarCategoricalVariantProperties`.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 0..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string` | 0..1 | MUST be "CategoricalVariant" |
| `name` | `string` | 0..1 | A primary name for the entity. |
| `description` | `string` | 0..1 | A free-text description of the Entity. |
| `aliases` | `string`[] (unordered) | 0..m | Alternative name(s) for the Entity. |
| `extensions` | [ExtensionClinvarHgvsList](ClinvarCategoricalVariant.md#extensionclinvarhgvslist) \| [ExtensionClinvarGeneList](ClinvarCategoricalVariant.md#extensionclinvargenelist) \| [ExtensionCategoricalVariationType](ClinvarCategoricalVariant.md#extensioncategoricalvariationtype) \| [ExtensionDefiningVrsVariationType](ClinvarCategoricalVariant.md#extensiondefiningvrsvariationtype) \| [ExtensionClinvarVariationType](ClinvarCategoricalVariant.md#extensionclinvarvariationtype) \| [ExtensionClinvarSubclassType](ClinvarCategoricalVariant.md#extensionclinvarsubclasstype) \| [ExtensionClinvarCytogeneticLocation](ClinvarCategoricalVariant.md#extensionclinvarcytogeneticlocation) \| [ExtensionVrsPreProcessingIssue](ClinvarCategoricalVariant.md#extensionvrspreprocessingissue) \| [ExtensionsVrsProcessingException](ClinvarCategoricalVariant.md#extensionsvrsprocessingexception)[] (unordered) | 0..m | A list of extensions to the entity. Extensions are not expected to be natively understood, but may be used for pre-negotiated exchange of message attributes between systems. |
| `members` | [Variation](https://va-spec.ga4gh.org/en/latest/core-information-model/domain-entities.html#variation){ target=_blank rel=noopener } \| [iriReference](https://va-spec.ga4gh.org/en/latest/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }[] (unordered) | 0..m | A non-exhaustive list of VRS Variations that satisfy the constraints of this categorical variant. |
| `constraints` | [Constraint](https://va-spec.ga4gh.org/en/latest/appendices/imported-models/constraint.html#constraint){ target=_blank rel=noopener }[] (unordered) | 0..m |  |
| `mappings` | [ConceptMapping](https://va-spec.ga4gh.org/en/latest/core-information-model/elements/concept-mapping.html#conceptmapping){ target=_blank rel=noopener }[] (unordered) | 0..m | A list of mappings to concepts in terminologies or code systems. Each mapping should include a coding and a relation. |

