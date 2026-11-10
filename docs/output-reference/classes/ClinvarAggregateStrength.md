# ClinvarAggregateStrength

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The strength of a ClinVar VCV or RCV aggregate statement: a ClinvarTerm (no coding) whose concept type is 'Strength'.

**JSON Schema:** [ClinvarAggregateStrength](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarAggregateStrength){ target=_blank }

Some ClinvarAggregateStrength attributes are inherited from [ClinvarTerm](ClinvarTerm.md).

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`MappableConcept` | 1..1 | MUST be "MappableConcept". |
| `name` | `string` | 0..1 | A primary name for the concept. |
| `conceptType` | `string`<br>`Strength` | 0..1 | Must be 'Strength'. |

**Not used by ClinVar-GKM:** `id`, `description`, `aliases`, `extensions`, `mappings`, `primaryCoding`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

