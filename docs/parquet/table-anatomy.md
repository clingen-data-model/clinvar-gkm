# Anatomy of a Table

!!! info "Release"
    Outputs, sizes and counts on this page are from the **2026-10 monthly release** (published 14 Oct 2026). They change with every release; re-run a query to get today's numbers.

!!! note "One bundle section, one table"
    The JSON bundle is organized into 22 named **sections** (`variation`, `scv`, `condition`, …). The Parquet release turns each section into exactly one **table**, stored as one file (`variation.parquet`, `scv.parquet`, `condition.parquet`, …), with one row per object in that section. This track calls them tables.

All 22 tables are built the same way, so what you learn reading one applies to the rest. This page covers what they have in common: how to read a table's schema, the `id` and `data` columns, the column types and how to reach inside nested ones, and which columns to leave alone. The [column reference](tables.md#column-reference) then documents each table individually in that shared shape. Everything here stays inside one table at a time; no joins.

Every query here except the last runs in the [live console](index.md#run-a-query-now). Paste it in and replace `'<table>.parquet'` with `'{BASE}/<table>.parquet'`. The last one scans a 3 GB table, so it belongs on your machine.

## Read the schema first

`DESCRIBE` lists a table's columns and types. It reads only the file's footer, so it is instant even on the largest table, locally or over the network.

```sql
DESCRIBE SELECT * FROM 'condition.parquet';
```

```text
column_name    column_type
id             VARCHAR
type           VARCHAR
conceptType    VARCHAR
name           VARCHAR
aliases        VARCHAR[]
primaryCoding  STRUCT("name" VARCHAR, code VARCHAR, "system" VARCHAR, iris VARCHAR[])
mappings       STRUCT(coding STRUCT("name" VARCHAR, code VARCHAR, "system" VARCHAR, iris VARCHAR[]), relation VARCHAR)[]
```

The types you will meet:

| Type | What it holds | How to read it |
| --- | --- | --- |
| `VARCHAR`, `BIGINT` | A plain value | Use the column directly |
| `VARCHAR[]` | A **list** of values | `aliases[1]` (1-based), `len(aliases)`, `unnest(aliases)` for one row per element |
| `STRUCT(...)` | A **record** with named fields | `primaryCoding.code` |
| `STRUCT(...)[]` | A list of records | `unnest(mappings)`, then dot into each one |

Run the same `DESCRIBE` on `scv.parquet` and most of its columns are `STRUCT`s: `classification`, `strength`, `quality`, `specifiedBy`, `contributions`, `extensions`. The full list for every table, with a description of each column, is in the [column reference](tables.md#column-reference).

## Every table has an `id`

Every row has an `id`, and its shape tells you which table it belongs to (`clinvar.trait:2645` is a condition, `clinvar:51592` a variant; see [Ids tell you where to look](tables.md#ids-tell-you-where-to-look)). Ids are how tables connect, and they are how you look up one row.

Two tables spell it differently: `therapy` and `therapyGroup` have just a `key` column (the id) and a `value` column (the JSON object).

## The `data` column holds everything else

Most tables also have a `data` column: the row's complete JSON object as a string. The typed columns are a fast subset of it. Anything without a typed column is still in `data`, and `->>` reaches into it with a JSON path:

```sql
-- The alternate base and the gnomAD-style id of the first five alleles; neither has a typed column
SELECT id,
       name,
       data->>'$.state.sequence' AS alt,
       [e.value FOR e IN CAST(data->'$.expressions' AS STRUCT(syntax VARCHAR, value VARCHAR)[])
                IF e.syntax = 'gnomad'][1] AS gnomad
FROM 'allele.parquet'
LIMIT 5;
```

```text
id                                         name                         alt  gnomad
ga4gh:VA.KqJix9Wg3wCbUTjTt8CLY4TXToP2NyoC  NC_000016.10:g.376236G>A     A    16-376236-G-A
ga4gh:VA.B4RiRl78A-gSU0a3yOz_aLl2jR7qxpdW  NC_000002.12:g.107882735G>A  A    2-107882735-G-A
ga4gh:VA.E8L_Ltq8nC8OPjbEk1jasgkF9SXDKEkf  NC_000017.11:g.8173472G>A    A    17-8173472-G-A
…
```

`->>` returns text, and `->` returns JSON that you can `CAST` to a typed list or struct, as `expressions` is here. `condition` is the exception: it has no `data` column.

## Reading a `STRUCT` column

The most common first mistake is to treat a `STRUCT` column as text. In `scv.parquet`, `classification` is a whole record (a GA4GH *MappableConcept*), not a string:

```sql
SELECT count(*) FROM 'scv.parquet' WHERE classification = 'Pathogenic';
```

```text
Conversion Error: Type VARCHAR with value 'Pathogenic' can't be cast to the destination type
STRUCT("type" VARCHAR, conceptType VARCHAR, "name" VARCHAR, primaryCoding STRUCT(code VARCHAR, "system" VARCHAR), …)
```

Name the field you want with a dot:

```sql
SELECT id,
       classification.name                AS classification,   -- what the submitter wrote
       classification.primaryCoding.code  AS code,             -- the normalized value
       quality.name                       AS submission_level
FROM 'scv.parquet'
LIMIT 5;
```

The same goes for `strength`, `quality`, and `condition.primaryCoding`:

```sql
SELECT id, name, primaryCoding.code AS medgen_cui, aliases[1] AS first_alias, len(aliases) AS n_aliases
FROM 'condition.parquet'
WHERE name = 'Marfan syndrome';
```

```text
id                  name             medgen_cui  first_alias                   n_aliases
clinvar.trait:2645  Marfan syndrome  C0024796    FBN1-Related Marfan Syndrome  5
```

## Never `SELECT *` on a big table

This is the one warning on this page that costs real time if ignored. Parquet stores each column separately and compressed. A query reads only the columns it names, so naming fewer columns means reading less. `SELECT *` names them all, and on a big table "all" is mostly the `data` column.

Here is `scv.parquet`, by column:

| Column | On disk | In memory (uncompressed) |
| --- | ---: | ---: |
| `data` | 2.04 GB | **15.38 GB** |
| `description` | 0.40 GB | 2.17 GB |
| `extensions` | 0.37 GB | 1.54 GB |
| `classification` | 0.12 GB | 0.91 GB |
| `id` | 0.06 GB | 0.25 GB |
| everything else | 0.11 GB | 0.27 GB |
| **whole table** | **3.10 GB** | **20.5 GB** |

A 3 GB file becomes about **20 GB** once decompressed, three quarters of it the `data` column. `SELECT * FROM 'scv.parquet'`, or loading it whole into pandas, asks for all of it. On a laptop the machine swaps until it is unusable or the process is killed; in the browser console the tab runs out of memory.

The fix is always the same: **name the columns you need**, and leave `data` out unless you need something only it holds. The sizes of every table are in the [column reference](tables.md#column-reference).

## A worked example: what do submitters say?

Count every SCV by its classification. The query reads only the `classification` fields (well under 1 MB on disk) instead of the whole 3 GB file, so it finishes in a fraction of a second on downloaded files. Over the network it needs a request per row group, which trips the console's rate limit, so run this one locally.

```sql
SELECT classification.name AS classification, count(*) AS n
FROM 'scv.parquet'
GROUP BY ALL
ORDER BY n DESC;
```

It returns **44** distinct values, and some of them are the same call written differently:

```text
classification            n
Uncertain significance    3,293,960
Likely benign             1,881,719
Benign                      648,029
Pathogenic                  517,828
Likely pathogenic           282,443
Uncertain Significance       32,593
…
pathogenic                    2,792
…
PATHOGENIC                       22
```

`classification.name` is the text the submitter sent, so case varies. Group by the normalized `primaryCoding.code` instead, and keep its `system` (the guideline the classification follows), because the same code can come from different guidelines:

```sql
SELECT classification.primaryCoding.code   AS code,
       classification.primaryCoding.system AS guideline,
       count(*) AS n
FROM 'scv.parquet'
GROUP BY ALL
ORDER BY n DESC;
```

```text
code                    guideline                                           n
uncertain significance  ACMG Guidelines, 2015                               3,326,410
likely benign           ACMG Guidelines, 2015                               1,902,052
benign                  ACMG Guidelines, 2015                                 651,462
pathogenic              ACMG Guidelines, 2015                                 520,642
likely pathogenic       ACMG Guidelines, 2015                                 290,567
not provided            ClinVar                                                29,121
…
tier 1                  AMP/ASCO/CAP (AAC) Guidelines, 2017                     1,018
likely oncogenic        ClinGen/CGC/VICC Guidelines for Oncogenicity, 2022        998
…
```

That collapses the 44 spellings into **34** code–guideline pairs. The normalization goes beyond case: the one SCV that says `no known pathogenicity` is counted under `benign`.

Next: the [22 tables](tables.md) and how they fit together, then [joining them](joining.md).
