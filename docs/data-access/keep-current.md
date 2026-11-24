# Keep Your Data Current

Links: [Weekly Deltas](weekly-deltas.md) · [Monthly Full Bundles](monthly-full.md) · [Weekly Full Bundles](weekly-full.md) · [Parquet Files](parquet.md) · [How Releases Work](release-model.md)

ClinVar-GKM publishes a release every week. This page keeps a local copy at the newest release by applying each
weekly delta, instead of downloading a 4.9 GB full bundle or a 4.6 GB Parquet set every week. It covers:

- a **bundle copy**: every record of a full bundle in a DuckDB table, updated in place;
- **Parquet tables**: the published tables, with each delta's rows merged in;
- a **custom dataset** cut from either, re-cut after each update;
- **missed weeks, rollovers and line changes**, and how to check a copy.

If you need the newest release only now and then, downloading it is simpler: the newest weekly full is
`weekly/clinvar-gkm_00-latest_weekly.json.gz` ([Weekly Full Bundles](weekly-full.md)), and the published Parquet
is always the newest release ([Parquet Files](parquet.md)). To rebuild a **past** week, see
[Rebuild a past week](weekly-deltas.md#rebuild-a-past-week).

!!! note "Prerequisites"
    - **Python 3.9 or later** (tested with 3.14.5) and the **`duckdb`** Python package (tested with 1.5.4),
      installed in [Get the script](#get-the-script).
    - **[uv](https://docs.astral.sh/uv/getting-started/installation/)**, for the Parquet recipe only: it runs
      [`gkm-bundle-parquet`](../parquet/build-your-own.md) 2.0.0 as `uvx gkm-bundle-parquet@2.0.0`.
    - **curl**, for the downloads in the shell examples. macOS and Linux both have it.
    - **Disk and time.** A bundle copy starts from a full bundle: a 4.9 GB download, and a DuckDB database of
      about 40 GB that takes about 15 minutes to load (estimated from the measured load of a 1.8-million-record
      delta; the full load was not run for this page). A Parquet copy starts from the published set: a 4.6 GB
      download, and up to 5 GB more while a week is merged. A weekly delta is 5 to 60 MB.
    - Run every command from one working directory: later blocks use the script and files earlier blocks
      leave there.

---

## How a delta updates a copy { #how-a-delta-updates-a-copy }

A copy is current when it holds the records of one release. Applying a delta moves it to the next release. Both
recipes on this page follow the same rules:

1. **Record the release, line and schema version of the copy.** A bundle carries its `schema_version` but no
   release date. The release comes from `index.json`: a monthly's `source_release`, or a weekly full's or a
   delta's `release`. The recipes find a bundle's entry in `index.json` by its sha256.
2. **Resolve the line from the root [`index.json`](https://data.clinvar-gkm.org/index.json).** Its `current`
   names the current line (`v1/1.2`). If the copy is on another line, stop: a new line starts from its own
   checkpoint monthly, and its deltas don't apply to the old line's records
   ([Line changes](#line-changes)).
3. **Take every delta of that line whose `release` is later than the copy's,** oldest first, with each one's
   path from the line's `index.json` (`deltas`, plus `archives.<year>.deltas` after a year rollover). Never
   compose a path: a delta moves to `deltas/YYYY-MM/` when its month ends.
4. **Check the chain.** The first delta's `baseline_release` equals the copy's release, and each later delta's
   `baseline_release` equals the previous delta's `release`. Check each delta's `schema_version` against the
   copy's, and each download's sha256 against `index.json`.
5. **Apply each delta in one transaction:** delete every key its [manifest](weekly-deltas.md#manifestjson) lists
   under `sections.<section>.deleted`, delete every key the delta bundle holds, insert the delta bundle's
   records, and record the delta's `release` as the copy's. Deleting the delta's own keys before inserting them
   is the upsert: an updated record replaces the old one.

A new ClinVar version is a new key. SCV, VCV and RCV keys carry the accession's version, so a new version shows
as a delete of the old key and an add of the new one (`clinvar.submission:SCV000024262.157` deleted,
`clinvar.submission:SCV000024262.158` added, in the 2026-11-15 delta). The rules above handle it like any other
delete and add. Proposition keys carry no version.

---

## Keep a bundle copy current { #keep-a-bundle-copy-current }

The copy is a DuckDB database, `clinvar-gkm.duckdb`, with a table `records(section, key, json)` holding each
record's JSON text as published, and a table `state` holding the copy's `last_release`, `line` and
`schema_version`. [`keep-current.py`](../assets/scripts/keep-current.py) loads it and applies the deltas, by the
rules above.

### Get the script { #get-the-script }

```bash
curl -fsSO https://clinvar-gkm.org/1.2/assets/scripts/keep-current.py
python3 -m venv .venv
. .venv/bin/activate
pip install duckdb==1.5.4
```

The later blocks run `python3` in this virtual environment. In a new shell, run `. .venv/bin/activate` again.

### Start from a full bundle { #start-from-a-full-bundle }

Download the newest monthly of the line and load it. `init` looks the file up in the line's `index.json` by its
sha256, so it knows the release without a date in the file (a monthly is at its `source_release`), and refuses a
file that isn't listed:

```bash
curl -fO https://data.clinvar-gkm.org/v1/1.2/clinvar-gkm_00-latest.json.gz
python3 keep-current.py init clinvar-gkm_00-latest.json.gz
```

On the 1.2 line today this loads the `2026-11` monthly, so the copy is at 2026-10-31 and prints
`loaded clinvar-gkm_2026-11.json.gz: at release 2026-10-31, line v1/1.2, schema 1.2.0` (the name of the dated
monthly with the same sha256). The newest weekly full (`v1/1.2/weekly/clinvar-gkm_00-latest_weekly.json.gz`)
works too, and leaves fewer deltas to apply. `init` reads the file twice, for its sha256 and then its records,
and doesn't need it afterwards.

### Apply the new deltas { #apply-the-new-deltas }

Run `update` after `init`, and again whenever you want the copy current; each run applies every delta published
since the last:

```bash
python3 keep-current.py update
python3 keep-current.py status
```

From the `2026-11` monthly, `update` applies the 2026-11-08 and 2026-11-15 deltas. The 2026-11-15 one prints:

```text
applied 2026-11-15: {'A': 16335, 'U': 22738, 'D': 8296}
at release 2026-11-15
```

`A`, `U` and `D` are the manifest's added, updated and deleted counts; `status` prints the state and the number
of records. The deltas are downloaded into `gkm-cache/` and kept, so a rerun after an interruption doesn't
download them again; delete the folder when you no longer need them. The line, chain and schema checks run on
every manifest before the first delta is applied. Each delta is applied in one transaction, after its download's
sha256 is checked, so the copy is always at one release.

### Query the copy { #query-the-copy }

The JSON text is queried with DuckDB's JSON functions. A variant's current germline VCV classification
(continues from [Get the script](#get-the-script)):

```bash
python3 - <<'EOF'
import duckdb
con = duckdb.connect("clinvar-gkm.duckdb", read_only=True)
con.sql("""
  SELECT key, json->>'$.classification.name' AS classification
  FROM records WHERE section = 'vcv' AND key LIKE 'VCV000183114.%-G-PATH'
""").show()
EOF
```

```text
┌────────────────────────┬────────────────────────┐
│          key           │     classification     │
│        varchar         │        varchar         │
├────────────────────────┼────────────────────────┤
│ VCV000183114.35-G-PATH │ Uncertain significance │
└────────────────────────┴────────────────────────┘
```

That is the copy at 2026-11-15. The key carries the VCV's version, so match the accession with `LIKE`, not the
key. To query typed columns instead of JSON text, keep the Parquet tables current ([below](#keep-parquet-current)).

!!! info "How the bundle recipe was tested"
    - **Seeded copy.** A copy was seeded with the records of the 2026-11-08 delta (1,779,702 records) and its
      state set to 2026-11-08: a **test seed**, not a full bundle, so the test ran in seconds. `update` applied
      the 2026-11-15 delta in 1.2 s. The copy then held 1,815,952 records, each equal, key and text, to an
      independent replay of the two deltas in Python dictionaries.
    - **Refusals.** `update` refused a copy on the frozen `v1/1.1` line, a copy whose `schema_version` is 1.1.0,
      and a copy at a release no delta builds on (a broken chain); `init` refused a file not listed in
      `index.json`.
    - **Records sha256.** `verify` computed the seeded copy's records sha256 as `gkm-bundle-parquet` 2.0.0 did
      for a build of the same records (`f59fae5f…`), and the same hashing over the 2026-11-15 weekly full gave
      the published value; see [Check your copy](#check-your-copy).
    - **The bundle layout.** The reader `init` and `update` use was run over the whole 2026-11-15 weekly full
      (91,973,603 records, the longest 0.5 MB) without an unexpected line.
    - **Not run on a full bundle.** The 15-minute and 40 GB figures for `init` are estimates from the seeded
      load (17.5 s and 664 MB for 1.8 million records; a full bundle holds about 92 million). The cost of
      `update` on a full copy was measured on a synthetic table of 92 million rows: the deletes and inserts of a
      delta the size of 2026-11-08's (1.7 million of each) took about 1 s, so reading the delta (17 s for
      2026-11-08) is most of it.

---

## Keep Parquet current { #keep-parquet-current }

The published Parquet set is built for one release, the newest, and replaced every week
([Parquet Files](parquet.md)). To keep your own tables current without downloading the 4.6 GB set every week,
start from the published set once, then merge each week's delta into it.

Each of the 20 tables holds **one row per bundle record**, and its `id` column is the record's bundle key (the
same text). There are no child or join tables: lists and nested objects are LIST and STRUCT columns of the
record's row. So a delta's change to a record is a change to exactly one row of one table, and the merge works
table by table, by `id`:

1. Build the delta's tables with `gkm-bundle-parquet` (9 s for the 2026-11-15 delta), with the same tool version
   and bundle schema as the published set, so the columns match.
2. For each table, keep every row of your table whose `id` is neither in the manifest's `deleted` list for that
   section nor in the delta's table, and add every row of the delta's table.
3. Write the new tables to a new folder, then swap it in, with the release they are at.

`keep-current.py` does this ([Get the script](#get-the-script)):

```bash
python3 keep-current.py parquet-init clinvar-gkm-tables
python3 keep-current.py parquet-update clinvar-gkm-tables
```

```text
downloaded 20 tables at release 2026-11-15
up to date at 2026-11-15
```

`parquet-init` downloads the published tables, checks each file's sha256 against the published
`parquet/manifest.json`, and writes `clinvar-gkm-tables/keep-current.json` with the release, line, schema
version and table spec they are at. `parquet-update` applies every newer delta, by the rules in
[How a delta updates a copy](#how-a-delta-updates-a-copy), and keeps each delta and its built tables in
`gkm-cache/`. Run right after `parquet-init`, it has nothing to do; run it after each weekly release. `--only scv,submitter` on `parquet-init` keeps only those tables, and the
updates then merge only them.

Query the tables as you query the published ones (see [Query with SQL](../parquet/index.md)):

```bash
python3 -c "import duckdb; duckdb.sql(\"SELECT count(*) FROM 'clinvar-gkm-tables/scv.parquet'\").show()"
```

**What it guarantees.** Each merged table has the rows a build of the full bundle at the new release would
have, as long as the tables you started from were exact and every delta in the chain was applied. Tested on real
tables: tables built from the 2026-11-08 delta, with the 2026-11-15 delta merged in, held the same rows, in all
20 tables, as tables built from the 2026-11-08 and 2026-11-15 records replayed together, with no `id` twice.

**What it doesn't.** Nothing checks the merged set's content. The files are not the bytes the tool would write:
the row order, row groups and compression differ, so their sha256 never matches the published files. They carry
no `manifest.json` of the tool's, so `gkm-bundle-parquet verify` and `rebuild` don't apply to them. At the newest
release, `parquet-check` compares each table's row count with the published manifest and checks that no `id`
appears twice. That catches a missed or doubled delta, not a changed value:

```bash
python3 keep-current.py parquet-check clinvar-gkm-tables
```

```text
20 of 20 tables match the published row counts
```

To start again from exact tables, delete the folder and run `parquet-init` again.

!!! info "Measured runs"
    On an Apple M2 Pro laptop (16 GB of memory, 10 cores): `parquet-init` downloaded the 2026-11-15 set (20
    files, 4.6 GB) in 60 s. Merging a delta into the full published tables takes about **3 minutes** (193 s,
    6.2 GB peak memory, measured by merging the 2026-11-15 delta into the 2026-11-15 tables, which also showed
    that re-applying a delta changes nothing: every table kept the same rows). The merged files are smaller than
    the published ones (2.5 GB), because DuckDB's default Parquet settings differ from the tool's.

---

## Keep a custom dataset current { #keep-a-custom-dataset-current }

To keep a subset current, such as one submitter's SCVs or one gene's variants, update the merged tables (or the
bundle copy) first, then cut the subset from them again after each update. For example, every SCV of one
submitter and the pathogenicity propositions they make, from the tables kept by
[Keep Parquet current](#keep-parquet-current):

```bash
python3 - <<'EOF'
import duckdb
duckdb.sql("""
  COPY (SELECT * FROM 'clinvar-gkm-tables/scv.parquet'
        WHERE list_contains([c.contributor FOR c IN contributions], 'clinvar.submitter:505870'))
    TO 'submitter-scv.parquet';
  COPY (SELECT p.* FROM 'clinvar-gkm-tables/propositionPathogenicity.parquet' p
        JOIN 'submitter-scv.parquet' s
          ON s.proposition_section = 'propositionPathogenicity' AND s.proposition = p.id)
    TO 'submitter-propositions.parquet';
""")
EOF
```

**Don't cut the subset from each delta and add it to last week's.** A delta isn't a small bundle of your subset:

- **It holds only the records that changed.** A selection follows references, and from a delta most of them
  lead to records that didn't change and aren't there, so the walk stops: the
  one-submitter selection on [Build Your Own Tables and Mini-Bundles](../parquet/build-your-own.md), run on
  the 2026-11-15 delta, reports 72 references to propositions the delta doesn't carry. When the seeded test above cut this
  submitter's SCVs from tables holding only the 2026-11-08 delta's records, it found 159,886 SCVs but 9,319 of
  their propositions: the SCVs changed that week, most of their propositions didn't.
- **It carries no deletes.** A deleted or re-versioned record is only in the manifest, so the old record would
  stay in your subset.
- **Records leave a subset.** An SCV reclassified from Pathogenic to Uncertain significance no longer matches a
  `classification.name = 'Pathogenic'` filter, so its new version is not selected and its old one is never
  removed.

Cutting from complete, current tables has none of these problems, and takes seconds.

---

## Missed weeks, rollovers and line changes { #missed-weeks-rollovers-and-line-changes }

### Missed weeks { #missed-weeks }

Nothing to do: `update` and `parquet-update` apply every delta after the copy's release, in order, however many
there are. Deltas are kept on the host for good ([How Releases Work](release-model.md)), so a copy can always
catch up on its line. If the chain check fails, a delta is missing or the copy's release is wrong; start again
from a full bundle or the published tables.

### Month and year rollovers { #month-and-year-rollovers }

At a month's first release its deltas move from `deltas/` to `deltas/YYYY-MM/`, and at a year's first release
the year's monthlies and deltas move to `archive/YYYY/` (see Month and Year Rollover on
[How Releases Work](release-model.md)). The file names and bytes don't change. Read every path from `index.json` (`deltas` and `archives.<year>.deltas`),
as `keep-current.py` does, and a rollover changes nothing for a copy.

### Line changes { #line-changes }

Deltas apply only to a copy of the same line. The 1.2 line's first delta (2026-11-08) has `baseline_release`
2026-10-31, the last release of the frozen 1.1 line, so a 1.1 copy at 2026-10-31 passes a chain check on dates
alone; applying 1.2 deltas to it would mix 1.1.0 and 1.2.0 records. `keep-current.py` refuses:

```text
refused: the copy is on v1/1.1 (frozen, superseded by v1/1.2); the current line is v1/1.2. Its deltas don't apply to this copy: start a new one on v1/1.2
```

Start a new copy on the new line: `init` from its checkpoint monthly (the line's first monthly; the
`checkpoint_full` of its deltas' manifests), or `parquet-init` for tables. A copy also stops when a delta's
`schema_version` differs from the copy's. See Version Lines on [How Releases Work](release-model.md).

### Check your copy { #check-your-copy }

The published Parquet's `manifest.json` gives `records_sha256`: a sha256 over every record of the bundle it was
built from, in a canonical form (the definition is in `gkm-bundle-parquet`'s
[round-trip.md](https://github.com/clingen-data-model/gkm-bundle-parquet/blob/main/docs/round-trip.md)). The
published Parquet is the newest release, so when your bundle copy is at that release, its records sha256 must
equal the published one:

```bash
python3 keep-current.py verify
```

It prints `match` or `DIFFERENT`, with both values, and exits 1 on a difference. It refuses a copy that isn't at
the newest release; check it after the next `update`. A difference means the copy isn't the published state:
start again from a full bundle.

`verify` hashes every record on every CPU. This hashing was tested at full size on the 2026-11-15 weekly full,
streamed from the host instead of loaded into a copy: over its 91,973,603 records it gave
`d0d9dbf6abdad07582f88b4014eecd5f1350d9cbcd6b0dd47de5135e2eb0a859`, the published Parquet's `records_sha256`,
in 16 minutes including the download. On the seeded copy, which holds only two deltas' records, `verify` took
33 s and reported `DIFFERENT`, as it should.
