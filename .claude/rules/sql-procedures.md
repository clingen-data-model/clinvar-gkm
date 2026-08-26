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
- BQ-touching changes are **oracle-gated**: a full-vs-incremental oracle and the delta-reconstruction oracle
  (`oracle-delta-reconstruction.sh`) must both report `0,0,0` before publishing.
