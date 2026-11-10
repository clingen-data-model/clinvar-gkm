# ClinvarMappingCoding

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The coding of a concept mapping: a ClinvarCoding without a name.

**JSON Schema:** [ClinvarMappingCoding](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarMappingCoding){ target=_blank }

Some ClinvarMappingCoding attributes are inherited from [ClinvarCoding](ClinvarCoding.md).

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `system` | `string` | 1..1 | The terminology/code system that defined the code. May be reported as a free-text name (e.g. 'Sequence Ontology'), but it is preferable to provide a uri/url for the system. |
| `code` | [code](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#code){ target=_blank rel=noopener } | 1..1 | A symbol uniquely identifying the concept, as in a syntax defined by the code system. e.g. 'civic.did:30', 'MONDO:005061', and 'C3512' are codes defined by different systems for representing the concept of 'lung adenocarcinoma'.  If a dereferencable identifier is available for the code, it should be provided in the `iris` field. |
| `iris` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }[] (unordered) | 0..m | A list of IRIs that are associated with the coding. This can be used to provide additional context or to link to additional information about the concept. |

**Not used by ClinVar-GKM:** `id`, `extensions`, `systemVersion`, `name`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

