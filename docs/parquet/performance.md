# Working at Scale

!!! info "Release"
    File and row-group sizes on this page are from a `gkm-bundle-parquet` 2.0.0 build of the **2026-10-31
    release**. Timings and peak memory for queries over the full 2.0 tables have not been measured yet; the habits
    below don't depend on them. Your numbers will differ with the release and your machine.

The 2026-10-31 tables total **4.6 GB**. Eight are over 100 MB: `variation` (1.66 GB), `scv` (784 MB), `allele` (701 MB), `location` (427 MB), `propositionPathogenicity` (401 MB), `evidenceLine` (265 MB), `rcv` (182 MB) and `vcv` (145 MB). The other twelve are each 5 MB or less. A handful of habits keeps queries over the big ones fast on a laptop.

## What you need { #requirements }

| | |
| --- | --- |
| **DuckDB** | The files are written with DuckDB **1.5.4** (each file's `gkm_bundle_parquet.duckdb_version` metadata and the manifest's `duckdb_version` say so). The queries in this track were run with DuckDB 1.5.4, from the command line and from Python. Any reader with Parquet nested types (`STRUCT`, lists) reads the files; the SQL uses DuckDB syntax. |
| **Disk** | 4.6 GB for all 20 tables. Most questions need only a few: the [column reference](tables.md#column-reference) gives every table's size. `condition`, `conditionSet`, `gene`, `submitter`, `therapy`, `therapyGroup` and the three smaller proposition tables together are under 20 MB. Add room for DuckDB's spill files when a big join runs short of memory (see [settings](#settings)). |
| **Memory** | Depends on the query, not the file size: a query reads only the columns it names. Lookups and filters on one table need little. A join or `GROUP BY` across two of the big tables is the heavy case; DuckDB caps itself at 80 % of RAM and spills to disk past that, so it finishes on a laptop, more slowly. Loading a whole big table into pandas needs its full decompressed size, several times its size on disk. |
| **Python** | `duckdb` 1.5.4 and, for Arrow or pandas, `pyarrow`; see [Working in Python](../working-in-python.md) for a tested set of versions. |
| **To build the tables yourself** | A full build needs far more: about 65 GiB of memory and 65 GB of working disk; see [Build Your Own](build-your-own.md#a-full-bundle). |

## Name your columns { #name-your-columns }

Parquet stores each column separately, and a query reads only the columns it names. This is the single biggest lever you have. In `scv.parquet`, the free-text `description` and the `extensions` are most of the table, on disk and far more in memory ([the breakdown](table-anatomy.md#never-select-on-a-big-table)). A query that names two small fields reads almost none of it.

To see where any table's bytes are, ask its metadata. This reads only the file footer:

```sql
SELECT split_part(path_in_schema, ',', 1)          AS col,
       round(sum(total_compressed_size)   / 1e6, 2) AS mb_on_disk,
       round(sum(total_uncompressed_size) / 1e6, 2) AS mb_in_memory
FROM parquet_metadata('scv.parquet')
GROUP BY 1
ORDER BY mb_in_memory DESC;
```

The same holds for fields inside a `STRUCT`: `classification.name` reads that one field, not the whole `classification` record. Selecting `*` or the struct as a whole reads everything.

## Look up by id { #look-up-by-id }

Every table is **sorted by `id`** and written in row groups of up to 122,880 rows, each with the minimum and maximum `id` it holds. A filter on `id` (`WHERE id = …`, `WHERE id LIKE 'VCV000000010.%'`) lets DuckDB skip every row group whose range can't match, so it reads one or two row groups instead of the whole file. That is what makes the evidence-line lookups in [Seam D](joining.md#seam-d-inside-an-aggregate) fast: filtering `evidenceLine` by an accession prefix reads one row group of about 176.

A filter on any other column (`subject`, `object`, `name`) can't skip anything, because those values are spread across the file. When you look up by such a column again and again, [materialize](#materialize-join-tables) a copy sorted by it.

## Reach into nested lists without `unnest` { #nested-lists }

Several columns are lists of records: `variation.extensions`, `variation.members`, `scv.contributions`, `scv.reportedIn`. To filter on something inside them, prefer a **list comprehension**, `[x.field FOR x IN list IF …]`, over `unnest`. `unnest` turns every list element into its own row before filtering; a comprehension filters each list in place, which is many times faster on `variation`. The [gene rollup recipe](recipes.md#gene-rollup) shows the comprehension.

Use comprehensions rather than lambda functions (`list_filter(l, x -> …)`). DuckDB 1.5 deprecates that arrow syntax, and the replacement (`lambda x: …`) is too new for the browser console's engine. Comprehensions work in both.

## Join on a plain equality { #equi-joins }

DuckDB joins two big tables fast, with a **hash join**, when the `ON` clause is one equality between them. Add a second condition (`ON p.object_section = 'condition' AND c.id = p.object`), or join through a function (`ON list_contains(…)`), and DuckDB 1.5 plans a **nested-loop join** instead, which compares row against row and can run for hours on `propositionPathogenicity`. Fold the extra condition into the key, `ON c.id = CASE WHEN p.object_section = 'condition' THEN p.object END`, or `unnest` the list in a subquery and join on the plain column. [Seam B](joining.md#seam-b-proposition-condition-or-conditionset) shows the first; [Find the variant](recipes.md#find-the-variant) shows the second. Put `EXPLAIN` in front of a query to check before you run it: `HASH_JOIN` is the fast kind; `NESTED_LOOP_JOIN`, `BLOCKWISE_NL_JOIN` and `PIECEWISE_MERGE_JOIN` are the slow kinds.

## Local or remote { #local-or-remote }

DuckDB reads Parquet over HTTPS with **range requests**: it fetches the file's footer first, then only the byte ranges of the row groups and columns a query needs. That makes some remote queries as cheap as local ones and others impractical:

| Over the network | Requests | Works? |
| --- | --- | --- |
| `DESCRIBE`, `count(*)`, `parquet_metadata(…)` | footer only | yes, in about a second on any table |
| `LIMIT n` without a filter | footer + first row group | yes |
| A filter on `id` | footer + the row groups whose range matches | yes |
| Any query on a small table (`condition`, `gene`, `submitter`, `therapy`, …) | a few | yes |
| Any other filter, `GROUP BY` or join over a big table | one per row group per column: about 56 row groups in `scv`, 228 in `propositionPathogenicity`, 176 in `evidenceLine` | **slowly**, and a burst of requests can be refused; download for repeated or heavier work |

The CDN in front of `data.clinvar-gkm.org` allows about **55 requests per 10 seconds** per client and refuses more with **HTTP 429** for a short time. The rule: **query remotely to explore, download to analyze.** Download the tables a question needs once (see [Start Here](index.md#put-the-file-on-your-machine)), and the queries on this page and in [Recipes](recipes.md) run locally.

## DuckDB settings for a laptop { #settings }

DuckDB's defaults suit most queries here: it uses every CPU core, caps itself at 80 % of RAM, and spills to a `.tmp` directory when a query needs more. When a big join or `GROUP BY` runs out of memory, you see this:

```text
Out of Memory Error: could not allocate block of size 256.0 KiB (953.5 MiB/953.6 MiB used)

Possible solutions:
* Reducing the number of threads (SET threads=X)
* Disabling insertion-order preservation (SET preserve_insertion_order=false)
* Increasing the memory limit (SET memory_limit='...GB')
```

The suggestions are the right ones, in that order:

| Setting | Effect |
| --- | --- |
| `SET threads = 2;` | Each thread holds its own working memory; fewer threads means a smaller peak. |
| `SET preserve_insertion_order = false;` | Lets DuckDB skip buffering rows to keep them in file order. Use it whenever the result has an `ORDER BY` or order doesn't matter. |
| `SET memory_limit = '8GB';` | Raises (or lowers) the cap. |
| `SET temp_directory = '/path/with/space';` | Moves the spill files to a disk with room. |

For work you repeat, open a database file (`duckdb clinvar-gkm.duckdb`) rather than an in-memory session. Tables you create there persist, which is what makes the next section possible.

## Materialize the joins you repeat { #materialize-join-tables }

Statements and propositions live in separate tables. An SCV row holds its classification but not the variant or condition it is about. Those are on the proposition, in one of four tables with different qualifier columns. So any question about statements by **subject** (a variant), **object** (a condition, tumor type or therapy) or **qualifier** (gene context, mode of inheritance, penetrance) has to join two big tables first.

Paying for that join on every query is slow locally, and slower over the network: `scv.parquet` is sorted by SCV id and has no variant column, so a lookup for one variant must read every row group of the file. In the browser's [live console](index.md#run-a-query-now) it can also exhaust memory or trip the CDN's rate limit (**HTTP 429**).

The fix is to run the join **once**, store the result as a table sorted by the column you look up most, and query that table instead. DuckDB has no `CREATE MATERIALIZED VIEW`; `CREATE TABLE … AS SELECT` in a database file does the same job. You refresh it by re-running the script when you download a new release.

### Build it

Download the four proposition tables and `scv.parquet` (see [Start Here](index.md#put-the-file-on-your-machine)), then run this in the same directory. It writes a database file, `clinvar-gkm.duckdb`, that persists between sessions:

```bash
duckdb clinvar-gkm.duckdb < materialize.sql
```

```sql
-- materialize.sql
SET preserve_insertion_order = false;   -- lets DuckDB build large tables with less memory

-- 1. One proposition table: union_by_name lines up the four tables' different qualifier columns.
CREATE OR REPLACE TABLE prop AS
SELECT id, type AS proposition_type, predicate,
       subject AS variant_id, object AS object_id, object_section,
       geneContextQualifier.name                    AS gene_context_name,
       'ncbigene:' || geneContextQualifier.primaryCoding.code AS gene_context_id,
       modeOfInheritanceQualifier.name              AS mode_of_inheritance,
       penetranceQualifier.name                     AS penetrance,
       conditionQualifier                           AS condition_qualifier_id
FROM read_parquet('proposition*.parquet', union_by_name = true);

-- 2. SCV statements with their proposition's subject, object and qualifiers inlined,
--    sorted by variant so a lookup by variant touches one small slice of the table.
CREATE OR REPLACE TABLE scv_by_variant AS
SELECT p.variant_id, p.object_id, p.object_section, p.proposition_type, p.predicate,
       p.gene_context_name, p.gene_context_id, p.mode_of_inheritance, p.penetrance, p.condition_qualifier_id,
       s.id                     AS scv_id,
       s.classification.name    AS classification,
       s.quality.name           AS submission_level,
       s.direction,
       [c.contributor FOR c IN s.contributions IF c.activityType = 'submitted'][1] AS submitter_id,
       [r.pmid FOR r IN s.reportedIn IF r.pmid IS NOT NULL]                        AS pmids
FROM 'scv.parquet' s
JOIN prop p ON p.id = s.proposition
ORDER BY p.variant_id, s.id;
```

Only the columns the questions below need are carried over. Add others, such as `s.description` or `s.specifiedBy.name`, the same way.

### Query it

Each of these reads one small, sorted table, where the same question against the raw Parquet files means a join of two big ones.

**By subject (a variant)**

```sql
-- PubMed ids cited by the SCVs for one variant
SELECT pmid, count(*) AS n_scvs,
       string_agg(replace(scv_id, 'clinvar.submission:', ''), ', ') AS cited_by
FROM (SELECT scv_id, unnest(pmids) AS pmid
      FROM scv_by_variant WHERE variant_id = 'clinvar:10')
GROUP BY pmid
ORDER BY n_scvs DESC, pmid;
```

**By object (a condition)**

```sql
-- What submitters have called variants for one condition
SELECT classification, count(*) AS n
FROM scv_by_variant
WHERE object_id = 'clinvar.trait:9580'      -- Hereditary spastic paraplegia 48
GROUP BY ALL ORDER BY n DESC;
```

This matches propositions whose object *is* that condition. A proposition about a condition **set** that contains it has a `clinvar.traitset:` or `clinvar.conditionset:` object instead. To include those, expand the sets as shown in [Joining Tables](joining.md).

**By qualifier**

```sql
-- Pathogenic calls made under autosomal recessive inheritance, by submission level
SELECT submission_level, count(*) AS n
FROM scv_by_variant
WHERE mode_of_inheritance = 'Autosomal recessive inheritance'
  AND classification = 'Pathogenic'
GROUP BY ALL ORDER BY n DESC;
```

### The same pattern for the aggregates

VCV and RCV statements join to the same `prop` table. Add this to `materialize.sql` to get every aggregate statement for a variant in one lookup:

```sql
CREATE OR REPLACE TABLE vcv_by_variant AS
SELECT p.variant_id, p.object_id, p.proposition_type,
       v.id AS vcv_id, v.classification.name AS classification,
       v.quality.name AS aggregate_level, v.direction
FROM 'vcv.parquet' v
JOIN prop p ON p.id = v.proposition
ORDER BY p.variant_id, v.id;
```

For `rcv`, swap in `rcv.parquet`.

### Share it as a sorted Parquet file

A materialized table can go back out as Parquet. Because the rows are sorted by `variant_id`, DuckDB's per-row-group min/max statistics let a reader skip almost all of the file, the same way the published tables skip by `id`:

```sql
COPY scv_by_variant TO 'scv_by_variant.parquet' (FORMAT parquet);
```

The same layout is what would make per-variant queries practical over the network, where every row group read is a request.

## Errors that look worse than they are { #confusing-errors }

**`Parser Error: syntax error at or near "end"`**: `end` is a reserved word, and `location` has a column named `end`. Quote it: `"end"`. The same error with `"name"` means a column alias without `AS`: many words used as column names in these tables are reserved, so `SELECT name name FROM 'condition.parquet'` fails while `SELECT name AS name …` works. The same goes for `type`, `value`, `system`, `key`, `rows` and `year`. Always write `AS`.

**`Conversion Error: … can't be cast to the destination type STRUCT(…)`**: comparing a `STRUCT` column to text, as in `WHERE classification = 'Pathogenic'`. Name the field: `classification.name`. See [Reading a `STRUCT` column](table-anatomy.md#reading-a-struct-column).

**`Binder Error: Referenced column "conditionQualifier" not found`** or **`schema mismatch in glob`**: reading `proposition*.parquet` without `union_by_name = true`. The four tables have [different columns](tables.md#proposition-columns).

**Text that prints `\n`**: the DuckDB command line shows a newline inside a value as `\n`, so a list joined with newlines looks broken. The data is fine. Switch to `.mode line` to see the value as written, or join with `'; '` instead.

**`HTTP 429 Too Many Requests`**: a remote query read too many row groups; see [Local or remote](#local-or-remote).
