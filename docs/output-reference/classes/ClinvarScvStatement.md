# ClinvarScvStatement

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A ClinVar SCV (submitted clinical variant) statement. Represents a single submitter's assertion about a variant-condition relationship, including their classification, direction, strength, method, and contributions.
Allowable proposition types at SCV level:
Germline classification (9 types): VariantPathogenicityProposition, ClinvarRiskFactorProposition, ClinvarProtectiveProposition, ClinvarDrugResponseProposition, ClinvarAffectsProposition, ClinvarAssociationProposition, ClinvarConfersSensitivityProposition, ClinvarOtherProposition, ClinvarNotProvidedProposition.
Oncogenicity (1 type): VariantOncogenicityProposition.
Somatic clinical impact (1 type): VariantClinicalSignificanceProposition with evidence lines carrying VariantTherapeuticResponseProposition, VariantDiagnosticProposition, or VariantPrognosticProposition.
Conflicting data (1 type): ClinvarConflictingDataFromSubmitterProposition.

**JSON Schema:** [ClinvarScvStatement](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarScvStatement){ target=_blank }

Some ClinvarScvStatement attributes are inherited from [Statement](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/entities/information-entities/statement.html#statement){ target=_blank rel=noopener }, `ClinvarScvStatementProperties`.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 0..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string`<br>`Statement` | 1..1 | MUST be "Statement". |
| `description` | `string` | 0..1 | A free-text description of the Entity. |
| `extensions` | [ExtensionClinvarScvId](ClinvarScvStatement.md#extensionclinvarscvid) \| [ExtensionClinvarScvVersion](ClinvarScvStatement.md#extensionclinvarscvversion) \| [ExtensionClinvarScvReviewStatus](ClinvarScvStatement.md#extensionclinvarscvreviewstatus) \| [ExtensionSubmittedScvLocalKey](ClinvarScvStatement.md#extensionsubmittedscvlocalkey) \| [ExtensionSubmissionLevel](ClinvarScvStatement.md#extensionsubmissionlevel) \| [ExtensionSubmittedScvClassification](ClinvarScvStatement.md#extensionsubmittedscvclassification) \| [ExtensionSubmittedCondition](ClinvarScvStatement.md#extensionsubmittedcondition) \| [ExtensionSubmittedConditionSet](ClinvarScvStatement.md#extensionsubmittedconditionset)[] (unordered) | 0..m | SCV-level extensions including submission metadata, review status, and the submitter's original condition mapping. |
| `specifiedBy` | [ClinvarMethod](ClinvarMethod.md) | 0..1 | The submission's assertion method. |
| `contributions` | [ClinvarContribution](ClinvarContribution.md)[] (ordered) | 0..m | The submitter's submission, creation and evaluation of the record. |
| `reportedIn` | [ClinvarDocument](ClinvarDocument.md)[] (unordered) | 0..m | The submission's citations. |
| `proposition` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/propositionPathogenicity/<id>` or `#/propositionOncogenicity/<id>` or `#/propositionSomaticClinicalImpact/<id>` or `#/propositionClinvarCustom/<id>` | 1..1 | The proposition assessed by this SCV statement, a pointer into one of the bundle's proposition sections. It is one of the GA4GH standard proposition types (pathogenicity, oncogenicity, clinical significance) or a ClinVar-specific proposition type (risk factor, protective, drug response, affects, association, confers sensitivity, other, not provided, conflicting data). |
| `direction` | `string`<br>one of `supports`, `neutral`, `disputes` | 0..1 | A term indicating whether the Statement supports, disputes, or remains neutral w.r.t. the validity of the Proposition it evaluates. |
| `strength` | [ClinvarStrength](ClinvarStrength.md) | 0..1 | The strength of the classification (e.g. 'Likely'), when it has one. |
| `quality` | [ClinvarQuality](ClinvarQuality.md) | 0..1 | The quality of the assessment, from the submission's review status. |
| `classification` | [ClinvarScvClassification](ClinvarScvClassification.md) | 0..1 | The submitter's classification. |
| `hasEvidenceLines` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }[] (unordered)<br>pointer to `#/evidenceLine/<id>` | 0..m | Evidence lines for this SCV statement, each a '#/evidenceLine/<id>' pointer into this bundle. For somatic clinical impact (SCI) statements, evidence lines carry target propositions (VariantTherapeuticResponseProposition, VariantDiagnosticProposition, or VariantPrognosticProposition) and an evidence outcome reflecting the AMP/ASCO/CAP tier. Germline and oncogenicity SCVs typically do not have evidence lines. |

**Not used by ClinVar-GKM:** `name`, `aliases`, `score`, `hasEvidence`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

## Extensions

These extensions are defined for `ClinvarScvStatement`.

### ExtensionClinvarScvId

The SCV accession identifier without version (e.g., SCV001571657).

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`clinvarScvId` | 0..1 | Must be 'clinvarScvId'. |
| `value` | `string` | 0..1 | The SCV accession identifier without version suffix. |

### ExtensionClinvarScvReviewStatus

The review status of the individual SCV submission as reported by ClinVar (e.g., "criteria provided, single submitter", "no assertion criteria provided").

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`clinvarScvReviewStatus` | 0..1 | Must be 'clinvarScvReviewStatus'. |
| `value` | `string`<br>one of `criteria provided, single submitter`, `criteria provided, conflicting classifications`, `criteria provided, multiple submitters, no conflicts`, `no assertion criteria provided`, `no classification provided`, `no assertion provided`, `practice guideline`, `reviewed by expert panel`, `flagged submission` | 0..1 | The ClinVar review status for the submission. |

### ExtensionClinvarScvVersion

The version number of the SCV submission (e.g., "2").

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`clinvarScvVersion` | 0..1 | Must be 'clinvarScvVersion'. |
| `value` | `string` | 0..1 | The version number as a string. |

### ExtensionSubmissionLevel

The submission level category based on review status. Determines the aggregation tier when building VCV and RCV aggregate statements.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`submissionLevel` | 0..1 | Must be 'submissionLevel'. |
| `value` | `string`<br>one of `PG`, `EP`, `CP`, `NOCP`, `NOCL`, `FLAG` | 0..1 | Practice Guideline (PG), Expert Panel (EP), Criteria Provided (CP), No Criteria Provided (NOCP), No Classification Provided (NOCL), or Flagged Submission (FLAG). Ranked PG > EP > CP > NOCP > NOCL > FLAG. |

### ExtensionSubmittedCondition

The submitter's original condition for single-condition submissions. Contains the submitted condition details and how they were mapped to the ClinVar canonical condition. Present on SCV statements and somatic evidence lines when the submission has exactly one condition.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`submittedCondition` | 0..1 | Must be 'submittedCondition'. |
| `value` | [SubmittedCondition](SubmittedCondition.md) | 0..1 | The submitted condition mapping details. Includes a reference to the resolved condition and the full mapping provenance. |

### ExtensionSubmittedConditionSet

The submitter's original conditions for multi-condition submissions. Contains the submitted condition set details, the multiple condition explanation (AND/OR), and an array of individual condition mappings. Present on SCV statements and somatic evidence lines when the submission has two or more conditions.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`submittedConditionSet` | 0..1 | Must be 'submittedConditionSet'. |
| `value` | [SubmittedConditionSet](SubmittedConditionSet.md) | 0..1 | The submitted condition set with mapping details for each condition. |

### ExtensionSubmittedScvClassification

The original classification label as submitted by the submitter, before any normalization. Present when the submitted classification differs from the normalized classification.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`submittedScvClassification` | 0..1 | Must be 'submittedScvClassification'. |
| `value` | `string` | 0..1 | The original submitted classification string. |

### ExtensionSubmittedScvLocalKey

The local key submitted by the submitter for this SCV, typically a combination of variant and condition identifiers used internally by the submitting lab.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`submittedScvLocalKey` | 0..1 | Must be 'submittedScvLocalKey'. |
| `value` | `string` | 0..1 | The submitter's local key string. |

