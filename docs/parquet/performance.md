# Working at Scale

!!! info "Release"
    Timings and measured results on this page are from the **2026-10 monthly release** (published 14 Oct 2026), measured with DuckDB 1.5 on a laptop. File and column sizes are from the **2026-10-18 release**. Your numbers will differ with the release and your machine.

Nine tables are over 500 MB: `variation` (3.9 GB), `scv` (3.2 GB), `propositionPathogenicity` (1.5 GB), `allele` (1.1 GB), `location`, and the RCV and VCV statements and evidence lines (0.5–0.9 GB each). The other thirteen are each about 11 MB or less. A handful of habits keeps queries over the big ones fast on a laptop.

## Name your columns { #name-your-columns }

Parquet stores each column separately, and a query reads only the columns it names. This is the single biggest lever you have. In `scv.parquet` the `data` column is 2.1 GB of the 3.2 GB on disk and 15.7 GB of the 21 GB in memory ([the breakdown](table-anatomy.md#never-select-on-a-big-table)). A query that leaves it out reads a quarter of the file; one that names two small fields reads almost none of it.

To see where any table's bytes are, ask its metadata. This reads only the file footer:

```sql
SELECT split_part(path_in_schema, ',', 1)          AS col,
       round(sum(total_compressed_size)   / 1e9, 2) AS gb_on_disk,
       round(sum(total_uncompressed_size) / 1e9, 2) AS gb_in_memory
FROM parquet_metadata('scv.parquet')
GROUP BY 1
ORDER BY gb_in_memory DESC;
```

The same holds for fields inside a `STRUCT`: `classification.name` reads that one field, not the whole `classification` record. Selecting `*` or the struct as a whole reads everything.

## Reach into nested lists without `unnest` { #nested-lists }

Several columns are lists of records: `variation.extensions`, `variation.members`, `scv.contributions`, `scv.reportedIn`. To filter on something inside them, prefer a **list comprehension**, `[x.field FOR x IN list IF …]`, over `unnest`. `unnest` turns every list element into its own row before filtering; a comprehension filters each list in place.

The difference is large. Finding the variants in one gene by filtering `variation.extensions` takes **4 s and 1.5 GB** as a comprehension and **37 s and 2.5 GB** with `unnest`, for the same 5,942 variants. The [gene rollup recipe](recipes.md#gene-rollup) shows the comprehension.

Use comprehensions rather than lambda functions (`list_filter(l, x -> …)`). DuckDB 1.5 deprecates that arrow syntax, and the replacement (`lambda x: …`) is too new for the browser console's engine. Comprehensions work in both.

## Join on a plain equality { #equi-joins }

DuckDB joins two big tables fast, with a **hash join**, when the `ON` clause is one equality between them. Add a second condition (`ON p.object_type = 'condition' AND c.id = p.object_id`), or join through a function (`ON list_contains(v.members, a.id)`), and DuckDB 1.5 plans a **nested-loop join** instead, which compares row against row and runs for over an hour on `propositionPathogenicity`. Fold the extra condition into the key, `ON c.id = CASE WHEN p.object_type = 'condition' THEN p.object_id END`, or `unnest` the list in a subquery and join on the plain column. [Seam B](joining.md#seam-b-proposition-condition-or-conditionset) shows the first; [Find the variant](recipes.md#find-the-variant) shows the second. Put `EXPLAIN` in front of a query to check before you run it: `HASH_JOIN` is the fast kind; `NESTED_LOOP_JOIN`, `BLOCKWISE_NL_JOIN` and `PIECEWISE_MERGE_JOIN` are the slow kinds.

## Local or remote { #local-or-remote }

DuckDB reads Parquet over HTTPS with **range requests**: it fetches the file's footer first, then only the byte ranges of the row groups and columns a query needs. That makes some remote queries as cheap as local ones and others impossible:

| Over the network | Requests | Works? |
| --- | --- | --- |
| `DESCRIBE`, `count(*)`, `parquet_metadata(…)` | footer only | yes, in under a second on any table |
| `LIMIT n` without a filter | footer + first row group | yes |
| Any query on a small table (`condition`, `gene`, `submitter`, `therapy`, …) | a few | yes |
| A filter, `GROUP BY` or join over a big table | one per row group per column; 55 row groups in `scv`, about 223 in `propositionPathogenicity` | **slowly**: 10–35 s per query, reading hundreds of MB; download for repeated or heavier work |

The published files are not sorted by any lookup key, so even a filter for a single variant or SCV has to read every row group of the filtered column. The CDN in front of `data.clinvar-gkm.org` allows **250 requests per 10 seconds** per client IP and blocks for 10 seconds past that (HTTP 429). From the command line, single-table scans and two-table joins on the big tables now complete within it (a `GROUP BY` over all of `scv` in about 30 s; a variant's PubMed ids in about 25 s), but each reads hundreds of megabytes, so repeated or larger work belongs on a downloaded copy.

The rule: **query remotely to explore, download to analyze.** Download the tables a question needs once (see [Start Here](index.md#put-the-file-on-your-machine)), and every query on this page and in [Recipes](recipes.md) runs in seconds.

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

A `GROUP BY` on `scv.description`, a free-text column with millions of distinct values, fails as above with a 1 GB memory limit. With `threads = 2` and `preserve_insertion_order = false` added, it finishes in under 3 seconds within the same limit.

For work you repeat, open a database file (`duckdb clinvar-gkm.duckdb`) rather than an in-memory session. Tables you create there persist, which is what makes the next section possible.

## Materialize the joins you repeat { #materialize-join-tables }

Statements and propositions live in separate tables. An SCV row holds its classification but not the variant or condition it is about. Those are on the proposition, in one of four tables, each spelling the columns slightly differently. So any question about statements by **subject** (a variant), **object** (a condition, tumor type or therapy) or **qualifier** (gene context, mode of inheritance, penetrance) has to join two multi-GB tables first.

Paying for that join on every query is slow locally, and slower over the network: `scv.parquet` has no variant column, so a lookup for one variant must read every row group of the file. From the command line that takes about 25 seconds and hundreds of megabytes per query; in the browser's [live console](index.md#run-a-query-now) it can also exhaust memory or trip the CDN's rate limit (**HTTP 429**).

The fix is to run the join **once**, store the result as a table sorted by the column you look up most, and query that table instead. DuckDB has no `CREATE MATERIALIZED VIEW`; `CREATE TABLE … AS SELECT` in a database file does the same job. You refresh it by re-running the script when you download a new release.

### Build it

Download the four proposition tables and `scv.parquet` (see [Start Here](index.md#put-the-file-on-your-machine)), then run this in the same directory. It writes a database file, `clinvar-gkm.duckdb`, that persists between sessions:

```bash
duckdb clinvar-gkm.duckdb < materialize.sql
```

```sql
-- materialize.sql
SET preserve_insertion_order = false;   -- lets DuckDB build large tables with less memory

-- 1. One proposition table: the four tables share one column schema, so one glob reads them all.
CREATE OR REPLACE TABLE prop AS
SELECT id, type AS proposition_type, predicate,
       subject_variant_id AS variant_id, object_id, object_type,
       gene_context_name, gene_context_id, mode_of_inheritance, penetrance, condition_qualifier_id
FROM read_parquet('proposition*.parquet');

-- 2. SCV statements with their proposition's subject, object and qualifiers inlined,
--    sorted by variant so a lookup by variant touches one small slice of the table.
CREATE OR REPLACE TABLE scv_by_variant AS
SELECT p.variant_id, p.object_id, p.object_type, p.proposition_type, p.predicate,
       p.gene_context_name, p.gene_context_id, p.mode_of_inheritance, p.penetrance, p.condition_qualifier_id,
       s.id                     AS scv_id,
       s.classification.name    AS classification,
       s.quality.name           AS submission_level,
       s.direction,
       [c.contributor FOR c IN s.contributions IF c.activityType = 'submitted'][1] AS submitter_id,
       [r.pmid FOR r IN s.reportedIn IF r.pmid IS NOT NULL]                        AS pmids
FROM 'scv.parquet' s
JOIN prop p ON p.id = s.proposition_id
ORDER BY p.variant_id, s.id;
```

The build takes about **30 seconds** and peaks near **5 GB** of memory. Every one of the 6,735,011 SCVs finds its proposition, and the database file comes to about 650 MB. Only the columns the questions below need are carried over. Add others, such as `s.description` or `s.specifiedBy.name`, the same way.

### Query it

Each of these returns in about **10 ms**, where the same question against the raw Parquet files means a multi-GB join.

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
JOIN prop p ON p.id = v.proposition_id
ORDER BY p.variant_id, v.id;
```

It builds in about 6 seconds and holds all 9,079,449 VCV statements. For `rcv`, swap in `rcv.parquet`.

### Share it as a sorted Parquet file

A materialized table can go back out as Parquet. Because the rows are sorted by `variant_id`, DuckDB's per-row-group min/max statistics let a reader skip almost all of the file:

```sql
COPY scv_by_variant TO 'scv_by_variant.parquet' (FORMAT parquet);
```

The result is about **107 MB**, versus 3.2 GB for `scv.parquet`. A `WHERE variant_id = 'clinvar:10'` lookup reads **1 of its 55 row groups**. The same layout is what would make per-variant queries practical over the network, where every row group read is a request.

## Errors that look worse than they are { #confusing-errors }

**`Parser Error: syntax error at or near "name"`**: a column alias without `AS`. Many words used as column names in these tables are reserved in SQL, so `SELECT value->>'name' name` fails while `SELECT value->>'name' AS name` works. The same goes for `type`, `data`, `key`, `value`, `rows`, `names`, `target`, `role`, `end` and `year`. Always write `AS`.

**`Conversion Error: … can't be cast to the destination type STRUCT(…)`**: comparing a `STRUCT` column to text, as in `WHERE classification = 'Pathogenic'`. Name the field: `classification.name`. See [Reading a `STRUCT` column](table-anatomy.md#reading-a-struct-column).

**Text that prints `\n`**: the DuckDB command line shows a newline inside a value as `\n`, so a list joined with newlines looks broken:

```text
│ GM1 gangliosidosis\nMucopolysaccharidosis, MPS-IV-B │
```

The data is fine. Switch to `.mode line` to see the value as written, or join with `'; '` instead.

**`HTTP 429 Too Many Requests`**: a remote query read too many row groups; see [Local or remote](#local-or-remote).
