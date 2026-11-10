# ClinvarTherapy

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A record of the therapy section: a Therapy named by its submitted text. No id, description, aliases, extensions, codings or mappings.

**JSON Schema:** [ClinvarTherapy](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarTherapy){ target=_blank }

Some ClinvarTherapy attributes are inherited from [Therapy](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/domain-entities.html#therapy){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`MappableConcept` | 1..1 | MUST be "MappableConcept". |
| `name` | `string` | 0..1 | A primary name for the concept. |
| `conceptType` | `string` \| `string` | 0..1 | A term indicating the type of concept being represented by the MappableConcept. |

**Not used by ClinVar-GKM:** `id`, `description`, `aliases`, `extensions`, `primaryCoding`, `mappings`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

