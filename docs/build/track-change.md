# Track Change Over Time

A bundle is the state of ClinVar at one release. To follow how a variant's classification, or a submitter's
submissions, changed from week to week, combine the releases into a **history table**: one row for each version
of each statement, with the releases it was current for. This page builds that table from a monthly full and the
weekly deltas, queries it, and shows the cheaper alternative when two points in time are enough: comparing two
monthlies.

!!! note "Prerequisites"
    - **Python 3.9 or later** (tested with 3.14.5) and the **`duckdb`** Python package (tested with 1.5.4):

        ```bash
        curl -fsSO https://dataexchange.clinicalgenome.org/clinvar-gkm/1.2/assets/scripts/track-history.py
        python3 -m venv .venv
        . .venv/bin/activate
        pip install duckdb==1.5.4
        ```

      The later blocks run `python3` in this virtual environment, from the same working directory.
    - **Data.** A history from deltas only downloads every delta since 2026-07-06 and its manifest: 20 deltas,
      0.5 GB, and 0.26 GB of manifests. A complete history adds one monthly full, 4.5 GB, read once after its
      sha256 is checked. Comparing two monthlies reads two of them. See [Scope](#scope) for what each gives.
    - **Disk and time.** The deltas-only history is a DuckDB file of 0.12 GB, built in about 4 minutes after
      the download. A history from a monthly also holds a row for each of the monthly's statements (about 28
      million), so expect a few GB.

---

## Scope { #scope }

- **History on the host starts at 2026-06-27.** The first monthly is the frozen 1.1 line's `2026-07`, built from
  the 2026-06-27 release, and the first delta is 2026-07-06. The same weeks are in the frozen 1.0 line, in
  schema 1.0.1; this page uses the newest line that holds each week.
- **It spans two schemas.** Releases up to 2026-10-31 are in `v1/1.1/` (schema 1.1.0); from 2026-10-31 on, in
  `v1/1.2/` (schema 1.2.0). The 1.2 line starts from a checkpoint monthly at 2026-10-31, and its first delta,
  2026-11-08, is computed against that checkpoint, so it carries ClinVar's changes only. A record that didn't
  change keeps, in the history, the form it had in the last 1.1 delta that carried it. The history keeps only
  values whose path and meaning are the same in both schemas (below): every row of the deltas-only history still
  current at 2026-11-15, 2,649,530 of them from 1.1 deltas, has the classification, review status and submitter
  of the same key in the 1.2.0 weekly full. For any other value, compare the two `2026-11` monthlies,
  `v1/1.1/clinvar-gkm_2026-11.json.gz` and `v1/1.2/clinvar-gkm_2026-11.json.gz`: both are the 2026-10-31
  release, so every difference between them comes from the schema, not from ClinVar.
- **Release dates come from `index.json`.** A bundle carries no release date. A row's `valid_from` is the
  `release` of the delta that added it, or the monthly's `source_release` for rows loaded from the monthly
  (current then, and possibly earlier). The dates inside records, such as an SCV's `submitted` contribution
  date, are ClinVar's dates, not release dates.
- **A history from deltas only** sees every change from 2026-07-06 on, but not the state before a statement's
  first change: a statement that never changed has no row, and a statement's first row is its first new
  version. Start from a monthly to have both.

---

## Build the history { #build-the-history }

[`track-history.py`](../assets/scripts/track-history.py) builds the table in `clinvar-gkm-history.duckdb`:

| Column | Description |
| --- | --- |
| `section` | `scv`, `vcv` or `rcv` |
| `stable_id` | The key without ClinVar's version: the SCV accession (`SCV000024262`, the record's `clinvarScvId`), or the VCV or RCV accession with its group and type suffix (`VCV000183114-G-PATH`, `RCV000041109-G-PATH-CP`). The rows of one statement across versions share it |
| `key` | The bundle key, with the version (`clinvar.submission:SCV000024262.158`, `VCV000183114.35-G-PATH`) |
| `proposition` | The statement's proposition key. Proposition keys carry no version (`SCV000024262-PATH`, `VCV000183114-G-PATH`) |
| `classification` | `classification.name` |
| `review_status` | The `clinvarScvReviewStatus` (SCV) or `clinvarReviewStatus` (VCV, RCV) extension |
| `submitter` | An SCV's submitter: the `contributor` of its `submitted` contribution (`clinvar.submitter:3`) |
| `valid_from` | The release the row became current |
| `valid_to` | The release whose delta deleted or replaced it; NULL while it is current |

