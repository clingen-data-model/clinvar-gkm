# Build Your Own Tables and Mini-Bundles

The published Parquet is built by one open tool, [`gkm-bundle-parquet`](https://github.com/clingen-data-model/gkm-bundle-parquet),
from the published JSON bundle. You can run the same tool yourself to:

- **build the tables** for any release, including releases whose Parquet is no longer published (for the frozen
  lines, see [Parquet for Previous Releases](previous-releases.md));
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

!!! info "Measured runs"
    Every command on this page was run with `gkm-bundle-parquet` 2.0.0 from PyPI, on an Apple M2 Pro laptop
    (16 GB of memory, 10 cores), against the published **2026-10-31 weekly delta**
    (`v1/1.1/deltas/clinvar-gkm-delta_2026-1031.json.gz`, 26 MB, 495,547 records), relabelled as schema 1.2.0 to
    match the 1.2 tables. The output quoted is the real output. Figures for a **full** bundle come from the tool's
    own release measurements, except the full-bundle `select`, which was run on this laptop against the
    2026-10-31 weekly full.

---

## Install

```bash
uvx gkm-bundle-parquet@2.0.0 version          # run a pinned release with no install
pipx install gkm-bundle-parquet==2.0.0        # or install the command
pip install gkm-bundle-parquet==2.0.0         # or into a virtual environment of your own
```

DuckDB is pinned exactly (1.5.4), because the bytes of the files depend on it, so `uvx` or `pipx` keep it apart
from a DuckDB you use for queries. The examples below write `gkm-bundle-parquet`; with `uvx`, put
`uvx gkm-bundle-parquet@2.0.0` in its place.

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
- **A 1.1.0 bundle gives wider tables.** Its schema leaves many classes open, so the same delta built with the
  1.1.0 schema has 339 top-level columns, and `generate` lists 181 JSON-text positions. The records are the same;
  only the columns differ. ClinVar-GKM publishes a column set that narrows them to what 1.1.0 bundles hold; see
  [Parquet for Previous Releases](previous-releases.md).

!!! note "1.2.0 schema URLs"
    w3id resolves a version's URL once ClinVar-GKM has tagged that version. Until the `1.2.0` tag exists, the 1.2.0
    URL returns 404; the runs on this page used a local copy of the 1.2.0 schema set.

The commands below use a shell variable for the two options:

```bash
P="--bundle-schema https://w3id.org/clingen/schema/clinvar-gkm/1.2.0/clinvar-gkm-bundle.schema.json --version-property schema_version"
```

---

## Build the tables

`build` reads one bundle and writes one Parquet file per section, plus `manifest.json` and `table-spec.json`:

```bash
gkm-bundle-parquet build --full clinvar-gkm-delta_2026-1031.json.gz $P --out parquet/
```

```text
built 20 table(s) of spec sections 2.0, 495547 rows
  sequenceReference                               2  f22d7c101464
  location                                    11127  fc513d9a09e6
  allele                                      16557  5e04e6f6f12b
  …
  propositionPathogenicity                   128868  df50d27432d0
  …
  evidenceLine                               140861  8bbc531b110a
  scv                                         33417  74d0129753b9
  vcv                                         70246  6d3490a3dc7b
  rcv                                         67768  e51e94c67090
manifest: parquet/manifest.json
```

The last column is the start of each file's sha256. Progress lines go to stderr.

On the delta: **28 s**, 2.5 GB peak memory, 23 MB of output (20 tables, `manifest.json`, `table-spec.json`).

- **The bundle's checksum.** Pass `--sha256 <hex>`, or keep the published `<file>.sha256` sidecar beside the
  bundle and the tool checks it. A bundle URL works as `--full` too; it is streamed.
- **Every row is checked.** Before a file is written, each row is turned back into JSON and compared with its
  source record. A difference stops the build; nothing is dropped silently.
- **What you get is the published layout.** The same bundle and schema give the same tables and the same
  `table_spec_sha256` as the published set.

### A full bundle

To build the tables of a whole release, pass a monthly or weekly full bundle (about 4.8 GB compressed, 91.9
million records in 2026-10-31). Measured by the tool's maintainers on the 2026-10-31 full relabelled as 1.2.0, on
a 16-core cloud machine with 128 GiB of memory:

| Command | Time | Peak memory |
| --- | ---: | ---: |
| `build` | 38 min | 65 GiB |
| `verify --bundle-recompute` | 9 min | |
| `verify --roundtrip` | 30 min | |
| `rebuild` | 20 min | |
| `validate` (`rs` engine) | 11 min | |

The output is 4.6 GB. Plan for about 65 GB of free working disk for a full build: the staged records and DuckDB's
spill files go to `--work-dir` (default: beside `--out`). A full build was not run on a laptop for this page.

**Memory.** Without `--memory-limit`, the tool gives DuckDB half the memory the process may use (the machine's, or
a container's limit when lower), and DuckDB spills to `--work-dir` past that. On a smaller machine set it
explicitly, and point `--work-dir` at a disk with room:

```bash
gkm-bundle-parquet build --full clinvar-gkm_2026-11.json.gz $P --out parquet/ \
    --memory-limit 12GB --work-dir /big/disk/tmp
```

The limit doesn't change the files: a build that spills writes the same bytes. Full builds have been measured
only on the 128 GiB machine above; on a smaller one, expect them to take longer. When you need only part of a
release, cut a mini-bundle instead.

---

## Cut a mini-bundle

A **selection** starts from rows of one table, the **driver**, and follows the bundle's `#/…` references to
collect related records. The result is a **mini-bundle**: those records, byte for byte as published, in the
bundle's own layout. It is a real bundle: every tool that reads ClinVar-GKM bundles reads it.

| Option | Meaning |
| --- | --- |
| `--driver <table>` | the table the selection starts from |
| `--where "<SQL>"` | a DuckDB condition over that table's columns, e.g. `name = 'OMIM'` |
| `--ids a,b` / `--ids-file f` | starting keys (added to `--where`) |
| `--follow out` | add every record a selected record points to (the default) |
| `--follow in` | add every record that points to a selected record |
| `--follow both` | both, from every record reached |
| `--max-depth N` | stop after N reference hops from the driver |
| `--sections a,b` | only traverse and write these sections |

Choose `--follow` and `--max-depth` with the bundle's hubs in mind. Following references **out** of a record
always ends: a statement points to its proposition, which points to its variant and condition. Following them
**in** to a widely shared record does not: `--follow in` from the condition `not provided` collects millions of
propositions. Keep `--max-depth` low whenever the walk can reach a condition, gene or submitter from the inside.

### One submitter's submissions

Every SCV of one submitter, their propositions and evidence lines, the variants and conditions they are about,
and the VCV and RCV statements that cite them:

```bash
gkm-bundle-parquet select --full clinvar-gkm-delta_2026-1031.json.gz $P \
    --driver submitter --where "name = 'Clingen Galactosemia Variant Curation Expert Panel, ClinGen'" \
    --follow both --max-depth 3 \
    --out galactosemia-ep.json.gz
```

```text
selected 465 record(s) in 7 section(s) from clinvar-gkm-delta_2026-1031.json.gz: galactosemia-ep.json.gz (29340 bytes, sha256 ccc3bb72…)
  variation                                       8
  submitter                                       1
  propositionPathogenicity                       76
  evidenceLine                                  152
  scv                                            76
  vcv                                            76
  rcv                                            76
```

**5 s** on the delta. From the submitter, depth 1 reaches its SCVs; depth 2 their propositions and the VCV and
RCV evidence lines that cite them; depth 3 the variants, the conditions and the citing VCV and RCV statements.
A delta holds only the records that changed that week, so the run also reported 70 references to records the
delta doesn't carry (unchanged conditions and variants); a selection from a full bundle has none.

### One variant

A variant's propositions and every statement about them, from a full bundle:

```bash
gkm-bundle-parquet select --full clinvar-gkm_2026-1031.json.gz $P \
    --driver variation --ids clinvar:10,clinvar:51592 \
    --follow in --max-depth 2 \
    --out two-variants.json.gz
```

`--follow in` from a variant reaches its propositions (depth 1) and the SCV, VCV and RCV statements about them
(depth 2). To add what those statements point to (submitters, conditions, the VRS records), run a second
selection from the statements with `--follow out`, for example `--driver vcv --ids-file vcv-ids.txt --follow out`.

Run on this laptop against the 2026-10-31 weekly full (4.8 GB) for four variants: **11 min**, two passes over
the file, under 100 MB of memory, 662 records. A selection streams the bundle, so it needs neither the memory nor
the disk of a full build.

### One gene's variants

The gene list on each variant points to `gene`, so `--follow in` from a gene reaches its variants, then their
propositions, then the statements:

```bash
gkm-bundle-parquet select --full clinvar-gkm_2026-1031.json.gz $P \
    --driver gene --where "name = 'MYH7'" \
    --follow in --max-depth 3 \
    --out myh7.json.gz
```

This is a full-bundle example: a weekly delta holds only the genes whose records changed. It was not run for
this page.

### Tables straight from a selection

`build` takes the same options and builds the selection's tables directly:

```bash
gkm-bundle-parquet build --full clinvar-gkm-delta_2026-1031.json.gz $P \
    --driver submitter --where "name = 'Clingen Galactosemia Variant Curation Expert Panel, ClinGen'" \
    --follow both --max-depth 3 \
    --out galactosemia-ep/
```

**8 s**, 0.5 GB peak memory, 324 KB of tables. Every file records the selection in its key-value metadata
(`gkm_bundle_parquet.selection`), and so does `manifest.json`. `verify --bundle-recompute` checks such a set
against its mini-bundle. `rebuild` refuses a set built with `--driver`; to get tables you can rebuild from,
`select` the mini-bundle first and `build --full` it.

---

## Rebuild the bundle

`rebuild` turns a full set of tables back into a bundle:

```bash
gkm-bundle-parquet rebuild parquet/ -o rebuilt.json.gz
```

```text
rebuilt rebuilt.json.gz: bundle schema 1.2.0, 17 section(s), 495547 records, 372644811 bytes of text, records sha256 1ff1c2dbe58c8f0ef72e9a84c3178be1c0b0b74f97e8f86e6a7d5fc83185bc7c (matches the manifest's records_sha256 and every section's section_records_sha256: record-identical to the source)
```

**15 s**, 1.1 GB peak memory, a 17 MB bundle. It needs every table, `manifest.json` and `table-spec.json`, but neither the
schema nor the source bundle. **Record-identical** means each rebuilt record has the same canonical JSON as its
source record: keys sorted, arrays compared as sets of values, numbers by value. The file's text differs (key
order, spacing); the records don't. The **records sha256** is a hash over every record's canonical form, which
anyone can recompute from a bundle with a JSON parser and sha256; the tool's
[round-trip.md](https://github.com/clingen-data-model/gkm-bundle-parquet/blob/main/docs/round-trip.md) defines it.

---

## Verify a set of tables

```bash
gkm-bundle-parquet verify parquet/                                                     # the directory alone
gkm-bundle-parquet verify parquet/ --roundtrip --full clinvar-gkm-delta_2026-1031.json.gz          # rebuild and compare
gkm-bundle-parquet verify parquet/ --bundle-recompute --full clinvar-gkm-delta_2026-1031.json.gz $P # recompute every value
```

```text
verify pass: directory check: 0 problem(s)
verify pass: directory check: 0 problem(s); round trip: identical
verify pass: directory check: 0 problem(s); bundle recompute: 0 group(s) differ
```

| Check | What it proves | Delta |
| --- | --- | ---: |
| `verify DIR` | every file matches the manifest's sha256 and row counts, and carries the expected metadata | < 1 s |
| `--roundtrip` | the tables rebuild the bundle's records exactly | 21 s, 1.1 GB |
| `--bundle-recompute` | every row and value equals what the bundle gives | 4 s, 0.4 GB |

This is how the published set is checked before each upload, and how you can check a downloaded copy against
the bundle of the same release.

---

## Validate a bundle

`validate` checks every record against the bundle's JSON Schema, each record on its own:

```bash
gkm-bundle-parquet validate clinvar-gkm-delta_2026-1031.json.gz $P
```

```text
bundle: clinvar-gkm-delta_2026-1031.json.gz (sha256 f6eefaa4…, not checked)
version: 1.2.0; schema set sha256 23610f38…
engine: rs; 10 workers
  section                                records  failing cpu ms/rec  compile s
  …
  scv                                     33,417        0      0.044        0.1
  vcv                                     70,246        0      0.055        0.0
  rcv                                     67,768        0      0.056        0.0
records: 495,547  failing: 0  (7.7 s)
PASS
```

**8 s** on the delta. `--failures bad.jsonl` writes each failing record's section, key and error paths. The
default engine is `jsonschema-rs`; `--engine python` uses the GA4GH GKM Toolkit's validator instead (much
slower; install `gkm-bundle-parquet[reference]`). Validate a bundle against its own `schema_version`'s schema.

---

## See the columns before you build

`generate` writes the column set the tables follow from, and lists every position the schema leaves as JSON
text or as an IRI without a declared target:

```bash
gkm-bundle-parquet generate $P -o clinvar-gkm-1.2.0.columns.yaml
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

A column set you write yourself is a **projection**: it narrows the tables (fewer columns, other names) and must
say `projection: <name>`. See
[column-set-format.md](https://github.com/clingen-data-model/gkm-bundle-parquet/blob/main/docs/column-set-format.md).
The published tables use no column set: they are the 1.2.0 schema's default.

Next: the [20 tables](tables.md) the default gives, and [moving from the 1.1 tables](migrating-from-1.1.md).
