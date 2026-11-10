# ClinvarAggregateEvidenceLine

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

An evidence line of a VCV or RCV aggregate statement. A 'Contributing' line (direction 'supports') lists the statements the aggregate statement is built from; a 'Non-contributing' line (direction 'neutral') lists those of a lower review-status priority that did not contribute. Its items are pointers to SCV statements (at the classification layer) or to VCV or RCV statements (at the priority and aggregate layers). No name, description, aliases, extensions, method, contributions, citations, target proposition, score or evidence outcome.

**JSON Schema:** [ClinvarAggregateEvidenceLine](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarAggregateEvidenceLine){ target=_blank }

Some ClinvarAggregateEvidenceLine attributes are inherited from [EvidenceLine](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/entities/information-entities/evidence-line.html#evidenceline){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 0..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string`<br>`EvidenceLine` | 1..1 | MUST be "EvidenceLine". |
| `hasEvidenceItems` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }[] (unordered)<br>pointer to `#/scv/<id>` or `#/vcv/<id>` or `#/rcv/<id>` | 0..m | The statements the line groups, each a '#/scv/<id>', '#/vcv/<id>' or '#/rcv/<id>' pointer into this bundle. |
| `directionOfEvidenceProvided` | `string`<br>one of `supports`, `neutral` | 1..1 | 'supports' for a Contributing line, 'neutral' for a Non-contributing line. |
| `strengthOfEvidenceProvided` | [ClinvarTerm](ClinvarTerm.md) | 0..1 | 'Contributing' or 'Non-contributing', as a ClinvarTerm of concept type 'Strength'. |

**Not used by ClinVar-GKM:** `name`, `description`, `aliases`, `extensions`, `specifiedBy`, `contributions`, `reportedIn`, `targetProposition`, `scoreOfEvidenceProvided`, `evidenceOutcome`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

