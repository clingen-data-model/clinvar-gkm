# ClinvarConceptMapping

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A ConceptMapping as ClinVar-GKM writes it: a ClinvarMappingCoding and its relation. No id or extensions.

**JSON Schema:** [ClinvarConceptMapping](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarConceptMapping){ target=_blank }

Some ClinvarConceptMapping attributes are inherited from [ConceptMapping](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/concept-mapping.html#conceptmapping){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `coding` | [ClinvarMappingCoding](ClinvarMappingCoding.md) | 1..1 | The coding the concept maps to. |
| `relation` | `string`<br>one of `closeMatch`, `exactMatch`, `broadMatch`, `narrowMatch`, `relatedMatch` | 1..1 | A mapping relation between concepts as defined by the Simple Knowledge Organization System (SKOS). |

**Not used by ClinVar-GKM:** `id`, `extensions`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