It is a slowly changing dimension of type 2. For each delta, in release order, the script adds a row for every
SCV, VCV and RCV record of the delta bundle, and closes the current row of every key the delta deletes (the
manifest's `deleted` lists) or replaces. A new ClinVar version arrives as a delete of the old key and an add of the
new one ([Weekly Deltas](../data-access/weekly-deltas.md#manifestjson)), so it closes one row and opens the next
under the same `stable_id`. It checks the chain (each delta's `baseline_release` is the release before it) and
each download's sha256, and takes every path from the `index.json` files.

### A complete history, from the first monthly { #from-a-monthly }

```bash
MONTHLY=$(curl -fsS https://data.clinvar-gkm.org/v1/1.1/index.json | python3 -c '
import json, sys
print(next(m["path"] for m in json.load(sys.stdin)["datasets"]["monthly"] if m["release"] == "2026-07"))')
curl -fO "https://data.clinvar-gkm.org/${MONTHLY}"
python3 track-history.py base clinvar-gkm_2026-07.json.gz --line v1/1.1
python3 track-history.py update
```

`base` finds the monthly in the line's `index.json` by its sha256 and loads its statements as current at its
`source_release` (2026-06-27). This was not run for this page; reading a monthly's statements (about 28
million) is estimated at about 10 minutes, from the measured 12.5 s for the 0.9 million statements of the
2026-11-08 delta.

### A history from deltas only { #from-deltas-only }

```bash
python3 track-history.py base --from-release 2026-06-27
python3 track-history.py update
```

```text
history starts at 2026-06-27 (deltas only, from 2026-06-27)
2026-07-06 (v1/1.1): 5535 statement rows added
2026-07-15 (v1/1.1): 11593 statement rows added
…
2026-10-31 (v1/1.1): 171431 statement rows added
2026-11-08 (v1/1.2): 924737 statement rows added
2026-11-15 (v1/1.2): 23051 statement rows added
history at 2026-11-15
```

Run `update` again after each weekly release to add the new deltas. `update --to 2026-10-31` stops at a release.

---

## Query the history { #query-the-history }

The queries run in DuckDB on `clinvar-gkm-history.duckdb`. Each block is a complete Python script; the output
shown is from the deltas-only history at 2026-11-15.

### One variant's classification timeline { #one-variants-classification-timeline }

The germline pathogenicity classification ClinVar shows for a variant is its VCV aggregate statement, the
`-G-PATH` key ([VCV Statements](../output-reference/vcv-statements.md)). Its rows, oldest first:

```bash
python3 - <<'EOF'
import duckdb
con = duckdb.connect("clinvar-gkm-history.duckdb", read_only=True)
con.sql("""
  SELECT key, classification, review_status, valid_from, valid_to
  FROM history WHERE stable_id = 'VCV000487338-G-PATH'
  ORDER BY valid_from
""").show(max_width=200)
EOF
```

```text
┌────────────────────────┬──────────────────────────────┬──────────────────────────────────────────────────────┬────────────┬────────────┐
│          key           │        classification        │                    review_status                     │ valid_from │  valid_to  │
│        varchar         │           varchar            │                       varchar                        │  varchar   │  varchar   │
├────────────────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┼────────────┼────────────┤
│ VCV000487338.20-G-PATH │ Pathogenic                   │ criteria provided, multiple submitters, no conflicts │ 2026-09-05 │ 2026-09-13 │
│ VCV000487338.21-G-PATH │ Pathogenic/Likely pathogenic │ criteria provided, multiple submitters, no conflicts │ 2026-09-13 │ 2026-09-23 │
│ VCV000487338.22-G-PATH │ Pathogenic/Likely pathogenic │ criteria provided, multiple submitters, no conflicts │ 2026-09-23 │ 2026-09-28 │
│ VCV000487338.22-G-PATH │ Pathogenic                   │ criteria provided, multiple submitters, no conflicts │ 2026-09-28 │ 2026-10-18 │
│ VCV000487338.23-G-PATH │ Likely pathogenic            │ reviewed by expert panel                             │ 2026-10-18 │ NULL       │
└────────────────────────┴──────────────────────────────┴──────────────────────────────────────────────────────┴────────────┴────────────┘
```

A new version is a new key; a change without a new version (2026-09-28) is a new row under the same key. The
VCV accession's number is the variant's ClinVar variation ID: the proposition `VCV000487338-G-PATH` is about
`clinvar:487338`. For the statements at other levels of the hierarchy (`-G-PATH-CP`, `-G-PATH-EP`, …), use their
`stable_id`.

### SCV reclassifications by submitter { #scv-reclassifications-by-submitter }

A reclassification is two consecutive rows of one SCV whose classifications differ: usually the delete of one
version and the add of the next. Counted by submitter, with the submitters' names from the published
`submitter` table (a 0.1 MB file):

```bash
curl -fO https://data.clinvar-gkm.org/v1/1.2/parquet/submitter.parquet
python3 - <<'EOF'
import duckdb
con = duckdb.connect("clinvar-gkm-history.duckdb", read_only=True)
con.sql("""
  CREATE TEMP VIEW scv_changes AS
  WITH s AS (
    SELECT *, lag(classification) OVER w AS before, lag(valid_to) OVER w AS before_to
    FROM history WHERE section = 'scv'
    WINDOW w AS (PARTITION BY stable_id ORDER BY valid_from, key))
  SELECT stable_id, valid_from AS release, before, classification AS after, submitter
  FROM s WHERE before_to = valid_from AND after IS DISTINCT FROM before
""")
con.sql("""
  SELECT c.submitter, s.name, count(*) AS changes, count(DISTINCT stable_id) AS scvs
  FROM scv_changes c
  LEFT JOIN 'submitter.parquet' s ON s.id = c.submitter
  GROUP BY ALL ORDER BY changes DESC LIMIT 4
""").show(max_width=200)
EOF
```

```text
┌──────────────────────────┬───────────────────────────────────────────┬─────────┬───────┐
│        submitter         │                   name                    │ changes │ scvs  │
│         varchar          │                  varchar                  │  int64  │ int64 │
├──────────────────────────┼───────────────────────────────────────────┼─────────┼───────┤
│ clinvar.submitter:505870 │ CeGaT Center for Human Genetics Tuebingen │     628 │   628 │
│ clinvar.submitter:3      │ OMIM                                      │     319 │    42 │
│ clinvar.submitter:26957  │ GeneDx                                    │      38 │    38 │
│ clinvar.submitter:61756  │ Ambry Genetics                            │      37 │    37 │
└──────────────────────────┴───────────────────────────────────────────┴─────────┴───────┘
```

Read the counts with the records in hand. 284 of OMIM's 319 changes are between `Pathogenic` and `Affects` on
the same 42 SCVs, which take a new version almost every week: `SCV000024286` alternates between the two in its
versions 137 to 156. To see one SCV's versions, select its rows: `WHERE stable_id = 'SCV000024286'`.

### Conflicts appearing and resolving { #conflicts-appearing-and-resolving }

A VCV aggregate whose classification becomes, or stops being, `Conflicting classifications of pathogenicity`,
per release:

```bash
python3 - <<'EOF'
import duckdb
con = duckdb.connect("clinvar-gkm-history.duckdb", read_only=True)
con.sql("""
  WITH s AS (
    SELECT *, lag(classification) OVER w AS before, lag(valid_to) OVER w AS before_to
    FROM history WHERE section = 'vcv' AND stable_id LIKE '%-G-PATH'
    WINDOW w AS (PARTITION BY stable_id ORDER BY valid_from, key))
  SELECT valid_from AS release,
         count(*) FILTER (WHERE classification = 'Conflicting classifications of pathogenicity') AS appeared,
         count(*) FILTER (WHERE before = 'Conflicting classifications of pathogenicity') AS resolved
  FROM s WHERE before_to = valid_from AND classification IS DISTINCT FROM before
  GROUP BY 1 ORDER BY 1 DESC LIMIT 5
""").show()
EOF
```

```text
┌────────────┬──────────┬──────────┐
│  release   │ appeared │ resolved │
│  varchar   │  int64   │  int64   │
├────────────┼──────────┼──────────┤
│ 2026-11-15 │       18 │        6 │
│ 2026-11-08 │      124 │       36 │
│ 2026-10-31 │      184 │       47 │
│ 2026-10-24 │        9 │        1 │
│ 2026-10-18 │       64 │       66 │
└────────────┴──────────┴──────────┘
```

From deltas only, a conflict is counted when the VCV's earlier version is in the history too; a history from a
monthly counts every one.

---

## Compare two releases { #compare-two-releases }

When two points in time are enough, skip the history: extract the statements of two monthlies and join them on
`stable_id`. `extract` writes one release's statements, with the same columns as the history less the two dates,
to a Parquet file. The 1.1 line's first and last monthlies, 2026-06-27 and 2026-10-31:

```bash
for MONTH in 2026-07 2026-11; do
  P=$(curl -fsS https://data.clinvar-gkm.org/v1/1.1/index.json | python3 -c "
import json, sys
print(next(m['path'] for m in json.load(sys.stdin)['datasets']['monthly'] if m['release'] == '${MONTH}'))")
  curl -fO "https://data.clinvar-gkm.org/${P}"
  python3 track-history.py extract "clinvar-gkm_${MONTH}.json.gz" "statements-${MONTH}.parquet"
done
```

```bash
python3 - <<'EOF'
import duckdb
duckdb.sql("""
  SELECT stable_id, a.classification AS before, b.classification AS after
  FROM 'statements-2026-07.parquet' a JOIN 'statements-2026-11.parquet' b USING (section, stable_id)
  WHERE section = 'vcv' AND stable_id LIKE '%-G-PATH' AND a.classification IS DISTINCT FROM b.classification
  ORDER BY stable_id LIMIT 10
""").show()
EOF
```

A `FULL JOIN` adds the statements present in only one release (new variants, and withdrawn ones). Each monthly
is a 4.5 GB download read once; the extraction is estimated at about 10 minutes per monthly (see
[A complete history](#from-a-monthly)). Two monthlies of the same line compare only ClinVar's changes; a monthly
of `v1/1.1` and one of `v1/1.2` compare schemas too ([Scope](#scope)).

!!! info "How these recipes were tested"
    - The deltas-only history was built from the 20 published deltas from 2026-07-06 to 2026-11-15 (the 1.1
      line then the 1.2 line), in 3.5 minutes on an Apple M2 Pro laptop with the delta bundles already
      downloaded, and every query above was run on it; the output shown is that run's.
    - Every row of it still current at 2026-11-15 (3,596,191 rows) was compared with the 2026-11-15 weekly full:
      each key is in the full, with the same classification, review status and submitter.
    - `extract` and the comparison query were run on two deltas in place of the two monthlies.
