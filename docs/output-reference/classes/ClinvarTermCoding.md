# ClinvarTermCoding

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The coding of a ClinVar term: a ClinvarCoding with only its code and system. No name or IRIs.

**JSON Schema:** [ClinvarTermCoding](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarTermCoding){ target=_blank }

Some ClinvarTermCoding attributes are inherited from [ClinvarCoding](ClinvarCoding.md).

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `system` | `string` | 1..1 | The terminology/code system that defined the code. May be reported as a free-text name (e.g. 'Sequence Ontology'), but it is preferable to provide a uri/url for the system. |
| `code` | [code](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#code){ target=_blank rel=noopener } | 1..1 | A symbol uniquely identifying the concept, as in a syntax defined by the code system. e.g. 'civic.did:30', 'MONDO:005061', and 'C3512' are codes defined by different systems for representing the concept of 'lung adenocarcinoma'.  If a dereferencable identifier is available for the code, it should be provided in the `iris` field. |

**Not used by ClinVar-GKM:** `id`, `extensions`, `systemVersion`, `name`, `iris`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

