# VCV Aggregation Rules

## Overview

VCV (Variant-level Classification) aggregation combines individual SCV (Submission-level Classification) submissions into aggregate variant-level classification statements. Each SCV represents a single submitter's classification of a variant; VCV aggregation produces a summary classification that reflects the consensus (or conflict) across all submissions for the same variant and statement type.

The aggregation process is governed by **submission levels** — categories that reflect the authority and review rigor behind each submission. Submission levels determine how classifications are combined, whether conflicts are detected, and what review status label the aggregate statement receives.

---

## Submission Levels

Every SCV is assigned a submission level based on its ClinVar review status:

| Code | Label | Rank | Stars | Description |
| --- | --- | --- | --- | --- |
| PG | practice guideline | 6 | 4 | Published practice guidelines from authoritative bodies |
| EP | expert panel | 5 | 3 | Classifications reviewed and approved by expert panels |
| CP | assertion criteria provided | 4 | 1 | Submitter provided criteria for their classification |
| NOCP | no assertion criteria provided | 3 | 0 | Classification submitted without documented criteria |
| NOCL | no classification provided | 2 | -1 | Submission present but no classification given |
| FLAG | flagged submission | 1 | -3 | Submission flagged by ClinVar for quality concerns |

Every submission level is aggregated independently — only SCVs with the same submission level can aggregate together. At the Aggregate Contribution Layer, submission levels are ranked `PG > EP > CP > NOCP > NOCL > FLAG` and the highest-ranked level becomes the winner-takes-all contributing result.

---

## SCV Description Extension

Every SCV classification includes a formatted `description` extension that summarizes the submission context:

```
for <condition_name>
Classification is based on the <submission_level_label> submission
<evaluated_date> by <submitter_name>
```

Where:

- **condition_name** — the condition name from the SCV, or "`N` conditions" for submissions with multiple conditions
- **submission_level_label** — the full label of the submission level (e.g., "expert panel", "assertion criteria provided")
- **evaluated_date** — formatted as `Mon YYYY`, or `(-)` if not provided
- **submitter_name** — the submitting organization name

This description is carried on the SCV classification and is not propagated onto VCV aggregate statements.

---

## Aggregation by Submission Level

### PG (Practice Guideline)

Practice guideline submissions are aggregated independently. Like CP, concordance and conflict detection produce a single aggregate label.

- **Output attribute:** `classification`
- **Review status:** always `practice guideline`

### EP (Expert Panel)

Expert panel submissions are aggregated independently. Like CP, concordance and conflict detection produce a single aggregate label.

- **Output attribute:** `classification`
- **Review status:** always `reviewed by expert panel`

### CP (Assertion Criteria Provided)

Standard aggregation with concordance and conflict detection.

