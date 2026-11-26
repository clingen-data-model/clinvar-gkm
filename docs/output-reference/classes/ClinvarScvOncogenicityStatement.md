# ClinvarScvOncogenicityStatement

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A ClinVar SCV statement about a variant's oncogenicity, modelled on the VA-Spec CCV 2022 VariantOncogenicityStatement. Its classification and strength are coded under the ClinGen/CGC/VICC 2022 oncogenicity guidelines. It differs from the community profile in one way: specifiedBy is optional. See the Community Profiles page.

**JSON Schema:** [ClinvarScvOncogenicityStatement](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarScvOncogenicityStatement){ target=_blank }

Some ClinvarScvOncogenicityStatement attributes are inherited from [ClinvarScvStatement](ClinvarScvStatement.md).

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 1..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string`<br>`Statement` | 1..1 | MUST be "Statement". |
| `description` | `string` | 0..1 | A free-text description of the Entity. |
| `extensions` | [ExtensionClinvarScvId](ClinvarScvStatement.md#extensionclinvarscvid) \| [ExtensionClinvarScvVersion](ClinvarScvStatement.md#extensionclinvarscvversion) \| [ExtensionClinvarScvReviewStatus](ClinvarScvStatement.md#extensionclinvarscvreviewstatus) \| [ExtensionSubmittedScvLocalKey](ClinvarScvStatement.md#extensionsubmittedscvlocalkey) \| [ExtensionSubmissionLevel](ClinvarScvStatement.md#extensionsubmissionlevel) \| [ExtensionSubmittedScvClassification](ClinvarScvStatement.md#extensionsubmittedscvclassification) \| [ExtensionSubmittedCondition](ClinvarScvStatement.md#extensionsubmittedcondition) \| [ExtensionSubmittedConditionSet](ClinvarScvStatement.md#extensionsubmittedconditionset)[] (unordered) | 1..m | SCV-level extensions including submission metadata, review status, and the submitter's original condition mapping. |
| `specifiedBy` | [ClinvarMethod](ClinvarMethod.md) | 0..1 | The submission's assertion method. |
| `contributions` | [ClinvarContribution](ClinvarContribution.md)[] (ordered) | 1..m | The submitter's submission, creation and evaluation of the record. |
| `reportedIn` | [ClinvarDocument](ClinvarDocument.md)[] (unordered) | 0..m | The submission's citations. |
| `proposition` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/propositionOncogenicity/<id>` | 1..1 | The oncogenicity proposition, a pointer into the bundle's propositionOncogenicity section. |
| `direction` | `string`<br>one of `supports`, `neutral`, `disputes` | 0..1 | A term indicating whether the Statement supports, disputes, or remains neutral w.r.t. the validity of the Proposition it evaluates. |
| `strength` | [ClinvarStrength](ClinvarStrength.md) | 0..1 | The strength, coded under CCV 2022. |
| `quality` | [ClinvarQuality](ClinvarQuality.md) | 1..1 | The quality of the assessment, from the submission's review status. |
| `classification` | [ClinvarScvClassification](ClinvarScvClassification.md) | 1..1 | The classification, coded under CCV 2022. |
| `hasEvidenceLines` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }[] (unordered)<br>pointer to `#/evidenceLine/<id>` | 0..m | Evidence lines for this SCV statement, each a '#/evidenceLine/<id>' pointer into this bundle. For somatic clinical impact (SCI) statements, evidence lines carry target propositions (VariantTherapeuticResponseProposition, VariantDiagnosticProposition, or VariantPrognosticProposition) and an evidence outcome reflecting the AMP/ASCO/CAP tier. Germline and oncogenicity SCVs typically do not have evidence lines. |

**Not used by ClinVar-GKM:** `name`, `aliases`, `score`, `hasEvidence`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

