# ClinvarCodedTerm

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A term of a ClinVar vocabulary (a strength, say) as a MappableConcept: its concept type, its name and, when the term has one, a ClinvarTermCoding. No id, description, aliases, mappings or extensions.

**JSON Schema:** [ClinvarCodedTerm](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarCodedTerm){ target=_blank }

Some ClinvarCodedTerm attributes are inherited from [MappableConcept](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/mappable-concept.html#mappableconcept){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`MappableConcept` | 1..1 | MUST be "MappableConcept". |
| `name` | `string` | 0..1 | A primary name for the concept. |
| `conceptType` | `string` | 1..1 | A term indicating the type of concept being represented by the MappableConcept. |
| `primaryCoding` | [ClinvarTermCoding](ClinvarTermCoding.md) | 0..1 | The term's code and its system. |

**Not used by ClinVar-GKM:** `id`, `description`, `aliases`, `extensions`, `mappings`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

