# ClinvarSubmitter

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A record of the submitter section: an Agent for a ClinVar submitter, with its id and name. No description, aliases, agent type or extensions.

**JSON Schema:** [ClinvarSubmitter](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarSubmitter){ target=_blank }

Some ClinvarSubmitter attributes are inherited from [Agent](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/entities/agent.html#agent){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 1..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string`<br>`Agent` | 1..1 | MUST be "Agent". |
| `name` | `string` | 0..1 | The given name of the Agent. |

**Not used by ClinVar-GKM:** `description`, `aliases`, `extensions`, `agentType`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

