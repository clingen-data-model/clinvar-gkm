# Roadmap

ClinVar-GKM's direction is shaped in the open. The table below is the current backlog of ideas under
consideration. Each idea has a matching **GitHub Discussion** where anyone can weigh in — **👍 upvote** ideas
you want prioritized, **👎** those you don't, and comment with your use case. The maintainers use those
signals to decide the order in which features and improvements are taken on.

Nothing here is a commitment or a delivery date — it's a prioritization board. Items move through
**Proposed → Spec'd → In progress → Shipped** as they gain support and get built.

## Current backlog

| # | Idea | Status | Discuss & vote |
| --- | --- | --- | --- |
| 1 | **VCV/RCV clinical-significance & star-level aggregate extensions** — adds `reviewStarRating`, `aggregateSignificance` (conflict bitmask), and `significanceBreakdown` to aggregate statements. [Design spec](https://github.com/clingen-data-model/clinvar-gkm/blob/main/docs/superpowers/specs/2026-08-26-vcv-rcv-clinsig-star-extensions-design.md) | Spec'd | [#99](https://github.com/clingen-data-model/clinvar-gkm/discussions/99) |
| 2 | **Starter-kit documentation page** — using the bundle + Parquet with the GA4GH Python libraries (vrs-python, cat-vrs-python, va-spec-python) | Proposed | [#100](https://github.com/clingen-data-model/clinvar-gkm/discussions/100) |
| 3 | **Upstream `clinvar-ingest` pipeline docs** — how ClinVar XML becomes the relational BigQuery tables this pipeline consumes | Proposed | [#101](https://github.com/clingen-data-model/clinvar-gkm/discussions/101) |
| 4 | **Expert Panel / Practice Guideline VCV classification fix** — distinct aggregate classifications when multiple SCVs contribute | Proposed | [#102](https://github.com/clingen-data-model/clinvar-gkm/discussions/102) |
| 5 | **Per-release exception log + processing-policy reference** — anomaly log per release + a transformation-rules reference artifact | Proposed | [#103](https://github.com/clingen-data-model/clinvar-gkm/discussions/103) |
| 6 | **Capture submission case data as EvidenceLines/EvidenceItems** — aggregate case-related values + grouped/individual case-level evidence records, attached to the submitting SCV (currently excluded) | Proposed | [#104](https://github.com/clingen-data-model/clinvar-gkm/discussions/104) |
| 7 | **Capture functional-data submissions (incl. MaveDB)** — ClinVar's functional-data SCVs and MaveDB submissions (currently excluded); design shaped with interested community members | Proposed | [#105](https://github.com/clingen-data-model/clinvar-gkm/discussions/105) |

## How it works

- **Vote:** open an idea's discussion and use the 👍 / 👎 reactions on the top post, and comment with how you'd
  use it. More signal → higher priority consideration.
- **Propose a new idea:** open a discussion in the **[Ideas](https://github.com/clingen-data-model/clinvar-gkm/discussions/categories/ideas)**
  category. If it gains traction it will be added to this table.
- **Follow progress:** an idea's status here is updated as it moves toward implementation; the linked
  discussion carries the detailed conversation.

Feedback and feature requests are always welcome via the
[GitHub issue tracker](https://github.com/clingen-data-model/clinvar-gkm/issues) as well.
