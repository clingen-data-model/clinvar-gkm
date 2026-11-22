# Parquet for Previous Releases

From release 1.2.0, only the current line (`v1/1.2/`) has published Parquet. A frozen line keeps its bundles and
no Parquet ([ADR 0008](../decisions/0008-bundles-are-the-public-record.md)): the bundle is the record, and the
tables are derived from it. This page shows how to build the tables of a frozen line yourself, with
[`gkm-bundle-parquet`](build-your-own.md) 2.0.0 and a column set ClinVar-GKM publishes, so that you get compact
tables and can prove that no value was lost.

| Line | Bundle `schema_version` | Build its Parquet |
| --- | --- | --- |
| `v1/1.1/` | `1.1.0` | with the [1.1.0 column set](#the-110-column-set), on this page |
| `v1/1.0/` | `1.0.1` | not supported: build from the `v1/1.1/` bundle of the same release; see [The 1.0 line](#the-10-line) |

!!! warning "These are the 2.0 tables, not the old 1.1 tables"
    `gkm-bundle-parquet` 2.0.0 writes table spec `sections` 2.0: one table per bundle section, 20 for a 1.1.0
    bundle. These are not the 22 tables the 1.1 line published at `v1/1.1/parquet/` (exported from BigQuery,
    with other names and columns), and queries written for those need rewrites; see
    [Moving from the 1.1 Tables to 2.0](migrating-from-1.1.md). The tables differ from the
    [20 tables](tables.md) of the 1.2 line only where the 1.1.0 schema differs from 1.2.0.

---

## Why a column set

The tool generates a bundle's tables from its JSON Schema. With no column set, every property the schema allows
becomes a column. The 1.2.0 schema narrows ClinVar-GKM's classes to what the pipeline writes, so its default is
the published tables. The 1.1.0 schema leaves many classes as general as the GA4GH classes they extend, so its
default is much wider than the data:

| Built from the 2026-10-31 weekly delta (495,547 records) | Top-level columns | Leaf columns | JSON-text columns |
| --- | ---: | ---: | ---: |
| 1.1.0 schema, generated default | 339 | 553 | 122 |
| 1.1.0 schema, ClinVar-GKM's 1.1.0 column set | 163 | 366 | 0 |

Both sets rebuild the same records. The default's extra columns are properties no 1.1 bundle holds (always
NULL), and positions it keeps as JSON text because the schema leaves them open. The column set lists only the
properties the 1.1 pipeline writes, each with a type.

The column set is a **named projection** (`projection: clinvar-gkm-1.1.0-producer`): the tool labels every file
and the manifest with that name and the column set's sha256, so the tables can't be mistaken for the default.
A projection could lose data if it left out a property a record holds, but in 2.0.0 that can't happen silently:
the build stops on any record holding a property the column set doesn't list, naming the record. A build that
completes kept every value, and the round-trip check below proves it record by record.

---

## The 1.1.0 column set { #the-110-column-set }

| | |
| --- | --- |
| File | [`clinvar-gkm-1.1.0.columns.yaml`](../assets/column-sets/clinvar-gkm-1.1.0.columns.yaml) |
| URL | `https://dataexchange.clinicalgenome.org/clinvar-gkm/1.2/assets/column-sets/clinvar-gkm-1.1.0.columns.yaml` |
| For | bundles of `schema_version` `1.1.0`: every bundle in `v1/1.1/` |
| Schema it pairs with | `--bundle-schema https://w3id.org/clingen/schema/clinvar-gkm/1.1.0/clinvar-gkm-bundle.schema.json` |
| Tool | `gkm-bundle-parquet` 2.0.0 |

`--column-set` takes the file or the URL. The set is the tool's own 1.1.0 test fixture, with one change: it
names the schema `$id` that the 1.1.0 URL actually serves (`…/1.1.0/json/ClinvarGkmBundle`, from the 1.1.0 tag),
so it pairs with that URL. The tool's fixture names the `$id` corrected after the tag, which the URL doesn't
serve, and is refused with it.

---

## Build the tables

The commands run the tool with `uvx`, which needs no install; with the tool installed
([Install](build-your-own.md#install)), write `gkm-bundle-parquet` in place of `uvx gkm-bundle-parquet@2.0.0`.
They work in bash and zsh.

### 1. Find the bundle

Read the paths from the line's own `index.json`. A frozen line keeps every path, but the folders differ by
month (the line's last month of deltas is in `deltas/`, earlier months in `deltas/YYYY-MM/`), so copy the path
rather than guess it.

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

`--column-set` also takes the downloaded file. For a monthly, give the monthly's file name, and see
[Time and memory](#time-and-memory) first.

The tool reads the `.sha256` sidecar beside the bundle and records it in `manifest.json`. A build that
completes lists the 20 tables and their rows; a build that stops names the section, the record key and the
property no column covers:

```text
error: table submitter: … record: key clinvar.submitter:509943: top-level field(s) no column covers: [name]
```

No published 1.1 bundle stops the build (see [What is verified](#what-is-verified)). If one does, build that
bundle with no `--column-set` (the wide default) and open an issue.

!!! note "If the build stops with a DuckDB `Parallel CSV Reader` error"
    On one of the 18 deltas (2026-08-16), `gkm-bundle-parquet` 2.0.0 stops with `NotImplementedException: Not
    implemented Error: The Parallel CSV Reader currently does not support a full read on this file`, with or
    without a column set. It comes from DuckDB reading the tool's own staging files, not from the bundle. Run the
    same command again with `--threads 1`, and pass `--threads 1` to `verify` too: both then complete, and the
    round trip is identical.

### 4. Prove that nothing was lost

```bash
uvx gkm-bundle-parquet@2.0.0 verify parquet/ --roundtrip --full clinvar-gkm-delta_2026-0928.json.gz
```

```text
verify pass: directory check: 0 problem(s); round trip: identical
```

`--roundtrip --full` rebuilds the records from the tables and compares them with the bundle's own records, by
their canonical form ([round trip](https://github.com/clingen-data-model/gkm-bundle-parquet/blob/v2.0.0/docs/round-trip.md)).
To keep the rebuilt bundle, run `rebuild parquet/ -o rebuilt.json.gz` instead: it ends with
`record-identical to the source` when every record matches.

---

## Time and memory

| Bundle | `build` (time, peak memory) | `verify --roundtrip` | Where |
| --- | ---: | ---: | --- |
| 2026-10-31 delta, 495,547 records | 22 s, 2.4 GB | 16 s, 0.9 GB | a 16 GB laptop |
| 2026-09-23 delta, 4,530,457 records (the largest) | 82 s, 3.3 GB | 66 s, 1.7 GB | a 16 GB laptop |
| a monthly, about 90 million records | 38 min, 65 GiB | 30 min | a 128 GiB machine |

Every delta builds on a laptop. A monthly needs a large machine: the full-bundle figures are the tool's own
measurements of a 1.2.0 full ([A full bundle](build-your-own.md#a-full-bundle)), and a 1.1.0 full with this
column set is the same size of job. On a smaller machine, pass `--memory-limit` and a `--work-dir` with about
65 GB free, and expect a much longer run; a monthly was not built on a laptop for this page. If you need only
part of a release, [cut a mini-bundle](build-your-own.md#cut-a-mini-bundle) instead: `select` takes the same
`--bundle-schema` and `--column-set`.

---

## What is verified

Run on 2026-11-20 with `gkm-bundle-parquet` 2.0.0, the published 1.1.0 column set and the 1.1.0 schema URL:

- **Every published `v1/1.1/` delta** (18 deltas, 2026-07-06 to 2026-10-31, 10,267,303 records):
  each built, `rebuild` reported it record-identical to the source, `verify --roundtrip --full` passed, and a
  separate record-by-record comparison of the rebuilt bundle with the source, keeping array order, found no
  difference. The 2026-08-16 delta needed `--threads 1` (see the note under [Build](#build)).
- **The newest monthly**, `clinvar-gkm_2026-11.json.gz` (source release 2026-10-31, 91,854,927 records), was
  not built: that needs a large machine. Instead it was streamed once, and every property each record holds was
  listed with the JSON kind of its value and the section each `#/…` pointer names, then compared with what the
  verified deltas hold. 528 records hold something no delta holds: the 38 `therapy` and 10 `therapyGroup`
  records, 463 somatic clinical impact propositions that point to a therapy, a therapy group or a condition set
  or carry a condition qualifier,
  and 17 statements and evidence lines with a method or condition extension no delta has. Built on their own
  with the column set, those 528 round-trip identically. Every other record holds only what the verified deltas
  hold. The scan took 26 minutes on the laptop.

---

## The 1.0 line { #the-10-line }

The 1.0 line (`v1/1.0/`, schema `1.0.1`) can't be built with `gkm-bundle-parquet`, with or without a column
set, for two reasons:

- **Its schema closes each part of a class.** In the 1.0.1 schema each class combines a GA4GH class with a
  ClinVar-GKM part (`allOf`), and the ClinVar-GKM part says `additionalProperties: false`. Read strictly, as the
  tool reads it, a variation may then hold only `extensions`, and a statement only `extensions`, `proposition`
  and `hasEvidenceLines`. The generated default has no column for `id`, `type` or `constraints`, and a column
  set can't add a property the schema doesn't allow, so the build stops on the first variation. The 1.1.0
  schema fixed this.
- **Some bundles hold a key twice.** In 10 of the 15 published `v1/1.0/` deltas, one to seven `allele` keys
  appear twice, with different `expressions`. The tool refuses a bundle with a repeated key
  (`section allele, key ga4gh:VA.…: appears 2 times`).

**Use the 1.1 line instead.** `v1/1.1/` holds a bundle for every release `v1/1.0/` holds: the same monthlies
(2026-07 to 2026-10) and the same weekly deltas (2026-07-06 to 2026-10-11), built from the same ClinVar
releases with schema 1.1.0. Build the tables from the `v1/1.1/` bundle of the release you need, as above. The
1.0 bundles themselves stay published unchanged; see [Previous Releases](../data-access/previous-releases.md).
