# ClinvarIsWithinMatch

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The match characteristic of a ClinVar defining location constraint: a MappableConcept with only its type and primary coding (code `is_within`, system `ga4gh-gks-term:location-match`, no IRIs).

**JSON Schema:** [ClinvarIsWithinMatch](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarIsWithinMatch){ target=_blank }

Some ClinvarIsWithinMatch attributes are inherited from [MappableConcept](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/mappable-concept.html#mappableconcept){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`MappableConcept` | 1..1 | MUST be "MappableConcept". |
| `primaryCoding` | [Coding](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/coding.html#coding){ target=_blank rel=noopener }<br>`code`: `is_within`; `system`: `ga4gh-gks-term:location-match` | 1..1 | The match characteristic's code and system. |

**Not used by ClinVar-GKM:** `id`, `name`, `description`, `aliases`, `extensions`, `conceptType`, `mappings`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

