# Variant-Sorted Statement Parquet (C1) — Design Plan

> **Status: design only (2026-10-17).** Nothing here is wired into the release pipeline. This plan answers
> the **C1** "Plan first" item in `docs/superpowers/plans/2026-10-16-parquet-followups.md` (branch
> `docs/parquet-followups-plan`, PR #144). The export SQL below is a prototype, quoted here so it can't be
> mistaken for a live `parquet-schemas/` file. Decisions marked **(maintainer)** are listed at the end.

**Goal:** publish one pre-joined Parquet file of statements × propositions, sorted by variant. A question
about one variant ("PubMed ids for `clinvar:10`") then reads one row group, not every row group of
`scv.parquet`. That makes per-variant questions run over HTTPS, including in the browser console, which today
gets HTTP 429 after about 55 requests in 10 s.

**Measurement sources:**
- **Local:** the 2026-10 monthly Parquet set in `~/Development/sandbox/clinvar-gkm-parquet`, with DuckDB 1.5.4.
- **BigQuery (read-only):** `clinvar_2026_10_11_v2_6_0` and `clinvar_2026_09_28_v2_6_0`. The latter is the
  source of the 2026-10 monthly set; its `gkm_dict_scv/vcv/rcv` row counts match the published set exactly.
- **Request counts:** DuckDB's `httpfs` reading from a local HTTP server that supports range requests and
  logs every one. Each query ran in a fresh process with `SET threads = 1`, to match the single-threaded
  browser console.

---

## Recommendations at a glance

| Question | Recommendation |
| --- | --- |
| Which statements | **SCV, VCV and RCV in one file**, with a `source_table` column (`scv` / `vcv` / `rcv`) |
| File name | **`statement-by-variant.parquet`** |
| Sort | **`variant_id, source_table, statement_id`** (a total order, so rebuilds are byte-stable) |
| Row groups | **122,880 rows** (DuckDB default) → 226 row groups |
| Compression | **ZSTD** (189 MB vs 328 MB with Snappy) |
| Bloom filters | **Off** (`WRITE_BLOOM_FILTER false`). With them on, any second filter costs one request per row group |
| `proposition_id` | **Drop it**: it's 31 % of the file. `statement_id` joins back to the statement table **(maintainer)** |
| Schema version | Parquet key/value metadata, not a column |
| Built by | `parquet-schemas/statement-by-variant.sql` (BigQuery `EXPORT DATA`), then **sorted in the local merge step** |
| Deltas | **Not shipped in deltas.** Rebuilt whole for every monthly set |
| R2 layout | Inside each monthly set: `v1/datasets/parquet/YYYY-MM/` and `00-latest/` |
| Upload / index scripts | `upload-gkm-to-r2.sh`: none. `generate-r2-index.sh`: one additive field, so the browser lists only files that exist |
| Past releases | **Yes for the 4 monthly sets** (2026-07 … 2026-10); not needed for the 15 weeklies |
| Size | **189 MB** for 2026-10 (27.65 M rows); about 192 MB projected for 2026-10-11 (28.05 M rows) |
| Pruning | One variant reads **1 of 226** row groups. The PubMed lookup takes **17 requests** (today: 399 requests, 331 MB) |

---

## 1. Which statements

**Recommendation: SCV, VCV and RCV in one file, one row per statement, with `source_table` naming the
statement table it came from.**

- **Coverage:** all three tiers join to a proposition 100 % of the time (0 unjoined of 28,045,103 rows on
  2026-10-11), and every proposition subject is a `clinvar:` variant id.
- **One file answers the whole question:** "everything ClinVar says about variant X" (submissions, the VCV
  layers, the RCVs) is one footer fetch plus one row group. Three files would mean three footers (0.12–0.5 MB
  each) and three sets of requests.
- **Filtering by tier stays cheap.** A `source_table = 'scv'` filter on top of `variant_id` adds no requests,
  as long as bloom filters are off (§2).
- **Cost:** SCV alone is 75 MB. VCV and RCV add 114 MB, for 189 MB total.

`source_table` is named after the table the `statement_id` lives in (`scv.parquet`, `vcv.parquet`,
`rcv.parquet`), so a join back to the full record is obvious. It deliberately avoids "tier" and "level",
which already name the VCV aggregation layers.

**Alternative (maintainer):** SCV only (75 MB). It answers the motivating PubMed question, but a reader who
wants the aggregate classification would still have to scan `vcv.parquet`.

## 2. File name, columns, sort, row groups

### Name

`statement-by-variant.parquet`. It is a derived lookup file, not a bundle section, so it doesn't follow
section naming. The name leaves room for a companion `statement-by-object.parquet` (§8, open question 3).

### Columns

All ids are bare (no `#/section/` pointers), like every other typed-Parquet foreign-key column after #143.

| Column | Type | From | Notes |
| --- | --- | --- | --- |
| `variant_id` | string | proposition `subject` | **Sort key 1.** `clinvar:<variation id>` |
| `source_table` | string | — | `scv`, `vcv` or `rcv`. Sort key 2 |
| `statement_id` | string | statement `id` | Sort key 3. Joins to `id` in `scv`/`vcv`/`rcv.parquet` |
| `proposition_type` | string | proposition `type` | e.g. `VariantPathogenicityProposition`, `ClinvarRiskFactorProposition` |
| `predicate` | string | proposition `predicate` | |
| `object_id` | string | proposition `object` | A `clinvar.trait:`, `clinvar.traitset:`, `clinvar.conditionset:`, tumor-type, `clinvar.therapy:` or `clinvar.therapygroup:` id |
| `condition_qualifier_id` | string | `conditionQualifier` | Therapeutic-response propositions only |
| `gene_context_name` | string | `geneContextQualifier.name` | SCV only today (see C4) |
| `mode_of_inheritance` | string | `modeOfInheritanceQualifier.name` | SCV only |
| `penetrance` | string | `penetranceQualifier.name` | SCV only |
| `classification_name` | string | `classification.name` | |
| `strength_name` | string | `strength.name` | |
| `quality_name` | string | `quality.name` | Submission level (SCV) or aggregate level (VCV/RCV) |
| `direction` | string | `direction` | |
| `submitter_id` | string | first `contributions[]` with `activityType = 'submitted'` | SCV only. Joins to `submitter.parquet` |
| `date_last_evaluated` | date | first `contributions[]` with `activityType = 'evaluated'` | SCV only |
| `pmids` | list\<string\> | `reportedIn[].pmid` | SCV only. Empty list for VCV/RCV |

The struct columns are flattened to strings with a `_name` suffix (`classification_name`, not
`classification`). The suffix keeps them from being mistaken for the structs in `scv.parquet`, where
`classification.name` is the idiom.

**Not carried:** `data`, `description`, `specifiedBy`, extensions. These are 2 GB+ in `scv.parquet`, and a
one-variant lookup can fetch them with a join back on `statement_id` once `scv.parquet` is id-sorted (§8,
open question 4).

**`proposition_id`, recommend dropping (maintainer).** At 91 MB of a 292 MB file it is the second-largest
column, and every field a lookup needs from the proposition is already inlined. For VCV/RCV it is derivable
from `statement_id` (drop the `.version`). For SCV it isn't (`clinvar.submission:SCV004905533.1` →
`SCV004905533-PATH`), so it is still reachable through `scv.parquet`.

