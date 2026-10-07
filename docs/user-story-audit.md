# User Story: Auditing a Submitter's ClinVar Footprint

**Why this matters**

A lab that submits to ClinVar accumulates a large body of classifications over years — and it is easy
to lose track of which ones have aged, slipped to a weak or flagged review status, or point at
conditions and therapies that no longer look right. Because ClinVar-GKM republishes every ClinVar
release as typed **Parquet** (and a self-contained **bundle**), a submitter can pull their *own*
complete footprint and run a repeatable audit on every release — turning "is anything of ours stale or
wrong?" into a query that produces a fresh report each time ClinVar updates.

**At a glance**

- **Implementer** — a ClinVar submitting lab (worked example: the Institute for Genomic Medicine (IGM)
  Clinical Laboratory at Nationwide Children's Hospital, submitter `196472`)
- **Products** — VA-Spec, Cat-VRS, VRS, GKM-Core
- **Pattern** — Submitter self-audit / QC across releases
- **Tools** — [DuckDB](https://duckdb.org/) or pandas over the published
  [Parquet](data-access/parquet.md); the [sub-bundle](pipeline/sub-bundle.md) extract;
  optionally [va-spec-python](https://github.com/ga4gh/va-spec-python)
- **Status** — Release candidate

!!! tip "New to GKM datasets?"
    The GA4GH [**GKM Starter Kit**](https://ga4gh.github.io/gkm-starter-kit/) is the best place to get
    oriented — it collects the reference libraries, the [GKM Toolkit](https://ga4gh.github.io/gkm-starter-kit/tools/gkm-toolkit/getting-started/)
    for loading and exploring bundles, and [other user stories](https://ga4gh.github.io/gkm-starter-kit/user-stories/)
    showing how projects put GKM to work.

---

## The challenge

An active submitter can have hundreds to thousands of SCVs in ClinVar, submitted and re-evaluated over
many years. Several quality questions are hard to answer from ClinVar's web UI or flat XML:

- **Which classifications are stale?** Assertions last evaluated years ago may predate current criteria
  and warrant re-review.
- **Which sit at a weak or flagged review status?** Submissions with *no assertion criteria provided*,
  *no classification provided*, or a *flagged submission* status stand out for cleanup.
- **Which point at odd conditions?** Placeholder or non-specific traits ("not provided", "not
  specified") — or conditions that have since been remapped — are worth a look.
- **Which reference unusual therapies?** For therapeutic-response submissions, a malformed or unexpected
  drug or drug combination is easy to miss one record at a time.

Answering these one variant at a time doesn't scale, and ClinVar offers no turnkey "export everything
*we* submitted as a queryable table."

## What GKM enables

ClinVar-GKM makes the whole submission set queryable and self-describing:

- **Every SCV is a typed VA-Spec `Statement`** with an explicit `classification`, a `quality` (the
  review status / star level), `direction` and `strength`, submitter `contributions` (each with a date
  and activity type), and a `proposition` linking the variant to a condition — or, for therapeutic
  response, to a therapy or therapy group.
- **The whole release is typed Parquet** — one file per bundle section, each with an `id`, typed columns
  for the common fields, and the full JSON object — so filtering *your* SCVs and joining them to
  conditions, therapies, and variants is ordinary SQL.
- **Releases are dated and incremental.** `datasets/parquet/00-latest/` always points at the newest
  monthly full, so the same audit re-runs against each release and its results can be diffed over time.

## The data

To make this concrete, the repository ships
**[`nch-igm-bundle.json.gz`](https://github.com/clingen-data-model/clinvar-gkm/blob/main/nch-igm-bundle.json.gz)** —
the complete GKM extract of one real submitter, the IGM Clinical Laboratory at Nationwide Children's
Hospital (submitter `196472`): **all 2,443 of their SCVs** plus every variation, condition, therapy,
proposition, and submitter record those statements reference, in a single self-contained 1.4 MB file. It
is exactly "everything one submitter has in ClinVar," and it is the shape an audit consumes. (It was
produced with the maintainer [sub-bundle](pipeline/sub-bundle.md) tool — `sub-bundle.py --submitter 196472`.)

For the recurring, release-over-release audit, a submitter works from the published Parquet instead. A
single DuckDB query flags the records that need a second look:

```sql
-- Everything submitter 196472 has in ClinVar, flagged for review.
-- (scv.parquet, varcond-proposition.parquet, condition.parquet from
--  datasets/parquet/00-latest/ — the newest monthly full.)
WITH mine AS (
  SELECT
    s.id,
    s.classification.name AS classification,
    s.quality.name        AS review_status,
    cond.name             AS condition_name,
    (SELECT max(c.date)                        -- most recent evaluation
       FROM unnest(s.contributions) AS t(c)
      WHERE c.activityType = 'evaluated')      AS last_evaluated
  FROM 'scv.parquet' s
  JOIN 'varcond-proposition.parquet' p ON s.proposition_id = p.id
  LEFT JOIN 'condition.parquet' cond   ON p.object_condition_id = cond.id
  WHERE list_contains(
          [c.contributor FOR c IN s.contributions],
          '#/submitter/clinvar.submitter:196472')
)
SELECT
  id, classification, review_status, condition_name, last_evaluated,
  last_evaluated < '2022-01-01'                        AS stale,
  review_status IN ('no assertion criteria provided',
                    'no classification provided',
                    'flagged submission')               AS weak_status,
  coalesce(lower(condition_name) IN ('not provided', 'not specified'), TRUE)
                                                        AS odd_condition
FROM mine
WHERE stale OR weak_status OR odd_condition
ORDER BY last_evaluated;
```

The column shapes follow the bundle's JSON field names; run `DESCRIBE SELECT * FROM 'scv.parquet'` to
confirm them for a given release. The same idea extends to therapies: swap `varcond-proposition` for
`vartherapy-proposition` (its `object_therapy` and `condition_qualifier_id` columns) and join the
`therapy` / `therapyGroup` sections to spot a malformed or unexpected drug or drug combination.

Because `00-latest` refreshes every month, running the query on each release and diffing against the
previous month's output turns the audit into a standing report — new stale rows, newly flagged statuses,
and newly odd conditions surface on their own.

## The tools used

- **[DuckDB](https://duckdb.org/) / pandas** — query the published Parquet locally and build the audit
  report; DuckDB reads the `.parquet` files directly with no load step.
- **The clinvar-gkm [Parquet](data-access/parquet.md)** — one typed file per bundle
  section, refreshed every release.
- **The [sub-bundle](pipeline/sub-bundle.md) tool** (maintainers) — `--submitter <id>` extracts one
  submitter's entire footprint into a single portable bundle, as with `nch-igm-bundle.json.gz`.
- **[va-spec-python](https://github.com/ga4gh/va-spec-python)** — optionally load the flagged statements
  as typed VA-Spec models for deeper, programmatic checks.

## How to explore this

- **Get the data** — [Parquet Files](data-access/parquet.md) (the Parquet section under
  `datasets/parquet/00-latest/`).
- **See one submitter's whole footprint** — open
  [`nch-igm-bundle.json.gz`](https://github.com/clingen-data-model/clinvar-gkm/blob/main/nch-igm-bundle.json.gz)
  (2,443 SCVs, self-contained).
- **Understand review status** — [Review Status](profiles/review-status.md) (the star levels the audit
  flags on).
- **Extract your own** — maintainers can run the [sub-bundle](pipeline/sub-bundle.md) tool by
  `--submitter`; anyone can filter the Parquet by their submitter id as shown above.
- **See more GKM use cases** — the GKM Starter Kit's
  [user stories](https://ga4gh.github.io/gkm-starter-kit/user-stories/).
