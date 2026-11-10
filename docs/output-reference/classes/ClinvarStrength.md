# ClinvarStrength

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The strength of a ClinVar SCV statement: a ClinvarCodedTerm whose concept type is 'Strength'.

**JSON Schema:** [ClinvarStrength](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarStrength){ target=_blank }

Some ClinvarStrength attributes are inherited from [ClinvarCodedTerm](ClinvarCodedTerm.md).

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`MappableConcept` | 1..1 | MUST be "MappableConcept". |
| `name` | `string` | 0..1 | A primary name for the concept. |
| `conceptType` | `string`<br>`Strength` | 1..1 | Must be 'Strength'. |
| `primaryCoding` | [ClinvarTermCoding](ClinvarTermCoding.md) | 0..1 | The term's code and its system. |

**Not used by ClinVar-GKM:** `id`, `description`, `aliases`, `extensions`, `mappings`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