### Sort and pruning

`ORDER BY variant_id, source_table, statement_id`. `statement_id` is unique within a table, so the order is
total and two builds of the same dataset write the same bytes. Each row group's min/max statistics on
`variant_id` then cover a narrow, non-overlapping id range, and an equality filter skips every other row
group.

`variant_id` sorts as text (`clinvar:10` < `clinvar:100` < `clinvar:11`). That is fine for equality and
`IN (…)` lookups, which are the use case. A numeric range of variation ids would not prune; no recipe needs
one.

### Row-group size

| Rows per group | Row groups | File | Footer | Requests: `SELECT *` for one variant |
| --- | --- | --- | --- | --- |
| **122,880 (default)** | **226** | **201 MB*** | **0.52 MB** | **11** |
| 61,440 | 451 | 205 MB* | 1.03 MB | 17 |
| 30,720 | 901 | 212 MB* | 2.03 MB | 28 |

\* With bloom filters and `proposition_id` dropped. The final layout (no bloom filters) is 189 MB.

Smaller groups read fewer bytes per lookup but make the footer bigger, add requests, and grow the file.
Across a random sample of 2,000 variants plus `clinvar:10` and the busiest variant (`clinvar:17004`, 189
statements), **every lookup touched exactly 1 row group** at every size tested. Keep the default.

