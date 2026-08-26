# Roadmap

ClinVar-GKM's direction is shaped in the open. The table below is the current backlog of ideas under
consideration, ordered by community **upvotes**. Each idea has a matching **GitHub Discussion** — open it and
use the **Upvote** button (the ▲ next to the discussion title) to signal you want it prioritized, and comment
with your use case. Maintainers use the upvote tally to decide the order in which features and improvements are
taken on.

Nothing here is a commitment or a delivery date — it's a prioritization board. Items move through
**Proposed → Spec'd → In progress → Shipped** as they gain support and get built.

## Current backlog

The table is generated automatically from the GitHub Discussions labeled `roadmap authorized`, ordered by
upvote count. To read the full proposal (and any linked spec) for an item, open its discussion.

<!-- ROADMAP:START -->
| # | Idea | Status | Upvotes | Discussion |
| --- | --- | --- | --- | --- |
| 1 | **VCV/RCV clinical-significance & star-level aggregate extensions** — Add three additive extensions to the aggregate (VCV & RCV) statements so consumers can query review quality and concordance/conflict directly: reviewStarRating… | Spec'd | 1 | [#99](https://github.com/clingen-data-model/clinvar-gkm/discussions/99) |
| 2 | **Starter-kit documentation page** — A docs page showing how to consume the published bundle + Parquet with the GA4GH Python libraries (vrs-python, cat-vrs-python, va-spec-python) — load-from-bund… | Proposed | 1 | [#100](https://github.com/clingen-data-model/clinvar-gkm/discussions/100) |
| 3 | **Upstream clinvar-ingest pipeline documentation** — Document the upstream clinvar-ingest project: how it parses each released ClinVar XML dataset into JSON + relational BigQuery tables (the clinvar_ingest datase… | Proposed | 1 | [#101](https://github.com/clingen-data-model/clinvar-gkm/discussions/101) |
| 4 | **Expert Panel / Practice Guideline VCV classification fix** — Fix EP and PG VCV statements so that when multiple contributing SCVs exist they produce distinct, correct aggregate classifications rather than collapsing. | Proposed | 1 | [#102](https://github.com/clingen-data-model/clinvar-gkm/discussions/102) |
| 5 | **Per-release exception log + processing-policy reference** — Produce a per-release exception/anomaly log (vrsify + proc issues) and a comprehensive processing-policy / transformation-rules reference artifact so consumers… | Proposed | 1 | [#103](https://github.com/clingen-data-model/clinvar-gkm/discussions/103) |
| 6 | **Release browser reorganization + weekly Parquet + archiving** — Reorganize the Downloads "Browse All Releases" widget into a clear 2×2 — Bundles (Monthly/Full, Weekly/Deltas) and Parquet (Monthly/Full, Weekly/Deltas) — and … | Spec'd | 1 | [#112](https://github.com/clingen-data-model/clinvar-gkm/discussions/112) |
| 7 | **Capture submission case data (aggregate + case-level) as EvidenceLines/EvidenceItems** — Submissions sometimes include case data — aggregate case-related values, and sometimes grouped or individual case-level evidence records. These are currently n… | Proposed | 0 | [#104](https://github.com/clingen-data-model/clinvar-gkm/discussions/104) |
| 8 | **Capture functional-data submissions (incl. MaveDB) from ClinVar** — ClinVar has long allowed functional data submissions alongside regular classification SCVs, and has recently improved UI access and display of this data and ad… | Proposed | 0 | [#105](https://github.com/clingen-data-model/clinvar-gkm/discussions/105) |
| 9 | **Backfill historical ClinVar releases (potentially to July 2019)** — Currently, ClinVar-GKM releases start from July 2026. We could backfill historical releases as far back as July 2019 — when ClinVar's VCV XML files were first … | Proposed | 0 | [#107](https://github.com/clingen-data-model/clinvar-gkm/discussions/107) |
| 10 | **Temporal representation of ClinVar data for analytics** — Provide a temporal representation of ClinVar data to support analytics on how the data changes over time — e.g. the changing nature of classifications, the rat… | Proposed | 0 | [#109](https://github.com/clingen-data-model/clinvar-gkm/discussions/109) |
| 11 | **Submitter tool: compare, manage, and simulate ClinVar submissions (with API)** — Provide a submitter tool that works with these data releases to help submitters: | Proposed | 0 | [#110](https://github.com/clingen-data-model/clinvar-gkm/discussions/110) |
<!-- ROADMAP:END -->

## How it works

- **Upvote:** open an idea's discussion and click the **Upvote** button (the ▲ next to the discussion title).
  The upvote tally drives the ordering above. GitHub Discussions support **upvotes only — there is no
  downvote.** Add a comment with your use case for extra signal.
- **Propose a new idea:** open a discussion in the **[Ideas](https://github.com/clingen-data-model/clinvar-gkm/discussions/categories/ideas)**
  category. If the maintainers authorize it (by adding the `roadmap authorized` label), it appears in the table
  automatically.
- **Follow progress:** an idea's status is updated as it moves toward implementation; the linked discussion
  carries the detailed conversation.

Feedback and feature requests are always welcome via the
[GitHub issue tracker](https://github.com/clingen-data-model/clinvar-gkm/issues) as well.
