# Your First Dataset

This page builds one small dataset end to end: the submissions one laboratory added to ClinVar in one week, as
Parquet tables, queried with DuckDB, and as a mini-bundle of the published records. It reads a 5 MB weekly delta
and takes about five minutes, most of it reading.

!!! note "Prerequisites"
    - **[uv](https://docs.astral.sh/uv/getting-started/installation/)**, to run `gkm-bundle-parquet` 2.0.0 with
      `uvx` (tested with uv 0.6.14 and Python 3.14.5; the tool needs Python 3.10 or later). To install the tool
      instead, see [Install](../parquet/build-your-own.md#install).
    - **[DuckDB CLI](https://duckdb.org/docs/installation/)**, tested with 1.5.4, and `curl` and `python3`.
    - **bash or zsh**, on macOS or Linux. Tested in zsh 5.9, bash 5.2 and macOS's bash 3.2.
    - **Data:** the 2026-11-15 weekly delta (5 MB) and two small published Parquet tables, `submitter.parquet`
      (0.1 MB) and `condition.parquet` (2 MB), all downloaded below. Every command finishes in a few seconds
      with under 2 GB of memory.
    - Run the blocks in order, in one shell and one folder: later blocks use the files and the `P` array that
      earlier blocks make.

---

## Get the input

Make a folder and download the 2026-11-15 weekly delta with its checksum sidecar. A delta's path changes when its
month ends, so the command looks the path up in the line's `index.json`:

```bash
mkdir -p first-dataset && cd first-dataset
DELTA=$(curl -fsS https://data.clinvar-gkm.org/v1/1.2/index.json | python3 -c '
import json, sys
print(next(d["bundle"]["path"] for d in json.load(sys.stdin)["deltas"] if d["release"] == "2026-11-15"))')
curl -fO "https://data.clinvar-gkm.org/${DELTA}"
curl -fO "https://data.clinvar-gkm.org/${DELTA}.sha256"
```

A **delta** holds only the records that changed in that week's release. That makes it the right input for "what
changed this week", and the wrong input for "everything about X" (see [What the result covers](#what-the-result-covers)).

---

## Find the submitter

Submitters are identified by id. Look the id up by name in the published `submitter.parquet`:

```bash
curl -fO https://data.clinvar-gkm.org/v1/1.2/parquet/submitter.parquet
duckdb -c "SELECT id, name FROM 'submitter.parquet' WHERE name ILIKE 'hema,%'"
```

```text
┌──────────────────────────┬──────────────────────────────────────────────────────────┐
│            id            │                           name                           │
│         varchar          │                         varchar                          │
├──────────────────────────┼──────────────────────────────────────────────────────────┤
│ clinvar.submitter:510823 │ Hema, HEMA – Genetic and Molecular Diagnostic Laboratory │
└──────────────────────────┴──────────────────────────────────────────────────────────┘
```

HEMA's first submissions to ClinVar are in the 2026-11-15 release.

---

## Build the tables

Every command that reads a bundle needs the bundle's schema. Put the two schema options in a shell array; an
array works in both bash and zsh, where a plain string variable would reach the tool as one argument:

```bash
P=(--bundle-schema https://w3id.org/clingen/schema/clinvar-gkm/1.2.0/clinvar-gkm-bundle.schema.json --version-property schema_version)
```

Build the tables of a **selection**: start from the submitter (`--driver submitter --ids …`), follow pointers in
both directions for two hops (`--follow both --max-depth 2`), and write a table per section:

```bash
uvx gkm-bundle-parquet@2.0.0 build --full clinvar-gkm-delta_2026-1115.json.gz "${P[@]}" \
    --driver submitter --ids clinvar.submitter:510823 \
    --follow both --max-depth 2 \
    --out hema/
```

```text
built 20 table(s) of spec sections 2.0, 1149 rows, a selection driven by submitter
  …
  submitter                                       1  80e5a1eaa6de
  propositionPathogenicity                      287  4556b6f69c83
  …
  evidenceLine                                  574  9df13aafdb32
  scv                                           287  ca7d38662aef
  …
manifest: hema/manifest.json
```

Progress lines go to stderr; tables with no rows are written too. The walk, hop by hop:

| Hop | Direction | Records |
| --- | --- | --- |
| 0 | the driver | the submitter |
| 1 | in: records that point to the submitter | its 287 SCVs |
| 2 | out of the SCVs, and in to them | the 287 propositions they assert; the 574 VCV and RCV evidence lines that cite them |

`--max-depth` keeps the walk small. Without it, `--follow both` keeps going through every shared record (a
condition, a gene) and collects much of the bundle.

---

## Query the tables

Count the week's submissions by classification. The variant is the proposition's `subject`:

```bash
duckdb -c "
SELECT s.classification.name     AS classification,
       count(*)                  AS scvs,
       count(DISTINCT p.subject) AS variants
FROM 'hema/scv.parquet' s
JOIN 'hema/propositionPathogenicity.parquet' p ON p.id = s.proposition
GROUP BY ALL
ORDER BY scvs DESC"
```

```text
┌────────────────────────────┬───────┬──────────┐
│       classification       │ scvs  │ variants │
│          varchar           │ int64 │  int64   │
├────────────────────────────┼───────┼──────────┤
│ Uncertain significance     │   191 │      191 │
│ Pathogenic                 │    66 │       66 │
│ Likely pathogenic          │    26 │       26 │
│ Pathogenic, low penetrance │     2 │        2 │
│ Established risk allele    │     2 │        2 │
└────────────────────────────┴───────┴──────────┘
```

Name the conditions with the published `condition.parquet` (2 MB). The proposition's `object` is a condition id:

```bash
curl -fO https://data.clinvar-gkm.org/v1/1.2/parquet/condition.parquet
duckdb -c "
SELECT c.name AS condition, count(*) AS scvs
FROM 'hema/scv.parquet' s
JOIN 'hema/propositionPathogenicity.parquet' p ON p.id = s.proposition
JOIN 'condition.parquet' c ON c.id = p.object
GROUP BY ALL
ORDER BY scvs DESC, condition
LIMIT 5"
```

```text
┌─────────────────────────────────────┬───────┐
│              condition              │ scvs  │
│               varchar               │ int64 │
├─────────────────────────────────────┼───────┤
│ Lynch syndrome                      │    67 │
│ ATM-related cancer predisposition   │    47 │
│ PALB2-related cancer predisposition │    24 │
│ CHEK2-related cancer predisposition │    22 │
│ BRCA2-related cancer predisposition │    21 │
└─────────────────────────────────────┴───────┘
```

A hereditary cancer laboratory. In general a proposition's object can also be a condition set
(`object_section = 'conditionSet'`); [Joining Tables](../parquet/joining.md) shows that join. All 287 here name
one condition.

---

## Keep the records

The tables are for querying. To keep the selection as **records**, byte for byte as published, write it as a
mini-bundle with `select` and the same options, then validate it:

```bash
uvx gkm-bundle-parquet@2.0.0 select --full clinvar-gkm-delta_2026-1115.json.gz "${P[@]}" \
    --driver submitter --ids clinvar.submitter:510823 \
    --follow both --max-depth 2 \
    --out hema.json.gz
uvx gkm-bundle-parquet@2.0.0 validate hema.json.gz "${P[@]}"
```

```text
selected 1149 record(s) in 4 section(s) from clinvar-gkm-delta_2026-1115.json.gz: hema.json.gz (99427 bytes, sha256 28e17faa…)
  submitter                                       1
  propositionPathogenicity                      287
  evidenceLine                                  574
  scv                                           287
…
records: 1,149  failing: 0  (0.4 s)
PASS
```

The same inputs and options give the same bytes, so the sha256 identifies the selection. A mini-bundle is a real
bundle: every tool that reads ClinVar-GKM bundles reads it, including `build`.

---

## What the result covers { #what-the-result-covers }

The dataset holds what the 2026-11-15 **delta** holds, and nothing else:

- **It is the week's changes.** Each of HEMA's 287 SCVs is version 1, new in this release, so here the week's
  changes are all of HEMA's submissions. For a submitter with older submissions, the same command returns only
  those that changed this week.
- **Unchanged records are missing.** The variants and conditions the propositions point to didn't change this
  week, so the delta doesn't carry them. The condition names above come from the published Parquet instead.
- **The latest release can differ.** The published `submitter.parquet` and `condition.parquet` are the newest
  release, overwritten weekly; the delta is fixed to 2026-11-15.

For everything about a submitter, run the same command on a full bundle (about 4.9 GB, from
[Monthly Full Bundles](../data-access/monthly-full.md)); `select` streams it in about 11 minutes with under 100 MB
of memory. For the newest release, the published Parquet answers without the tool:
[One submitter's dataset](../parquet/recipes.md#submitter-dataset).

---

## Next steps

- [CLI Reference](cli-reference.md): every option, including `--where` on nested columns, `--ids-file` and `--sections`.
- [Build Your Own Tables and Mini-Bundles](../parquet/build-your-own.md): full bundles, past weeks, `verify` and
  `rebuild`.
- [Recipes](../parquet/recipes.md): questions over the whole release with the published Parquet.