### Bloom filters off

DuckDB writes a bloom filter for every dictionary-encoded column by default. The published `scv.parquet` has
them on 3,523 of its 3,960 column chunks. When a query filters on a column whose min/max can't rule a row
group out, DuckDB probes that column's bloom filter, one HTTP request per row group. It does this even when
the `variant_id` filter has already excluded the group:

| Query on the variant-sorted file | Bloom filters on | Bloom filters off |
| --- | --- | --- |
| `WHERE variant_id = 'clinvar:10'` | 11 requests | 10 requests |
| `… AND source_table = 'scv'` (the PubMed recipe) | **238 requests** | **16 requests** |
| `… AND classification_name = 'Pathogenic'` | **238 requests** | **16 requests** |
| `WHERE object_id = 'clinvar.trait:9580'` (no variant) | 487 requests | 358 requests |

Bloom filters never help here: the sort key already prunes, and lookups by other columns aren't remote-viable
on this file either way (§8). **Write with `WRITE_BLOOM_FILTER false`.**

### Compression

ZSTD: 189 MB, against 328 MB for Snappy (the other published files use Snappy). Every DuckDB release in use,
DuckDB-Wasm, pyarrow and polars read ZSTD. The smaller pages also mean fewer bytes per lookup (2.0 MB vs 2.6
MB for one variant's rows).

### Schema version and provenance

The release and schema version go in Parquet key/value metadata, not a column. A constant column would cost
almost nothing on disk, but the published files don't carry one, and metadata is readable from the footer
alone:

```sql
SELECT decode(key) AS k, decode(value) AS v FROM parquet_kv_metadata('statement-by-variant.parquet');
-- clinvar_gkm_release        2026-10
-- clinvar_gkm_schema_version 1.0.2
-- sort_order                 variant_id,source_table,statement_id
```

Verified with DuckDB 1.5.4 `COPY … (KV_METADATA {…})`. Whether to stamp the other 22 files the same way is
open question 5.

## 3. How it is built

**Recommendation: one `EXPORT DATA` query from a new `parquet-schemas/statement-by-variant.sql`, then a
special case in the local merge step that sorts and writes the final file.**

1. **`export-gkm-dicts.sh`:** add `extract_parquet_typed statement-by-variant.parquet
   statement-by-variant.sql`, **skipped when `--delta` is set** (§4).
2. **`release-gkm.sh` step 3**, when merging shards: for `statement-by-variant`, replace the plain `COPY` with:

   ```sql
   SET preserve_insertion_order = false;
   COPY (SELECT * FROM read_parquet('<shards>/statement-by-variant-*.parquet')
         ORDER BY variant_id, source_table, statement_id)
   TO '<dir>/statement-by-variant.parquet'
   (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 122880, WRITE_BLOOM_FILTER false,
    KV_METADATA {clinvar_gkm_release: '<YYYY-MM>', clinvar_gkm_schema_version: '<x.y.z>',
                 sort_order: 'variant_id,source_table,statement_id'});
   ```

   Measured: 50 s and 4.3 GB peak memory for 27.65 M rows.
3. **Gate in the same step:** fail the release unless every one of these holds:
   - `count(*)` equals `scv + vcv + rcv` row counts
   - `count(*) FILTER (WHERE variant_id IS NULL)` is 0
   - `parquet_metadata` shows 0 bloom filters
   - a probe `variant_id` falls in exactly 1 row group

Why not sort in BigQuery: `EXPORT DATA` writes shards in parallel, with no row-group or bloom-filter control
and no promised order across shards. The merge already rewrites every file through DuckDB, so the sort costs
one extra step.

**Cost per build:** dry run on 2026-10-11 = **11.19 GB processed** (upper bound), about $0.07 on demand, plus
the 50 s merge.

**Equivalence check:** I ran the prototype SQL on `clinvar_2026_09_28_v2_6_0` and the local build (the
`performance.md` recipe extended to VCV/RCV) on the published 2026-10 Parquet, then compared aggregates per
`source_table`. Every one matched exactly:

- row counts
- distinct variants and objects
- non-null counts of every qualifier, submitter and date column
- total PubMed ids
- a length checksum over 14 string columns

**Alternative considered:** build locally in DuckDB from the merged section files (no BigQuery cost). Not
recommended, for three reasons:

- It ties the file to the column names of five typed tables, including the pre-#143 quoted
  `object_therapy` pointer.
- It only works where a full Parquet set exists on disk, so it rules out weekly copies.
- It breaks the "one SQL file per published Parquet file" convention.

The BigQuery SQL strips pointers itself, so it doesn't depend on #143.

## 4. Deltas

**Recommendation: never ship it in weekly deltas, and rebuild it whole for each monthly set.**

- **The `--delta` table rewrite can't produce it.** `extract_parquet_typed --delta` rewrites
  `.gkm_dict_` → `.delta_gkm_dict_` in the schema SQL. Here that would join *changed statements* to
  *changed propositions*, dropping every statement whose proposition didn't change, and the reverse. A correct
  delta is "rows whose statement **or** proposition changed", a union over two sections, plus deletes taken
  from three manifest sections. That doesn't fit the per-section model. (The comment in
  `extract_parquet_typed` saying every schema file reads exactly ONE table is already inaccurate: the
  proposition and therapy files read 3–4. Reword it when this lands.)
