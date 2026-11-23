# Build Your Own Tables and Mini-Bundles

The published Parquet is built by one open tool, [`gkm-bundle-parquet`](https://github.com/clingen-data-model/gkm-bundle-parquet),
from the published JSON bundle. You can run the same tool yourself to:

- **build the tables** for any release, including releases whose Parquet is no longer published (for one week,
  see [Parquet for one weekly release](#parquet-for-one-weekly-release); for the frozen lines, see
  [Parquet for Previous Releases](previous-releases.md));
- **cut a mini-bundle**: the records of one submitter, one variant or one gene and everything they point to,
  as a small JSON bundle or a small set of tables;
- **rebuild the bundle** from a set of tables and prove the records are identical;
- **validate** a bundle against its JSON Schema.

| | |
| --- | --- |
| Source, issues, docs | [github.com/clingen-data-model/gkm-bundle-parquet](https://github.com/clingen-data-model/gkm-bundle-parquet): the [README](https://github.com/clingen-data-model/gkm-bundle-parquet#readme), [generate.md](https://github.com/clingen-data-model/gkm-bundle-parquet/blob/main/docs/generate.md) (how the tables follow from the schema), [column-set-format.md](https://github.com/clingen-data-model/gkm-bundle-parquet/blob/main/docs/column-set-format.md), [round-trip.md](https://github.com/clingen-data-model/gkm-bundle-parquet/blob/main/docs/round-trip.md), [validate.md](https://github.com/clingen-data-model/gkm-bundle-parquet/blob/main/docs/validate.md) |
| Package | [pypi.org/project/gkm-bundle-parquet](https://pypi.org/project/gkm-bundle-parquet/), version **2.0.0** |
| Writes | table spec `sections` 2.0, default policy 2.0, with DuckDB 1.5.4 (pinned) |
| Needs | Python 3.10 or later |

!!! note "Prerequisites"
    - **Python 3.10 or later** (tested with 3.14.5), and one way to run the tool:
      [uv](https://docs.astral.sh/uv/getting-started/installation/) (`uvx`, as the examples are written; tested
      with 0.6.14), [pipx](https://pipx.pypa.io/stable/), or `pip` in a virtual environment of your own. See
      [Install](#install).
    - **bash or zsh.** The commands work in both, on macOS and Linux.
    - **A bundle.** The examples read the **2026-11-15 weekly delta**,
      `clinvar-gkm-delta_2026-1115.json.gz` (5 MB, 39,062 records), downloaded in
      [Build the tables](#build-the-tables). The full-bundle examples read the newest monthly,
      `clinvar-gkm_00-latest.json.gz` (4.9 GB compressed), from [Monthly Full Bundles](../data-access/monthly-full.md).
    - **Resources.** Every command on the delta finishes in under 15 s with under 2 GB of memory. A full-bundle
      `build` takes about 3.5 hours on a 16 GB machine (10 GiB of memory, about 30 GB of free disk), or 40
      minutes on a large one ([A full bundle](#a-full-bundle)); a full-bundle `select` streams, taking about 11
      minutes and under 100 MB of memory.
    - Run every command from one working directory: later blocks read the files earlier blocks write.

!!! info "Measured runs"
    Every command on this page was run with `gkm-bundle-parquet` 2.0.0 from PyPI, on an Apple M2 Pro laptop
    (16 GB of memory, 10 cores), against the published **2026-11-15 weekly delta**
    (`v1/1.2/deltas/clinvar-gkm-delta_2026-1115.json.gz`, 5 MB, 39,062 records). The output quoted is the real
    output. Figures for a **full** bundle come from a 16 GB cloud machine and the tool's own release measurements
    ([A full bundle](#a-full-bundle)), except the full-bundle `select` and the
    [weekly replay](#rebuild-a-weeks-full-bundle), which were run on this laptop.

---

## Install

The quickest way to run the tool is [`uvx`](https://docs.astral.sh/uv/), from [uv](https://docs.astral.sh/uv/):
it fetches the pinned release and runs it, with nothing to install. **Every command on this page is written that
way**, as `uvx gkm-bundle-parquet@2.0.0 …`, so you can paste it as it is:

```bash
uvx gkm-bundle-parquet@2.0.0 version
```

```text
gkm-bundle-parquet 2.0.0: table spec sections 2.0, policy 2.0; duckdb 1.5.4
…
```

`version --json` prints the same as JSON (the tool, table spec, policy, DuckDB and validator versions), for a
script that records what built a set.

To have a `gkm-bundle-parquet` command instead, install it with one of these (uv, pipx, or pip into a virtual
environment of your own), then write `gkm-bundle-parquet` wherever this page writes `uvx gkm-bundle-parquet@2.0.0`:

```bash
uv tool install gkm-bundle-parquet==2.0.0
```

```bash
pipx install gkm-bundle-parquet==2.0.0
```

```bash
pip install gkm-bundle-parquet==2.0.0
```

!!! tip "`command not found: gkm-bundle-parquet`"
    The shell finds no installed command. Run the `uvx gkm-bundle-parquet@2.0.0` form, or install the tool with
    one of the lines above (after `uv tool install` or `pipx install`, open a new shell if the command is still
    not found: `uv tool update-shell` or `pipx ensurepath` puts their folder on your `PATH`).

DuckDB is pinned exactly (1.5.4), because the bytes of the files depend on it, so `uvx`, `uv tool` and `pipx`
keep it apart from a DuckDB you use for queries.

---

## Name the bundle's schema

Every command that reads a bundle takes the bundle's JSON Schema, `--bundle-schema`. The tables are generated from
that schema, so the schema decides the columns. For a ClinVar-GKM bundle, pass the schema `$id` of the bundle's
own `schema_version`, and `--version-property schema_version`:

| Bundle `schema_version` | `--bundle-schema` |
| --- | --- |
| `1.2.0` (line `v1/1.2/`) | `https://w3id.org/clingen/schema/clinvar-gkm/1.2.0/clinvar-gkm-bundle.schema.json` |
| `1.1.0` (line `v1/1.1/`) | `https://w3id.org/clingen/schema/clinvar-gkm/1.1.0/clinvar-gkm-bundle.schema.json` |

The tool fetches the schema and every schema it references once, and caches them
(`~/.cache/gkm-bundle-parquet/`). A schema-set directory works too, for offline use.

- **A 1.2.0 bundle gives exactly the tables this guide documents.** Its schema narrows ClinVar-GKM's classes and
  declares the target table of most references, so nearly every value gets a typed column: 146 top-level columns
  over the 20 tables. `generate` lists the 51 positions it keeps as JSON text, mostly extensions nested inside
  extensions.
- **A 1.1.0 bundle gives wider tables.** Its schema leaves many classes open, so the 1.1.0 2026-10-31 delta
  (495,547 records) built with the 1.1.0 schema has 339 top-level columns, and `generate` lists 181 JSON-text
  positions. The records are the same;
  only the columns differ. ClinVar-GKM publishes a column set that narrows them to what 1.1.0 bundles hold; see
  [Parquet for Previous Releases](previous-releases.md).

The commands below use a shell array for the two options, written `"${P[@]}"`; an array works in both bash and
zsh, where a plain string variable would reach the tool as one argument. Set it once in the shell you run the
other blocks in:

```bash
P=(--bundle-schema https://w3id.org/clingen/schema/clinvar-gkm/1.2.0/clinvar-gkm-bundle.schema.json --version-property schema_version)
```

---

## Build the tables

Download the 2026-11-15 weekly delta and its checksum sidecar into the working directory. Every delta example on
this page reads it. Its path changes when its month ends (it moves to `deltas/2026-11/`), so the commands look it
up in the line's `index.json`:

```bash
DELTA=$(curl -fsS https://data.clinvar-gkm.org/v1/1.2/index.json | python3 -c '
import json, sys
print(next(d["bundle"]["path"] for d in json.load(sys.stdin)["deltas"] if d["release"] == "2026-11-15"))')
curl -fO "https://data.clinvar-gkm.org/${DELTA}"
curl -fO "https://data.clinvar-gkm.org/${DELTA}.sha256"
```

`build` reads one bundle and writes one Parquet file per section, plus `manifest.json` and `table-spec.json`
(uses `P` from [Name the bundle's schema](#name-the-bundles-schema)):

```bash
uvx gkm-bundle-parquet@2.0.0 build --full clinvar-gkm-delta_2026-1115.json.gz "${P[@]}" --out parquet/
```

```text
built 20 table(s) of spec sections 2.0, 39062 rows
  sequenceReference                               0  e3e7d2b96baf
  location                                      176  8b17d4d0e861
  allele                                        230  dbc7056a155d
  …
  propositionPathogenicity                     3399  4f59dd9944fe
  …
  evidenceLine                                 6064  038fd5c573b3
  scv                                         17562  333222b90a40
  vcv                                          2941  ca684960ee57
  rcv                                          2548  b7796596ea52
manifest: parquet/manifest.json
```

The last column is the start of each file's sha256. Progress lines go to stderr. A delta holds only the records
that changed that week, so some tables are empty.

On the delta: **9 s**, 1.9 GB peak memory, 5 MB of output (20 tables, `manifest.json`, `table-spec.json`).

- **The bundle's checksum.** Pass `--sha256 <hex>`, or keep the published `<file>.sha256` sidecar beside the
  bundle and the tool checks it. A bundle URL works as `--full` too; it is streamed.
- **Every row is checked.** Before a file is written, each row is turned back into JSON and compared with its
  source record. A difference stops the build; nothing is dropped silently.
- **What you get is the published layout.** The same bundle and schema give the same tables and the same
  `table_spec_sha256` as the published set.
- **Only some tables.** `--tables submitter,scv` builds only those tables (on the delta: 4 s, 1.0 GB peak
  memory). Such a set is for querying: `verify` reports the other tables missing, and `rebuild` and
  `verify --roundtrip` need every table.

### A full bundle

To build the tables of a whole release, pass a monthly or weekly full bundle (about 4.9 GB compressed; 91,973,603
records in the 2026-11-15 weekly full), such as `clinvar-gkm_00-latest.json.gz` from
[Monthly Full Bundles](../data-access/monthly-full.md). It builds on a 16 GB machine; more memory makes it faster.

| Command | 16 GB machine | 128 GiB machine |
| --- | ---: | ---: |
| `build` | 3 h 19 min, 10.0 GiB peak | 38 min, 65 GiB peak |
| `verify --bundle-recompute` | | 9 min |
| `verify --roundtrip` | over 2 h (not run to the end) | 30 min |
| `rebuild` | | 20 min |
| `validate` (`rs` engine) | | 11 min |

The **16 GB machine** is a Google Cloud `e2-standard-4` (4 vCPUs, 16 GB of memory, SSD, Debian 12), building the
2026-11-15 weekly full on 2026-11-22 with the defaults and a `--work-dir`. The same command for the newest monthly
(replace `/big/disk/tmp` with a directory on a disk with about 30 GB free):

```bash
uvx gkm-bundle-parquet@2.0.0 build --full clinvar-gkm_00-latest.json.gz "${P[@]}" --out parquet-full/ \
    --work-dir /big/disk/tmp
```

All 20 tables were written, with no `--threads 1` needed. The machine as a whole peaked at 11.3 GiB used, with no
swap. The round trip was stopped after 2 hours, still running, when the measurement ended. The **128 GiB machine**
figures are the tool maintainers' own, on a 16-core cloud machine, for the 2026-10-31 full relabelled as 1.2.0.

The output is 4.6 GB. **Disk:** the staged records and DuckDB's spill files go to `--work-dir` (default: beside
`--out`); on the 16 GB machine they peaked at 24 GiB beside the bundle, so plan for about 30 GB free there plus the
bundle and the output. `validate` was also run on the laptop, on a full bundle: 24 minutes, with 0 failing records
(see [Parquet for one weekly release](#parquet-for-one-weekly-release)).

**Memory.** Without `--memory-limit`, the tool gives DuckDB half the memory the process may use (the machine's, or
a container's limit when lower), and DuckDB spills to `--work-dir` past that. The limit is DuckDB's, not the
whole process's: on the 16 GB machine the default gave DuckDB about 7.8 GiB and the process peaked at 10.0 GiB.
So the default suits a machine the build has to itself. Set `--memory-limit` lower only when other work needs the
memory, and leave about 3 GB above it for the rest of the process; a lower limit means more spilling and a slower
build, and wasn't measured. The limit doesn't change the files: a build that spills writes the same bytes. When
you need only part of a release, cut a mini-bundle instead.

---

## Parquet for one weekly release { #parquet-for-one-weekly-release }

`build` reads one bundle (`--full`), so a full set of tables for one week is built from that week's full bundle:

| The week | How |
| --- | --- |
| The newest release | Already published at `v1/1.2/parquet/`; see [Parquet Files](../data-access/parquet.md) |
| A week in the current month | Download its weekly full from `v1/1.2/weekly/` ([Weekly Full Bundles](../data-access/weekly-full.md)) and `build --full` it |
| Any earlier week | Rebuild that week's full bundle from a monthly plus deltas (below), then `build --full` it |

Building any full bundle takes about 3.5 hours on a 16 GB machine, or 40 minutes on a large one
([A full bundle](#a-full-bundle)). To get only some of the week's records, use its full bundle for
[selections](#cut-a-mini-bundle) instead: `select` streams it.

### Rebuild a week's full bundle

Weekly fulls are kept only for the current month. For an earlier week, download
[`replay-bundle.py`](../assets/scripts/replay-bundle.py), a script ClinVar-GKM publishes. It needs only `python3`
(3.9 or later, standard library), in bash or zsh:

```bash
curl -fsSO --retry 5 https://dataexchange.clinicalgenome.org/clinvar-gkm/1.2/assets/scripts/replay-bundle.py
python3 replay-bundle.py --release 2026-11-15 --plan
```

```text
line v1/1.2, release 2026-11-15
  monthly clinvar-gkm_2026-11.json.gz (source_release 2026-10-31, 4,881,641,096 bytes)
  delta   clinvar-gkm-delta_2026-1108.json.gz (60,824,851 bytes)
  delta   clinvar-gkm-delta_2026-1115.json.gz (5,355,360 bytes)
```

`--plan` lists what it would use and stops. Without it, the script downloads them and writes the week's bundle:

```bash
python3 replay-bundle.py --release 2026-11-15
```

What it does:

- **It picks the bundles from `index.json`** as [Rebuild a past week](../data-access/weekly-deltas.md#rebuild-a-past-week)
  says: the newest official monthly whose `source_release` is on or before the week (never the `00-latest`
  copy), and every delta after that `source_release`, up to and including the week, in release order. It checks
  the chain (each delta's `baseline_release` is the release before it) and stops on a gap.
- **It checks every download.** Each bundle's sha256 must match `index.json`. Downloads are retried, and a
  partial download resumes. A bundle already in the folder (`--dir`, default the current one) is used when its
  sha256 matches, so a monthly you downloaded before isn't downloaded again.
- **It needs little memory.** It reads the deltas into memory as text, section by section: each delta's
  deletes (from its manifest) and then its records. It then streams the monthly once: a record a delta replaced
  is written from the delta, a deleted one is dropped, any other is copied as it is, and each section ends with
  the deltas' new records.
- **It writes the published layout.** The result, `clinvar-gkm_2026-1115.replayed.json.gz`, has the same
  one-record-per-line layout and `schema_version` as the published bundles, and a `.sha256` sidecar beside it.

Measured on the laptop, rebuilding 2026-11-15 from the 2026-11 monthly and the 2026-11-08 and 2026-11-15 deltas
(1,818,764 records and 1,669,779 deletes): **7.6 minutes** in an empty folder, downloads included (6.4 minutes
with the monthly already there), 2.2 GB peak memory, a 4.9 GB bundle of 91,973,603 records. Both runs wrote the
same bytes (sha256 `876b41ec…`): the output doesn't depend on the run.

**It matches the published weekly full.** Compared with `v1/1.2/weekly/clinvar-gkm_2026-1115.json.gz` section by
section, by the record count and the sum of the sha256 of every record line (its key and its text, so the order
of records doesn't matter), all 20 sections are equal: every record of the rebuilt bundle has the published
record's exact text. Only the order of the records within a section differs. And the tool reads it:

```bash
uvx gkm-bundle-parquet@2.0.0 validate clinvar-gkm_2026-1115.replayed.json.gz "${P[@]}"
```

```text
bundle: clinvar-gkm_2026-1115.replayed.json.gz (sha256 876b41ecb379019726fa1f80124400a6770bde359b33b2f1a787fb14c35436aa, sidecar)
version: 1.2.0; schema set sha256 3b3920180d08f3343d7466ce55bbcb95f5cbc467c505a4e03797b8f3c48d6798
engine: rs; 10 workers
  section                                records  failing cpu ms/rec  compile s
  …
records: 91,973,603  failing: 0  (1,438.0 s)
PASS
```

Then build it, as for any full bundle ([A full bundle](#a-full-bundle); not run on the replayed file for this page,
which holds the same records as the weekly full measured there):

```bash
uvx gkm-bundle-parquet@2.0.0 build --full clinvar-gkm_2026-1115.replayed.json.gz "${P[@]}" --out parquet-2026-1115/
```

For a week of the frozen 1.1 line, add `--line v1/1.1` to the script, and build with the 1.1.0 schema and column
set ([Parquet for Previous Releases](previous-releases.md)). Tested on 1.1's 2026-10-24 (the 2026-10 monthly and
four deltas, 91,502,593 records, 7.3 minutes with the downloads), every record matches the published weekly full
of that week, but not every one byte for byte: 1,461 `condition` records list their `aliases` in another order.
The 1.1 pipeline wrote that array in the order its source gave, which changed between releases (1.2.0 sorts it),
so a 1.1 replay keeps the order of the monthly and deltas. As sets of values, the tool's round-trip comparison,
they are identical.

---

---

## Cut a mini-bundle

A **selection** starts from rows of one table, the **driver**, and follows the bundle's `#/…` references to
collect related records. The result is a **mini-bundle**: those records, byte for byte as published, in the
bundle's own layout. It is a real bundle: every tool that reads ClinVar-GKM bundles reads it.

| Option | Meaning |
| --- | --- |
| `--driver <table>` | the table the selection starts from |
| `--where "<SQL>"` | a DuckDB condition over that table's columns, e.g. `name = 'OMIM'`; a field inside a STRUCT column by its dotted path, e.g. `classification.name = 'Pathogenic'` |
| `--ids a,b` / `--ids-file f` | starting keys (added to `--where`) |
| `--follow out` | add every record a selected record points to (the default) |
| `--follow in` | add every record that points to a selected record |
| `--follow both` | both, from every record reached |
| `--max-depth N` | stop after N reference hops from the driver; `0` keeps only the driver rows `--where` matched |
| `--sections a,b` | only traverse and write these sections |

Choose `--follow` and `--max-depth` with the bundle's hubs in mind. Following references **out** of a record
always ends: a statement points to its proposition, which points to its variant and condition. Following them
**in** to a widely shared record does not: `--follow in` from the condition `not provided` collects millions of
propositions. Keep `--max-depth` low whenever the walk can reach a condition, gene or submitter from the inside.

### One submitter's submissions

Every SCV of one submitter, their propositions and evidence lines, the variants and conditions they are about,
and the VCV and RCV statements that cite them:

```bash
uvx gkm-bundle-parquet@2.0.0 select --full clinvar-gkm-delta_2026-1115.json.gz "${P[@]}" \
    --driver submitter --where "name = 'ClinGen Leukodystrophy and Leukoencephalopathy Variant Curation Expert Panel, ClinGen'" \
    --follow both --max-depth 3 \
    --out leukodystrophy-ep.json.gz
```

```text
selected 219 record(s) in 5 section(s) from clinvar-gkm-delta_2026-1115.json.gz: leukodystrophy-ep.json.gz (17718 bytes, sha256 989c64af…)
  submitter                                       1
  evidenceLine                                   73
  scv                                            72
  vcv                                             1
  rcv                                            72
```

**1 s** on the delta. From the submitter, depth 1 reaches its SCVs; depth 2 their propositions and the VCV and
RCV evidence lines that cite them; depth 3 the variants, the conditions and the citing VCV and RCV statements.
A delta holds only the records that changed that week: here the SCVs changed but their propositions didn't, so
the walk stops at them, and the run also reported 72 references to records the delta doesn't carry (the
unchanged propositions). A selection from a full bundle has none.

### One variant

A variant's propositions and every statement about them, from a full bundle (`clinvar-gkm_00-latest.json.gz`,
from [Monthly Full Bundles](../data-access/monthly-full.md)):

```bash
uvx gkm-bundle-parquet@2.0.0 select --full clinvar-gkm_00-latest.json.gz "${P[@]}" \
    --driver variation --ids clinvar:10,clinvar:51592 \
    --follow in --max-depth 2 \
    --out two-variants.json.gz
```

`--follow in` from a variant reaches its propositions (depth 1) and the SCV, VCV and RCV statements about them
(depth 2). To add what those statements point to (submitters, conditions, the VRS records), run a second
selection from the statements with `--follow out`, for example `--driver vcv --ids-file vcv-ids.txt --follow out`.

Run on this laptop against the `2026-11` monthly (4.9 GB): **11 min**, two passes over the file, under 100 MB
of memory, 336 records. A selection streams the bundle, so it needs neither the memory nor
the disk of a full build.

### One gene's variants

The gene list on each variant points to `gene`, so `--follow in` from a gene reaches its variants, then their
propositions, then the statements:

```bash
uvx gkm-bundle-parquet@2.0.0 select --full clinvar-gkm_00-latest.json.gz "${P[@]}" \
    --driver gene --where "name = 'MYH7'" \
    --follow in --max-depth 3 \
    --out myh7.json.gz
```

This is a full-bundle example, and it was not run for this page on a full bundle. A weekly delta holds only the
genes whose records changed: the 2026-11-15 delta holds five, and MYH7 isn't one of them, so on the delta this
command stops with `no driver keys`. With one of the delta's genes, `--where "name = 'TMEM266-AS1'"`, the same
command selects the gene and the 3 changed variants that point to it, in **1 s**.

### Rows of one table

`--max-depth 0` follows no references, so a selection is a plain filter on the driver table. `--where` reaches
into STRUCT columns by their dotted path. Every SCV classified Pathogenic in the delta:

```bash
uvx gkm-bundle-parquet@2.0.0 select --full clinvar-gkm-delta_2026-1115.json.gz "${P[@]}" \
    --driver scv --where "classification.name = 'Pathogenic'" \
    --max-depth 0 \
    --out pathogenic-scvs.json.gz
```

```text
selected 2242 record(s) in 1 section(s) from clinvar-gkm-delta_2026-1115.json.gz: pathogenic-scvs.json.gz (491629 bytes, sha256 2253d30d…)
  scv                                          2242
```

**2 s**, 0.45 GB peak memory. The result is a bundle with one section; `validate` passes it.

### Tables straight from a selection

`build` takes the same options and builds the selection's tables directly:

```bash
uvx gkm-bundle-parquet@2.0.0 build --full clinvar-gkm-delta_2026-1115.json.gz "${P[@]}" \
    --driver submitter --where "name = 'ClinGen Leukodystrophy and Leukoencephalopathy Variant Curation Expert Panel, ClinGen'" \
    --follow both --max-depth 3 \
    --out leukodystrophy-ep/
```

**3 s**, 0.3 GB peak memory, 264 KB of tables. Every file records the selection in its key-value metadata
(`gkm_bundle_parquet.selection`), and so does `manifest.json`. `verify --bundle-recompute` checks such a set
against its mini-bundle. `rebuild` refuses a set built with `--driver`; to get tables you can rebuild from,
`select` the mini-bundle first and `build --full` it.

---

## Rebuild the bundle

`rebuild` turns a full set of tables back into a bundle:

```bash
uvx gkm-bundle-parquet@2.0.0 rebuild parquet/ -o rebuilt.json.gz
```

```text
rebuilt rebuilt.json.gz: bundle schema 1.2.0, 14 section(s), 39062 records, 68660443 bytes of text, records sha256 473016fd65cf2b61a81c04487597fa6f4b2a6cdea71ee694a14e6b518cb66927 (matches the manifest's records_sha256 and every section's section_records_sha256: record-identical to the source)
```

**5 s**, 0.7 GB peak memory, a 4 MB bundle. It needs every table, `manifest.json` and `table-spec.json`, but neither the
schema nor the source bundle. **Record-identical** means each rebuilt record has the same canonical JSON as its
source record: keys sorted, arrays compared as sets of values, numbers by value. The file's text differs (key
order, spacing); the records don't. The **records sha256** is a hash over every record's canonical form, which
anyone can recompute from a bundle with a JSON parser and sha256; the tool's
[round-trip.md](https://github.com/clingen-data-model/gkm-bundle-parquet/blob/main/docs/round-trip.md) defines it.

---

## Verify a set of tables

```bash
uvx gkm-bundle-parquet@2.0.0 verify parquet/
uvx gkm-bundle-parquet@2.0.0 verify parquet/ --roundtrip --full clinvar-gkm-delta_2026-1115.json.gz
uvx gkm-bundle-parquet@2.0.0 verify parquet/ --bundle-recompute --full clinvar-gkm-delta_2026-1115.json.gz "${P[@]}"
```

The first checks the directory alone, the second rebuilds the records and compares them with the bundle's, and
the third recomputes every value from the bundle:

```text
verify pass: directory check: 0 problem(s)
verify pass: directory check: 0 problem(s); round trip: identical
verify pass: directory check: 0 problem(s); bundle recompute: 0 group(s) differ
```

| Check | What it proves | Delta |
| --- | --- | ---: |
| `verify DIR` | every file matches the manifest's sha256 and row counts, and carries the expected metadata | < 1 s |
| `--roundtrip` | the tables rebuild the bundle's records exactly | 6 s, 0.7 GB |
| `--bundle-recompute` | every row and value equals what the bundle gives | 1 s, 0.2 GB |

This is how the published set is checked before each upload, and how you can check a downloaded copy against
the bundle of the same release. Add `--report verify-report.md` to any of the three to keep the result as a
Markdown report, with a `verify-report.json` beside it.

---

## Validate a bundle

`validate` checks every record against the bundle's JSON Schema, each record on its own:

```bash
uvx gkm-bundle-parquet@2.0.0 validate clinvar-gkm-delta_2026-1115.json.gz "${P[@]}"
```

```text
bundle: clinvar-gkm-delta_2026-1115.json.gz (sha256 b370d385…, sidecar)
version: 1.2.0; schema set sha256 3b392018…
engine: rs; 10 workers
  section                                records  failing cpu ms/rec  compile s
  …
  scv                                     17,562        0      0.050        0.0
  vcv                                      2,941        0      0.069        0.0
  rcv                                      2,548        0      0.079        0.0
records: 39,062  failing: 0  (3.7 s)
PASS
```

**4 s** on the delta. `--failures bad.jsonl` writes each failing record's section, key and error paths. The
default engine is `jsonschema-rs`; `--engine python` uses the GA4GH GKM Toolkit's validator instead (much
slower; install `gkm-bundle-parquet[reference]`). Validate a bundle against its own `schema_version`'s schema.

---

## See the columns before you build

`generate` writes the column set the tables follow from, and lists every position the schema leaves as JSON
text or as an IRI without a declared target:

```bash
uvx gkm-bundle-parquet@2.0.0 generate "${P[@]}" -o clinvar-gkm-1.2.0.columns.yaml
```

```yaml
schema: "https://w3id.org/clingen/schema/clinvar-gkm/1.2.0/clinvar-gkm-bundle.schema.json"
version_property: "schema_version"
sections:
  sequenceReference: {type, name, extensions, refgetAccession, residueAlphabet, moleculeType}
  location: {id, type, digest, sequenceReference, start, end}
  allele: {id, type, name, digest, expressions, location, state}
  …
```

A column set you write yourself is a **projection** and must say `projection: <name>`. In 2.0.0 a projection can
rename a column (`name as submitter_name`) and give a type to a position the schema leaves as JSON text, but it
can't drop data: it must list every section, and the build stops on any record that holds a property no column
covers. The 1.2.0 schema allows only what the pipeline writes, so a 1.2.0 column set has no column it can leave
out. On the 2026-11-15 delta, leaving `name` out of `submitter`, and leaving the `submitter` section out, stop the
build with:

```text
error: table submitter: query failed: Invalid Input Error: table submitter: record: key clinvar.submitter:509533: top-level field(s) no column covers: [name]
error: schema …/1.2.0/clinvar-gkm-bundle.schema.json: section submitter: position (the record): the collection has no entry in the column set; the column set must list its properties
```

The [1.1.0 column set](previous-releases.md#the-110-column-set) has fewer columns than its default only because
the 1.1.0 schema allows properties no 1.1 bundle holds. See
[column-set-format.md](https://github.com/clingen-data-model/gkm-bundle-parquet/blob/main/docs/column-set-format.md).
The published tables use no column set: they are the 1.2.0 schema's default.

To get **fewer tables**, build with `--tables` ([Build the tables](#build-the-tables)). To get **fewer columns**,
build the tables and copy the columns you want into a file of your own with DuckDB, as in
[Materialize the joins you repeat](performance.md#materialize-join-tables) (continues from
[Build the tables](#build-the-tables)):

```bash
duckdb -c "COPY (SELECT id, classification.name AS classification, proposition FROM 'parquet/scv.parquet') TO 'scv-narrow.parquet' (FORMAT parquet)"
```

Such a file is yours to query; the tool's `verify` and `rebuild` don't read it.

Next: the [20 tables](tables.md) the default gives, and [moving from the 1.1 tables](migrating-from-1.1.md).
