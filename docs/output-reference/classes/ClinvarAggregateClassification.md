# ClinvarAggregateClassification

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The classification of a ClinVar VCV or RCV aggregate statement: a MappableConcept with its concept type and the aggregate classification label as its name and, when the submissions conflict, an ExtensionConflictingExplanation. No id, description, aliases, coding or mappings.

**JSON Schema:** [ClinvarAggregateClassification](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarAggregateClassification){ target=_blank }

Some ClinvarAggregateClassification attributes are inherited from [MappableConcept](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/mappable-concept.html#mappableconcept){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`MappableConcept` | 1..1 | MUST be "MappableConcept". |
| `name` | `string` | 0..1 | A primary name for the concept. |
| `extensions` | [ExtensionConflictingExplanation](ClinvarAggregateClassification.md#extensionconflictingexplanation)[] (unordered) | 0..m | The conflicting classifications, in an ExtensionConflictingExplanation. |
| `conceptType` | `string`<br>`Classification` | 0..1 | Must be 'Classification'. |

**Not used by ClinVar-GKM:** `id`, `description`, `aliases`, `primaryCoding`, `mappings`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

## Extensions

These extensions are defined for `ClinvarAggregateClassification`.

### ExtensionConflictingExplanation

The classifications behind a conflicting aggregate classification, with the number of submissions for each (e.g., "Pathogenic(2); Uncertain significance(1)").

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`conflictingExplanation` | 0..1 | Must be 'conflictingExplanation'. |
| `value` | `string` | 0..1 | The classifications and their submission counts, separated by '; '. |