- **Applying a delta would undo the point.** The keyed upsert in Downloads → Parquet Files produces rows in
  arbitrary order. A consumer would have to re-sort 28 M rows, which costs the same as rebuilding from their
  updated section set with the Working at Scale recipe (about 50 s).
- **It isn't a section.** The manifest, the delta-reconstruction oracle and the replay examples iterate over
  bundle sections. A derived file in `deltas/<date>/parquet/` would be listed beside the changed-rows files
  and mislead downloaders.

Weekly freshness is open question 2: a *full* weekly copy in its own directory, never a delta.

## 5. R2 layout, `index.json` and scripts

**Location:** `v1/datasets/parquet/YYYY-MM/statement-by-variant.parquet`, and `…/00-latest/` through the
existing server-side copy. Year-end archiving moves it with the rest of the set (`archive_parquet_yearly` moves every file in
the directory). An upload run with `R2_PREFIX=''` publishes the flat-root copy the same way.

| Script | Change |
| --- | --- |
| `export-gkm-dicts.sh` | Add the export line, guarded by `if ! $DELTA` |
| `release-gkm.sh` | Special-case the merge for this file (§3), including the gate |
| `upload-gkm-to-r2.sh` | **None.** `upload_parquet` already uploads every `*.parquet` in the directory and copies each to `00-latest/`. The new dated path was never cached, so nothing needs purging |
| `generate-r2-index.sh` | **Additive:** give each `datasets.parquet[]` entry a `"parquet": [...]` list of the files present (reuse `r2_parquet_sections_under`, which delta entries already use). Without it, `r2-browser.js` can't tell which month sets have the file |
| `docs/assets/js/r2-browser.js` | Render the files listed in `parquet` for each month set, falling back to the fixed 22 when the field is absent. Label the new file "lookup (derived)" |
| `upload-gkm-delta-to-r2.sh`, `release-gkm-delta.sh`, `build-delta-manifest.py`, oracles | None |

