# ClinvarAggregateStatement

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A ClinVar aggregate statement — the shared base for VCV and RCV statements. Represents an aggregate classification across contributing submissions, grouping them into evidence lines by review status priority tier. Concrete aggregate statements are ClinvarVcvStatement (across all conditions for a variant) and ClinvarRcvStatement (scoped to a single condition or condition set). No name, description, aliases, method, contributions, citations, score or direct evidence.

**JSON Schema:** [ClinvarAggregateStatement](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarAggregateStatement){ target=_blank }

Some ClinvarAggregateStatement attributes are inherited from [Statement](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/entities/information-entities/statement.html#statement){ target=_blank rel=noopener }, `ClinvarAggregateStatementProperties`.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 1..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string`<br>`Statement` | 1..1 | MUST be "Statement". |
| `extensions` | [ExtensionClinvarReviewStatus](ClinvarAggregateStatement.md#extensionclinvarreviewstatus)[] (unordered) | 0..m | The aggregate review status, in an ExtensionClinvarReviewStatus. Absent on the somatic priority-layer statements. |
| `proposition` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/propositionPathogenicity/<id>` or `#/propositionOncogenicity/<id>` or `#/propositionSomaticClinicalImpact/<id>` or `#/propositionClinvarCustom/<id>` | 1..1 | The aggregate proposition assessed by this VCV or RCV statement, a pointer into one of the bundle's proposition sections. Uses the same proposition types as SCV statements. The proposition at the aggregate level represents the consensus or highest-priority classification across contributing submissions. |
| `direction` | `string`<br>one of `supports`, `neutral`, `disputes` | 0..1 | A term indicating whether the Statement supports, disputes, or remains neutral w.r.t. the validity of the Proposition it evaluates. |
| `strength` | [ClinvarAggregateStrength](ClinvarAggregateStrength.md) | 0..1 | The strength of the aggregate classification (e.g. 'Likely'), when it has one. |
| `quality` | [ClinvarQuality](ClinvarQuality.md) | 1..1 | The quality of the aggregate, from the submission level of its submissions. |
| `classification` | [ClinvarAggregateClassification](ClinvarAggregateClassification.md) | 1..1 | The aggregate classification. |
| `hasEvidenceLines` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }[] (unordered)<br>pointer to `#/evidenceLine/<id>` | 1..m | The statement's evidence lines, each a '#/evidenceLine/<id>' pointer into this bundle: always its contributing evidence line and, at the priority and aggregate layers, a non-contributing evidence line when there are non-contributing items. The evidence line's items point to the SCV statements (classification layer) or to the lower-layer aggregate statements (priority and aggregate layers). |

**Not used by ClinVar-GKM:** `name`, `description`, `aliases`, `specifiedBy`, `contributions`, `reportedIn`, `score`, `hasEvidence`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

## Extensions

These extensions are defined for `ClinvarAggregateStatement`.

### ExtensionClinvarReviewStatus

The aggregate review status for a VCV or RCV statement. Reflects the highest review status among contributing submissions (e.g., "practice guideline", "reviewed by expert panel", "criteria provided, multiple submitters, no conflicts").

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`clinvarReviewStatus` | 1..1 | Must be 'clinvarReviewStatus'. |
| `value` | `string`<br>one of `practice guideline`, `reviewed by expert panel`, `criteria provided, conflicting classifications`, `criteria provided, multiple submitters, no conflicts`, `criteria provided, single submitter`, `no assertion criteria provided`, `no classification provided`, `flagged submission` | 1..1 | The aggregate review status. |

