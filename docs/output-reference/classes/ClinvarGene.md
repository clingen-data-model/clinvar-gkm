# ClinvarGene

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A record of the gene section: a MappableConcept for an NCBI Gene, with its primary coding and its mappings to other gene codes. No description, aliases or extensions.

**JSON Schema:** [ClinvarGene](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarGene){ target=_blank }

Some ClinvarGene attributes are inherited from [MappableConcept](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/mappable-concept.html#mappableconcept){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 0..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string`<br>`MappableConcept` | 1..1 | MUST be "MappableConcept". |
| `name` | `string` | 0..1 | A primary name for the concept. |
| `conceptType` | `string` | 0..1 | A term indicating the type of concept being represented by the MappableConcept. |
| `primaryCoding` | [ClinvarCoding](ClinvarCoding.md) | 0..1 | The gene's NCBI Gene coding. |
| `mappings` | [ClinvarConceptMapping](ClinvarConceptMapping.md)[] (unordered) | 0..m | Mappings of the gene to other gene codes. |

**Not used by ClinVar-GKM:** `description`, `aliases`, `extensions`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

