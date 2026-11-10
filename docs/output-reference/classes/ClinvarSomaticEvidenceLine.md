# ClinvarSomaticEvidenceLine

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The evidence line of a ClinVar somatic clinical impact (SCI) SCV statement. It links the statement's VariantClinicalSignificanceProposition to the specific assertion: its target proposition (a VariantTherapeuticResponseProposition, VariantDiagnosticProposition or VariantPrognosticProposition, in the propositionSomaticClinicalImpact section), always supported, with an evidence outcome reflecting the AMP/ASCO/CAP tier and the submitter's original condition(s) in an extension. No name, description, aliases, method, contributions, citations, evidence items, strength or score.

**JSON Schema:** [ClinvarSomaticEvidenceLine](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarSomaticEvidenceLine){ target=_blank }

Some ClinvarSomaticEvidenceLine attributes are inherited from [EvidenceLine](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/entities/information-entities/evidence-line.html#evidenceline){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 1..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string`<br>`EvidenceLine` | 1..1 | MUST be "EvidenceLine". |
| `extensions` | [ExtensionEvidenceLineSubmittedCondition](ClinvarSomaticEvidenceLine.md#extensionevidencelinesubmittedcondition) \| [ExtensionEvidenceLineSubmittedConditionSet](ClinvarSomaticEvidenceLine.md#extensionevidencelinesubmittedconditionset)[] (unordered) | 0..m | The submitter's original condition, in an ExtensionEvidenceLineSubmittedCondition, or conditions, in an ExtensionEvidenceLineSubmittedConditionSet. |
| `targetProposition` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/propositionSomaticClinicalImpact/<id>` | 1..1 | The specific assertion, a '#/propositionSomaticClinicalImpact/<id>' pointer to a VariantTherapeuticResponseProposition, VariantDiagnosticProposition or VariantPrognosticProposition in this bundle. |
| `directionOfEvidenceProvided` | `string`<br>`supports`; one of `supports`, `neutral`, `disputes` | 1..1 | Always 'supports'. |
| `evidenceOutcome` | [ClinvarTerm](ClinvarTerm.md) | 1..1 | The evidence level for the AMP/ASCO/CAP tier, as a ClinvarTerm of concept type 'Outcome': 'Level A/B' for Tier I, 'Level C/D' for Tier II; for any other tier, the SCV's classification code. |

**Not used by ClinVar-GKM:** `name`, `description`, `aliases`, `specifiedBy`, `contributions`, `reportedIn`, `hasEvidenceItems`, `strengthOfEvidenceProvided`, `scoreOfEvidenceProvided`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

## Extensions

These extensions are defined for `ClinvarSomaticEvidenceLine`.

### ExtensionEvidenceLineSubmittedCondition

The submitter's original condition, for a somatic clinical impact submission with one condition. The same extension as the SCV statement's submittedCondition extension.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`submittedCondition` | 1..1 | Must be 'submittedCondition'. |
| `value` | [SubmittedCondition](SubmittedCondition.md) | 1..1 | The submitted condition mapping details, with the condition it resolved to. |

### ExtensionEvidenceLineSubmittedConditionSet

The submitter's original conditions, for a somatic clinical impact submission with two or more conditions. The same extension as the SCV statement's submittedConditionSet extension.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`submittedConditionSet` | 1..1 | Must be 'submittedConditionSet'. |
| `value` | [SubmittedConditionSet](SubmittedConditionSet.md) | 1..1 | The submitted condition set with mapping details for each condition. |

