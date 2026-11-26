# ClinvarClassificationCoding

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The coding of a ClinVar SCV classification: a ClinvarCoding with its code, its system and, when the guideline defines one, the term's canonical name (e.g. 'Tier I' for 'tier i'). No IRIs.

**JSON Schema:** [ClinvarClassificationCoding](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarClassificationCoding){ target=_blank }

Some ClinvarClassificationCoding attributes are inherited from [ClinvarCoding](ClinvarCoding.md).

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string` | 0..1 | The human-readable name for the coded concept, as defined by the code system. |
| `system` | `string` | 1..1 | The terminology/code system that defined the code. May be reported as a free-text name (e.g. 'Sequence Ontology'), but it is preferable to provide a uri/url for the system. |
| `code` | [code](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#code){ target=_blank rel=noopener } | 1..1 | A symbol uniquely identifying the concept, as in a syntax defined by the code system. e.g. 'civic.did:30', 'MONDO:005061', and 'C3512' are codes defined by different systems for representing the concept of 'lung adenocarcinoma'.  If a dereferencable identifier is available for the code, it should be provided in the `iris` field. |

**Not used by ClinVar-GKM:** `id`, `extensions`, `systemVersion`, `iris`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