## 6. Past releases and the backfill

**Recommendation: yes for the four monthly sets (2026-07, -08, -09, -10). The 15 weeklies need nothing,
because the file never lives in a delta directory.**

Why it's worth doing: the console's release picker lists all four months, and so does the docs file browser.
If only new months have the file, the console example returns 404 for every month the picker offers today.

It **does not need** to ride in the consolidated backfill. That backfill exists because overwriting
published section files changes delta reconstruction and needs CDN purges. This file:

- is new, at a path that has never been cached
- appears in no manifest
- feeds no oracle

So it can be added to past months at any time without breaking the "one rebuild, one backfill" rule. If C1
is implemented before the backfill runs, fold it in; otherwise publish it as a separate additive step.

**Cost of including it, per monthly set:**

| Step | Cost |
| --- | --- |
| `EXPORT DATA` from the month's source dataset (2026-10 ← `clinvar_2026_09_28_v2_6_0`, per ADR 0002) | ~11 GB processed, ~$0.07 |
| Download shards + sort/merge | ~1 min, ~4.3 GB RAM |
| Upload | ~190 MB (+ one server-side copy for `00-latest`) |
| CDN purge | none (new path) |

**Total for four sets:** about $0.30 of BigQuery, about 5 minutes of merging, about 0.8 GB of uploads, then
one `index.json` regeneration. There is no oracle or reconstruction re-run, and no existing file changes.

The only ordering constraint is C4. If `gene_context_name` gets populated on aggregate propositions, VCV/RCV
rows in this file change. Build past months from their datasets as they stand after whatever C4 decides for
history. Forward builds pick up C4 automatically, since the file is rebuilt whole.

## 7. Docs changes (in the implementation PR, on `main`)

Docs ship with the first release that publishes the file. A console example that 404s is worse than none.

- [ ] **Recipes** (`docs/parquet/recipes.md`): a "One variant, over the network" section built on
  `statement-by-variant.parquet`:
  - PubMed ids for a variant (the existing recipe, now runnable remotely)
  - a variant's VCV layers
  - its SCVs with submitter and condition names, joining the small `submitter`/`condition` tables, measured
    at 23 requests
- [ ] **Console** (`docs/assets/duckdb-console.html`):
  - add an example "PubMed ids cited for one variant" against `{BASE}/statement-by-variant.parquet`
  - point the 429 hint at the published file as well as the local recipe
- [ ] **Working at Scale** (`docs/parquet/performance.md`):
  - open "Materialize the joins you repeat" with an admonition: per-variant lookups are published pre-built
    as `statement-by-variant.parquet`, so download it or query it remotely
  - keep the local recipe for object/qualifier lookups and custom columns
  - in **Local or remote**, add a row: a `variant_id` lookup on `statement-by-variant.parquet` is ~10–17
    requests, so yes
  - update "Share it as a sorted Parquet file" to say this is what the release now publishes, and why bloom
    filters are off
- [ ] **The 22 Tables** (`docs/parquet/tables.md`): a "Derived lookup file" section with the column table from §2.
  Say plainly that it is not a bundle section, has no `id` column and no delta, and is rebuilt monthly.
- [ ] **Downloads → Parquet Files** (`docs/data-access/parquet.md`): list it under "Available Parquet files"
  as derived and monthly-only, and add a line to the delta section saying it isn't in deltas.
- [ ] **ADR:** a short ADR, "Derived Parquet files," recording: not a section; full rebuild per monthly set;
  never in deltas; sorted; no bloom filters; key/value metadata.

