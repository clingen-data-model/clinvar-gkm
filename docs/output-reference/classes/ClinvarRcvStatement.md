# ClinvarRcvStatement

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A ClinVar RCV (reference clinical variant) statement. Represents an aggregate classification for a specific variant-condition pair across all submissions sharing the same proposition type and condition. RCV statements contain evidence lines that group contributing SCV submissions by review status priority tier, scoped to a single condition or condition set.
RCV statements use the same 13 proposition types as SCV statements. Unlike VCV statements which aggregate across all conditions for a variant, RCV statements are scoped to a single condition. Evidence lines at the RCV level follow the same priority tier structure as VCV statements.

**JSON Schema:** [ClinvarRcvStatement](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarRcvStatement){ target=_blank }

Some ClinvarRcvStatement attributes are inherited from [ClinvarAggregateStatement](ClinvarAggregateStatement.md).

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

