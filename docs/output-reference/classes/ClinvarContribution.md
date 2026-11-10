# ClinvarContribution

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A Contribution as ClinVar-GKM writes it: a submitter's activity on a ClinVar record, with its date. The contributor is a pointer to a record of the submitter section. No id, name, description, aliases or extensions.

**JSON Schema:** [ClinvarContribution](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarContribution){ target=_blank }

Some ClinvarContribution attributes are inherited from [Contribution](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/entities/contribution.html#contribution){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`Contribution` | 1..1 | MUST be "Contribution". |
| `contributor` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/submitter/<id>` | 0..1 | The submitter, a '#/submitter/<id>' pointer into this bundle. |
| `activityType` | `string`<br>one of `submitted`, `created`, `evaluated` | 0..1 | What the submitter did on the date: submitted (last updated), created, or evaluated the record. |
| `date` | [datetime](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#datetime){ target=_blank rel=noopener } | 0..1 | When the contributing activity was completed. |

**Not used by ClinVar-GKM:** `id`, `name`, `description`, `aliases`, `extensions`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

