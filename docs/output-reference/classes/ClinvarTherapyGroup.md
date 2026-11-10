# ClinvarTherapyGroup

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A record of the therapyGroup section: a TherapyGroup whose concepts are pointers to records of the therapy section. No id, name, description, aliases, extensions or concept set type.

**JSON Schema:** [ClinvarTherapyGroup](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarTherapyGroup){ target=_blank }

Some ClinvarTherapyGroup attributes are inherited from [TherapyGroup](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/domain-entities.html#therapygroup){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`ConceptSet` | 1..1 | MUST be "ConceptSet". |
| `concepts` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }[] (unordered)<br>pointer to `#/therapy/<id>` | 2..m | The group's members, each a '#/therapy/<id>' pointer into this bundle. |
| `membershipOperator` | `string`<br>one of `AND`, `OR` | 1..1 | The logical relationship between concepts in the set, in the context of some knowledge reported about them. The value 'AND' indicates that the concepts are dependent and occur together in this context - i.e. the reported assertion is not necessarily true for each concept on its own - only in combination with the other(s). The value 'OR' indicates that each concept applies independently in this context - i.e. the reported assertion is necessarily true for each concept on its own, independent of the presence of the other(s). |

**Not used by ClinVar-GKM:** `id`, `name`, `description`, `aliases`, `extensions`, `conceptSetType`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

