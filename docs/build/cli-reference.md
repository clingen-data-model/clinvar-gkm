# CLI Reference

Every command and option of `gkm-bundle-parquet` **2.0.0**, the tool that builds Parquet tables and mini-bundles
from a ClinVar-GKM bundle, one line each, with a tested example for the main commands. The tool's own
[README at v2.0.0](https://github.com/clingen-data-model/gkm-bundle-parquet/blob/v2.0.0/README.md) is the
authority; `uvx gkm-bundle-parquet@2.0.0 <command> --help` prints the same options.
[Build Your Own Tables and Mini-Bundles](../parquet/build-your-own.md) explains when to use each command, with
timings on a full bundle.

!!! note "Prerequisites"
    - **[uv](https://docs.astral.sh/uv/getting-started/installation/)** (tested with 0.6.14), to run the tool as
      `uvx gkm-bundle-parquet@2.0.0`, or the tool installed as in
      [Install](../parquet/build-your-own.md#install). Python 3.10 or later (tested with 3.14.5).
    - **bash or zsh** on macOS or Linux (tested in zsh 5.9 and bash 5.2).
    - **Data:** the examples read the 2026-11-15 weekly delta, `clinvar-gkm-delta_2026-1115.json.gz` (5 MB), and
      its `.sha256` sidecar, in the folder you run them from. [Your First Dataset](first-dataset.md#get-the-input)
      downloads both. Each example finishes in under 15 seconds.
    - The examples use the shell array `P` for the schema options; set it once:

        ```bash
        P=(--bundle-schema https://w3id.org/clingen/schema/clinvar-gkm/1.2.0/clinvar-gkm-bundle.schema.json --version-property schema_version)
        ```

| Command | Does |
| --- | --- |
| [`build`](#build) | builds the Parquet tables of a bundle, or of a selection of it |
| [`select`](#select) | writes a selection as a mini-bundle: the selected records, byte for byte |
| [`rebuild`](#rebuild) | turns a full set of tables back into a bundle with identical records |
| [`verify`](#verify) | checks a set of tables: the directory alone, the round trip, or every value against the bundle |
| [`validate`](#validate) | validates every record of a bundle against its JSON Schema |
| [`generate`](#generate) | writes a schema's default column set, or checks a column set against it |
| [`compile-spec`](#compile-spec) | prints the compiled table spec of a schema and column set, with no build |
| [`version`](#version) | prints the tool, spec, policy, DuckDB and validator versions |

**Exit codes.** `0` success. `1` a check failed: `verify` found a problem, `validate` found a failing record (or
the bundle lacks a root property the schema requires), `generate --check` found a difference. `2` anything else:
a missing or unreadable input, an unknown option or section, a missing `--bundle-schema`, a refused column set,
a selection with no driver keys.

---

## Options shared by several commands

### The bundle

| Option | Commands | Meaning |
| --- | --- | --- |
| `--full <bundle>` | `build`, `select` (required); `verify` | the bundle: a path or URL, `.json` or `.json.gz`; a URL is streamed |
| `--sha256 <hex>` | `build`, `select`, `verify`, `validate` | the bundle's expected sha256; without it, a `<file>.sha256` sidecar beside the bundle is checked when there is one |

### The schema

| Option | Commands | Meaning |
| --- | --- | --- |
| `--bundle-schema <schema>` | required by `build`, `select`, `validate`, `generate`, `compile-spec`; optional for `verify` | the bundle's JSON Schema: a URL, a file, or a schema-set directory for [offline use](../parquet/build-your-own.md#offline-schema-set) |
| `--version-property <name>` | same | the root property holding the bundle's version: `schema_version` for ClinVar-GKM |
| `--column-set <file>` | `build`, `select`, `verify`, `generate --check`, `compile-spec` | a column set that is the schema's default written out, or a named projection; default: the generated default |

The tables are generated from the schema, so the schema decides the columns: pass the schema of the bundle's own
`schema_version` ([Name the bundle's schema](../parquet/build-your-own.md#name-the-bundles-schema)).

**Projections are limited in 2.0.0.** A column set of your own must declare `projection: <name>`, and can only
rename a column (`name as submitter_name`) or give a type to a position the schema leaves as JSON text. It can't
drop a column or a section: the build stops on a record holding a property no column covers. For fewer tables
use `--tables`; for fewer columns, copy the columns you want into your own file with DuckDB
([See the columns before you build](../parquet/build-your-own.md#see-the-columns-before-you-build)).

### The engine

| Option | Commands | Meaning |
| --- | --- | --- |
| `--threads <n>` | `build`, `select`, `rebuild`, `verify` | DuckDB threads (default: DuckDB's, one per core) |
| `--memory-limit <size>` | `build`, `select`, `rebuild`, `verify` | DuckDB's memory limit, e.g. `12GB` (default: half the memory the process may use, or of a container's limit); a lower limit spills more, the files are the same |
| `--work-dir <dir>` | `build`, `select`, `rebuild`, `verify` | where staged records and DuckDB spill files go (default: a directory beside `--out`); a full build needs about 30 GB free there |
| `--keep-work` | `build` | keep the staging files, and a selection's mini-bundle, after the build |

### Selection

`build` and `select` take these; `select` requires `--driver`. A selection starts from rows of the **driver**
table and follows the bundle's `#/…` pointers.

| Option | Meaning |
| --- | --- |
| `--driver <table>` | the table the selection starts from, e.g. `submitter`, `scv`, `variation`, `gene` |
| `--where "<expr>"` | a DuckDB boolean expression over the driver table as the build makes it (no `;`) |
| `--ids k1,k2` | driver keys, added to the `--where` matches |
| `--ids-file <file>` | a file of driver keys, one per line, added to the `--where` matches |
| `--follow out\|in\|both` | follow pointers out of the selected records (the default), into them, or both |
| `--max-depth <n>` | stop after `n` pointer hops from the driver (default: no limit); `0` keeps only the driver rows |
| `--sections a,b` | only traverse and write these sections |

- **Nested columns in `--where`.** A STRUCT field is reached by its dotted path, `classification.name =
  'Pathogenic'`, and a list by a list comprehension:
  `"[c.contributor FOR c IN contributions IF c.activityType = 'submitted'][1] = 'clinvar.submitter:500031'"`
  selects one submitter's SCVs from the `scv` table.
- **Every `--ids` key must be in the bundle.** One missing key stops the selection (`driver key(s) not in …;
  nothing was written`). To start from a list that may hold keys the bundle lacks, such as a delta, match them in
  `--where` instead: `--where "subject IN (SELECT column0 FROM read_csv('ids.txt', header = false))"`, as in
  [Gene-panel subset](../parquet/recipes.md#gene-panel).
- **No driver rows, no selection.** A `--where` that matches nothing stops with `no driver keys` (exit 2).
- **Hubs.** `--follow in` or `both` from a widely shared record (a condition, a gene, a submitter) reaches a large
  part of the bundle. Keep `--max-depth` low.

!!! warning "On a delta, set `--max-depth`"
    A delta omits the sections in which nothing changed that week (the 2026-11-15 delta has no
    `sequenceReference`, `copyNumberCount`, `therapy`, `therapyGroup` or somatic proposition sections). In 2.0.0 a
    walk that reaches a pointer into an omitted section keeps reading the bundle and does not finish: for
    example `--follow out` from `scv` with no `--max-depth` reaches `location` and then `sequenceReference`. A
    full bundle has every section and is not affected. On a delta, stop the walk before it gets there: from
    `scv`, `--follow out --max-depth 4` ends at `location` (tested on the 2026-11-15 delta).

---

## build

Reads one bundle and writes one Parquet file per section, plus `manifest.json` and `table-spec.json`. With
`--driver`, builds the tables of a selection instead.

| Option | Meaning |
| --- | --- |
| `--full`, `--sha256` | [the bundle](#the-bundle) |
| `--bundle-schema`, `--version-property`, `--column-set` | [the schema](#the-schema) |
| `--out <dir>` | the output directory (required) |
| `--tables a,b` | build only these tables (default: all); such a set can't be rebuilt or round-tripped |
| `--threads`, `--memory-limit`, `--work-dir`, `--keep-work` | [the engine](#the-engine) |
| `--driver`, `--where`, `--ids`, `--ids-file`, `--follow`, `--max-depth`, `--sections` | [selection](#selection) |

```bash
uvx gkm-bundle-parquet@2.0.0 build --full clinvar-gkm-delta_2026-1115.json.gz "${P[@]}" --out parquet/
```

```text
built 20 table(s) of spec sections 2.0, 39062 rows
  sequenceReference                               0  e3e7d2b96baf
  …
  scv                                         17562  333222b90a40
  vcv                                          2941  ca684960ee57
  rcv                                          2548  b7796596ea52
manifest: parquet/manifest.json
```

Two tables only, with the engine options:

```bash
uvx gkm-bundle-parquet@2.0.0 build --full clinvar-gkm-delta_2026-1115.json.gz "${P[@]}" --out two/ \
    --tables submitter,scv --threads 4 --memory-limit 2GB --work-dir work/ --keep-work
```

```text
built 2 table(s) of spec sections 2.0, 17572 rows
  submitter                                      10  6451c8a350e0
  scv                                         17562  333222b90a40
manifest: two/manifest.json
```

The files are the same bytes as the full build's `submitter` and `scv` (same sha256): the engine options don't
change the output. `--keep-work` left the staging directory under `work/`.

---

## select

Writes the mini-bundle of a selection: the selected records, verbatim, in the bundle's own layout (`.json.gz`;
the file must not exist). The same inputs and options give the same bytes.

| Option | Meaning |
| --- | --- |
| `--full`, `--sha256` | [the bundle](#the-bundle) |
| `--bundle-schema`, `--version-property`, `--column-set` | [the schema](#the-schema) |
| `--out <file>` | the mini-bundle to write (required) |
| `--threads`, `--memory-limit`, `--work-dir` | [the engine](#the-engine) |
| `--driver` (required), `--where`, `--ids`, `--ids-file`, `--follow`, `--max-depth`, `--sections` | [selection](#selection) |

Every SCV classified Pathogenic, with `--max-depth 0` (no pointers followed) and a nested `--where`:

```bash
uvx gkm-bundle-parquet@2.0.0 select --full clinvar-gkm-delta_2026-1115.json.gz "${P[@]}" \
    --driver scv --where "classification.name = 'Pathogenic'" --max-depth 0 \
    --out pathogenic-scvs.json.gz
```

```text
selected 2242 record(s) in 1 section(s) from clinvar-gkm-delta_2026-1115.json.gz: pathogenic-scvs.json.gz (491629 bytes, sha256 2253d30d…)
  scv                                          2242
```

One submitter and the SCVs that point to it, writing only those two sections:

```bash
uvx gkm-bundle-parquet@2.0.0 select --full clinvar-gkm-delta_2026-1115.json.gz "${P[@]}" \
    --driver submitter --ids clinvar.submitter:510823 --follow in --max-depth 1 \
    --sections submitter,scv --out hema-scvs.json.gz
```

```text
selected 288 record(s) in 2 section(s) from clinvar-gkm-delta_2026-1115.json.gz: hema-scvs.json.gz (64432 bytes, sha256 bc89e6be…)
  submitter                                       1
  scv                                           287
```

A selection from a delta can point to records the delta doesn't carry; the tool counts them as **dangling
pointers** and writes the mini-bundle anyway. A selection from a full bundle has none.

---

## rebuild

Writes a full set of tables back as a bundle whose records are identical to the source's (the same canonical
JSON: key order, array order and spacing don't count), and checks it against the records sha256s the build
recorded. Needs every table, `manifest.json` and `table-spec.json`, and no schema. Refuses a selection and a
build with `--tables`.

| Option | Meaning |
| --- | --- |
| `dir` | the built directory (positional) |
| `-o`, `--out <file>` | the bundle to write, `.json` or `.json.gz` (required) |
| `--threads`, `--memory-limit`, `--work-dir` | [the engine](#the-engine) |

```bash
uvx gkm-bundle-parquet@2.0.0 rebuild parquet/ -o rebuilt.json.gz
```

```text
rebuilt rebuilt.json.gz: bundle schema 1.2.0, 14 section(s), 39062 records, 68660443 bytes of text, records sha256 473016fd… (matches the manifest's records_sha256 and every section's section_records_sha256: record-identical to the source)
```

---

## verify

Checks a built directory against the spec the build wrote beside its manifest. Needs no schema; given
`--bundle-schema` (and `--column-set`, if the build had one), it also checks that they compile to that spec.

| Option | Meaning |
| --- | --- |
| `dir` | the built directory (positional) |
| *(none)* | the directory check: every file matches the manifest's sha256 and row counts, and carries the expected metadata |
| `--roundtrip` | rebuild the records (hashed, not written) and compare their sha256s with the recorded ones and, with `--full`, the bundle's own; a full build only |
| `--bundle-recompute` | recompute every row and value from the bundle given with `--full`; for a selection, `--full` is its mini-bundle |
| `--full`, `--sha256` | [the bundle](#the-bundle) to compare with |
| `--bundle-schema`, `--version-property`, `--column-set` | also check they compile to the spec that wrote the files |
| `--report <file.md>` | write a Markdown report there, and a `.json` beside it |
| `--threads`, `--memory-limit`, `--work-dir` | [the engine](#the-engine) |

```bash
uvx gkm-bundle-parquet@2.0.0 verify parquet/ --report verify-report.md
uvx gkm-bundle-parquet@2.0.0 verify parquet/ --roundtrip --full clinvar-gkm-delta_2026-1115.json.gz
uvx gkm-bundle-parquet@2.0.0 verify parquet/ --bundle-recompute --full clinvar-gkm-delta_2026-1115.json.gz "${P[@]}"
```

```text
report: verify-report.md and verify-report.json
verify pass: directory check: 0 problem(s)
verify pass: directory check: 0 problem(s); round trip: identical
verify pass: directory check: 0 problem(s); bundle recompute: 0 group(s) differ
```

---

## validate

Validates each record of a bundle on its own, as a one-section bundle with the bundle's version, so key patterns
are checked too.

| Option | Meaning |
| --- | --- |
| `bundle` | the bundle: a path or URL (positional) |
| `--bundle-schema`, `--version-property` | [the schema](#the-schema); validate against the schema of the bundle's own `schema_version` |
| `--sha256` | the bundle's expected sha256 |
| `--engine rs\|python` | `rs`, jsonschema-rs (the default); `python`, the GA4GH GKM Toolkit's validator, the reference (much slower; needs `gkm-bundle-parquet[reference]` and Python 3.11 or later) |
| `--workers <n>` | worker processes (default: one per CPU) |
| `--failures <file>` | write every failing record's section, key and errors there, as JSON lines |
| `--json <file>` | write the counts and timings there, as JSON |
| `--max-print <n>` | how many failing records to print (default 20) |

```bash
uvx gkm-bundle-parquet@2.0.0 validate clinvar-gkm-delta_2026-1115.json.gz "${P[@]}" \
    --workers 4 --failures bad.jsonl --json validate.json --max-print 5
```

```text
…
records: 39,062  failing: 0  (8.3 s)
PASS
```

`bad.jsonl` is empty when nothing fails. `validate.json` holds `bundle`, `bundle_sha256`, `engine`, `failing`,
`records`, `schema_set_sha256`, `seconds`, `sections`, `version` and `workers`. The `python` engine wasn't run
for this page.

---

## generate

Writes the default column set of a bundle schema: every collection, every property its record schema allows.
On stderr it lists every position kept as JSON text and every IRI with no declared target, with the reason.

| Option | Meaning |
| --- | --- |
| `--bundle-schema`, `--version-property` | [the schema](#the-schema) |
| `-o`, `--out <file>` | write the column set there (default: stdout) |
| `--check` | check `--column-set` against the default; exit 1 and list each difference if it differs |
| `--column-set <file>` | with `--check`: the column set to check |

```bash
uvx gkm-bundle-parquet@2.0.0 generate "${P[@]}" -o cols.yaml
uvx gkm-bundle-parquet@2.0.0 generate --check \
    --bundle-schema https://w3id.org/clingen/schema/clinvar-gkm/1.2.0/clinvar-gkm-bundle.schema.json \
    --column-set cols.yaml
```

```text
cols.yaml: complies: it compiles to the default (policy 2.0)
```

A column set names its own version property, so `--check` needs only `--bundle-schema` and `--column-set`.

---

## compile-spec

Prints the `sections` table spec a schema and column set compile to, as YAML, with no bundle and no build: every
table, column and type, and the three sha256s each Parquet file records.

| Option | Meaning |
| --- | --- |
| `--bundle-schema`, `--version-property`, `--column-set` | [the schema](#the-schema) |

```bash
uvx gkm-bundle-parquet@2.0.0 compile-spec "${P[@]}" > spec.yaml
head -5 spec.yaml
```

```text
# Table spec sections 2.0, compiled (ADR 0006): the default (policy 2.0).
# schema_set_sha256: 3b3920180d08f3343d7466ce55bbcb95f5cbc467c505a4e03797b8f3c48d6798
# column_set_sha256: e07436add989762e1ffaefe157565e660a5b5ee57178fcffdeb23b3826e7a6fd
# table_spec_sha256: 8f87c3bcc6cc4ee22da9c3c0f2b8a2cf666d848fbafee2d949ea17ab0a9a3b32 (of what affects the tables, compiler.table_spec_sha256)
name: sections
```

---

## version

| Option | Meaning |
| --- | --- |
| `--json` | print as JSON: `tool_version`, `table_spec`, `table_spec_version`, `policy_version`, `schema_version_rule`, `kv_prefix`, `kv_prefixes_read`, `duckdb_version`, `validate_engines` |

```bash
uvx gkm-bundle-parquet@2.0.0 version --json
```

```text
{
  "tool_version": "2.0.0",
  "table_spec": "sections",
  "table_spec_version": "2.0",
  "policy_version": "2.0",
  …
  "duckdb_version": "1.5.4",
  …
}
```

A script that records what built a set can keep this output beside the tables. An engine's `version` is `null`
when it isn't installed (the `python` engine without the `reference` extra).
