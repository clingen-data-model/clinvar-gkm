# Build Parquet from the Bundles

The 1.1 line's Parquet (`v1/1.1/parquet/`, the 22 tables these docs describe) was published until release 1.2.0
replaced the line. It was **removed on 2026-11-23**, when `v1/1.1/` was frozen: a frozen line keeps its bundles
and no Parquet, because the bundle is the record and the tables are derived from it. This page shows how to build
tables from any `v1/1.1/` bundle yourself, with [`gkm-bundle-parquet`](https://github.com/clingen-data-model/gkm-bundle-parquet)
2.0.0 and a column set ClinVar-GKM publishes, so that you get compact tables and can prove that no value was lost.

!!! warning "These are the 2.0 tables, not the 22 tables on these pages"
    `gkm-bundle-parquet` 2.0.0 writes table spec `sections` 2.0: one table per bundle section, 20 for a 1.1.0
    bundle, with every property of a record a typed column. These are not the 22 tables the 1.1 line published
    (exported from BigQuery, with other names and columns), so the queries in [Query the Data](index.md) need
    rewrites. The 1.2 docs map every old table and column to the new ones:
    [Moving from the 1.1 Tables to 2.0](https://dataexchange.clinicalgenome.org/clinvar-gkm/1.2/parquet/migrating-from-1.1/).

---

## Why a column set

The tool generates a bundle's tables from its JSON Schema. With no column set, every property the schema allows
becomes a column. The 1.1.0 schema leaves many classes as general as the GA4GH classes they extend, so that
default is much wider than the data:

| Built from the 2026-10-31 weekly delta (495,547 records) | Top-level columns | Leaf columns | JSON-text columns |
| --- | ---: | ---: | ---: |
| 1.1.0 schema, generated default | 339 | 553 | 122 |
| 1.1.0 schema, ClinVar-GKM's 1.1.0 column set | 163 | 366 | 0 |

Both rebuild the same records. The default's extra columns are properties no 1.1 bundle holds (always NULL), and
positions it keeps as JSON text because the schema leaves them open. The column set lists only the properties the
1.1 pipeline writes, each with a type.

The column set is a **named projection** (`projection: clinvar-gkm-1.1.0-producer`): the tool labels every file
and the manifest with that name and the column set's sha256, so the tables can't be mistaken for the default. The
build stops on any record holding a property the column set doesn't list, naming the record, so a build that
completes kept every value, and the round-trip check below proves it record by record.

---

## The 1.1.0 column set { #the-110-column-set }

| | |
| --- | --- |
| URL | `https://dataexchange.clinicalgenome.org/clinvar-gkm/1.2/assets/column-sets/clinvar-gkm-1.1.0.columns.yaml` |
| For | bundles of `schema_version` `1.1.0`: every bundle in `v1/1.1/` |
| Schema it pairs with | `--bundle-schema https://w3id.org/clingen/schema/clinvar-gkm/1.1.0/clinvar-gkm-bundle.schema.json` |
| Tool | `gkm-bundle-parquet` 2.0.0 |

`--column-set` takes the URL or a downloaded copy of the file.

---

## Build the tables

The commands run the tool with [`uvx`](https://docs.astral.sh/uv/), which needs no install. To install it
instead, run `pip install gkm-bundle-parquet==2.0.0` (Python 3.10 or later) and write `gkm-bundle-parquet` in
place of `uvx gkm-bundle-parquet@2.0.0`. The commands work in bash and zsh.

### 1. Find the bundle

Read the paths from the line's own `index.json`. A frozen line keeps every path, but the folders differ by month
(the line's last month of deltas is in `deltas/`, earlier months in `deltas/YYYY-MM/`), so copy the path rather
than guess it.

```bash
curl -s https://data.clinvar-gkm.org/v1/1.1/index.json | python3 -c '
import json, sys
d = json.load(sys.stdin)
for m in d["datasets"]["monthly"]:
    print("monthly", m["release"], m["source_release"], m["size"], m["path"])
for x in d["deltas"]:
    print("delta  ", x["release"], x["bundle"]["size"], x["bundle"]["path"])'
```

A **monthly** is a full bundle (4.5 to 4.8 GB compressed, about 90 million records); its `source_release` is the
weekly release it holds. A **delta** holds only what changed in one weekly release (2 to 150 MB). To get a full
bundle for a week between monthlies, replay the deltas onto the monthly first; see
[Rebuild a past week](../data-access/weekly-deltas.md#rebuild-a-past-week).

### 2. Download it and check its sha256

```bash
B=v1/1.1/deltas/2026-09/clinvar-gkm-delta_2026-0928.json.gz     # a path from step 1
curl -O "https://data.clinvar-gkm.org/$B" -O "https://data.clinvar-gkm.org/$B.sha256"
shasum -a 256 -c "$(basename "$B").sha256"                       # sha256sum -c on Linux
```

### 3. Build { #build }

```bash
uvx gkm-bundle-parquet@2.0.0 build --full clinvar-gkm-delta_2026-0928.json.gz \
    --bundle-schema https://w3id.org/clingen/schema/clinvar-gkm/1.1.0/clinvar-gkm-bundle.schema.json \
    --column-set https://dataexchange.clinicalgenome.org/clinvar-gkm/1.2/assets/column-sets/clinvar-gkm-1.1.0.columns.yaml \
    --out parquet/
```

For a monthly, give the monthly's file name, and see [Time and memory](#time-and-memory) first. The tool reads
the `.sha256` sidecar beside the bundle and records it in `manifest.json`. A build that completes lists the 20
tables and their rows; a build that stops names the section, the record key and the property no column covers.
No published 1.1 bundle stops the build. If one does, build that bundle with no `--column-set` (the wide
default) and open an issue.

!!! note "If the build stops with a DuckDB `Parallel CSV Reader` error"
    On one of the 18 deltas (2026-08-16), `gkm-bundle-parquet` 2.0.0 stops with `NotImplementedException: Not
    implemented Error: The Parallel CSV Reader currently does not support a full read on this file`, with or
    without a column set. It comes from DuckDB reading the tool's own staging files, not from the bundle
    ([gkm-bundle-parquet#37](https://github.com/clingen-data-model/gkm-bundle-parquet/issues/37)). Run the same
    command again with `--threads 1`, and pass `--threads 1` to `verify` too: both then complete, and the round
    trip is identical.

### 4. Prove that nothing was lost

```bash
uvx gkm-bundle-parquet@2.0.0 verify parquet/ --roundtrip --full clinvar-gkm-delta_2026-0928.json.gz
```

```text
verify pass: directory check: 0 problem(s); round trip: identical
```

`--roundtrip --full` rebuilds the records from the tables and compares them with the bundle's own records. To
keep the rebuilt bundle, run `rebuild parquet/ -o rebuilt.json.gz` instead: it ends with
`record-identical to the source` when every record matches.

---

## Time and memory

| Bundle | `build` (time, peak memory) | `verify --roundtrip` | Where |
| --- | ---: | ---: | --- |
| 2026-10-31 delta, 495,547 records | 22 s, 2.4 GB | 16 s, 0.9 GB | a 16 GB laptop |
| 2026-09-23 delta, 4,530,457 records (the largest) | 82 s, 3.3 GB | 66 s, 1.7 GB | a 16 GB laptop |
| a monthly, about 90 million records | 38 min, 65 GiB | 30 min | a 128 GiB machine |

Every delta builds on a laptop. A monthly needs a large machine (the full-bundle figures are the tool's own
measurements of a full bundle of the same size). On a smaller machine, pass `--memory-limit` and a `--work-dir`
with about 65 GB free, and expect a much longer run.

---

## What is verified

On 2026-11-20, with `gkm-bundle-parquet` 2.0.0, the column set and the 1.1.0 schema URL above:

- **Every published `v1/1.1/` delta** (18 deltas, 2026-07-06 to 2026-10-31, 10,267,303 records) built, and the
  round trip was identical.
- **The newest monthly**, `clinvar-gkm_2026-11.json.gz` (91,854,927 records), was scanned for every property its
  records hold; the 528 records holding something no delta holds were built on their own and round-tripped
  identically.

The 1.2 docs give the details:
[Parquet for Previous Releases](https://dataexchange.clinicalgenome.org/clinvar-gkm/1.2/parquet/previous-releases/).

---

## The 1.0 line

The 1.0 line (`v1/1.0/`, schema `1.0.1`) can't be built with `gkm-bundle-parquet`: its schema closes each
ClinVar-GKM part of a class with `additionalProperties: false`, so the tool finds no column for most properties,
and some of its deltas hold an `allele` key twice. `v1/1.1/` holds a bundle for every release `v1/1.0/` holds,
built from the same ClinVar releases with schema 1.1.0, so build the tables from the `v1/1.1/` bundle of the
release you need, as above. The 1.0 bundles stay published unchanged; see
[Previous Releases](../data-access/previous-releases.md).
