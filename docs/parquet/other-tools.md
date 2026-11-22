# Beyond DuckDB

!!! info "Release"
    The expected answer is from the **2026-10-31 release**. The snippets were run against tables built with
    `gkm-bundle-parquet` 2.0.0, with Python 3.12, DuckDB 1.5.4, pyarrow 26.0.1, pandas 3.1.1 and polars 2.1.0, and
    with R 4.6.1, arrow 26.0.1.1 and dplyr 1.2.1.

Parquet is an open format, so any tool that reads it can read these files. This page does the **same small task** in each, so you can compare them: count the expert-panel SCVs by normalized classification, reading only the two fields that needs.

The expected answer, whichever tool you use:

```text
code                    n
pathogenic              10,068
uncertain significance   4,081
likely pathogenic        3,069
benign                   2,881
likely benign            2,867
…
```

Whatever the tool, the rule from [Anatomy of a Table](table-anatomy.md#never-select-on-a-big-table) holds: **read only the columns you need.** `scv.parquet` is 784 MB on disk in 2026-10-31, and several times that once loaded whole.

!!! note "Prerequisites"
    - **Data:** `scv.parquet` (784 MB) in the directory you run from, from
      [Downloads → Parquet Files](../data-access/parquet.md#download); the spreadsheet example reads
      `condition.parquet` (2 MB). Each snippet stands alone and reads only two fields; the pyarrow and pandas ones
      peaked at about 1.4 GB of memory.
    - **Python** (tested with 3.12): install only the libraries for the snippets you run.

        ```bash
        python3 -m venv .venv && . .venv/bin/activate
        pip install "duckdb==1.5.4" "pyarrow==26.0.1" "pandas==3.1.1" "polars==2.1.0"
        ```

    - **R** (tested with 4.6.1): `install.packages(c("arrow", "dplyr"))`. Where CRAN has no binary for your R,
      as with Homebrew's R on macOS, arrow compiles from source: set `Sys.setenv(NOT_CRAN = "true",
      LIBARROW_BINARY = "true")` first so it downloads a prebuilt Arrow C++ library, and expect the install to
      take 15 minutes or more.
    - **Command line:** the [DuckDB CLI](https://duckdb.org/docs/installation/), tested with 1.5.4.

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

pyarrow reads the schema and metadata from the footer, and can read individual fields out of nested columns. The footer also says what built the file: its key-value metadata has `gkm_bundle_parquet.*` entries such as `tool_version` and `bundle_schema_version`.

```python
import pyarrow.parquet as pq
import pyarrow.compute as pc

pf = pq.ParquetFile("scv.parquet")                     # opening reads only the footer
print(pf.metadata.num_rows, "rows in", pf.metadata.num_row_groups, "row groups")
print(pf.schema_arrow.field("quality").type)
print(pf.metadata.metadata[b"gkm_bundle_parquet.bundle_schema_version"])

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

# columns= is essential: without it pandas loads every column of scv, decompressed
df = pd.read_parquet("scv.parquet",
                     columns=["classification.primaryCoding.code", "quality.name"])
print(df.columns.tolist())                               # ['code', 'name']
print(df.loc[df["name"] == "expert panel", "code"].value_counts().head())
```

!!! warning "Never `pd.read_parquet` a big table without `columns=`"
    It loads every column into memory, decompressed: several times the file's size on disk, most of it free text
    and extensions you didn't ask for. On the big tables the process is killed or the machine swaps.

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
- **Every field is a typed column**, except the few nested positions kept as JSON text (see [Extensions](table-anatomy.md#extensions)); parse those with the engine's JSON functions (`JSON_VALUE` in BigQuery, `get_json_object` in Spark).
- **Ids are plain strings.** The joins on [Joining Tables](joining.md) translate directly, `_section` dispatch included.
- **Column names are camelCase** (`primaryCoding`, `hasEvidenceLines`), as in the bundle. Some engines fold unquoted names to lower case; check how yours matches Parquet column names.

## Spreadsheets and GUI tools

Excel, Google Sheets and most GUI tools can't open Parquet, and even those that can shouldn't open a multi-GB table. Filter to the rows you need first, then export that slice to CSV:

```bash
duckdb -c "COPY (SELECT id, name FROM 'condition.parquet') TO 'conditions.csv' (HEADER)"
```

[Recipes → Export a slice](recipes.md#export) has a fuller example. With no terminal at all, the [DuckDB Web Shell](https://shell.duckdb.org){ target=_blank rel=noopener } can open a small downloaded file in the browser and export the result.

## Which tool when

For exploring and for joins, **DuckDB**, from the command line or from Python or R: it reads only what a query needs and handles joins larger than memory. For a dataframe workflow in Python, **polars** with `scan_parquet` gives the same column pruning with a dataframe API. Use **pandas** or **pyarrow** when a library you depend on expects their objects, and always pass `columns=`. Reach for **Spark or a warehouse** only when the data has to live next to other large data in your cloud. For everyone else, 4.6 GB of Parquet on a laptop is small.
