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
| `type` | `string` | 0..1 | MUST be "Statement". |
| `name` | `string` | 0..1 | A primary name for the entity. |
| `description` | `string` | 0..1 | A free-text description of the Entity. |
| `aliases` | `string`[] (unordered) | 0..m | Alternative name(s) for the Entity. |
| `extensions` | [ExtensionClinvarScvId](ClinvarScvStatement.md#extensionclinvarscvid) \| [ExtensionClinvarScvVersion](ClinvarScvStatement.md#extensionclinvarscvversion) \| [ExtensionClinvarScvReviewStatus](ClinvarScvStatement.md#extensionclinvarscvreviewstatus) \| [ExtensionSubmittedScvLocalKey](ClinvarScvStatement.md#extensionsubmittedscvlocalkey) \| [ExtensionSubmissionLevel](ClinvarScvStatement.md#extensionsubmissionlevel) \| [ExtensionSubmittedScvClassification](ClinvarScvStatement.md#extensionsubmittedscvclassification) \| [ExtensionSubmittedCondition](ClinvarScvStatement.md#extensionsubmittedcondition) \| [ExtensionSubmittedConditionSet](ClinvarScvStatement.md#extensionsubmittedconditionset)[] (unordered) | 0..m | SCV-level extensions including submission metadata, review status, and the submitter's original condition mapping. |
| `specifiedBy` | [Method](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/entities/information-entities/method.html#method){ target=_blank rel=noopener } \| [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener } | 0..1 | A specification that describes all or part of the process that led to creation of the Information Entity |
| `contributions` | [Contribution](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/entities/contribution.html#contribution){ target=_blank rel=noopener }[] (ordered) | 0..m | Specific actions taken by an Agent toward the creation, modification, validation, or deprecation of an Information Entity. |
| `reportedIn` | [Document](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/entities/information-entities/document.html#document){ target=_blank rel=noopener } \| [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }[] (unordered) | 0..m | A document in which the the Information Entity is reported. |
| `proposition` | [ClinvarProposition](ClinvarProposition.md) \| [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener } | 0..1 | The proposition assessed by this SCV statement. Must be one of the GA4GH standard proposition types (pathogenicity, oncogenicity, clinical significance) or a ClinVar-specific proposition type (risk factor, protective, drug response, affects, association, confers sensitivity, other, not provided, conflicting data). |
| `direction` | `string` | 0..1 | A term indicating whether the Statement supports, disputes, or remains neutral w.r.t. the validity of the Proposition it evaluates. |
| `strength` | [MappableConcept](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/mappable-concept.html#mappableconcept){ target=_blank rel=noopener } \| [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener } | 0..1 | A term used to report the strength of a Proposition's assessment in the direction indicated (i.e. how strongly supported or disputed the Proposition is believed to be).  Implementers may choose to frame a strength assessment in terms of how *confident* an agent is that the Proposition is true or false, or in terms of the *strength of all evidence* they believe supports or disputes it. |
| `quality` | [MappableConcept](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/mappable-concept.html#mappableconcept){ target=_blank rel=noopener } \| [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener } (draft) | 0..1 | A term used to report the quality of the assessment of a Proposition taking into consideration the reliability of the method, the contributor's self-reporting of the rigor of the evaluation, and the overall robustness of the supporting or disputing evidence. This is useful when there is a consistent policy and authority that manages and a governing framework for evaluating the quality of evidence. Also known as trust rating, review status or ranking. |
| `score` | `number` (draft) | 0..1 | A quantitative score that indicates the strength of a Proposition's assessment in the direction indicated (i.e. how strongly supported or disputed the Proposition is believed to be). Depending on its implementation, a score may reflect how *confident* that agent is that the Proposition is true or false, or the *strength of evidence* they believe supports or disputes it. Instructions for how to interpret the meaning of a given score may be gleaned from the method or document referenced in 'specifiedBy' attribute. |
| `classification` | [MappableConcept](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/mappable-concept.html#mappableconcept){ target=_blank rel=noopener } \| [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener } | 0..1 | A single term or phrase summarizing the result of direction and strength assessments of a Statement's Proposition, in terms of a classification of its subject. |
| `hasEvidence` | [Statement](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/entities/information-entities/statement.html#statement){ target=_blank rel=noopener } \| [StudyResult](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/entities/information-entities/study-result.html#studyresult){ target=_blank rel=noopener } \| [DataItem](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/entities/information-entities/data-item.html#dataitem){ target=_blank rel=noopener } \| [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }[] (unordered) | 0..m | An individual piece of information that was evaluated as evidence in assessing the validity of the Proposition put forth by the Statement. |
| `hasEvidenceLines` | [ClinvarSomaticEvidenceLine](ClinvarSomaticEvidenceLine.md) \| [EvidenceLine](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/entities/information-entities/evidence-line.html#evidenceline){ target=_blank rel=noopener } \| [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }[] (unordered) | 0..m | Evidence lines for this SCV statement. For somatic clinical impact (SCI) statements, evidence lines carry target propositions (VariantTherapeuticResponseProposition, VariantDiagnosticProposition, or VariantPrognosticProposition) and an evidence outcome reflecting the AMP/ASCO/CAP tier. Germline and oncogenicity SCVs typically do not have evidence lines. |

## Extensions

These extensions are defined for `ClinvarScvStatement`.

### ExtensionClinvarScvId

The SCV accession identifier without version (e.g., SCV001571657).

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string` | 0..1 | Must be 'clinvarScvId'. |
| `value` | `string` | 0..1 | The SCV accession identifier without version suffix. |

### ExtensionClinvarScvReviewStatus

The review status of the individual SCV submission as reported by ClinVar (e.g., "criteria provided, single submitter", "no assertion criteria provided").

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string` | 0..1 | Must be 'clinvarScvReviewStatus'. |
| `value` | `string` | 0..1 | The ClinVar review status for the submission. |

### ExtensionClinvarScvVersion

The version number of the SCV submission (e.g., "2").

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string` | 0..1 | Must be 'clinvarScvVersion'. |
| `value` | `string` | 0..1 | The version number as a string. |

### ExtensionSubmissionLevel

The submission level category based on review status. Determines the aggregation tier when building VCV and RCV aggregate statements.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string` | 0..1 | Must be 'submissionLevel'. |
| `value` | `string` | 0..1 | Practice Guideline (PG), Expert Panel (EP), Criteria Provided (CP), or No Criteria Provided (NOCP). |

### ExtensionSubmittedCondition

The submitter's original condition for single-condition submissions. Contains the submitted condition details and how they were mapped to the ClinVar canonical condition. Present on SCV statements and somatic evidence lines when the submission has exactly one condition.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string` | 0..1 | Must be 'submittedCondition'. |
| `value` | `object` | 0..1 | The submitted condition mapping details. Includes a reference to the resolved condition and the full mapping provenance. |

### ExtensionSubmittedConditionSet

The submitter's original conditions for multi-condition submissions. Contains the submitted condition set details, the multiple condition explanation (AND/OR), and an array of individual condition mappings. Present on SCV statements and somatic evidence lines when the submission has two or more conditions.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string` | 0..1 | Must be 'submittedConditionSet'. |
| `value` | `object` | 0..1 | The submitted condition set with mapping details for each condition. |

### ExtensionSubmittedScvClassification

The original classification label as submitted by the submitter, before any normalization. Present when the submitted classification differs from the normalized classification.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string` | 0..1 | Must be 'submittedScvClassification'. |
| `value` | `string` | 0..1 | The original submitted classification string. |

### ExtensionSubmittedScvLocalKey

The local key submitted by the submitter for this SCV, typically a combination of variant and condition identifiers used internally by the submitting lab.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string` | 0..1 | Must be 'submittedScvLocalKey'. |
| `value` | `string` | 0..1 | The submitter's local key string. |

