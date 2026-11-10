# ClinvarScvClassification

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The classification of a ClinVar SCV statement: a MappableConcept with its concept type, name, a ClinvarTermCoding, and ClinVar's description of it in an extension. No id, description, aliases or mappings.

**JSON Schema:** [ClinvarScvClassification](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarScvClassification){ target=_blank }

Some ClinvarScvClassification attributes are inherited from [MappableConcept](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/mappable-concept.html#mappableconcept){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`MappableConcept` | 1..1 | MUST be "MappableConcept". |
| `name` | `string` | 0..1 | A primary name for the concept. |
| `extensions` | [ExtensionClassificationDescription](ClinvarScvClassification.md#extensionclassificationdescription)[] (unordered) | 0..m | The classification's description, in an ExtensionClassificationDescription. |
| `conceptType` | `string`<br>`Classification` | 0..1 | Must be 'Classification'. |
| `primaryCoding` | [ClinvarTermCoding](ClinvarTermCoding.md) | 0..1 | The classification's code and its system (the guideline that defines it). |

**Not used by ClinVar-GKM:** `id`, `description`, `aliases`, `mappings`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

## Extensions

These extensions are defined for `ClinvarScvClassification`.

### ExtensionClassificationDescription

ClinVar's description of the SCV's classification: the condition, the review status and the date and submitter of the assessment, as text.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`description` | 0..1 | Must be 'description'. |
| `value` | `string` | 0..1 | The description text. |

