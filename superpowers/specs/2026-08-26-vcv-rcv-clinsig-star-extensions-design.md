# VCV/RCV Clinsig + Star Aggregate Extensions — Design

**Status:** design approved 2026-08-26 (brainstorming). Next: implementation plan (writing-plans), oracle-gated.

## Goal

Surface, as va-spec extensions on the aggregate (VCV and RCV) statements, three pieces of information that
the aggregation procs already compute internally but do not expose: the ClinVar **review star level**, an
**aggregate significance bitmask** that makes concordance/conflict machine-queryable, and a per-type
**significance breakdown** (the evidence distribution behind the aggregate). Also document how "conflicting"
aggregations are determined in the grouping layer.

Everything here is additive to the published statements. No SCV changes, no Parquet-column changes.

## Background: the three aggregation layers

`gkm_vcv_proc` / `gkm_rcv_proc` build the aggregate tables through three layers, and
`gkm_vcv_statement_proc` / `gkm_rcv_statement_proc` emit a statement per layer (unioned into
`gkm_dict_vcv` / `gkm_dict_rcv`):

1. **Classification grouping** — group contributing SCVs by variation (+ trait for RCV) · statement group ·
   proposition type · submission_level [· tier]; one aggregate classification per submission_level.
2. **Priority grouping** (somatic `sci` only) — aggregate tiers within a submission_level.
3. **Aggregate-contribution** — winner-takes-all across submission_levels (`PG > EP > CP > NOCP > NOCL > FLAG`).

Each emitted statement already carries `clinvarReviewStatus` (label) + `conflictingExplanation` extensions.
The three new extensions below go on **all three layers**, each computed from that layer's own group.

## The significance-bucket model (existing data)

`clinvar_ingest.clinvar_clinsig_types.significance` (INT64) already buckets every classification code into
`0 / 1 / 2`:

| Bucket | Meaning | Example codes |
| --- | --- | --- |
| `0` | benign-side / disputes | `b`, `lb`, `b/lb`, `t4`, `protect`, `np`, `oth`, `assocnf` |
| `1` | uncertain | `vus`, `vus-h/m/l`, `ura`, `t3`, `cdfs` |
| `2` | pathogenic-side / supports | `p`, `lp`, `p/lp`, `p-lp`, `lp-lp`, `era`, `lra`, `o`, `lo`, `t1`, `t2`, `aff`, `assoc`, `cs`, `dr`, `rf` |

The bucket is a benign↔pathogenic (or benign↔oncogenic) axis **only** for proposition types `path`
(pathogenicity) and `onco` (oncogenicity). For `sci` (somatic clinical impact) the buckets are tier levels
(Tier I–IV), and for the remaining single-code types (`aff`, `assoc`, `dr`, `rf`, …) they are not a conflict
axis. `prop_type` in the procs = `clinvar_proposition_types.code`.

## The three extensions

All three are appended to each aggregate statement's `extensions`. Names are un-prefixed camelCase (matching
GKS-computed aggregates like `conflictingExplanation`, `submissionLevel`).

### 1. `reviewStarRating` — integer 0–4

Numeric companion to the existing `clinvarReviewStatus` label, derived from `aggregate_review_status`:

| `aggregate_review_status` | `reviewStarRating` |
| --- | --- |
| `practice guideline` | 4 |
| `reviewed by expert panel` | 3 |
| `criteria provided, multiple submitters, no conflicts` | 2 |
| `criteria provided, single submitter` | 1 |
| `criteria provided, conflicting classifications` | 1 |
| `no assertion criteria provided` | 0 |
| `no classification provided` / `flagged submission` | **omit** (n/a) |

Emitted whenever a star value applies (i.e. omitted only for NOCL/FLAG).

### 2. `aggregateSignificance` — integer 0–7 (bitmask)

A 3-bit mask of which significance buckets are present in the group. **Gated to pathogenicity/oncogenicity**:

```
aggregateSignificance = IF(prop_type IN ('path','onco'), BIT_OR(1 << significance), 0)   -- per group
```

`bit0 = benign(1)`, `bit1 = uncertain(2)`, `bit2 = pathogenic/oncogenic(4)`:

| Value | bits (P·U·B) | buckets present | interpretation |
| --- | --- | --- | --- |
| 0 | 000 | none | n/a (empty, or a non-path/onco type) |
| 1 | 001 | benign | concordant benign |
| 2 | 010 | uncertain | concordant VUS |
| 3 | 011 | benign + uncertain | conflict (not clin-sig) |
| 4 | 100 | path/onc | concordant path/onc |
| 5 | 101 | benign + path/onc | **clinically-significant conflict** |
| 6 | 110 | uncertain + path/onc | **clinically-significant conflict** |
| 7 | 111 | all three | **clinically-significant conflict** |

**`aggregateSignificance > 4`** returns exactly the clinically/oncogenically significant conflicts
(path/onc present with ≥1 non-path/onc bucket) — values 5, 6, 7. Always emitted (0 when n/a). It is consistent
with the existing `significance_count` (which equals the popcount of this mask): the bitmask additionally says
*which* buckets, not only how many.

### 3. `significanceBreakdown` — array of `{clinsigType, count, significanceBucket}`

The structured evidence distribution behind the aggregate — the machine-readable form of ClinVar's
`Pathogenic(3); Benign(1)` summary. One entry per distinct classification label contributing to the group,
ordered deterministically by `classif_type_order`:

