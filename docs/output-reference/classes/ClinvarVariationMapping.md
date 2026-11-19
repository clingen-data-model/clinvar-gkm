# ClinvarVariationMapping

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A mapping of a ClinVar variation: a ClinvarConceptMapping whose relation is `exactMatch` (the ClinVar variation), `closeMatch` (a ClinGen allele) or `relatedMatch` (every other cross-reference).

**JSON Schema:** [ClinvarVariationMapping](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarVariationMapping){ target=_blank }

Some ClinvarVariationMapping attributes are inherited from [ClinvarConceptMapping](ClinvarConceptMapping.md).

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `coding` | [ClinvarMappingCoding](ClinvarMappingCoding.md) | 1..1 | The coding the concept maps to. |
| `relation` | `string`<br>one of `exactMatch`, `closeMatch`, `relatedMatch` | 1..1 | `exactMatch` for the ClinVar variation, `closeMatch` for a ClinGen allele, `relatedMatch` for every other cross-reference. |

**Not used by ClinVar-GKM:** `id`, `extensions`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

