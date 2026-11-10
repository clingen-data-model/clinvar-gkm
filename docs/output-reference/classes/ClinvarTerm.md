# ClinvarTerm

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A term of a ClinVar vocabulary with no coding (a quality, say): a ClinvarCodedTerm with only its concept type and name.

**JSON Schema:** [ClinvarTerm](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarTerm){ target=_blank }

Some ClinvarTerm attributes are inherited from [ClinvarCodedTerm](ClinvarCodedTerm.md).

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`MappableConcept` | 1..1 | MUST be "MappableConcept". |
| `name` | `string` | 0..1 | A primary name for the concept. |
| `conceptType` | `string` | 0..1 | A term indicating the type of concept being represented by the MappableConcept. |

**Not used by ClinVar-GKM:** `id`, `description`, `aliases`, `extensions`, `mappings`, `primaryCoding`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

