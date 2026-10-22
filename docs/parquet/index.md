# Start Here

!!! info "Release"
    Counts on this page are from the **2026-10-18 release**. Parquet is derived from the bundle and regenerated each release, and one dataset is published, overwritten every release, so the console's numbers are today's and may be higher than this page's.

ClinVar-GKM publishes all of ClinVar as **Parquet** — 22 typed tables you query with SQL, with no database server and no data-loading step. This page gets a real answer from real ClinVar data in about five minutes: no joins, no genomics background, and — to begin — nothing to install.

## Run a query now

The console below runs SQL **in your browser**, directly against the published data at `data.clinvar-gkm.org`. It reads the one published Parquet dataset, `v1/1.1/parquet/`, overwritten every release; the **Release** label shows the release it was built from. Pick an example from the dropdown and press **Run**. The first query loads the engine (a few seconds, once); everything after is immediate.

<iframe src="../assets/duckdb-console.html" style="width:100%; height:640px; border:1px solid rgba(128,128,128,.25); border-radius:8px;" title="ClinVar-GKM live query console" loading="lazy"></iframe>

The first example counts every **condition** in ClinVar: **23,414**. `condition.parquet` is the right table to start with — about 5 MB, one row per condition, and a plain-English `name` column, with none of the variant identifiers or nested structures the larger tables carry.

---

## Three queries

Each of these is in the console's **Example** dropdown. Read them top to bottom — they go from "how much is here" to "find the one I care about".

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
BASE="https://data.clinvar-gkm.org/v1/1.1/parquet"
curl -O "${BASE}/condition.parquet"

duckdb -c "SELECT id, name FROM 'condition.parquet' WHERE name ILIKE '%marfan%'"
```

The [Downloads → Parquet Files](../data-access/parquet.md) page lists every file and the stable URL. Parquet is derived from the bundle and regenerated each release: the published set is always the latest release.

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

`condition.parquet` is 1 of 22 tables. The rest hold the variants, the clinical assertions (SCVs), and the ClinVar aggregates (VCVs and RCVs) — and they reference each other. The [table map](tables.md) shows all 22 at a glance; from there, pick by the question you have:

- **What columns does a table have?** — [Anatomy of a Table](table-anatomy.md)
- **How do the tables join?** — [Joining Tables](joining.md)
- **Give me a working query for a real task** — [Recipes](recipes.md)
- **The big tables are slow or run out of memory** — [Working at Scale](performance.md)
- **I work in Python, R, or Spark** — [Beyond DuckDB](other-tools.md)
