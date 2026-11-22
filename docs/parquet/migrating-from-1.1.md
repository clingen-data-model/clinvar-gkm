# Moving from the 1.1 Tables to 2.0

!!! info "Release"
    Sizes and row counts on this page are from the **2026-10-31 release** for the 2.0 tables (built as schema 1.2.0)
    and the **2026-10-24 release** for the 1.1 tables, the last set the 1.1 line published.

From release **1.2.0**, the published Parquet is built by [`gkm-bundle-parquet`](https://github.com/clingen-data-model/gkm-bundle-parquet)
2.0.0 directly from the JSON bundle, and published at `v1/1.2/parquet/`. It replaces the set exported from BigQuery
for the 1.1 line, at `v1/1.1/parquet/`. This page calls them the **2.0 tables** and the **1.1 tables**. The
records are the same; the table layout is not. Every query written for the 1.1 tables needs a review, and most
need small rewrites.

!!! note "Prerequisites"
    - **[DuckDB CLI](https://duckdb.org/docs/installation/)**, tested with **1.5.4**. No extension is needed.
    - **The 2.0 tables**: download all 20 into one folder ([Parquet Files → Download](../data-access/parquet.md#download))
      and start `duckdb` in that folder. The queries name each table by its file name (`'scv.parquet'`) and read
      the four proposition tables with the glob `proposition*.parquet`.
    - **The 1.1 tables**, for the queries marked `-- 1.1` only: the same file names under
      `https://data.clinvar-gkm.org/v1/1.1/parquet/` while that set is still served (see [Timeline](#timeline)),
      in a folder of their own. The set is 13.2 GB; `scv.parquet` and `variation.parquet` are 3 to 4 GB each.
    - **[uv](https://docs.astral.sh/uv/getting-started/installation/)**, for the `rebuild` example only. It reads
      the whole 2.0 set and writes a bundle about the size of the published one (about 5 GB compressed).

---

## Who is affected

- **Parquet users: yes.** Two tables are gone, almost every column outside the statement classifications is
  renamed or reshaped, and the `data` column is gone. A query against the 1.1 tables fails on the 2.0 tables
  with a binder error (`Referenced column "proposition_id" not found`), not with wrong numbers, so a broken
  query is easy to find.
- **JSON bundle users: no.** The bundle is the record, and the Parquet change doesn't touch it. The bundle
  changes in 1.2.0 (the narrowed schema profiles, and aggregate `primaryCoding`, `strength` and `direction`) are
  in the [changelog](../reference/changelog.md#120).
- **Copies you already downloaded keep working.** A 1.1 table on your disk is unchanged; it simply stops being
  refreshed.

---

## What stays the same

- **One row per bundle record, one table per bundle section**, named after the section (`scv.parquet`,
  `variation.parquet`, …). Every id is unchanged: `clinvar:51592`, `clinvar.submission:SCV000056982.2`,
  `VCV000051592.122-G-PATH-CP` and every other key is the same string in both sets.
- **The statement columns most queries use.** `scv`, `vcv` and `rcv` keep `classification`, `strength`,
  `quality` and `direction`, read the same way (`classification.name`, `classification.primaryCoding.code`,
  `quality.name`). `scv` keeps `description`, `contributions`, `reportedIn` and `specifiedBy`, and every
  statement keeps `proposition_section`. `condition` keeps `name`, `aliases`, `conceptType`, `primaryCoding` and
  `mappings`. Columns are matched by name, so their changed order inside a STRUCT doesn't matter.
- **One dataset, overwritten every release**, with a `manifest.json` beside it naming the release it was built
  from ([Parquet Files](../data-access/parquet.md)).
- **DuckDB, pandas, polars, R and Spark read both sets the same way.** Only column names and types change.

---

## At a glance

| | 1.1 tables | 2.0 tables |
| --- | --- | --- |
| Built by | BigQuery `EXPORT DATA` from the pipeline's tables | [`gkm-bundle-parquet`](https://github.com/clingen-data-model/gkm-bundle-parquet) 2.0.0, from the published bundle |
| Published at | `v1/1.1/parquet/` | `v1/1.2/parquet/` |
| Tables | 22 | 20: one per bundle section |
| Evidence lines | `evidenceLine` (SCV), `vcv_evidenceLine`, `rcv_evidenceLine` | `evidenceLine`, all three kinds |
| Column names | snake_case derived columns (`proposition_id`, `subject_variant_id`, `location_id`) | the bundle's own property names (`proposition`, `subject`, `location`) |
| `data` column (the record as a JSON string) | on every table (`value` on `therapy`, `therapyGroup`) | none: every property is a typed column, and the tables rebuild the bundle's records exactly |
| References | bare ids in typed columns; `#/…` pointers inside `data` | bare ids, plus a `<column>_section` column where the target table varies |
| Qualifiers | flattened (`gene_context_id`, `mode_of_inheritance`, `penetrance`) | whole STRUCTs (`geneContextQualifier`, `modeOfInheritanceQualifier`, `penetranceQualifier`) |
| The four proposition tables | one shared column schema | each table has only the columns its propositions use; read them together with `union_by_name = true` |
| Row order | unsorted | sorted by `id` |
| Size | 13.2 GB (2026-10-24) | 4.6 GB (2026-10-31) |
| Self-description | `manifest.json` | `manifest.json`, `table-spec.json`, and key-value metadata in every file |

---

## Which set do you have?

Any one of these tells them apart:

- **`manifest.json`.** The 1.1 set says `"builder": "BigQuery export"`; the 2.0 set says
  `"builder": "gkm-bundle-parquet 2.0.0"` and `"table_spec_version": "2.0"`.
- **`table-spec.json`.** Only the 2.0 set has one: the compiled table spec, with every column's type,
  derivation and foreign keys.
- **The files themselves.** A 2.0 file carries key-value metadata under the prefix `gkm_bundle_parquet.`; a 1.1
  file has a `data` column (or, for `therapy` and `therapyGroup`, `key` and `value`).

```sql
-- 2.0 tables: one row per entry (tool version, spec version, the bundle's schema version, sha256s, ...)
-- 1.1 tables: no rows
SELECT decode(key) AS key, decode(value) AS value
FROM parquet_kv_metadata('scv.parquet')
WHERE decode(key) LIKE 'gkm_bundle_parquet.%';
```

---

## Timeline

| When | 1.1 tables (`v1/1.1/parquet/`) | 2.0 tables (`v1/1.2/parquet/`) |
| --- | --- | --- |
| Until 1.2.0 is published | the published set (built from 2026-10-24, not rebuilt since) | not published |
| When 1.2.0 is published: `v1/1.2/` starts and `v1/1.1/` is frozen | kept, not rebuilt, until the 2.0 set is published | empty until the set built from the newest 1.2 release is published, shortly after |
| Once the 2.0 set is published | removed: a frozen line keeps no Parquet ([ADR 0008](../decisions/0008-bundles-are-the-public-record.md)) | the one published set, rebuilt every release |

- **The live console** on [Start Here](index.md#run-a-query-now) reads the current line's Parquet, so from the
  moment 1.2.0 is published it reads `v1/1.2/parquet/`. It has no tables to read for the short time until the 2.0
  set is published.
- **To keep the 1.1 tables**, download them before 1.2.0 is published; the advance notice gives the date. They
  are not rebuilt afterwards: they came from BigQuery, not from the bundle.
- **To get tables for an earlier release**, build them from that release's bundle with `gkm-bundle-parquet`
  (see [Build Your Own](build-your-own.md) and [Earlier releases](../data-access/parquet.md#earlier-releases)). The columns come from the bundle's
  schema, so a bundle of schema 1.1.0 gives a wider set than the one this documentation describes, with more
  positions kept as JSON text; a bundle of schema 1.2.0 gives exactly these tables. For the 1.1 line, build with
  ClinVar-GKM's 1.1.0 column set instead: [Parquet for Previous Releases](previous-releases.md).

---

## Tables: 22 become 20

Twenty tables keep their name. Two are gone:

| 1.1 table | 2.0 table | Rows |
| --- | --- | --- |
| `evidenceLine` (SCV evidence lines, somatic clinical impact only) | [`evidenceLine`](tables.md#evidenceLine), ids `clinvar.submission:SCV…` | 1,568 in 1.1 |
| `vcv_evidenceLine` | [`evidenceLine`](tables.md#evidenceLine), ids `VCV…` | 9,376,374 in 1.1 |
| `rcv_evidenceLine` | [`evidenceLine`](tables.md#evidenceLine), ids `RCV…` | 12,157,527 in 1.1 |
| | **one `evidenceLine` table** | **21,620,159** in 2.0 |

The bundle has always held all three kinds in its one `evidenceLine` section; only the 1.1 tables split them.
See [Evidence lines are one table](#evidence-lines-are-one-table).

---

## Column by column

Every 1.1 column, and where it is in the 2.0 tables. A 2.0 column not listed is new. **Gone** means the
column has no 2.0 counterpart because what it held is in other columns. Generated from the published 1.1
footers and the 2.0 table spec, then checked by hand.

### Every table

| 1.1 | 2.0 |
| --- | --- |
| `data` (the record as a JSON string) | **gone**: every property is a typed column; see [No `data` column](#no-data-column) |
| `#/…` pointers inside `data` | bare ids in the typed columns, as before, plus `<column>_section` where the target varies |
| a `Coding`'s `iris` as `VARCHAR[]` (`condition.primaryCoding.iris`, every `mappings[].coding.iris`) | `STRUCT(id, section)[]`: read `iris[1].id` |

### Variant tables

| Table | 1.1 | 2.0 |
| --- | --- | --- |
| `variation` | `members` (`VARCHAR[]`) | `members` (`STRUCT(id, section)[]`): `m.id` is the VRS id, `m.section` its table (`allele`, `copyNumberCount`, `copyNumberChange`) |
| `variation` | `extensions[].value_hgvs_array` | `extensions[].value_object_array` on the `clinvarHgvsList` element |
| `variation` | `extensions[].value_gene_array` | `extensions[].value_object_array` on the `clinvarGeneList` element; `.gene` is still a bare `ncbigene:` id |
| `variation` | `extensions[].value_boolean`, `value_coding` | **gone**: no variation extension has those kinds |
| `variation` | `constraints[].allele`, `constraints[].location` | the same names, plus `allele_section`, `allele_json`, `location_section`, `location_json` |
| `allele` | `location_id` | `location` |
| `allele` | `data->'$.expressions'`, `data->'$.state'` | `expressions` (`STRUCT(syntax, value)[]`), `state` (`STRUCT(type, length, sequence, repeatSubunitLength)`) |
| `copyNumberCount` | `location_id` | `location` |
| `copyNumberChange` | `location_id`, `copy_change` | `location`, `copyChange` |
| `location` | `sequence_reference_id` | `sequenceReference` |
| `location` | `loc_start`, `loc_end` | `start`, `"end"`: `end` is a reserved word, so quote it |
| `location` | `loc_start_min`, `loc_start_max`, `loc_end_min`, `loc_end_max` | `start_min`, `start_max`, `end_min`, `end_max`, with the same meaning |
| `sequenceReference` | `refget_accession`, `molecule_type`, `residue_alphabet` | `refgetAccession`, `moleculeType`, `residueAlphabet` |
| `gene` | `concept_type` | `conceptType`; new: `type`, `primaryCoding` (the NCBI Gene coding) and `mappings` (HGNC) |

### Condition and therapy tables

| Table | 1.1 | 2.0 |
| --- | --- | --- |
| `conditionSet` | `concepts` (`VARCHAR[]`) | `concepts` (`STRUCT(id, section)[]`): `c.section` is `condition` or `conditionSet` |
| `therapy` | `key`, `value`, `concept_type` | `id`, *gone*, `conceptType`; new: `type` |
| `therapyGroup` | `key`, `value`, `membership_operator`, `members` | `id`, *gone*, `membershipOperator`, `concepts` (bare `therapy` ids); new: `type` |

### Proposition tables

| 1.1 | 2.0 |
| --- | --- |
| `subject_variant_id` | `subject` |
| `object_id` | `object` |
| `object_type` | `object_section` (the same values: `condition`, `conditionSet`, `therapy`, `therapyGroup`) |
| `condition_qualifier_id` | `conditionQualifier`, plus `conditionQualifier_section`; `propositionSomaticClinicalImpact` only |
| `gene_context_id` | `'ncbigene:' \|\| geneContextQualifier.primaryCoding.code` |
| `gene_context_name` | `geneContextQualifier.name` |
| `submitted_gene_symbols` | the `submittedGeneSymbols` extension of `geneContextQualifier` (`value_string_array`); NULL, not an empty list, when there is none |
| `gene_context_source` | the `geneContextSource` extension of `geneContextQualifier` (`value_string`) |
| `mode_of_inheritance` | `modeOfInheritanceQualifier.name`; `propositionPathogenicity` and `propositionClinvarCustom` only |
| `penetrance` | `penetranceQualifier.name`; `propositionPathogenicity` and `propositionClinvarCustom` only |

[Qualifiers are STRUCTs](#qualifiers-are-structs) gives the expressions as SQL.

### Statement and evidence-line tables

| Table | 1.1 | 2.0 |
| --- | --- | --- |
| `scv`, `vcv`, `rcv` | `proposition_id` | `proposition` (`proposition_section` is unchanged) |
| `scv`, `vcv`, `rcv` | `has_evidence_lines` | `hasEvidenceLines` |
| `vcv`, `rcv` | `extensions[].value`, `classification.extensions[].value` | `extensions[].value_string`, `classification.extensions[].value_string` |
| `vcv`, `rcv` | `classification` without a coding | `classification.primaryCoding` (`code`, `system`), new in schema 1.2.0 |
| `scv` | `contributions[].date` (`DATE`) | `contributions[].date` (`VARCHAR`, `YYYY-MM-DD`): `CAST(date AS DATE)` for date arithmetic |
| `scv`, `evidenceLine` | `extensions[].value_submitted_condition`, `value_submitted_condition_set` | `extensions[].value_object`, one STRUCT for both; a set's `concepts` are JSON text |
| `scv` | `specifiedBy.extensions[].value_document_array` | `specifiedBy.extensions[].value_object_array` |
| `evidenceLine` | `target_proposition_id` | `targetProposition` |
| `vcv_evidenceLine`, `rcv_evidenceLine` | `evidence_items` (`VARCHAR[]`) | `evidenceLine.hasEvidenceItems` (`STRUCT(id, section)[]`; `section` is `scv`, `vcv` or `rcv`) |
| `vcv_evidenceLine`, `rcv_evidenceLine` | `directionOfEvidenceProvided`, `strengthOfEvidenceProvided` | the same names, on `evidenceLine` |

---

## No `data` column { #no-data-column }

The 1.1 tables kept each record twice: a few typed columns, and the whole record as a JSON string in `data`.
The 2.0 tables give **every property of the record its own typed column** or STRUCT field, at any depth, and
drop `data`. They lose nothing: `gkm-bundle-parquet` rebuilds the bundle's records from the columns alone, and
the build checks every row against its source record before it writes the file.

What you read from `data` before is now a column:

```sql
-- The 1.1 tables had only data->>'$.state.sequence'
SELECT id,
       state.sequence AS alt,
       [e.value FOR e IN expressions IF e.syntax = 'gnomad'][1] AS gnomad
FROM 'allele.parquet'
LIMIT 3;
```

When you need JSON:

- **One column or STRUCT as JSON:** `to_json(classification)`, or `json_object('id', id, 'name', name)` for
  several columns. The result is JSON built from the columns: references are bare ids, not `#/…` pointers,
  extension values sit in their `value_<kind>` slot, and absent fields appear as `null`. It is not the bundle
  record.
- **The bundle's own records:** read the bundle, or rebuild it from a full set of tables:

    ```bash
    # run from the folder that holds clinvar-gkm-parquet/, the 20 tables and manifest.json
    curl -f -o clinvar-gkm-parquet/table-spec.json \
      "https://data.clinvar-gkm.org/v1/1.2/parquet/table-spec.json"
    uvx gkm-bundle-parquet@2.0.0 rebuild clinvar-gkm-parquet/ -o rebuilt.json.gz
    ```

    `rebuild` needs every table and the `manifest.json` and `table-spec.json` beside them. It writes a bundle
    whose records are identical to the source's: the same canonical JSON once key order, array order and
    whitespace are set aside. It checks that against the records sha256 the build recorded, and stops if
    anything differs. `verify --roundtrip` does the same check without keeping the output; see
    [Build Your Own](build-your-own.md#rebuild-the-bundle) for both, with measured runs, and the tool's
    [round-trip notes](https://github.com/clingen-data-model/gkm-bundle-parquet/blob/main/docs/round-trip.md).

Dropping `data` is most of the size difference. In the 1.1 tables, `data` (and `value`) took 7.8 GB, 59 % of
the 13.2 GB set, and the typed columns about 5.3 GB. Most of the remaining difference is in the evidence lines:
1.17 GB across three 1.1 tables, 0.26 GB in the one 2.0 table. The whole 2.0 set is 4.6 GB, about 65 % smaller
than the 1.1 set, although it holds a newer and slightly larger release.

---

## Evidence lines are one table { #evidence-lines-are-one-table }

`evidenceLine` holds every evidence line, and the id says which kind a row is:

| Id | Kind | Columns it fills |
| --- | --- | --- |
| `clinvar.submission:SCV<n>.<ver>` | an SCV's line (somatic clinical impact submissions only) | `targetProposition`, `evidenceOutcome`, `directionOfEvidenceProvided`, `extensions` |
| `VCV<…>.contributing`, `VCV<…>.non-contributing` | a VCV statement's line | `hasEvidenceItems`, `strengthOfEvidenceProvided`, `directionOfEvidenceProvided` |
| `RCV<…>.contributing`, `RCV<…>.non-contributing` | an RCV statement's line | the same |

To read only one kind, filter on the id, or reach the lines from their statements, which is what the queries on
[Joining Tables](joining.md#seam-d-inside-an-aggregate) do:

```sql
SELECT CASE WHEN id LIKE 'VCV%' THEN 'vcv'
            WHEN id LIKE 'RCV%' THEN 'rcv'
            ELSE 'scv' END AS kind,
       count(*) AS lines
FROM 'evidenceLine.parquet'
GROUP BY ALL ORDER BY kind;
```

`hasEvidenceItems` replaces `evidence_items`. Each item is `{id, section}`, so an item's table no longer has to
be read from its id's prefix: `section` is `scv`, `vcv` or `rcv`.

---

## References: bare ids and `_section` columns

A reference column holds the **bare id** of the record it points to, named after the bundle property:
`allele.location`, `location.sequenceReference`, a proposition's `subject`, a statement's `proposition`. Where
the property can point into more than one table, a `<column>_section` column beside it names the table:

| Column | `_section` values |
| --- | --- |
| proposition `object` | `condition`, `conditionSet`, `therapy`, `therapyGroup` (`object_section`) |
| `propositionSomaticClinicalImpact.conditionQualifier` | `condition`, `conditionSet` (`conditionQualifier_section`) |
| statement `proposition` | the four proposition tables (`proposition_section`) |

In a list, each element is one `STRUCT(id, section)`: `variation.members`, `conditionSet.concepts` and
`evidenceLine.hasEvidenceItems`. A list whose targets are all in one table stays a list of ids:
`therapyGroup.concepts`, and `hasEvidenceLines` on the statements.

Dispatch on the `_section` column, not on the id's prefix. The equality-join advice is unchanged: fold the
section test into the join key so DuckDB keeps a hash join.

```sql
SELECT p.id, p.object_section, coalesce(c.name, '(a condition set)') AS object_name
FROM 'propositionPathogenicity.parquet' p
LEFT JOIN 'condition.parquet' c
       ON c.id = CASE WHEN p.object_section = 'condition' THEN p.object END
LIMIT 5;
```

`table-spec.json` lists every reference column, with its target tables, under each table's `foreign_keys`.

---

## The proposition tables no longer share one schema

In the 1.1 tables, all four proposition tables had the same 14 columns, many always NULL. In the 2.0 tables each
has only the columns its propositions can have: only `propositionSomaticClinicalImpact` has
`conditionQualifier`, and only `propositionPathogenicity` and `propositionClinvarCustom` have
`modeOfInheritanceQualifier` and `penetranceQualifier`. Read the four together with `union_by_name = true`,
which fills a column a table lacks with NULL:

```sql
SELECT regexp_extract(filename, 'proposition[A-Za-z]+') AS prop_table,
       count(*) AS propositions,
       count(modeOfInheritanceQualifier) AS with_mode_of_inheritance
FROM read_parquet('proposition*.parquet', union_by_name = true, filename = true)
GROUP BY ALL ORDER BY propositions DESC;
```

Without `union_by_name`, DuckDB takes the glob's columns from the first file, `propositionClinvarCustom`. The
columns every proposition table has (`id`, `type`, `subject`, `predicate`, `object`, `object_section`,
`geneContextQualifier`) read as before, but `conditionQualifier` is a binder error ("not found"), and reading
`modeOfInheritanceQualifier` stops with a schema mismatch when the scan reaches a table without it. Every query
in these pages passes `union_by_name = true`.

---

## Qualifiers are STRUCTs { #qualifiers-are-structs }

A proposition's qualifiers are kept whole, as in the bundle, instead of being flattened into a few columns.
These expressions give back each dropped 1.1 column:

```sql
SELECT id,
       'ncbigene:' || geneContextQualifier.primaryCoding.code AS gene_context_id,
       geneContextQualifier.name                               AS gene_context_name,
       [e.value_string_array FOR e IN geneContextQualifier.extensions
                             IF e.name = 'submittedGeneSymbols'][1] AS submitted_gene_symbols,
       [e.value_string FOR e IN geneContextQualifier.extensions
                       IF e.name = 'geneContextSource'][1]          AS gene_context_source,
       modeOfInheritanceQualifier.name                         AS mode_of_inheritance,
       penetranceQualifier.name                                AS penetrance
FROM 'propositionPathogenicity.parquet'
WHERE geneContextQualifier IS NOT NULL
LIMIT 5;
```

- `gene_context_id` is NULL exactly where it was: the placeholder qualifier has no `primaryCoding`.
- A proposition with no qualifier has a NULL STRUCT, so every field of it reads NULL.
- `submitted_gene_symbols` is NULL where the 1.1 column held an empty list.
- The mode-of-inheritance qualifier also carries its HPO coding, `modeOfInheritanceQualifier.primaryCoding.code`
  (`HP:0000006` for autosomal dominant), which the 1.1 tables had only in `data`.

What a gene-context qualifier means is unchanged; see [Gene context](tables.md#gene-context).

---

## Extensions: one slot per kind of value

An `extensions` column is still a list of `STRUCT(name, value_<kind>, …)`, and each element still fills only the
slot its value needs. The slots are now named by the value's JSON kind rather than its meaning:

| Value | 1.1 slot | 2.0 slot |
| --- | --- | --- |
| a string | `value_string` (or `value` on `vcv`, `rcv`) | `value_string` |
| a boolean | `value_boolean` | `value_boolean` |
| a list of strings | in `data` only | `value_string_array` |
| an object | `value_submitted_condition`, `value_submitted_condition_set` | `value_object` |
| a list of objects | `value_hgvs_array`, `value_gene_array`, `value_document_array` | `value_object_array` |

Pick the element by `name`, as before:

```sql
SELECT id,
       [e.value_object_array FOR e IN extensions IF e.name = 'clinvarGeneList'][1] AS gene_list
FROM 'variation.parquet'
LIMIT 3;
```

An extension nested inside another extension's value (an HGVS entry's `nucleotideExpression.extensions`, a
condition set's `concepts`) is kept as **JSON text**, one string per element; read it with `json_extract_string`
or `->>`. `gkm-bundle-parquet generate` lists every position kept as JSON text.

---

## Smaller changes that break queries

- **`"end"` needs quotes.** `location.end` is a reserved word in SQL: write `"end"`, or alias the table
  (`l."end"`). `start`, `start_min`, `start_max`, `end_min` and `end_max` need no quotes.
- **Dates are text.** `scv.contributions[].date` is `VARCHAR` (`2025-03-04`). Text comparison and `ORDER BY`
  work as before, because the format is `YYYY-MM-DD`; `CAST(date AS DATE)` for date arithmetic.
- **Rows are sorted by `id`.** Nothing in the 1.1 tables promised an order, but a query that relied on file order
  now sees id order. A filter on `id` reads only the row groups whose id range can match (usually one),
because each row group's minimum and maximum id are in the footer.

---

## Query rewrites { #query-rewrites }

Each pair is a 1.1 query and its 2.0 equivalent. The 2.0 queries are the ones the other pages of this guide use.

### A variant's propositions

```sql
-- 1.1
SELECT p.type, count(*) AS propositions
FROM read_parquet('proposition*.parquet') p
WHERE p.subject_variant_id = 'clinvar:10'
GROUP BY ALL;
```

```sql
-- 2.0
SELECT p.type, count(*) AS propositions
FROM read_parquet('proposition*.parquet', union_by_name = true) p
WHERE p.subject = 'clinvar:10'
GROUP BY ALL;
```

### A statement's proposition and condition

```sql
-- 1.1
SELECT s.id, s.classification.name AS classification, c.name AS condition
FROM 'scv.parquet' s
JOIN read_parquet('proposition*.parquet') p ON p.id = s.proposition_id
LEFT JOIN 'condition.parquet' c
       ON c.id = CASE WHEN p.object_type = 'condition' THEN p.object_id END
LIMIT 10;
```

```sql
-- 2.0
SELECT s.id, s.classification.name AS classification, c.name AS condition
FROM 'scv.parquet' s
JOIN read_parquet('proposition*.parquet', union_by_name = true) p ON p.id = s.proposition
LEFT JOIN 'condition.parquet' c
       ON c.id = CASE WHEN p.object_section = 'condition' THEN p.object END
LIMIT 10;
```

### A condition set's member names

```sql
-- 1.1
SELECT cs.id, string_agg(c.name, '; ') AS members
FROM 'conditionSet.parquet' cs, unnest(cs.concepts) AS t(cid)
LEFT JOIN 'condition.parquet' c ON c.id = cid
GROUP BY cs.id
LIMIT 5;
```

```sql
-- 2.0
SELECT cs.id, string_agg(c.name, '; ') AS members
FROM 'conditionSet.parquet' cs, unnest(cs.concepts) AS t(m)
LEFT JOIN 'condition.parquet' c ON c.id = m.id
GROUP BY cs.id
LIMIT 5;
```

### The SCVs behind a VCV statement

```sql
-- 1.1
SELECT s.id AS vcv_statement, item AS scv_id
FROM (SELECT id, unnest(has_evidence_lines) AS el_id FROM 'vcv.parquet'
      WHERE id LIKE 'VCV000000010.%') s
JOIN 'vcv_evidenceLine.parquet' el ON el.id = s.el_id,
     unnest(el.evidence_items) AS t(item)
WHERE item LIKE 'clinvar.submission:%';
```

```sql
-- 2.0
SELECT s.id AS vcv_statement, item.id AS scv_id
FROM (SELECT id, unnest(hasEvidenceLines) AS el_id FROM 'vcv.parquet'
      WHERE id LIKE 'VCV000000010.%') s
JOIN 'evidenceLine.parquet' el ON el.id = s.el_id,
     unnest(el.hasEvidenceItems) AS t(item)
WHERE item.section = 'scv';
```

### Gene context

```sql
-- 1.1
SELECT gene_context_name, count(*) AS scv_propositions
FROM read_parquet('proposition*.parquet')
WHERE gene_context_id = 'ncbigene:7157'
GROUP BY ALL;
```

```sql
-- 2.0
SELECT geneContextQualifier.name AS gene_context_name, count(*) AS scv_propositions
FROM read_parquet('proposition*.parquet', union_by_name = true)
WHERE 'ncbigene:' || geneContextQualifier.primaryCoding.code = 'ncbigene:7157'
GROUP BY ALL;
```

### A variant's VRS chain

```sql
-- 1.1
SELECT v.id, a.id AS allele, l.loc_start, l.loc_end, sr.name AS sequence
FROM 'variation.parquet' v, unnest(v.members) AS t(member)
JOIN 'allele.parquet' a             ON a.id  = member
JOIN 'location.parquet' l           ON l.id  = a.location_id
JOIN 'sequenceReference.parquet' sr ON sr.id = l.sequence_reference_id
WHERE v.id = 'clinvar:51592';
```

```sql
-- 2.0
SELECT v.id, a.id AS allele, l.start, l."end", sr.name AS sequence
FROM 'variation.parquet' v, unnest(v.members) AS t(m)
JOIN 'allele.parquet' a             ON a.id  = m.id
JOIN 'location.parquet' l           ON l.id  = a.location
JOIN 'sequenceReference.parquet' sr ON sr.id = l.sequenceReference
WHERE v.id = 'clinvar:51592';
```

### A variant's gene list

```sql
-- 1.1
SELECT id, [g.gene FOR g IN e.value_gene_array] AS genes
FROM 'variation.parquet', unnest(extensions) AS t(e)
WHERE e.name = 'clinvarGeneList' AND id = 'clinvar:51592';
```

```sql
-- 2.0
SELECT id,
       [g.gene FOR g IN [e.value_object_array FOR e IN extensions
                         IF e.name = 'clinvarGeneList'][1]] AS genes
FROM 'variation.parquet'
WHERE id = 'clinvar:51592';
```

This 2.0 query, and the next, pick the extension with a list comprehension instead of `unnest(extensions)` in
`FROM`. The `unnest` form still returns the same rows, but it expands every record's extensions before it
filters: over a minute for this one variant, against a few seconds.

### Therapies

```sql
-- 1.1
SELECT g.key AS therapy_group, t.name AS therapy
FROM 'therapyGroup.parquet' g, unnest(g.members) AS u(tid)
JOIN 'therapy.parquet' t ON t.key = tid;
```

```sql
-- 2.0
SELECT g.id AS therapy_group, t.name AS therapy
FROM 'therapyGroup.parquet' g, unnest(g.concepts) AS u(tid)
JOIN 'therapy.parquet' t ON t.id = tid;
```

### An SCV's submitted condition

```sql
-- 1.1
SELECT id, e.value_submitted_condition.name AS submitted_condition
FROM 'scv.parquet', unnest(extensions) AS t(e)
WHERE e.name = 'submittedCondition'
LIMIT 5;
```

```sql
-- 2.0
SELECT id,
       [e.value_object.name FOR e IN extensions IF e.name = 'submittedCondition'][1] AS submitted_condition
FROM 'scv.parquet'
WHERE list_contains([e.name FOR e IN extensions], 'submittedCondition')
LIMIT 5;
```

The [Recipes](recipes.md), [Joining Tables](joining.md) and [Working at Scale](performance.md) pages are written
for the 2.0 tables throughout.
