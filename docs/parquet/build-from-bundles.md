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
    [Moving from the 1.1 Tables to 2.0](https://clinvar-gkm.org/1.2/parquet/migrating-from-1.1/).

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
| URL | `https://clinvar-gkm.org/1.2/assets/column-sets/clinvar-gkm-1.1.0.columns.yaml` |
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
curl -sSf --retry 5 -o index.json https://data.clinvar-gkm.org/v1/1.1/index.json && python3 -c '
import json
d = json.load(open("index.json"))
for m in d["datasets"]["monthly"]:
    print("monthly", m["release"], m["source_release"], m["size"], m["path"])
for x in d["deltas"]:
    print("delta  ", x["release"], x["bundle"]["size"], x["bundle"]["path"])'
```

`-f` makes `curl` stop with the HTTP error when a request fails, instead of saving the server's error page, and
`&&` runs Python only when the download succeeded; `--retry 5` rides out a brief server error (HTTP 5xx).

A **monthly** is a full bundle (4.5 to 4.8 GB compressed, about 90 million records); its `source_release` is the
weekly release it holds. The newest monthly is listed twice: under its own name and as
`clinvar-gkm_00-latest.json.gz`, a copy of it. A **delta** holds only what changed in one weekly release (2 to
150 MB). To get a full bundle for a week between monthlies, replay the deltas onto the monthly first; see
[Rebuild a past week](../data-access/weekly-deltas.md#rebuild-a-past-week).

### 2. Download it and check its sha256

```bash
B=v1/1.1/deltas/2026-09/clinvar-gkm-delta_2026-0928.json.gz
curl -f --retry 5 -O "https://data.clinvar-gkm.org/$B" -O "https://data.clinvar-gkm.org/$B.sha256"
shasum -a 256 -c "$(basename "$B").sha256"
```

`B` is a path from step 1. On Linux, `sha256sum -c` does the same as `shasum -a 256 -c`.

### 3. Build { #build }

```bash
uvx gkm-bundle-parquet@2.0.0 build --full clinvar-gkm-delta_2026-0928.json.gz \
    --bundle-schema https://w3id.org/clingen/schema/clinvar-gkm/1.1.0/clinvar-gkm-bundle.schema.json \
    --column-set https://clinvar-gkm.org/1.2/assets/column-sets/clinvar-gkm-1.1.0.columns.yaml \
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

## Parquet for one weekly release { #parquet-for-one-weekly-release }

`build` reads one bundle, so a full set of tables for one week is built from that week's full bundle. A
monthly is the full bundle of its `source_release`. For any other 1.1 week, rebuild the week's full bundle from
a monthly and the deltas after it with
[`replay-bundle.py`](https://clinvar-gkm.org/1.2/assets/scripts/replay-bundle.py),
the script the 1.2 docs publish. It needs only `python3` (3.9 or later); name the line with `--line v1/1.1`:

```bash
curl -fsSO --retry 5 https://clinvar-gkm.org/1.2/assets/scripts/replay-bundle.py
python3 replay-bundle.py --line v1/1.1 --release 2026-10-24 --plan
python3 replay-bundle.py --line v1/1.1 --release 2026-10-24
```

The first lists the monthly and deltas it would use; the second downloads them and replays the deltas.

It picks the monthly and the deltas as [Rebuild a past week](../data-access/weekly-deltas.md#rebuild-a-past-week)
says, refuses a broken chain, checks every download's sha256 against `index.json`, reuses a file already in the
folder when its sha256 matches, and writes `clinvar-gkm_2026-1024.replayed.json.gz` with a `.sha256` sidecar. It
keeps only the deltas' records in memory and streams the monthly once.

Measured on 2026-11-21 on a 16 GB laptop, rebuilding 2026-10-24 from the 2026-10 monthly (source release
2026-09-28) and the four deltas 2026-10-04 to 2026-10-24: **7.3 minutes** with the downloads (6.2 minutes of
replay), 2.2 GB peak memory, a 4.8 GB bundle of 91,502,593 records. Compared with the published weekly full
`v1/1.1/weekly/clinvar-gkm_2026-1024.json.gz` section by section (record count and the sha256 of every record line,
in any order), every record matches, and 19 of the 20 sections match byte for byte. In `condition`, 1,461 records
list their `aliases` in another order than that weekly full does. The 1.1 pipeline wrote that array in the order
its source gave, which changed from one release to the next (1.2.0 sorts it), and the replay keeps the order of
the monthly and deltas it was built from. With arrays compared as sets of values, as the tool's round trip
compares them, all 1,461 are identical.

Then build it as in [Build](#build), with the 1.1.0 schema URL and the column set:

```bash
uvx gkm-bundle-parquet@2.0.0 build --full clinvar-gkm_2026-1024.replayed.json.gz \
    --bundle-schema https://w3id.org/clingen/schema/clinvar-gkm/1.1.0/clinvar-gkm-bundle.schema.json \
    --column-set https://clinvar-gkm.org/1.2/assets/column-sets/clinvar-gkm-1.1.0.columns.yaml \
    --out parquet-2026-1024/
```

That is a full build: it needs the large machine in [Time and memory](#time-and-memory), and it was not run for
this page.

---

## Time and memory

| Bundle | `build` (time, peak memory) | `verify --roundtrip` | Where |
| --- | ---: | ---: | --- |
| 2026-10-31 delta, 495,547 records | 22 s, 2.4 GB | 16 s, 0.9 GB | a 16 GB laptop |
| 2026-09-23 delta, 4,530,457 records (the largest) | 82 s, 3.3 GB | 66 s, 1.7 GB | a 16 GB laptop |
| a full bundle, about 92 million records | 3 h 19 min, 10.0 GiB | over 2 h | a 16 GB cloud machine |
| a full bundle, about 92 million records | 38 min, 65 GiB | 30 min | a 128 GiB machine |

Every delta builds on a laptop. The full-bundle figures are for a 1.2 full bundle of the same size (the 2026-11-15
weekly full; the 16 GB run's round trip was stopped after 2 hours, still running). A monthly builds on a 16 GB
machine with the default memory settings and about 30 GB free in `--work-dir`, in a few hours; more memory makes
it faster. `--memory-limit` caps DuckDB, not the whole process, so leave about 3 GB above it. The 1.2 docs give
the details: [A full bundle](https://clinvar-gkm.org/1.2/parquet/build-your-own/#a-full-bundle).

---

## What is verified

On 2026-11-20 and 2026-11-21, with `gkm-bundle-parquet` 2.0.0, the column set and the 1.1.0 schema URL above:

- **Every published `v1/1.1/` delta** (18 deltas, 2026-07-06 to 2026-10-31, 10,267,303 records) built, and the
  round trip was identical.
- **The newest monthly**, `clinvar-gkm_2026-11.json.gz` (91,854,927 records), was scanned for every property its
  records hold; the 528 records holding something no delta holds were built on their own and round-tripped
  identically.
- **The oldest monthly**, `clinvar-gkm_2026-07.json.gz` (86,810,319 records), was scanned the same way; the 14
  `variation` records holding something new (extensions nested inside a `nucleotideExpression`) were built on
  their own and round-tripped identically.
- **The monthlies between** (2026-08 to 2026-10) each equal the 2026-07 monthly plus the deltas after it, so
  every record any published `v1/1.1/` bundle holds is covered, and no published 1.1 bundle stops the build.

The 1.2 docs give the details:
[Parquet for Previous Releases](https://clinvar-gkm.org/1.2/parquet/previous-releases/).

---

## The 1.0 line

The 1.0 line (`v1/1.0/`, schema `1.0.1`) can't be built with `gkm-bundle-parquet`: its schema closes each
ClinVar-GKM part of a class with `additionalProperties: false`, so the tool finds no column for most properties,
and some of its deltas hold an `allele` key twice. `v1/1.1/` holds a bundle for every release `v1/1.0/` holds,
built from the same ClinVar releases with schema 1.1.0, so build the tables from the `v1/1.1/` bundle of the
release you need, as above. The 1.0 bundles stay published unchanged; see
[Previous Releases](../data-access/previous-releases.md).
