# ClinvarNonConstrainedVariant

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A ClinVar variant that cannot be mapped to a specific VRS allele or location — haplotypes, genotypes, and other complex or ambiguously defined variants. These rely solely on the ClinVar variation ID and use the generalized Cat-VRS CategoricalVariant without VRS constraints or members.

**JSON Schema:** [ClinvarNonConstrainedVariant](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarNonConstrainedVariant){ target=_blank }

Some ClinvarNonConstrainedVariant attributes are inherited from [CategoricalVariant](https://va-spec.ga4gh.org/en/1.1.0/appendices/imported-models/categorical-variant.html#categoricalvariant){ target=_blank rel=noopener }, `ClinvarCategoricalVariantProperties`.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 1..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string`<br>`CategoricalVariant` | 1..1 | MUST be "CategoricalVariant" |
| `name` | `string` | 1..1 | A primary name for the entity. |
| `extensions` | [ExtensionClinvarHgvsList](ClinvarCategoricalVariant.md#extensionclinvarhgvslist) \| [ExtensionClinvarGeneList](ClinvarCategoricalVariant.md#extensionclinvargenelist) \| [ExtensionCategoricalVariationType](ClinvarCategoricalVariant.md#extensioncategoricalvariationtype) \| [ExtensionDefiningVrsVariationType](ClinvarCategoricalVariant.md#extensiondefiningvrsvariationtype) \| [ExtensionClinvarVariationType](ClinvarCategoricalVariant.md#extensionclinvarvariationtype) \| [ExtensionClinvarSubclassType](ClinvarCategoricalVariant.md#extensionclinvarsubclasstype) \| [ExtensionClinvarCytogeneticLocation](ClinvarCategoricalVariant.md#extensionclinvarcytogeneticlocation) \| [ExtensionVrsPreProcessingIssue](ClinvarCategoricalVariant.md#extensionvrspreprocessingissue) \| [ExtensionsVrsProcessingException](ClinvarCategoricalVariant.md#extensionsvrsprocessingexception)[] (unordered) | 1..m | A list of extensions to the entity. Extensions are not expected to be natively understood, but may be used for pre-negotiated exchange of message attributes between systems. |
| `mappings` | [ClinvarVariationMapping](ClinvarVariationMapping.md)[] (unordered) | 1..m | The variation's ClinVar identifier (`exactMatch`) and its cross-references to other variant resources. |

**Not used by ClinVar-GKM:** `description`, `aliases`, `members`, `constraints`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

