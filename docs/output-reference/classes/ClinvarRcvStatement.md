# ClinvarRcvStatement

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.0/appendices/maturity_model.html){ target=_blank rel=noopener }.

A ClinVar RCV (reference clinical variant) statement. Represents an aggregate classification for a specific variant-condition pair across all submissions sharing the same proposition type and condition. RCV statements contain evidence lines that group contributing SCV submissions by review status priority tier, scoped to a single condition or condition set.
RCV statements use the same 13 proposition types as SCV statements. Unlike VCV statements which aggregate across all conditions for a variant, RCV statements are scoped to a single condition. Evidence lines at the RCV level follow the same priority tier structure as VCV statements.

**JSON Schema:** [ClinvarRcvStatement](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarRcvStatement){ target=_blank }

Some ClinvarRcvStatement attributes are inherited from `Statement`, `ClinvarAggregateStatementProperties`.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 0..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string` | 0..1 | MUST be "Statement". |
| `name` | `string` | 0..1 | A primary name for the entity. |
| `description` | `string` | 0..1 | A free-text description of the Entity. |
| `aliases` | `string`[] (unordered) | 0..m | Alternative name(s) for the Entity. |
| `extensions` | `ExtensionClinvarReviewStatus`[] (unordered) | 0..m | Aggregate-level extensions including the overall review status. |
| `specifiedBy` | `Method` \| `iriReference` | 0..1 | A specification that describes all or part of the process that led to creation of the Information Entity |
| `contributions` | `Contribution`[] (ordered) | 0..m | Specific actions taken by an Agent toward the creation, modification, validation, or deprecation of an Information Entity. |
| `reportedIn` | `Document` \| `iriReference`[] (unordered) | 0..m | A document in which the the Information Entity is reported. |
| `proposition` | [ClinvarProposition](ClinvarProposition.md) \| `iriReference` | 0..1 | The aggregate proposition assessed by this VCV or RCV statement. Uses the same proposition types as SCV statements. The proposition at the aggregate level represents the consensus or highest-priority classification across contributing submissions. |
| `direction` | `string` | 0..1 | A term indicating whether the Statement supports, disputes, or remains neutral w.r.t. the validity of the Proposition it evaluates. |
| `strength` | `MappableConcept` \| `iriReference` | 0..1 | A term used to report the strength of a Proposition's assessment in the direction indicated (i.e. how strongly supported or disputed the Proposition is believed to be).  Implementers may choose to frame a strength assessment in terms of how *confident* an agent is that the Proposition is true or false, or in terms of the *strength of all evidence* they believe supports or disputes it. |
| `quality` | `MappableConcept` \| `iriReference` (draft) | 0..1 | A term used to report the quality of the assessment of a Proposition taking into consideration the reliability of the method, the contributor's self-reporting of the rigor of the evaluation, and the overall robustness of the supporting or disputing evidence. This is useful when there is a consistent policy and authority that manages and a governing framework for evaluating the quality of evidence. Also known as trust rating, review status or ranking. |
| `score` | `number` (draft) | 0..1 | A quantitative score that indicates the strength of a Proposition's assessment in the direction indicated (i.e. how strongly supported or disputed the Proposition is believed to be). Depending on its implementation, a score may reflect how *confident* that agent is that the Proposition is true or false, or the *strength of evidence* they believe supports or disputes it. Instructions for how to interpret the meaning of a given score may be gleaned from the method or document referenced in 'specifiedBy' attribute. |
| `classification` | `MappableConcept` \| `iriReference` | 0..1 | A single term or phrase summarizing the result of direction and strength assessments of a Statement's Proposition, in terms of a classification of its subject. |
| `hasEvidence` | `Statement` \| `StudyResult` \| `DataItem` \| `iriReference`[] (unordered) | 0..m | An individual piece of information that was evaluated as evidence in assessing the validity of the Proposition put forth by the Statement. |
| `hasEvidenceLines` | `EvidenceLine` \| `iriReference`[] (unordered) | 0..m | Evidence lines grouping contributing submissions by review status priority tier. Each evidence line contains nested sub-statements (classification layer) or SCV references (aggregate contribution layer). Tiers are: practice guideline (PG), expert panel (EP), criteria provided (CP), and no criteria provided (NOCP). |