```json
"significanceBreakdown": [
  { "clinsigType": "Pathogenic",             "count": 3, "significanceBucket": 2 },
  { "clinsigType": "Likely pathogenic",      "count": 1, "significanceBucket": 2 },
  { "clinsigType": "Uncertain significance", "count": 2, "significanceBucket": 1 },
  { "clinsigType": "Benign",                 "count": 1, "significanceBucket": 0 }
]
```

Derived from the existing `label_counts` CTE (SCV count per `classif_label`) joined to
`clinvar_clinsig_types.significance`. Emitted on all aggregate statements (all proposition types); for
non-path/onco types `significanceBucket` is the raw significance value (documented — the benign↔path
interpretation applies only when `aggregateSignificance` is non-zero).

### Worked example (relationship of the three)

A CP-level group with 2× Pathogenic + 1× Likely pathogenic (concordant):
`reviewStarRating=2`, `aggregateSignificance=4`, `significanceBreakdown=[{Pathogenic,2,2},{Likely pathogenic,1,2}]`.

The same group plus 1× Benign (conflict): `reviewStarRating=1`, `aggregateSignificance=5` (>4 → clin-sig
conflict), breakdown gains `{Benign,1,0}`.

## How "conflicting" is determined in the grouping layer (to document)

In the classification-grouping step (`gkm-vcv-proc.sql` / `gkm-rcv-proc.sql`, `conflict_strings` CTE):

- Each SCV's `classif_type` maps to a significance bucket via `clinvar_clinsig_types`.
- `significance_count = COUNT(DISTINCT significance)` across the group; `agg_classif_label` = `/`-joined
  labels; `agg_string` = labels with counts.
- The proposition type carries `conflict_detectable` (`clinvar_proposition_types`).
- A group is **conflicting ⟺ `significance_count > 1 AND conflict_detectable`** — so P + LP (same bucket)
  is not a conflict; P + B is. This drives the 1★ `criteria provided, conflicting classifications` review
  status and the `conflictingExplanation` extension. `aggregateSignificance > 4` is the stricter
  *clinically-significant* subset of these conflicts.

## Implementation

### Compute (`gkm-vcv-proc.sql`, `gkm-rcv-proc.sql`)

- In/after the classification-grouping CTEs, add per-group: `reviewStarRating` (CASE on the existing
  `aggregate_review_status`), `aggregateSignificance` (`IF(prop_type IN ('path','onco'), BIT_OR(1 <<
  significance), 0)`), and a `significanceBreakdown` array `ARRAY_AGG(STRUCT(classif_label AS clinsigType,
  scv_count AS count, significance AS significanceBucket) ORDER BY classif_type_order)`.
- Carry these three columns through the priority and aggregate-contribution layers (each recomputes from its
  own group / carries the winning group's values).
- **Determinism:** the breakdown array is `ORDER BY classif_type_order`; star and bitmask are functionally
  determined by the group key + counts. This preserves the incremental carry-forward invariant so
  full-vs-incremental and delta-reconstruction oracles stay byte-identical (0,0,0).

### Emit (`gkm-vcv-statement-proc.sql`, `gkm-rcv-statement-proc.sql`)

- Append the three extensions to each layer's `extensions` array (guarded like the existing ones —
  `reviewStarRating` omitted for NULL; `aggregateSignificance` always present; `significanceBreakdown` present
  when non-empty), via `JSON_STRIP_NULLS(..., remove_empty => TRUE)`.
- **BigQuery gotcha:** an array's element STRUCTs must be homogeneous. The extension element type must gain a
  `value_integer INT64` variant (star + bitmask) and a `value_significance_breakdown ARRAY<STRUCT<clinsigType
  STRING, count INT64, significanceBucket INT64>>` variant; every existing extension literal in the affected
  arrays must include the new fields as NULL so the array types unify.

### Schema + conformance

- Regenerate `schema/clinvar-gkm/json` (`cd schema/clinvar-gkm && make`), committing only semantic changes
  (canonical-diff to drop metaschema reorder churn). Broaden the `Extension.value` typing if the generated
  schema constrains it (va-spec `value` is otherwise unconstrained).
- **Conformance gate:** validate sampled emitted aggregate statements (a path conflict, an onco case, a
  concordant case, and a non-path/onco `sci` case) against `schema/clinvar-gkm/json/*` under va-spec 1.1.0.

### Docs

- `vcv-aggregation-rules.md` (+ RCV equivalent): the grouping-layer conflict-determination explanation; the
  **code→bucket** table; the **0–7 combination table** with concordant/conflict columns, the `>4` clin-sig
  rule, and the path/onco gate; the **star-mapping** table.
- `vcv-statements/index.md` + `rcv-statements/index.md`: replace the ASCII layer diagram with a **mermaid**
  layer graphic.
- `vcv-extensions.md` / `rcv-extensions.md`: reference the three new extensions with the Example-1/Example-2
  JSON.
- `mkdocs build --strict` must pass.

## Oracle gating

BQ-touching changes are oracle-gated: after deploying the proc changes, a full-vs-incremental oracle on the
vcv/rcv dict tables and a delta-reconstruction oracle must both report **0,0,0**. The determinism ordering
above is required for this to hold.

## Non-goals

- No SCV-statement changes (SCV keeps `clinvarScvReviewStatus`; no numeric star on SCV).
- No new typed Parquet columns — the extensions live in the JSON `extensions` array (and the existing Parquet
  extensions struct).
- No change to the aggregate classification label or `conflictingExplanation` logic.
