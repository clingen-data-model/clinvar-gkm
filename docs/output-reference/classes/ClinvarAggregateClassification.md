# ClinvarAggregateClassification

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The classification of a ClinVar VCV or RCV aggregate statement: a MappableConcept with its concept type, the aggregate classification label as its name, a ClinvarTermCoding for that label and, when the submissions conflict, an ExtensionConflictingExplanation. No id, description, aliases or mappings.

**JSON Schema:** [ClinvarAggregateClassification](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarAggregateClassification){ target=_blank }

Some ClinvarAggregateClassification attributes are inherited from [MappableConcept](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/mappable-concept.html#mappableconcept){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`MappableConcept` | 1..1 | MUST be "MappableConcept". |
| `name` | `string` | 0..1 | A primary name for the concept. |
| `extensions` | [ExtensionConflictingExplanation](ClinvarAggregateClassification.md#extensionconflictingexplanation)[] (unordered) | 0..m | The conflicting classifications, in an ExtensionConflictingExplanation. |
| `conceptType` | `string`<br>`Classification` | 1..1 | Must be 'Classification'. |
| `primaryCoding` | [ClinvarTermCoding](ClinvarTermCoding.md) | 0..1 | The aggregate classification's code and its system. A label that ClinVar's classification terms define (for a somatic clinical impact statement, its highest tier, without the tumor-type text) has the coding its SCVs carry, with the code in lower case. Any other label (a combination of terms, a conflicting classification, or no classifications from unflagged records) is a ClinVar-defined term: the lower-cased label as the code and 'ClinVar' as the system. |

**Not used by ClinVar-GKM:** `id`, `description`, `aliases`, `mappings`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

## Extensions

These extensions are defined for `ClinvarAggregateClassification`.

### ExtensionConflictingExplanation

The classifications behind a conflicting aggregate classification, with the number of submissions for each (e.g., "Pathogenic(2); Uncertain significance(1)").

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`conflictingExplanation` | 1..1 | Must be 'conflictingExplanation'. |
| `value` | `string` | 1..1 | The classifications and their submission counts, separated by '; '. |

