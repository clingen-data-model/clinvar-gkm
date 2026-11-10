# ClinvarConditionSet

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A record of the conditionSet section: a ConditionSet whose concepts are pointers to records of the condition or conditionSet section. No name, description, aliases or extensions.

**JSON Schema:** [ClinvarConditionSet](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarConditionSet){ target=_blank }

Some ClinvarConditionSet attributes are inherited from [ConditionSet](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/domain-entities.html#conditionset){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 0..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string`<br>`ConceptSet` | 1..1 | MUST be "ConceptSet". |
| `conceptSetType` | `string` | 0..1 | A term indicating the type of concept being represented by the ConceptSet. |
| `concepts` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }[] (unordered)<br>pointer to `#/condition/<id>` or `#/conditionSet/<id>` | 2..m | The set's members, each a '#/condition/<id>' or '#/conditionSet/<id>' pointer into this bundle. |
| `membershipOperator` | `string`<br>one of `AND`, `OR` | 1..1 | The logical relationship between concepts in the set, in the context of some knowledge reported about them. The value 'AND' indicates that the concepts are dependent and occur together in this context - i.e. the reported assertion is not necessarily true for each concept on its own - only in combination with the other(s). The value 'OR' indicates that each concept applies independently in this context - i.e. the reported assertion is necessarily true for each concept on its own, independent of the presence of the other(s). |

**Not used by ClinVar-GKM:** `name`, `description`, `aliases`, `extensions`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

