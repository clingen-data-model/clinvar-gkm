# Beyond DuckDB

!!! info "Release"
    Outputs and timings on this page are from the **2026-10 monthly release** (published 14 Oct 2026), run on a laptop against downloaded files with pyarrow 26, pandas 3, polars 2 and DuckDB 1.5.

Parquet is an open format, so any tool that reads it can read these files. This page does the **same small task** in each, so you can compare them: count the expert-panel SCVs by normalized classification, reading only the two fields that needs.

The expected answer, whichever tool you use:

```text
code                    n
pathogenic              9,906
uncertain significance  3,954
likely pathogenic       2,940
likely benign           2,822
benign                  2,807
…
```

Whatever the tool, the rule from [Anatomy of a Table](table-anatomy.md#never-select-on-a-big-table) holds: **read only the columns you need.** `scv.parquet` is 3.1 GB on disk and about 20 GB once loaded whole.

## Python

### DuckDB from Python

The SQL on the rest of this track runs unchanged from Python, and `.df()` hands the result to pandas:

```python
import duckdb

df = duckdb.sql("""
    SELECT classification.primaryCoding.code AS code, count(*) AS n
    FROM 'scv.parquet'
    WHERE quality.name = 'expert panel'
    GROUP BY ALL ORDER BY n DESC
""").df()
print(df.head())
```

Use this when the work is mostly joins and filtering: DuckDB does them out of memory, and only the small result becomes a DataFrame.

### pyarrow

pyarrow reads the schema and metadata from the footer, and can read individual fields out of nested columns:

```python
import pyarrow.parquet as pq
import pyarrow.compute as pc

pf = pq.ParquetFile("scv.parquet")                     # opening reads only the footer
print(pf.metadata.num_rows, "rows in", pf.metadata.num_row_groups, "row groups")
print(pf.schema_arrow.field("quality").type)

# Read two nested fields, not the whole table; they come back as columns "code" and "name"
t = pq.read_table("scv.parquet",
                  columns=["classification.primaryCoding.code", "quality.name"])
ep = t.filter(pc.equal(t["name"], "expert panel"))
print(ep.group_by("code").aggregate([("code", "count")])
        .sort_by([("code_count", "descending")]).slice(0, 5).to_pylist())
```

A dotted path in `columns=` reads just that leaf. Note that the result names the column by its last segment (`code`, `name`), not the full path.

### pandas

pandas reads Parquet through pyarrow, with the same `columns=`:

```python
import pandas as pd

# columns= is essential: without it pandas loads every column, about 20 GB for scv
df = pd.read_parquet("scv.parquet",
                     columns=["classification.primaryCoding.code", "quality.name"])
print(df.columns.tolist())                               # ['code', 'name']
print(df.loc[df["name"] == "expert panel", "code"].value_counts().head())
```

!!! warning "Never `pd.read_parquet` a big table without `columns=`"
    It loads every column, including the multi-GB `data` column, into memory. On `scv.parquet` that is about 20 GB. The process is killed or the machine swaps.

### polars

polars' `scan_parquet` is lazy: it builds a query plan and, on `.collect()`, reads only the columns and rows the plan needs:

```python
import polars as pl

out = (
    pl.scan_parquet("scv.parquet")                       # lazy: nothing is read yet
      .select(code=pl.col("classification").struct.field("primaryCoding").struct.field("code"),
              level=pl.col("quality").struct.field("name"))
      .filter(pl.col("level") == "expert panel")
      .group_by("code").len()
      .sort("len", descending=True)
      .collect()                                         # reads only the needed columns
)
print(out.head())
```

Use `scan_parquet`, not `read_parquet`: the eager `read_parquet` loads the file first, with the same memory problem as pandas.

## R

The `arrow` package opens a file as a dataset and translates `dplyr` verbs into a column-pruned scan; nothing is read until `collect()`:

```r
library(arrow)
library(dplyr)

open_dataset("scv.parquet") |>
  transmute(code  = classification$primaryCoding$code,
            level = quality$name) |>
  filter(level == "expert panel") |>
  count(code, sort = TRUE) |>
  collect()
```

The `duckdb` R package is the other route: it runs the SQL from this track unchanged.

## Spark and cloud warehouses

The files load directly into Spark (`spark.read.parquet(...)`) and into cloud warehouses: as BigQuery external or loaded tables from a Cloud Storage copy, or as Athena tables over an S3 copy. Copy the files into your own bucket first; `data.clinvar-gkm.org` is a download host, not a query endpoint for warehouse engines.

What survives the trip:

- **`STRUCT` and `LIST` columns** arrive as the engine's record and array types (`STRUCT`/`ARRAY` in BigQuery and Spark, `struct`/`array` in Athena), so dotted access like `classification.name` works the same way.
- **`data` is a string everywhere.** Parse it with the engine's JSON functions (`JSON_VALUE` in BigQuery, `get_json_object` in Spark) only when a field has no typed column.
- **Ids are plain strings.** The joins on [Joining Tables](joining.md) translate directly, prefix dispatch included.

## Spreadsheets and GUI tools

Excel, Google Sheets and most GUI tools can't open Parquet, and even those that can shouldn't open a multi-GB table. Filter to the rows you need first, then export that slice to CSV:

```bash
duckdb -c "COPY (SELECT id, name FROM 'condition.parquet') TO 'conditions.csv' (HEADER)"
```

[Recipes → Export a slice](recipes.md#export) has a fuller example. With no terminal at all, the [DuckDB Web Shell](https://shell.duckdb.org){ target=_blank rel=noopener } can open a small downloaded file in the browser and export the result.

## Which tool when

For exploring and for joins, **DuckDB**, from the command line or from Python or R: it reads only what a query needs and handles joins larger than memory. For a dataframe workflow in Python, **polars** with `scan_parquet` gives the same column pruning with a dataframe API. Use **pandas** or **pyarrow** when a library you depend on expects their objects, and always pass `columns=`. Reach for **Spark or a warehouse** only when the data has to live next to other large data in your cloud. For everyone else, a few GB of Parquet on a laptop is small.
