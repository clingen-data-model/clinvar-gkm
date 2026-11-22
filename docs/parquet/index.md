# Start Here

!!! info "Release"
    Counts on this page are from the **2026-10-31 release**. The Parquet tables are built from the JSON bundle and rebuilt each release, and one set is published per release line, overwritten every release, so the console's numbers are today's and may be higher than this page's.

!!! warning "New tables from release 1.2.0"
    From release 1.2.0 the tables are built by `gkm-bundle-parquet` 2.0 and published at `v1/1.2/parquet/`: 20 tables
    with different columns from the 22 BigQuery-exported tables at `v1/1.1/parquet/`. This track describes the new
    tables. If you have queries for the old ones, see [Moving from the 1.1 Tables](migrating-from-1.1.md).

ClinVar-GKM publishes all of ClinVar as **Parquet** — 20 typed tables you query with SQL, with no database server and no data-loading step. This page gets a real answer from real ClinVar data in about five minutes: no joins, no genomics background, and — to begin — nothing to install.

## Run a query now

The console below runs SQL **in your browser**, directly against the published data at `data.clinvar-gkm.org`. It reads the Parquet set of the current release line, `v1/1.2/parquet/`, overwritten every release; the **Release** label shows the release it was built from. When a new line starts, its Parquet set is published shortly after its first release, and the console has no tables to read until then (see [the timeline](migrating-from-1.1.md#timeline)). Pick an example from the dropdown and press **Run**. The first query loads the engine (a few seconds, once); everything after is immediate. A query still running after 10 seconds is stopped, and the console shows the commands to download the tables it reads and run the same query on your machine.

<iframe src="../assets/duckdb-console.html" style="width:100%; height:640px; border:1px solid rgba(128,128,128,.25); border-radius:8px;" title="ClinVar-GKM live query console" loading="lazy"></iframe>

The first example counts every **condition** in ClinVar: **23,426**. `condition.parquet` is the right table to start with — about 2 MB, one row per condition, and a plain-English `name` column, with none of the variant identifiers or nested structures the larger tables carry.

---

## Three queries

Each of these is in the console's **Example** dropdown. Read them top to bottom — they go from "how much is here" to "find the one I care about".

!!! note "Prerequisites"
    - **In the console:** nothing to install.
    - **On your machine:** the [DuckDB CLI](https://duckdb.org/docs/installation/) (tested with **1.5.4**) and
      `curl`, and `condition.parquet` (about 2 MB) downloaded into the directory you run DuckDB from, as in
      [Put the file on your machine](#put-the-file-on-your-machine).
    - **Querying a URL instead of a file** (`FROM 'https://data.clinvar-gkm.org/…'`): DuckDB installs and loads its
      `httpfs` extension the first time a query reads a URL, which needs internet access to DuckDB's extension
      repository. Where that is blocked, install it by hand
      ([installing extensions](https://duckdb.org/docs/stable/extensions/installing_extensions)), or download
      the file first.

```sql
-- 1. How many conditions are there?
SELECT count(*) FROM 'condition.parquet';

-- 2. What do they look like?
SELECT id, name FROM 'condition.parquet' LIMIT 10;

-- 3. Find one you care about
SELECT id, name FROM 'condition.parquet' WHERE name ILIKE '%marfan%';
```

The third returns 13 rows — every ClinVar condition whose name mentions Marfan, from `Marfan syndrome` to `Neonatal Marfan syndrome`. `ILIKE` is a case-insensitive match and `%` means "any text here".

These queries name the file as `'condition.parquet'` — how you run them once the file is on your machine. The console above points the same queries at the published URL for you.

---

## Put the file on your machine

To go past the browser console — larger queries, your own scripts, repeated work — download the file and query it with [DuckDB](https://duckdb.org/docs/installation/), a single self-contained binary.

```bash
BASE="https://data.clinvar-gkm.org/v1/1.2/parquet"
curl -fO "${BASE}/condition.parquet"

duckdb -c "SELECT id, name FROM 'condition.parquet' WHERE name ILIKE '%marfan%'"
```

The [Downloads → Parquet Files](../data-access/parquet.md) page lists every file and the stable URL. The tables are built from the bundle and rebuilt each release: the published set is always the latest release. For an earlier release, or for just the records you need, [build the tables yourself](build-your-own.md) from a published bundle.

---

## No terminal at all

Two ways to query without installing anything:

- **The console on this page** (above) — already running against the published data.
- **The DuckDB Web Shell** at [shell.duckdb.org](https://shell.duckdb.org){ target=_blank rel=noopener } — drag a downloaded `condition.parquet` onto the page (or use **Import**), then run `SELECT id, name FROM condition;`.

---

## Get the answer into a spreadsheet

Excel and Google Sheets cannot open Parquet, but one line turns a result into a CSV they can:

```bash
duckdb -c "COPY (SELECT id, name FROM 'condition.parquet') TO 'conditions.csv' (HEADER)"
```

---

## Where to go next

`condition.parquet` is 1 of 20 tables. The rest hold the variants, the clinical assertions (SCVs), and the ClinVar aggregates (VCVs and RCVs) — and they reference each other. The [table map](tables.md) shows all 20 at a glance; from there, pick by the question you have:

- **What columns does a table have?** — [Anatomy of a Table](table-anatomy.md)
- **How do the tables join?** — [Joining Tables](joining.md)
- **Give me a working query for a real task** — [Recipes](recipes.md)
- **The big tables are slow or run out of memory** — [Working at Scale](performance.md)
- **I work in Python, R, or Spark** — [Beyond DuckDB](other-tools.md)
- **I want the tables for another release, or a small slice as JSON** — [Build Your Own Tables and Mini-Bundles](build-your-own.md)
- **I have queries for the 1.1 tables** — [Moving from the 1.1 Tables](migrating-from-1.1.md)
- **I want tables for a frozen line (`v1/1.1/`, `v1/1.0/`)** — [Parquet for Previous Releases](previous-releases.md)
