# VCV Statements

!!! abstract "What this page answers"
    What ClinVar's variant-level aggregate says about one variant, and how it was reached from the submissions
    under it. Read it when you want ClinVar's overall classification of a variant, its review status, or which
    submissions counted towards it.

## Overview

The `vcv` bundle section contains one record per variation-level aggregate classification. Each record is a `Statement` that aggregates individual [SCV](../reference/glossary.md#scv) submissions into a hierarchical summary — combining classifications across submission levels to produce a single variation-level result. [VCV](../reference/glossary.md#vcv) is ClinVar's variant-level record; the aggregate [review status](../reference/glossary.md#review-status) is carried in the `clinvarReviewStatus` extension.

VCV statements use `#/` references for [propositions](../reference/glossary.md#proposition), contributing SCVs, and lower-level VCV groupings. They are produced by the [VCV Procedures](../pipeline/vcv-statements/vcv-proc.md).

---

## Layer Hierarchy

VCV statements are built through a multi-layer aggregation hierarchy. The top-level output is the Aggregate Contribution layer; lower layers appear in the `hasEvidenceItems` of higher layers.

| Layer | ID Format | Aggregates By | Scope |
| --- | --- | --- | --- |
| Classification | `{VCV}.{ver}-{group}-{PROP}-{level}[-{TIER}]` | Classification label within submission level | All |
| Priority | `{VCV}.{ver}-{group}-{PROP}-{level}` | Tier priority within submission level | Somatic only |
| Aggregate Contribution | `{VCV}.{ver}-{group}-{PROP}` | Submission level (winner-takes-all) | All |

Submission level ranking at the Aggregate Contribution layer is `PG > EP > CP > NOCP > NOCL > FLAG`, with only matching submission levels aggregating together at the Classification layer.

The diagram below reads one statement id left to right and shows the layers for germline and somatic statements.
It is drawn for the [Parquet tables](../parquet/tables.md#reading-a-variants-statements), whose ids, layers and
levels are the bundle's.

<iframe src="../assets/diagrams/parquet-vcv-levels.html" style="width:100%; height:760px; border:1px solid rgba(128,128,128,.25); border-radius:6px;" title="Reading a variant's statements" loading="lazy"></iframe>

See [Aggregation Rules](../pipeline/vcv-statements/vcv-aggregation-rules.md) for detailed submission level logic and [VCV Procedures](../pipeline/vcv-statements/vcv-proc.md) for implementation details.

---

## Record Structure

Each record is a `Statement` with the following top-level fields:

<div class="field-table" markdown>

| Field | Type | Description |
| --- | --- | --- |
| `id` | string | VCV layer ID — e.g., `VCV000012582.63-G-PATH-CP` |
| `type` | string | Always `Statement` |
| `proposition` | string | `#/proposition<Meaning>/{id}` reference to the aggregate proposition (the section is set by the proposition `type`; see [ID References](id-references.md)) |
| `classification` | object | MappableConcept — the aggregate classification label and its `primaryCoding`. See [Classification](#classification) |
| `strength` | object | MappableConcept — the aggregate evidence strength. See [Strength](#strength) |
| `direction` | string | `supports`, `disputes`, or `neutral` — the direction the SCVs carry for the aggregate classification. See [Direction](#direction) |
| `quality` | object | Concept struct with `conceptType: "Quality"` and `name` (the submission level label, e.g., `criteria provided`, `expert panel`) |
| `extensions` | array of [Extension](#extensions) | ClinVar-specific aggregate metadata (0..*). See [Extensions](#extensions) |
| `hasEvidenceLines` | array | `#/evidenceLine/` references to contributing and non-contributing evidence. See [Evidence Lines](#evidence-lines) |

</div>

---

## Classification

The `classification` field is a MappableConcept with the aggregate classification label and its coding:

```json
{
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
```

The `extensions` array includes a `conflictingExplanation` when multiple contributing submissions have different clinical significance values. This extension is only present for CP-level aggregations with conflicts.

`primaryCoding` (from schema 1.2.0) codes the label. A label that is one classification term has the coding
its SCVs carry, with the code in lower case (`Pathogenic` → `pathogenic` / `ACMG Guidelines, 2015`). A somatic
clinical impact label is coded by its tier, without the tumor-type text (`Tier I (Strong) for 2 tumor types` →
`tier 1` / `AMP/ASCO/CAP (AAC) Guidelines, 2017`). Any other label, such as a combination, a conflicting
classification or `no classifications from unflagged records`, is a ClinVar-defined term: the label in lower
case as the code and `ClinVar` as the system. See
[`classification.primaryCoding`](../pipeline/vcv-statements/vcv-aggregation-rules.md#classification-primarycoding)
for the rules and the list of ClinVar-defined codes.

---

## Strength

The `strength` field is a MappableConcept: the strength the SCVs carry for the aggregate classification, from
the same `clinvar_clinsig_types` row that gives the classification its `primaryCoding`:

```json
{
  "conceptType": "Strength",
  "name": "Definitive"
}
```

| Classification | Strength |
| --- | --- |
| Pathogenic; Benign; Oncogenic; Pathogenic, low penetrance; Established risk allele | Definitive |
| Likely pathogenic; Likely benign; Likely oncogenic; Likely pathogenic, low penetrance; Likely risk allele | Likely |
| Tier I (Strong) | Strong |
| Tier II (Potential) | Potential |
| Tier III; Tier IV; Uncertain significance; Conflicting; combinations such as Pathogenic/Likely pathogenic; any other label | *null (omitted)* |

A somatic clinical impact statement takes its tier's strength (at the priority and aggregate layers, the top
tier's). A classification-layer statement with one SCV passes that SCV's strength through. See
[`quality`, `direction`, and `strength`](../pipeline/vcv-statements/vcv-aggregation-rules.md#quality-direction-and-strength).

---

## Direction

The `direction` field is a string: the direction the SCVs carry for the aggregate classification, from the same
`clinvar_clinsig_types` row that gives the classification its `primaryCoding`. Every VCV statement has one.

| Classification | Direction |
| --- | --- |
| Pathogenic; Likely pathogenic; Pathogenic/Likely pathogenic; Oncogenic; Likely oncogenic; the low-penetrance and risk-allele labels except Uncertain risk allele; Tier I; Tier II; association; and ClinVar's other proposition types | `supports` |
| Uncertain significance; VUS-high, VUS-mid, VUS-low; Uncertain risk allele; Tier III; conflicting data from submitters | `neutral` |
| Benign; Likely benign; Benign/Likely benign; Tier IV; association not found | `disputes` |
| Conflicting classifications of pathogenicity / oncogenicity (no lookup row) | `neutral` |
| The FLAG label `no classifications from unflagged records` (no lookup row) | `neutral` |
| Combinations not in the lookup, such as Uncertain significance/VUS-high (no lookup row) | the direction every SCV in the group carries; `supports` if they differ |

A somatic clinical impact statement takes its tier's direction (at the priority and aggregate layers, the top
tier's). A classification-layer statement with one SCV passes that SCV's direction through. See
[`quality`, `direction`, and `strength`](../pipeline/vcv-statements/vcv-aggregation-rules.md#quality-direction-and-strength).

---

## Proposition

VCV propositions are delivered across the four proposition bundle sections (`propositionPathogenicity`, `propositionOncogenicity`, `propositionSomaticClinicalImpact`, `propositionClinvarCustom`) by meaning. Each VCV statement references its proposition via `#/proposition<Meaning>/{id}`.

A resolved VCV proposition contains:

| Field | Type | Description |
| --- | --- | --- |
| `type` | string | Proposition type matching the underlying SCVs (e.g., `VariantPathogenicityProposition`) |
| `id` | string | Proposition ID (e.g., `VCV000012582-G-PATH-CP`) |
| `subject` | string | `#/variation/clinvar:{id}` reference |
| `predicate` | string | Predicate matching the underlying SCVs (e.g., `isCausalFor`) |
| `object` | string | One reference to the conditions of the contributing SCVs. A single condition is `#/condition/clinvar.trait:{id}`, or `#/conditionSet/clinvar.traitset:{id}` when it is a ClinVar trait set. Several conditions are `#/conditionSet/clinvar.conditionset:vcv-{md5}`: a ConceptSet minted for the aggregate, with `membershipOperator: "OR"` and one `#/condition/` or `#/conditionSet/` reference per condition. Omitted when the contributing SCVs carry no condition |

---

## Evidence Lines

Each VCV statement contains `hasEvidenceLines` — an array of `#/evidenceLine/` JSON pointer references to evidence line records in the `evidenceLine` bundle section:

```json
{
  "hasEvidenceLines": [
    "#/evidenceLine/VCV000012582.63-G-PATH-CP.contributing",
    "#/evidenceLine/VCV000012582.63-G-PATH-CP.non-contributing"
  ]
}
```

Each referenced evidence line record contains:

| Field | Type | Description |
| --- | --- | --- |
| `type` | string | Always `EvidenceLine` |
| `directionOfEvidenceProvided` | string | `supports` or `neutral` |
| `strengthOfEvidenceProvided` | object | MappableConcept — `Contributing` or `Non-contributing` |
| `hasEvidenceItems` | array | `#/scv/` references (at classification layer) or `#/vcv/` references (at priority/aggregate layers) |

Contributing evidence lines use `directionOfEvidenceProvided: "supports"`. Non-contributing evidence lines (lower-ranked submission levels) use `directionOfEvidenceProvided: "neutral"`.

---

## Extensions

Extensions carry aggregate metadata not part of the GA4GH VA-Spec statement model. Each extension follows the GA4GH Extension structure: `{ "name": "<name>", "value": <value> }`. Extensions appear at two structural levels — on the top-level `Statement` and on the `classification` object.

See [VCV Extensions (Pipeline)](../pipeline/vcv-statements/vcv-extensions.md) for details on how these extensions are built during pipeline processing.

### Statement Extensions

<div class="field-table" markdown>

| Extension Name | Value Type | Description |
|---|---|---|
| `clinvarReviewStatus` | `string` | The aggregate review status derived from the submission level and aggregation outcome. Always present. Values: `practice guideline`, `reviewed by expert panel`, `criteria provided, single submitter`, `criteria provided, multiple submitters, no conflicts`, `criteria provided, conflicting classifications`, `no assertion criteria provided`, `no classification provided`, `flagged submission`. |

</div>

### Classification Extensions

Extensions on the `classification` MappableConcept within the Statement.

<div class="field-table" markdown>

| Extension Name | Value Type | Description |
|---|---|---|
| `conflictingExplanation` | `string` | A formatted breakdown of conflicting classification counts (e.g., `Pathogenic(3); Likely pathogenic(2)`). Present only when the classification is conflicting — multiple distinct significance values exist for a conflict-detectable proposition type. |

</div>

---

## Examples

Annotated JSONC examples of VCV statement records are available in the repository:

- [VCV statement examples](https://github.com/clingen-data-model/clinvar-gkm/tree/main/examples/vcv)

---

## See Also { #see-also }

- [Aggregation Rules](../pipeline/vcv-statements/vcv-aggregation-rules.md) — how each layer picks its classification, review status, direction and strength
- [RCV Statements](rcv-statements.md) — the same aggregation for one variant and one condition
- [SCV Statements](scv-statements.md) — the submissions the lowest layer cites
- [ID References](id-references.md#vcv-statement-ids) — the VCV statement and proposition id formats
- [Examples](../data-access/examples.md#vcv-statements) — whole VCV hierarchies for two variants