Run every SQL snippet against the published file before it ships (the docs convention).

## 8. Decisions needed from the maintainer

1. **Tiers:** SCV + VCV + RCV in one file (recommended, 189 MB), or SCV only (75 MB)?
2. **Weekly freshness:** monthly only (recommended for now), or also a *full* weekly copy at
   `v1/deltas/<YYYY-MMDD>/lookup/statement-by-variant.parquet` plus `deltas/00-latest/lookup/`?
   - **Cost per week:** one non-delta export (~$0.07), a 50 s merge and about 190 MB of R2 (~10 GB/year).
   - **Script work:** `release-gkm-delta.sh` would need a full-mode export of this one file, plus a
     `--lookup-dir` in `upload-gkm-delta-to-r2.sh`, a `lookup` field on delta index entries, and a
     console/browser option for it.
3. **Lookups by condition or gene:** this file doesn't speed them up.
   - **Measured on the variant-sorted file:** a condition lookup takes 358 requests and a gene lookup 229,
     both over the rate limit.
   - **An object-sorted companion** (`statement-by-object.parquet`, sorted by `object_id, variant_id, …`)
     measured 172 MB, and the same condition lookup took **5 requests**. The two catch-all objects (`not
     provided`, `not specified`: ~6.9 M rows each) would still span ~57 row groups.
   - **Options:** add it now, later, or leave condition/gene questions download-only.
4. **Sort every published section by `id` in the merge step?** Not part of C1, but it would let a lookup
   join back from `statement_id` to `scv.parquet` (for `data`, `description`) prune too. Today that join
   scans the whole file. It's a one-line `ORDER BY id` in the merge step, with no schema change.
5. **Key/value metadata:** stamp `clinvar_gkm_release` and `clinvar_gkm_schema_version` on this file only
   (recommended for now), or on all 23?
6. **Drop `proposition_id`?** Recommended: −91 MB, and nothing in the lookup recipes uses it.
7. **Backfill timing:** fold the four past months into the consolidated backfill if C1 is ready by then,
   otherwise run it as a separate additive publish (§6). The backfill doesn't need to wait for C1.

---

## Measurements (2026-10 monthly, DuckDB 1.5.4)

**Build:** the local join of 6,735,011 SCV + 9,079,449 VCV + 11,839,428 RCV rows took 49 s at 4.8 GB peak.
The sort and write took 50 s at 4.3 GB.

**Size by variant** (row groups of 122,880):

| Variant | Size | Row groups | Footer |
| --- | --- | --- | --- |
| **SCV+VCV+RCV, no `proposition_id`, ZSTD, no bloom filters (recommended)** | **189.2 MB** | **226** | **492 KB** |
| SCV+VCV+RCV, no `proposition_id`, ZSTD, bloom filters | 201.1 MB | 226 | 521 KB |
| SCV+VCV+RCV, no `proposition_id`, Snappy, bloom filters | 327.8 MB | 226 | — |
| SCV+VCV+RCV, with `proposition_id`, ZSTD, bloom filters | 291.7 MB | 226 | — |
| SCV only, ZSTD, bloom filters | 75.2 MB | 55 | 118 KB |
| Object-sorted companion, ZSTD, no bloom filters | 171.8 MB | 226 | — |

**Largest columns** in the recommended layout: `statement_id` 102 MB, `object_id` 24 MB, `variant_id` 13
MB, `gene_context_name` 12 MB and `date_last_evaluated` 12 MB. Everything else is under 8 MB.

**HTTP range requests per query** (fresh process, `threads = 1`, local range server; footer fetch included):