- **Output attribute:** `classification` — a single aggregate label
- **Concordant** — all contributing SCVs share the same classification: the label is the shared classification name
- **Conflicting** — contributing SCVs have different classifications: the label becomes "Conflicting classifications of `<proposition_type>`" with a `conflictingExplanation` extension showing the breakdown (e.g., "Pathogenic(3); Likely pathogenic(2)")
- **Review status upgrades:** CP submissions may receive upgraded review status based on submitter count and concordance (see [Aggregate Review Status](#aggregate-review-status))

### NOCP (No Assertion Criteria Provided)

Same aggregation logic as CP — concordance/conflict detection produces a single label.

- **Output attribute:** `classification`
- **No review status upgrade** — always "no assertion criteria provided" regardless of submitter count or concordance

### FLAG (Flagged Submissions)

No aggregation logic. Flagged submissions always produce a fixed result.

- **Output attribute:** `classification`
- **Label:** always "no classifications from unflagged records"
- **No conflict detection**

### NOCL (No Classification Provided)

Passthrough with no aggregation logic.

- **Output attribute:** `classification`
- **Label:** always "not provided"

---

## Classification Output

Every VCV statement uses a single `classification` attribute to represent its aggregate classification. The classification lives only on the statement — the proposition does not carry a copy of the classification value.

### `classification`

Used by all submission levels (PG, EP, CP, NOCP, NOCL, and FLAG). Contains a single aggregate label, its
`primaryCoding`, and an optional `conflictingExplanation` extension when contributing SCVs disagree.

```json
{
  "classification": {
    "type": "MappableConcept",
    "conceptType": "Classification",
    "name": "Conflicting classifications of pathogenicity",
    "primaryCoding": {
      "code": "conflicting classifications of pathogenicity",
      "system": "ClinVar"
    },
    "extensions": [
      {"name": "conflictingExplanation", "value": "Pathogenic(3); Uncertain significance(2)"}
    ]
  }
}
```

The `extension` array is only present when the classification is conflicting.

### `classification.primaryCoding` { #classification-primarycoding }

From schema 1.2.0, every VCV and RCV classification carries a `primaryCoding` (a `ClinvarTermCoding`: `code`
and `system` only) for its label, at all three layers. The coding is computed in the classification layer of
`gkm_vcv_proc` / `gkm_rcv_proc` (column `agg_classif_coding`) and follows the label:

1. **Coded label.** The label is looked up by proposition type and label in `clinvar_clinsig_types`, the table
   that codes SCV classifications. On a match, the coding is the one the SCVs with that label carry, with the
   code in lower case. For example, `Pathogenic` is `pathogenic` / `ACMG Guidelines, 2015` and `VUS-mid` is
   `vus-mid` / `SVC v4`.
2. **Somatic clinical impact.** The label carries tumor-type text (VCV: `Tier I (Strong) for Lung cancer`, and
   at the priority layer `+lower levels of evidence for N other tumor types`; RCV:
   `Tier I (Strong) - <assertion type> - <significance> (n)`). The coding uses the tier label without that
   text, so it is the coding of the tier: for example `tier 1` / `AMP/ASCO/CAP (AAC) Guidelines, 2017`. A
   classification-layer group is always one tier. The priority and aggregate layers take the coding of the top
   tier, the one whose label they show.
3. **Any other label is a ClinVar-defined term:** system `ClinVar` and the label in lower case as the code.
   These are the labels ClinVar's aggregation produces and no single SCV can carry. The `ClinVar` system is the
   one `clinvar_clinsig_types` already uses for ClinVar's own terms, including the two combinations it codes
   (`pathogenic/likely pathogenic` and `benign/likely benign`).

A non-empty label always gets a coding, so there is no unmapped case. The priority layer copies the top tier's
coding, and the aggregate layer copies the winning layer's.

**ClinVar-defined codes** (system `ClinVar`). The first group comes from `clinvar_clinsig_types`; the
rest are defined by the aggregation rules on this page. Combinations are open-ended: any set of distinct labels
that contributing submissions give at one submission level, joined by `/` in the label's order.

| Label | `code` | Where it comes from |
| --- | --- | --- |
| Pathogenic/Likely pathogenic | `pathogenic/likely pathogenic` | `clinvar_clinsig_types` (its code there is `pathogenic/Likely pathogenic`; aggregate codes are always lower case) |
| Benign/Likely benign | `benign/likely benign` | `clinvar_clinsig_types` |
| not provided, Affects, association, association not found, confers sensitivity, conflicting data from submitters, drug response, other, protective, risk factor | the label in lower case, such as `drug response` | `clinvar_clinsig_types` (ClinVar's other proposition types) |
| Conflicting classifications of pathogenicity | `conflicting classifications of pathogenicity` | conflict rule ([CP](#cp-assertion-criteria-provided)) |
| Conflicting classifications of oncogenicity | `conflicting classifications of oncogenicity` | conflict rule |
| no classifications from unflagged records | `no classifications from unflagged records` | [FLAG](#flag-flagged-submissions) rule |
| A combination of labels with no conflict, such as Uncertain significance/VUS-low | the combined label in lower case, such as `uncertain significance/vus-low` | combined label |

The 2026-10-31 full release has 20 combination codes, on 726 of its 21,309,008 VCV and RCV records:

- `uncertain significance/uncertain risk allele`, `uncertain significance/vus-high`,
  `uncertain significance/vus-mid`, `uncertain significance/vus-low`
- `pathogenic/pathogenic, low penetrance`, `pathogenic/likely pathogenic, low penetrance`,
  `pathogenic/likely pathogenic/pathogenic, low penetrance`,
  `pathogenic/likely pathogenic/likely pathogenic, low penetrance`,
  `pathogenic/likely pathogenic/pathogenic, low penetrance/established risk allele`,
  `likely pathogenic/pathogenic, low penetrance`, `likely pathogenic/likely pathogenic, low penetrance`
- `pathogenic/established risk allele`, `pathogenic/likely risk allele`,
  `pathogenic/established risk allele/likely risk allele`, `pathogenic/likely pathogenic/established risk allele`,
  `pathogenic/likely pathogenic/likely risk allele`,
  `pathogenic/likely pathogenic/established risk allele/likely risk allele`,
  `likely pathogenic/established risk allele`, `likely pathogenic/likely risk allele`
- `oncogenic/likely oncogenic`

!!! note "SCV and aggregate codes for Pathogenic/Likely pathogenic differ in case"
    `clinvar_clinsig_types` codes `Pathogenic/Likely pathogenic` as `pathogenic/Likely pathogenic`, and SCVs
    carry that code unchanged. Aggregate codes are always lower case, so a VCV or RCV with that label carries
    `pathogenic/likely pathogenic`. Compare codes case-insensitively, or see
    [Known Issues](../../reference/known-issues.md#scv-and-aggregate-codes-for-pathogeniclikely-pathogenic-differ-in-case).

### `quality`, `direction`, and `strength`

These statement-level fields are derived from the aggregate classification label:

- **`quality`** — a Concept struct with `conceptType: "Quality"` and `name` set to the submission level label (e.g., `"criteria provided"`, `"expert panel"`). Set on every VCV statement.
- **`direction`** — the direction the SCVs carry for the label. A classification-layer group with one SCV passes
  that SCV's direction through. Every other statement (a multi-SCV group, and every priority- and
  aggregate-layer statement) takes the `direction` of the `clinvar_clinsig_types` row that gives the label its
  coding: the same lookup by proposition type and label, with the somatic tier label in place of the decorated
  one. The priority layer takes the top tier's direction and the aggregate layer the winning layer's. A label
  with no lookup row has no SCV direction to follow, so it keeps a fixed rule: `neutral` for a conflicting
  label, `supports` for the others (combinations and the FLAG label). A combination of neutral terms, such as
  `Uncertain significance/Uncertain risk allele`, therefore gets `supports`. Every VCV and RCV statement has a
  direction. Column `agg_direction` of `gkm_vcv_proc` / `gkm_rcv_proc`.

    | Proposition type | Label | `direction` |
    | --- | --- | --- |
    | pathogenicity | Pathogenic; Likely pathogenic; Pathogenic/Likely pathogenic; Pathogenic, low penetrance; Likely pathogenic, low penetrance; Established risk allele; Likely risk allele | supports |
    | pathogenicity | Uncertain significance; VUS-high, VUS-mid, VUS-low; Uncertain risk allele | neutral |
    | pathogenicity, oncogenicity | Benign; Likely benign; Benign/Likely benign | disputes |
    | oncogenicity | Oncogenic; Likely oncogenic | supports |
    | oncogenicity | Uncertain significance | neutral |
    | somatic clinical impact | Tier I (Strong); Tier II (Potential) | supports |
    | somatic clinical impact | Tier III Unknown | neutral |
    | somatic clinical impact | Tier IV (Benign)/Likely benign | disputes |
    | association | association | supports |
    | association | association not found | disputes |
    | conflicting data from submitters | conflicting data from submitters | neutral |
    | ClinVar's other proposition types | Affects; confers sensitivity; drug response; not provided; other; protective; risk factor | supports |
    | any (no lookup row) | Conflicting classifications of pathogenicity / of oncogenicity | neutral |
    | any (no lookup row) | combinations not in the lookup, such as Likely pathogenic/Likely risk allele or Uncertain significance/VUS-high; the FLAG label `no classifications from unflagged records` | supports |
- **`strength`** — the strength the SCVs carry for the label. A classification-layer group with one SCV passes
  that SCV's strength through. Every other statement (a multi-SCV group, and every priority- and aggregate-layer
  statement) takes the `strength_label` of the `clinvar_clinsig_types` row that gives the label its coding: the
  same lookup by proposition type and label, with the somatic tier label in place of the decorated one. The
  priority layer takes the top tier's strength and the aggregate layer the winning layer's. A label with no
  lookup row has no strength, so `strength` is omitted: conflicting labels, combinations, and the FLAG label.
  Column `agg_strength_name` of `gkm_vcv_proc` / `gkm_rcv_proc`.

    | Proposition type | Label | `strength` |
    | --- | --- | --- |
    | pathogenicity | Pathogenic; Benign; Pathogenic, low penetrance; Established risk allele | Definitive |
    | pathogenicity | Likely pathogenic; Likely benign; Likely pathogenic, low penetrance; Likely risk allele | Likely |
    | oncogenicity | Oncogenic; Benign | Definitive |
    | oncogenicity | Likely oncogenic; Likely benign | Likely |
    | somatic clinical impact | Tier I (Strong) | Strong |
    | somatic clinical impact | Tier II (Potential) | Potential |
    | somatic clinical impact | Tier III Unknown; Tier IV (Benign)/Likely benign | omitted |
    | any | every other label: Uncertain significance; VUS-high, VUS-mid, VUS-low; Uncertain risk allele; Pathogenic/Likely pathogenic; Benign/Likely benign; the labels of ClinVar's other proposition types; conflicting, combination and FLAG labels | omitted |

---

## Aggregate Review Status

Every VCV statement includes a `clinvarReviewStatus` extension indicating the aggregate review confidence level. The value depends on the submission level and aggregation outcome.

| Submission Level | Condition | Review Status |
| --- | --- | --- |
| PG | Any | `practice guideline` |
| EP | Any | `reviewed by expert panel` |
| CP | Single submitter | `criteria provided, single submitter` |
| CP | Multiple submitters, concordant | `criteria provided, multiple submitters, no conflicts` |
| CP | Multiple submitters, conflicting | `criteria provided, conflicting classifications` |
| NOCP | Any | `no assertion criteria provided` |
| NOCL | Any | `no classification provided` |
| FLAG | Any | `flagged submission` |

The review status appears in the statement-level `extensions` array:

```json
{
  "extensions": [
    {"name": "clinvarReviewStatus", "value": "criteria provided, multiple submitters, no conflicts"}
  ]
}
```

---

## Aggregation Hierarchy

VCV aggregation builds statements through a two-layer hierarchy. Each layer may consist of multiple SQL steps, but conceptually there are two aggregation layers.

### Grouping Layer

The Grouping Layer produces the initial aggregation of individual SCVs into groups. It consists of two steps that run as separate SQL operations but form a single conceptual layer:

| Step | Name | Aggregates By | Description |
| --- | --- | --- | --- |
| Classification Grouping | `gkm_vcv_grouping_base_agg` | Variation + Statement Group + Proposition Type + Submission Level (+ Tier) | Lowest-level aggregation of individual SCVs. Applies submission-level-specific classification and conflict detection logic |
| Priority Grouping | `gkm_vcv_grouping_tier_agg` | Variation + Statement Group + Proposition Type + Submission Level | Combines tier-level groups (somatic sci only). Ranks tiers by priority, designates top tier as contributing |

Priority Grouping applies only to somatic tiered records (`tier_grouping IS NOT NULL`). Non-tiered records (all germline and non-sci somatic) flow directly from Classification Grouping to the Aggregate Contribution Layer.

### Aggregate Contribution Layer

| Step | Name | Aggregates By | Description |
| --- | --- | --- | --- |
| Aggregate Contribution | `gkm_vcv_aggregate_contribution` | Variation + Statement Group + Proposition Type | Winner-takes-all across submission levels. This is the terminal layer for both germline and somatic statements |

Submission levels are ranked `PG > EP > CP > NOCP > NOCL > FLAG`. The highest-ranked submission level becomes the "contributing" result; all others become "non-contributing" evidence.

Each layer's output includes `evidenceLines` that reference the layer below, creating a nested structure in the final JSON output.
