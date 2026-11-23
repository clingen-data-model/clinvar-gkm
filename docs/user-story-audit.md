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
  [Parquet](data-access/parquet.md); a [mini-bundle](parquet/build-your-own.md#cut-a-mini-bundle) cut with
  `gkm-bundle-parquet select`;
  optionally [va-spec-python](https://github.com/ga4gh/va-spec-python)
- **Status** — In production: generally available since 1.1.0; current line 1.2

!!! tip "New to GKM datasets?"
    The GA4GH [**GKM Starter Kit**](https://ga4gh.github.io/gkm-starter-kit/) is the best place to get
    oriented — it collects the reference libraries, the [GKM Toolkit](https://ga4gh.github.io/gkm-starter-kit/latest/tools/gkm-toolkit/)
    for loading and exploring bundles, and [other user stories](https://ga4gh.github.io/gkm-starter-kit/latest/user-stories/)
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
- **The whole release is typed Parquet** — one file per bundle section, keyed by `id`, with every
  property of a record in its own typed column — so filtering *your* SCVs and joining them to
  conditions, therapies, and variants is ordinary SQL.
- **Releases are dated and incremental.** The Parquet dataset at `v1/1.2/parquet/` is rebuilt from the
  newest release every week, so the same audit re-runs against each release and its results can be diffed
  over time.

## The data

To make this concrete, the repository ships
**[`nch-igm-bundle.json.gz`](https://github.com/clingen-data-model/clinvar-gkm/blob/main/nch-igm-bundle.json.gz)** —
the complete GKM extract of one real submitter, the IGM Clinical Laboratory at Nationwide Children's
Hospital (submitter `196472`): **all 2,443 of their SCVs** plus every variation, condition, therapy,
proposition, and submitter record those statements reference, in a single self-contained 1.6 MB file. It
is exactly "everything one submitter has in ClinVar," and it is the shape an audit consumes. It was
regenerated from the 2026-10-18 release with the maintainer [sub-bundle](pipeline/sub-bundle.md) tool —
`sub-bundle.py --submitter 196472` — so it carries the 1.1.0 proposition sections and `schema_version`
`1.1.0`, and it passes strict validation against the ClinVar-GKM schemas (6,432 records, 0 failing).

For the recurring, release-over-release audit, a submitter works from the published Parquet instead. A
single DuckDB query flags the records that need a second look:

!!! note "Prerequisites"
    The [DuckDB CLI](https://duckdb.org/docs/installation/), tested with **1.5.4**, run from a directory holding
    six files from `v1/1.2/parquet/`: `scv.parquet`, the four `proposition*.parquet` tables and
    `condition.parquet`, about 1.2 GB together ([Downloads → Parquet Files](data-access/parquet.md#download)).
    They must be local: `read_parquet('proposition*.parquet')` is a glob, and DuckDB can't expand a glob over
    HTTPS.

```sql
-- Everything submitter 196472 has in ClinVar, flagged for review.
-- Reads six downloaded files from v1/1.2/parquet/ (rebuilt from the newest release
-- every week): scv.parquet, the four proposition*.parquet tables and condition.parquet.
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
  JOIN read_parquet('proposition*.parquet', union_by_name = true) p ON s.proposition = p.id
  LEFT JOIN 'condition.parquet' cond          -- CASE keeps this an equi-join (fast); an AND in ON plans a nested loop
         ON cond.id = CASE WHEN p.object_section = 'condition' THEN p.object END
  WHERE list_contains(
          [c.contributor FOR c IN s.contributions],
          'clinvar.submitter:196472')
)
SELECT
  id, classification, review_status, condition_name, last_evaluated,
  last_evaluated < '2022-01-01'                        AS stale,
  review_status IN ('no assertion criteria provided',
                    'no classification',
                    'flagged')                          AS weak_status,
  coalesce(lower(condition_name) IN ('not provided', 'not specified'), TRUE)
                                                        AS odd_condition
FROM mine
WHERE stale OR weak_status OR odd_condition
ORDER BY last_evaluated;
```

The columns are named after the bundle's properties; run `DESCRIBE SELECT * FROM 'scv.parquet'` to
see them. Each proposition table has only the columns its propositions use, so
`read_parquet('proposition*.parquet', union_by_name = true)` reads all four and covers every SCV. A
contribution `date` is `YYYY-MM-DD` text, so `max` and the comparison with `'2022-01-01'` work on it directly. A
condition-set object (`object_section` = `conditionSet`) has no `condition.parquet` row and is flagged for a
look. The same idea extends to therapies: filter the propositions on `object_section IN ('therapy',
'therapyGroup')` and join `object` to the `id` of the `therapy` / `therapyGroup` tables (with
`propositionSomaticClinicalImpact.conditionQualifier` for the tumor type) to spot a malformed or unexpected drug
or drug combination.

Because the Parquet dataset is rebuilt from every weekly release, running the query each week and diffing
against the previous run's output turns the audit into a standing report — new stale rows, newly flagged statuses,
and newly odd conditions surface on their own.

## The tools used

- **[DuckDB](https://duckdb.org/) / pandas** — query the published Parquet locally and build the audit
  report; DuckDB reads the `.parquet` files directly with no load step.
- **The clinvar-gkm [Parquet](data-access/parquet.md)** — one typed file per bundle
  section, refreshed every release.
- **`gkm-bundle-parquet select`** — `--driver submitter` cuts one submitter's footprint out of a published
  bundle into a single portable [mini-bundle](parquet/build-your-own.md#cut-a-mini-bundle), the shape of
  `nch-igm-bundle.json.gz`.
- **[va-spec-python](https://github.com/ga4gh/va-spec-python)** — optionally load the flagged statements
  as typed VA-Spec models for deeper, programmatic checks.

## How to explore this

- **Get the data** — [Parquet Files](data-access/parquet.md) (the one Parquet dataset, at
  `v1/1.2/parquet/`).
- **See one submitter's whole footprint** — open
  [`nch-igm-bundle.json.gz`](https://github.com/clingen-data-model/clinvar-gkm/blob/main/nch-igm-bundle.json.gz)
  (2,443 SCVs, self-contained).
- **Understand review status** — [Review Status](profiles/review-status.md) (the star levels the audit
  flags on).
- **Extract your own** — cut your submissions out of a published bundle with `gkm-bundle-parquet select
  --driver submitter` ([One submitter's submissions](parquet/build-your-own.md#one-submitters-submissions)), or
  filter the Parquet by your submitter id as shown above.
- **See more GKM use cases** — the GKM Starter Kit's
  [user stories](https://ga4gh.github.io/gkm-starter-kit/latest/user-stories/).
