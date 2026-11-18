# ClinvarCategoricalCnvChange

!!! warning "Draft"

    May change significantly in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A ClinVar copy number variant with a qualitative change indication (gain or loss). Uses a DefiningLocationConstraint with a CopyChangeConstraint from Cat-VRS CategoricalCnv.

**JSON Schema:** [ClinvarCategoricalCnvChange](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarCategoricalCnvChange){ target=_blank }

Some ClinvarCategoricalCnvChange attributes are inherited from [CategoricalCnv](https://cat-vrs.ga4gh.org/en/1.1.1/concepts/Recipes/CategoricalCnv.html#categoricalcnv){ target=_blank rel=noopener }, `ClinvarCategoricalVariantProperties`.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 1..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string`<br>`CategoricalVariant` | 1..1 | MUST be "CategoricalVariant" |
| `name` | `string` | 1..1 | A primary name for the entity. |
| `extensions` | [ExtensionClinvarHgvsList](ClinvarCategoricalVariant.md#extensionclinvarhgvslist) \| [ExtensionClinvarGeneList](ClinvarCategoricalVariant.md#extensionclinvargenelist) \| [ExtensionCategoricalVariationType](ClinvarCategoricalVariant.md#extensioncategoricalvariationtype) \| [ExtensionDefiningVrsVariationType](ClinvarCategoricalVariant.md#extensiondefiningvrsvariationtype) \| [ExtensionClinvarVariationType](ClinvarCategoricalVariant.md#extensionclinvarvariationtype) \| [ExtensionClinvarSubclassType](ClinvarCategoricalVariant.md#extensionclinvarsubclasstype) \| [ExtensionClinvarCytogeneticLocation](ClinvarCategoricalVariant.md#extensionclinvarcytogeneticlocation) \| [ExtensionVrsPreProcessingIssue](ClinvarCategoricalVariant.md#extensionvrspreprocessingissue) \| [ExtensionsVrsProcessingException](ClinvarCategoricalVariant.md#extensionsvrsprocessingexception)[] (unordered) | 1..m | A list of extensions to the entity. Extensions are not expected to be natively understood, but may be used for pre-negotiated exchange of message attributes between systems. |
| `members` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }[] (unordered)<br>pointer to `#/copyNumberChange/<id>` | 1..m | The VRS copy number change, a '#/copyNumberChange/<id>' pointer into this bundle. |
| `constraints` | [ClinvarDefiningLocationConstraint](ClinvarDefiningLocationConstraint.md) \| [ClinvarCopyChangeConstraint](ClinvarCopyChangeConstraint.md)[] (unordered) | 2..2 | The defining location constraint and the copy change constraint. |
| `mappings` | [ClinvarVariationMapping](ClinvarVariationMapping.md)[] (unordered) | 1..m | The variation's ClinVar identifier (`exactMatch`) and its cross-references to other variant resources. |

**Not used by ClinVar-GKM:** `description`, `aliases`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

