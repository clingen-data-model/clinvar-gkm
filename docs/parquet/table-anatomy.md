# Anatomy of a Table

!!! info "Release"
    Outputs and counts on this page are from the **2026-10-31 release**, built with `gkm-bundle-parquet` 2.0.0.
    They change with every release; re-run a query to get today's numbers.

!!! note "One bundle section, one table"
    The JSON bundle is organized into 20 named **sections** (`variation`, `scv`, `condition`, …). The Parquet release turns each section into exactly one **table**, stored as one file (`variation.parquet`, `scv.parquet`, `condition.parquet`, …), with one row per record in that section. This track calls them tables.

All 20 tables are generated from the bundle's schema by the same rules, so what you learn reading one applies to the rest. This page covers what they have in common: how to read a table's schema, the `id` column, the column types and how to reach inside nested ones, extensions, getting a whole record back, and which columns to leave alone. The [column reference](tables.md#column-reference) then documents each table individually in that shared shape. Everything here stays inside one table at a time; no joins.

Every query here except the last two runs in the [live console](index.md#run-a-query-now). Paste it in and replace `'<table>.parquet'` with `'{BASE}/<table>.parquet'`. The last two scan all of `scv.parquet`, so they belong on your machine.

## Read the schema first

`DESCRIBE` lists a table's columns and types. It reads only the file's footer, so it is instant even on the largest table, locally or over the network.

```sql
DESCRIBE SELECT * FROM 'condition.parquet';
```

```text
column_name    column_type
id             VARCHAR
type           VARCHAR
name           VARCHAR
aliases        VARCHAR[]
conceptType    VARCHAR
primaryCoding  STRUCT("name" VARCHAR, "system" VARCHAR, code VARCHAR, iris STRUCT(id VARCHAR, section VARCHAR)[])
mappings       STRUCT(coding STRUCT("system" VARCHAR, code VARCHAR, iris STRUCT(id VARCHAR, section VARCHAR)[]), relation VARCHAR)[]
```

Column names are the bundle's own field names, camelCase included. The types you will meet:

| Type | What it holds | How to read it |
| --- | --- | --- |
| `VARCHAR`, `BIGINT`, `BOOLEAN` | A plain value | Use the column directly |
| `VARCHAR[]` | A **list** of values | `aliases[1]` (1-based), `len(aliases)`, `unnest(aliases)` for one row per element |
| `STRUCT(...)` | A **record** with named fields | `primaryCoding.code` |
| `STRUCT(...)[]` | A list of records | `unnest(mappings)`, then dot into each one |
| `STRUCT(id, section)[]` | A list of **references** | `m.id` is the referenced row's id, `m.section` its table |

Run the same `DESCRIBE` on `scv.parquet` and most of its columns are `STRUCT`s: `classification`, `strength`, `quality`, `specifiedBy`, `contributions`, `extensions`. The full list for every table, with a description of each column, is in the [column reference](tables.md#column-reference).

## Every table has an `id`

Every row has an `id`, and its shape tells you which table it belongs to (`clinvar.trait:2645` is a condition, `clinvar:51592` a variant; see [Ids tell you where to look](tables.md#ids-tell-you-where-to-look)). Ids are how tables connect, and they are how you look up one row. Rows are stored sorted by `id`, so a lookup by id reads only a small part of the file.

A column that refers to another row holds that row's bare id. When it could refer to more than one table, a `_section` column next to it says which: `object` and `object_section` on a proposition, `proposition` and `proposition_section` on a statement.

## Reading a `STRUCT` column

The most common first mistake is to treat a `STRUCT` column as text. In `scv.parquet`, `classification` is a whole record (a GA4GH *MappableConcept*), not a string:

```sql
SELECT count(*) FROM 'scv.parquet' WHERE classification = 'Pathogenic';
```

```text
Conversion Error: Type VARCHAR with value 'Pathogenic' can't be cast to the destination type
STRUCT("type" VARCHAR, "name" VARCHAR, "extensions" STRUCT("name" VARCHAR, value_string VARCHAR)[], conceptType VARCHAR, primaryCoding STRUCT("system" VARCHAR, code VARCHAR))
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
id                  name             medgen_cui  first_alias              n_aliases
clinvar.trait:2645  Marfan syndrome  C0024796    MARFAN SYNDROME, TYPE I          5
```

## Extensions { #extensions }

Many records carry an `extensions` list: named ClinVar attributes that the GA4GH models have no field for. Each element has a `name` and a value, and the value can be text on one extension and a list of records on another. So an extension's value is spread over **one column per kind of value**, named `value_<kind>`, and in each element exactly one of them is set:

| Slot | Holds | Examples |
| --- | --- | --- |
| `value_string` | text | `clinvarReviewStatus` on `vcv` and `rcv`; `clinvarScvReviewStatus`, `submissionLevel` on `scv`; `clinvarVariationType` on `variation`; `geneContextSource` on the gene context |
| `value_string_array` | a list of text | `submittedGeneSymbols` on the gene context |
| `value_boolean` | true or false | on a citation's extensions |
| `value_object` | one record | `submittedCondition`, `submittedConditionSet` on `scv` and `evidenceLine` |
| `value_object_array` | a list of records | `clinvarHgvsList`, `clinvarGeneList` on `variation`; `additionalClinvarMethodCitations` on `scv.specifiedBy` |

A table's `extensions` has only the slots its extensions use. Pick an extension by name with a list comprehension, then read the slot:

```sql
SELECT id,
       [e.value_string FOR e IN extensions IF e.name = 'clinvarReviewStatus'][1] AS review_status
FROM 'vcv.parquet'
WHERE id LIKE 'VCV000051592.%'
  AND NOT regexp_matches(id, '-(PG|EP|CP|NOCP|NOCL|FLAG)(-T[0-9])?$');
```

```text
id                       review_status
VCV000051592.122-G-NP    no classification provided
VCV000051592.122-G-PATH  reviewed by expert panel
```

When two extensions share a `value_object_array` slot, the slot's record has the fields of both, and the fields the other one uses are NULL: `clinvarGeneList` entries fill `gene`, `relationship_type` and `source`; `clinvarHgvsList` entries fill `nucleotideExpression`, `proteinExpression`, `molecularConsequence` and the MANE flags.

A few deeply nested positions are kept as **JSON text** instead, because the schema allows anything there. The one you are likely to meet is a submitted condition set's members, `value_object.concepts`, a list of JSON strings. Read them with DuckDB's JSON functions:

```sql
SELECT s.id,
       json_extract_string(c, '$.medgen_id')        AS medgen_id,
       json_extract_string(c, '$.normalized_match') AS condition_id
FROM 'scv.parquet' s,
     unnest([e.value_object.concepts FOR e IN s.extensions IF e.name = 'submittedConditionSet'][1]) AS t(c)
WHERE s.id = 'clinvar.submission:SCV000893709.1';
```

```text
id                                 medgen_id  condition_id
clinvar.submission:SCV000893709.1  C3280096   clinvar.trait:9587
clinvar.submission:SCV000893709.1  C2673520   clinvar.trait:5535
clinvar.submission:SCV000893709.1  C3469186   clinvar.trait:9582
clinvar.submission:SCV000893709.1  C0162532   clinvar.trait:3370
clinvar.submission:SCV000893709.1  C0268323   clinvar.trait:9601
clinvar.submission:SCV000893709.1             clinvar.trait:222
```

## The whole record { #whole-records }

There is no column holding the row's JSON. The typed columns **are** the record: every field of every bundle record is in a column. To get a row back as JSON, use `to_json`:

```sql
SELECT to_json(a) AS record
FROM 'allele.parquet' a
WHERE id = 'ga4gh:VA.Apas_jvqBJU7l4DGHGlvTGRY3BBh-UR9';
```

```text
record
{"id":"ga4gh:VA.Apas_jvqBJU7l4DGHGlvTGRY3BBh-UR9","type":"Allele","name":"NC_000013.11:g.32338445A>C","digest":"Apas_jvqBJU7l4DGHGlvTGRY3BBh-UR9","expressions":[{"syntax":"spdi","value":"NC_000013.11:32338444:A:C"},{"syntax":"hgvs.g","value":"NC_000013.11:g.32338445A>C"},{"syntax":"gnomad","value":"13-32338445-A-C"}],"location":"ga4gh:SL.Gga5J2ccypatzYD5tBIeQEU9K4sPXc6J","state":{"type":"LiteralSequenceExpression","length":null,"sequence":"C","repeatSubunitLength":null}}
```

Two things differ from the bundle record. References are bare ids where the bundle has a pointer (`"location": "ga4gh:SL.…"` for `"#/location/ga4gh:SL.…"`), and a field the record doesn't have is written as `null` (`"length": null`). For the records exactly as published, rebuild the bundle from the tables with [`gkm-bundle-parquet rebuild`](build-your-own.md#rebuild-the-bundle), or download the JSON bundle.

## Never `SELECT *` on a big table

Parquet stores each column separately and compressed. A query reads only the columns it names, so naming fewer columns means reading less. `SELECT *` names them all.

Here is `scv.parquet` built from the 2026-10-31 weekly delta (33,417 submissions), by column:

| Column | On disk | In memory (uncompressed) |
| --- | ---: | ---: |
| `description` | 2.74 MB | 15.17 MB |
| `extensions` | 0.99 MB | 6.82 MB |
| `id` | 0.18 MB | 1.24 MB |
| `proposition` | 0.17 MB | 0.70 MB |
| everything else | 0.35 MB | 0.90 MB |
| **whole table** | **4.44 MB** | **24.82 MB** |

The table is more than five times larger once decompressed, and most of that is the free-text `description` and the `extensions`. The full release's `scv.parquet` is 784 MB on disk; `SELECT * FROM 'scv.parquet'`, or loading it whole into pandas, asks for all of it, decompressed. In the browser console the tab runs out of memory.

The fix is always the same: **name the columns you need**. The sizes of every table are in the [column reference](tables.md#column-reference).

## A worked example: what do submitters say? { #a-worked-example-what-do-submitters-say }

Count every SCV by its classification. The query reads only the `classification` fields instead of the whole file, so it finishes in a fraction of a second on downloaded files. Over the network it needs a request per row group, which trips the console's rate limit, so run this one locally.

```sql
SELECT classification.name AS classification, count(*) AS n
FROM 'scv.parquet'
GROUP BY ALL
ORDER BY n DESC;
```

It returns **44** distinct values in 2026-10-31, and some of them are the same call written differently:

```text
classification            n
Uncertain significance    3,369,435
Likely benign             1,920,932
Benign                      649,701
Pathogenic                  535,920
Likely pathogenic           293,502
Uncertain Significance       32,732
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
uncertain significance  ACMG Guidelines, 2015                               3,401,911
likely benign           ACMG Guidelines, 2015                               1,941,309
benign                  ACMG Guidelines, 2015                                 653,132
pathogenic              ACMG Guidelines, 2015                                 538,734
likely pathogenic       ACMG Guidelines, 2015                                 302,236
not provided            ClinVar                                                29,122
…
likely oncogenic        ClinGen/CGC/VICC Guidelines for Oncogenicity, 2022      1,321
tier 1                  AMP/ASCO/CAP (AAC) Guidelines, 2017                     1,018
…
```

That collapses the 44 spellings into **34** code–guideline pairs. The normalization goes beyond case: the one SCV that says `no known pathogenicity` is counted under `benign`.

Next: the [20 tables](tables.md) and how they fit together, then [joining them](joining.md).