| Query | File | Requests | Bytes |
| --- | --- | --- | --- |
| PubMed ids for `clinvar:10` (today's way: `scv` ⨝ `varcond-proposition`) | published files | **399** | 331 MB |
| PubMed ids for `clinvar:10` | recommended file | **17** | 1.7 MB |
| VCV layers for `clinvar:10` | recommended | 17 | 1.7 MB |
| SCVs for `clinvar:10` + submitter + condition names (joins 2 small tables) | recommended + `submitter` + `condition` | 23 | 5.9 MB |
| `SELECT *` for `clinvar:10` (101 rows) | recommended | 10 | 2.1 MB |
| `count(*)` | recommended | 3 | 0.75 MB |
| condition `clinvar.trait:9580` (4,033 rows) | recommended | 358 | 26.8 MB |
| condition `clinvar.trait:9580` | object-sorted companion | 5 | 0.75 MB |
| gene `BRCA1` | recommended | 229 | 13.0 MB |

The browser console runs DuckDB-Wasm 1.29.0, not the CLI. Its request pattern needs checking before the docs
ship (task 6 below), but its min/max pruning is the same.

**BigQuery, `clinvar_2026_10_11_v2_6_0`** (read-only `SELECT`s; no `EXPORT DATA`, `CREATE` or `DELETE`):

| `source_table` | Rows | Distinct variants | Unjoined | Null `variant_id` | PubMed ids |
| --- | --- | --- | --- | --- | --- |
| scv | 6,845,745 | 4,444,468 | 0 | 0 | 1,553,011 |
| vcv | 9,156,181 | 4,444,468 | 0 | 0 | — |
| rcv | 12,043,177 | 4,444,468 | 0 | 0 | — |

The prototype dry run (`bq query --dry_run`) validates, with an upper bound of 11,193,634,399 bytes processed.

---

## Prototype export SQL

Proposed path: `src/scripts/parquet-schemas/statement-by-variant.sql`. `{DATASET}` is substituted by
`extract_parquet_typed`. It needs no `collapse_ext_values` (there is no `data` column).

```sql
-- statement-by-variant: one row per SCV, VCV and RCV statement, with its proposition's subject, object and
-- qualifiers inlined. Bare ids everywhere (no '#/section/' pointers), matching the typed-Parquet FK columns.
-- No ORDER BY: EXPORT DATA shards are written in parallel and BigQuery does not promise row order across
-- shards, so the sort (and row-group size, compression, no bloom filters) is applied in the local merge.
-- Reads SIX {DATASET}.gkm_dict_* tables, so the --delta '.gkm_dict_' -> '.delta_gkm_dict_' rewrite must NOT
-- be applied to this file: a delta join would drop every statement whose proposition did not change (and
-- vice versa). The file is rebuilt whole from the full dict tables instead.
WITH prop AS (
  SELECT
    key AS proposition_id,
    JSON_VALUE(value, '$.type') AS proposition_type,
    JSON_VALUE(value, '$.predicate') AS predicate,
    REGEXP_REPLACE(JSON_VALUE(value, '$.subject'), r'^#/[^/]+/', '') AS variant_id,
    REGEXP_REPLACE(JSON_VALUE(value, '$.object'), r'^#/[^/]+/', '') AS object_id,
    REGEXP_REPLACE(JSON_VALUE(value, '$.conditionQualifier'), r'^#/[^/]+/', '') AS condition_qualifier_id,
    JSON_VALUE(value, '$.geneContextQualifier.name') AS gene_context_name,
    JSON_VALUE(value, '$.modeOfInheritanceQualifier.name') AS mode_of_inheritance,
    JSON_VALUE(value, '$.penetranceQualifier.name') AS penetrance
  FROM (
    SELECT key, value FROM `{DATASET}.gkm_dict_proposition`
    UNION ALL SELECT key, value FROM `{DATASET}.gkm_dict_vcv_proposition`
    UNION ALL SELECT key, value FROM `{DATASET}.gkm_dict_rcv_proposition`
  )
),
stmt AS (
  SELECT
    'scv' AS source_table,
    s.id AS statement_id,
    REGEXP_REPLACE(s.proposition, r'^#/[^/]+/', '') AS proposition_id,
    s.classification.name AS classification_name,
    s.strength.name AS strength_name,
    s.quality.name AS quality_name,
    s.direction,
    (SELECT REGEXP_REPLACE(c.contributor, r'^#/[^/]+/', '') FROM UNNEST(s.contributions) AS c
       WHERE c.activityType = 'submitted' LIMIT 1) AS submitter_id,
    (SELECT c.date FROM UNNEST(s.contributions) AS c
       WHERE c.activityType = 'evaluated' LIMIT 1) AS date_last_evaluated,
    ARRAY(SELECT r.pmid FROM UNNEST(s.reportedIn) AS r WITH OFFSET AS o
          WHERE r.pmid IS NOT NULL ORDER BY o) AS pmids
  FROM `{DATASET}.gkm_dict_scv` AS s
  UNION ALL
  SELECT
    'vcv' AS source_table, v.id AS statement_id,
    REGEXP_REPLACE(v.proposition, r'^#/[^/]+/', '') AS proposition_id,
    v.classification.name AS classification_name, v.strength.name AS strength_name,
    v.quality.name AS quality_name, v.direction,
    CAST(NULL AS STRING) AS submitter_id, CAST(NULL AS DATE) AS date_last_evaluated,
    CAST([] AS ARRAY<STRING>) AS pmids
  FROM `{DATASET}.gkm_dict_vcv` AS v
  UNION ALL
  SELECT
    'rcv' AS source_table, r.id AS statement_id,
    REGEXP_REPLACE(r.proposition, r'^#/[^/]+/', '') AS proposition_id,
    r.classification.name AS classification_name, r.strength.name AS strength_name,
    r.quality.name AS quality_name, r.direction,
    CAST(NULL AS STRING) AS submitter_id, CAST(NULL AS DATE) AS date_last_evaluated,
    CAST([] AS ARRAY<STRING>) AS pmids
  FROM `{DATASET}.gkm_dict_rcv` AS r
)
SELECT
  p.variant_id,
  st.source_table,
  st.statement_id,
  p.proposition_type,
  p.predicate,
  p.object_id,
  p.condition_qualifier_id,
  p.gene_context_name,
  p.mode_of_inheritance,
  p.penetrance,
  st.classification_name,
  st.strength_name,
  st.quality_name,
  st.direction,
  st.submitter_id,
  st.date_last_evaluated,
  st.pmids
FROM stmt AS st
JOIN prop AS p ON p.proposition_id = st.proposition_id
```

To keep `proposition_id` (if decision 6 goes the other way), add `st.proposition_id` to the final `SELECT`.

---

## Implementation tasks (after the decisions)

Base: `1.0` for the scripts and SQL, with a paired `main` docs PR. Size M.

- [ ] **1.** Add `src/scripts/parquet-schemas/statement-by-variant.sql` (above, adjusted for the decisions).
- [ ] **2.** `export-gkm-dicts.sh`: export it in full mode only; fix the "exactly ONE table" comment.
- [ ] **3.** `release-gkm.sh` step 3: the sorted merge plus gate from §3, with `--month-label` passed into
  `KV_METADATA`. Validate with `bash -n` and `shellcheck`.
- [ ] **4.** `generate-r2-index.sh`: add the `parquet` file list to month-set entries. `r2-browser.js`: render it.
- [ ] **5.** Dry-run the release (`release-gkm.sh --dry-run`), then a real export to a scratch GCS prefix.
  Check the merged file against §3's gate, and its aggregates against the section files of the same set.
- [ ] **6.** Console check before publishing. No R2 writes needed:
  - serve the merged file locally with CORS and range support
  - point a local docs build's console at it
  - confirm the PubMed example stays under ~20 requests in DuckDB-Wasm 1.29.0
- [ ] **7.** Publish with the next monthly set. Backfill 2026-07 … 2026-10 per §6, with each live write
  confirmed.
- [ ] **8.** Docs per §7, merged in the same window as step 7.
