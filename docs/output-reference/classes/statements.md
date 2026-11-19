# Statements

ClinVar-GKM statements are profiles of the GA4GH [VA-Spec Statement](https://va-spec.ga4gh.org/) type. They exist at three levels of aggregation. Each points, through its `proposition`, at the proposition that defines what is being asserted, in one of the four proposition sections (see [Propositions](propositions.md)).

The [ClinvarStatement](ClinvarStatement.md) union type encompasses all three:

| Level | Profile | Bundle Section | Description |
| --- | --- | --- | --- |
| Submission | [ClinvarScvStatement](ClinvarScvStatement.md) | `scv` | A single submitter's classification |
| Variant aggregate | [ClinvarVcvStatement](ClinvarVcvStatement.md) | `vcv` | Aggregate across all submissions for a variant + proposition type |
| Condition aggregate | [ClinvarRcvStatement](ClinvarRcvStatement.md) | `rcv` | Aggregate scoped to a specific variant + condition pair |

VCV and RCV statements share the [ClinvarAggregateStatement](ClinvarAggregateStatement.md) profile. None of the statement profiles carries `name`, `aliases`, `hasEvidence`, or `score`, and their `proposition` and `hasEvidenceLines` are `#/` pointers limited to the proposition sections and the `evidenceLine` section.

---

## SCV Statements

Each SCV represents one submitter's assertion about a variant-condition relationship. SCV statements carry:

- **Classification** — the submitter's classification (e.g., Pathogenic, Likely benign, Tier I - Strong), a [ClinvarScvClassification](ClinvarScvClassification.md) with its code, its system, and ClinVar's description in an extension
- **Direction** — whether the evidence `supports`, `disputes`, or is `neutral` toward the proposition
- **Strength** — the strength of the assessment (e.g., definitive, likely), a [ClinvarStrength](ClinvarStrength.md), when the classification has one
- **Quality** — the quality of the assessment, from the submission's review status, a [ClinvarQuality](ClinvarQuality.md)
- **Contributions** — the submitter's `submitted`, `created`, and `evaluated` activities with their dates, each a [ClinvarContribution](ClinvarContribution.md) whose `contributor` is a `#/submitter/` pointer to a [ClinvarSubmitter](ClinvarSubmitter.md)
- **Method** — the classification guideline used (e.g., ACMG Guidelines 2015, AMP/ASCO/CAP Guidelines 2017), a [ClinvarMethod](ClinvarMethod.md)
- **Citations** — `reportedIn`, each a [ClinvarDocument](ClinvarDocument.md) with a PubMed id, DOI, or URLs

### SCV Extensions

| Extension | Description |
| --- | --- |
| `clinvarScvId` | SCV accession without version (e.g., `SCV001571657`) |
| `clinvarScvVersion` | Version number |
| `clinvarScvReviewStatus` | Review status (e.g., `criteria provided, single submitter`) |
| `submissionLevel` | Aggregation tier: `PG`, `EP`, `CP`, `NOCP`, `NOCL`, or `FLAG` |
| `submittedScvLocalKey` | Submitter's internal identifier |
| `submittedScvClassification` | Original classification before normalization (when different) |
| `submittedCondition` | Submitter's original condition for single-condition submissions |
| `submittedConditionSet` | Submitter's original conditions for multi-condition submissions |

The `submittedCondition` extension's value is a [SubmittedCondition](SubmittedCondition.md), and the `submittedConditionSet` extension's value is a [SubmittedConditionSet](SubmittedConditionSet.md) whose `concepts` are [SubmittedConditionMapping](SubmittedConditionMapping.md)s. They trace how the submitter's original conditions were mapped to the ClinVar canonical conditions.

---

## VCV and RCV Statements

Aggregate statements group SCV submissions into a hierarchical evidence structure. Both VCV and RCV follow the same three-layer pattern:

1. **Classification layer** — groups SCVs by classification label (e.g., all "Pathogenic" submissions)
2. **Priority layer** — groups by review status tier (practice guideline > expert panel > criteria provided > no criteria provided)
3. **Aggregate contribution layer** — references individual SCV submissions as evidence items

Each layer is connected via `hasEvidenceLines` — an array of `#/evidenceLine/` JSON pointer references to [ClinvarAggregateEvidenceLine](ClinvarAggregateEvidenceLine.md) records stored in the `evidenceLine` bundle section. Each statement has a contributing evidence line and, at the priority and aggregate layers, a non-contributing one when some items did not contribute; each line's `hasEvidenceItems` are `#/scv/`, `#/vcv/`, or `#/rcv/` pointers. Sub-statements carry the same proposition type as the parent but are scoped to a specific tier or classification group.

An aggregate statement's `classification` is a [ClinvarAggregateClassification](ClinvarAggregateClassification.md) — the aggregate label as its name, with no coding, and the conflicting classifications in a `conflictingExplanation` extension when the submissions conflict. Its `strength` is a [ClinvarAggregateStrength](ClinvarAggregateStrength.md) and its `quality` a [ClinvarQuality](ClinvarQuality.md) named from the submission level of its submissions.

### Aggregate Extensions

| Extension | Description |
| --- | --- |
| `clinvarReviewStatus` | The aggregate review status (e.g., `criteria provided, multiple submitters, no conflicts`). Absent on the somatic priority-layer statements |

### VCV vs RCV

- **VCV** statements aggregate across all conditions for a variant — the `object` on the proposition may reference multiple conditions or a condition set
- **RCV** statements are scoped to a single ClinVar RCV accession (one variant + one condition combination)
