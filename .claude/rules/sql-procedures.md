---
description: BigQuery stored-procedure conventions (dynamic SQL, gotchas, naming, oracle-gating)
paths:
  - "src/procedures/**"
---

# SQL Stored Procedure Conventions

The pipeline's heavy lifting is BigQuery SQL stored procedures in `src/procedures/` (named `gkm_*`).

## Dynamic SQL pattern

All procedures use `DECLARE` / `SET` / `REPLACE` / `EXECUTE IMMEDIATE`:

```sql
DECLARE query STRING;
SET query = """
  CREATE OR REPLACE TABLE {S}.my_table AS
  SELECT * FROM {S}.source_table
""";
SET query = REPLACE(query, '{S}', rec.schema_name);
EXECUTE IMMEDIATE query;
```

- `{S}` = `rec.schema_name` (target dataset/schema)
- `{CT}` = `temp_create` (switches between `CREATE TEMP TABLE` and `CREATE OR REPLACE TABLE` on the debug flag)
- `{P}` = table prefix (`_SESSION` for temp tables, `rec.schema_name` for debug)
- One `DECLARE` per query variable at the top of the procedure body

## BigQuery gotchas

- No DEFAULT parameter values in procedures
- Escape sequences in `EXECUTE IMMEDIATE` triple-quoted strings: `\\n`, `\\d`
- `ARRAY_CONCAT_AGG` cannot be used inside `UNNEST` — split into two layers
- `SELECT DISTINCT` cannot include JSON columns — use `GROUP BY` + `ANY_VALUE` instead
- `COALESCE` across subqueries returning different STRUCT types fails — use a `UNION ALL` CTE instead
- Arrays cannot contain NULL elements — guard with `IF(val IS NOT NULL, [FORMAT(...)], [])`
- An array's element STRUCTs must be homogeneous — when adding an extension `value_*` variant, add the new
  field (as NULL) to every extension literal in the array so the types unify
- `bq show DATASET.TABLE` is a location-agnostic existence check; `SELECT … INFORMATION_SCHEMA` queries need
  the dataset's region
- The incremental `gkm_vrs` seed `CLONE`s the prior release; BigQuery caps clone chains at depth 3, so the
  load falls back to a deep copy (`CREATE OR REPLACE … AS SELECT *`) to reset the chain (self-healing)

## Naming

- VCV/RCV aggregation layers: **classification** (by classification label), **priority** (by tier),
  **aggregate** (by submission level) — never "base"/"tier"
- Proposition IDs: `{scv_id}-{PROP_CODE}` for SCVs, `{accession}-{group}-{PROP}-{level}` for VCV/RCV
- Bundle references use `#/{section}/{key}` JSON-pointer format
- Procedures/tables are `gkm_*` (`gks_*` is upstream `clinvar_ingest`); the `gks_type` column is upstream — do
  not rename it to `gkm_type`

## Determinism / correctness

- Incremental procs must be **byte-identical** to a full rebuild (the carry-forward invariant). Use total-order
  `ORDER BY` in `ARRAY_AGG`/`STRING_AGG` and pick from ONE deterministic representative (smallest `full_scv_id`)
  rather than `ANY_VALUE` for attributes not determined by the group key.
- **One row per bundle key.** A `gkm_dict_*` table keyed by a VRS id must be built per id, never per ClinVar
  variation: distinct variations can normalize to the same allele, and a per-variation join emits a duplicate
  JSON key (the reader keeps whichever copy comes last). Merge such inputs per key (see `gkm_dict_allele`) and
  check `GROUP BY key HAVING COUNT(*) > 1` returns nothing.
- BQ-touching changes are **oracle-gated**: a full-vs-incremental oracle and the delta-reconstruction oracle
  (`oracle-delta-reconstruction.sh`) must both report `0,0,0` before publishing.

## Cat-VRS variant/constraint shapes (schema conformance — learned in 1.0.1)

These are emitted by `gkm-catvar-proc.sql` and must match the cat-vrs schemas, or the bundle's `variation`
`anyOf` rejects the record. Validate the produced data, not just that the SQL runs.

- **Empty constraints must be NULL, never an all-NULL STRUCT.** `ARRAY_AGG(STRUCT(...))` over a LEFT JOIN that
  missed produces one all-NULL element → serializes to `constraints: [{}]`, which matches no `anyOf` branch.
  Guard it: `IF(COUNTIF(cci.type IS NOT NULL)=0, NULL, ARRAY_AGG(IF(cci.type IS NULL, NULL, STRUCT(...)) IGNORE
  NULLS))`. A NULL array is coerced to `[]` on table write, which the assembler's `strip_empty` then drops →
  the attribute is omitted entirely → the variant validates as `ClinvarNonConstrainedVariant`
  (haplotypes/genotypes). Never emit `[{}]` or `[]` expecting the schema to accept it.
- **Numeric constraint fields are integers/Ranges, never strings.** cat-vrs `CopyCountConstraint.copies` is
  `oneOf[integer, Range]`; coordinates likewise. Cast to `INT64` (or build a VRS `Range`) in the proc — a
  string `"3"` fails `oneOf`. The copies/coords STRING→INTEGER fix landed in #132/1.0.1; keep new numeric
  constraint fields typed. (The UNION arms set the STRUCT field type, e.g. `CAST(null as INTEGER) as copies`,
  so the populated arm MUST also be INTEGER or the UNION won't type-unify — a built-in guard, don't defeat it.)
