# Choose Your Data

ClinVar-GKM publishes the same data in several forms. They differ in size, in how often they change, and in what they are good for. This page compares them, with their current sizes, and suggests where to start.

Sizes are from the line's `index.json` and Parquet `manifest.json` for the **2026-11-15 release**. A full bundle grows by a few MB a week; [Check the current sizes](#check-the-current-sizes) below reads them live.

---

## The options

| Data | Size | Updated | Good for | Where |
| --- | --- | --- | --- | --- |
| **Published Parquet tables** | 20 tables, 5 KB to 1.7 GB each, 4.6 GB in all; most questions need two or three ([sizes](#parquet-table-sizes)) | Every weekly release; one set, overwritten | SQL in DuckDB, Python, R or Spark; the browser console; questions about the current data | [Parquet Files](../data-access/parquet.md) |
| **Weekly full bundle** | 4.9 GB compressed, 68.5 GB decompressed | Every weekly release; kept for the current month only | The newest state as JSON; loading records into the GA4GH libraries | [Weekly Full Bundles](../data-access/weekly-full.md) |
| **Official monthly full bundle** | 4.9 GB compressed, 68.5 GB decompressed | Once a month, lined up with ClinVar's monthly release; kept for good | A fixed snapshot to cite or reproduce; the starting point for deltas | [Monthly Full Bundles](../data-access/monthly-full.md) |
| **Monthly plus weekly deltas** | One monthly (4.9 GB), then one delta a week: usually 2 to 30 MB, up to about 150 MB | Every weekly release | Keeping a local copy current without downloading 4.9 GB a week; seeing exactly what changed each week | [Weekly Deltas](../data-access/weekly-deltas.md), [Keep Your Data Current](../data-access/keep-current.md) |
| **Previous releases** | About 4.8 GB per monthly; deltas as above | Frozen: never change | Data in an older schema (1.1.x, 1.0.1), for work that was built on it | [Previous Releases](../data-access/previous-releases.md) |
| **Build your own** | Your choice: from a mini-bundle of one variant or one submitter to every table of a release | Whenever you run it | Parquet for an earlier release; a subset of ClinVar as a self-contained bundle; your own column set | [Build Your Own Dataset](../build/index.md) |

**Where to start:** query the published Parquet. The [Quick Start](quick-start.md) runs SQL in your browser with nothing to download; after that, download the two or three tables your question needs. To see the JSON format, download a weekly delta (a few MB) before a full bundle.

**When you need a full bundle:** use the newest weekly full for the current state, and the official monthly for a snapshot that matches ClinVar's monthly release. The monthly reflects the **last release of the previous month**, not the current week; [How Releases Work](../data-access/release-model.md) explains the schedule.

!!! warning "A full bundle is too large to open whole"
    Decompressed, a full bundle is 68.5 GB. Read it streamed (`gunzip -c`), one record per line, rather than loading it into memory or decompressing it to disk; see [Count records in a full bundle](../data-access/download.md#count-records-in-a-full-bundle). [Set Up Your Tools](setup.md) lists disk and memory needs.

---

## Parquet table sizes { #parquet-table-sizes }

Small tables are quick to download and to query over the network; the five largest are better downloaded once and queried locally. [The 20 Tables](../parquet/tables.md) explains what each holds.

| Table | Rows | Size |
| --- | ---: | ---: |
| `therapy` | 38 | 5 KB |
| `therapyGroup` | 10 | 6 KB |
| `sequenceReference` | 216 | 20 KB |
| `submitter` | 3,601 | 138 KB |
| `propositionSomaticClinicalImpact` | 12,607 | 147 KB |
| `propositionOncogenicity` | 12,233 | 154 KB |
| `condition` | 23,450 | 2.0 MB |
| `propositionClinvarCustom` | 186,357 | 2.4 MB |
| `copyNumberChange` | 31,753 | 3.3 MB |
| `gene` | 92,994 | 3.4 MB |
| `copyNumberCount` | 47,557 | 4.9 MB |
| `conditionSet` | 101,024 | 5.0 MB |
| `vcv` | 9,210,004 | 148 MB |
| `rcv` | 12,124,928 | 185 MB |
| `evidenceLine` | 21,646,324 | 265 MB |
| `propositionPathogenicity` | 28,020,731 | 403 MB |
| `location` | 4,230,835 | 428 MB |
| `allele` | 4,620,098 | 701 MB |
| `scv` | 6,895,428 | 785 MB |
| `variation` | 4,713,415 | 1.7 GB |
| **All 20** | | **4.6 GB** |

---

## Check the current sizes

These read the live index files. They need `curl` and `jq` ([Set Up Your Tools](setup.md)).

```bash
# Every Parquet table: file, size in bytes, rows
curl -fsS https://data.clinvar-gkm.org/v1/1.2/parquet/manifest.json \
  | jq -r '.tables[] | [.file, .size, .rows] | @tsv'

# The full bundles of the current line, monthly and weekly: path, size in bytes
curl -fsS https://data.clinvar-gkm.org/v1/1.2/index.json \
  | jq -r '(.datasets.monthly[], .datasets.weekly[]) | [.path, .size] | @tsv'

# This year's weekly deltas: release, size in bytes
curl -fsS https://data.clinvar-gkm.org/v1/1.2/index.json \
  | jq -r '.deltas[] | [.release, .bundle.size] | @tsv'
```
