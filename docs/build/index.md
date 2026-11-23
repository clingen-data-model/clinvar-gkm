# Build Your Own Dataset

ClinVar-GKM gives four ways to get the part of ClinVar you need. They read the same records, so the choice
depends on the question, the release, the machine you have, and whether you need the records themselves or rows
derived from them.

| Path | What you get | Releases | Machine | Provenance and citation |
| --- | --- | --- | --- | --- |
| **Query the published Parquet** | 20 typed tables you query with SQL; download only the tables a question reads | The newest release only; the set is overwritten every release | A laptop: the tables a question reads, from 2 MB (`condition`) to 1.7 GB (`variation`), 4.6 GB for all 20 | Rows derived from the bundle; `manifest.json` names the release and the bundle's sha256 |
| **Build tables with `gkm-bundle-parquet`** | The same 20 tables, or only some of them, or only the rows of a selection | Any release whose bundle you have: a monthly, a weekly full, a rebuilt past week, a delta | Seconds for a delta or a selection; about 3.5 hours for a full bundle on a 16 GB machine, 40 minutes on a large one | Every file records the tool, the schema set and the source bundle's sha256; `verify` checks them |
| **Cut a mini-bundle with `select`** | The records of one submitter, gene, variant or condition, and the records they point to, byte for byte as published | Any release whose bundle you have | Under 100 MB of memory; about 11 minutes to stream a full bundle, about 1 second for a delta | The records themselves, as published; the mini-bundle validates against the schema and records its selection |
| **Read the JSON bundle** | Every record of a release, the format of record | Every release: monthly fulls, weekly fulls of the current month, weekly deltas | About 4.9 GB compressed for a full bundle; stream it, don't load it | The published file and its sha256; what the [GA4GH libraries](../working-in-python.md) read |

Cite the release you used whichever path you take: [Data Use and Citation](../data-use.md).

---

## Choose your path

Start from the question.

| You want to | Take | Start with |
| --- | --- | --- |
| Try a query without installing anything | Published Parquet, in the browser | [Query with SQL](../parquet/index.md) (its live console) |
| Answer a question across all of ClinVar today (counts, conflicts, a gene, a condition) | Published Parquet | [Recipes](../parquet/recipes.md) |
| Join ClinVar to a VCF, gnomAD or another VRS dataset | Published Parquet | [VRS-keyed harmonization table](../parquet/recipes.md#harmonization-table) |
| A table per SCV for pandas, R or a spreadsheet | Published Parquet | [Flat analysis table](../parquet/recipes.md#flat-scv-table) |
| See what changed this week for your lab or your gene panel | Build tables from the week's delta | [Your First Dataset](first-dataset.md) |
| Tables for a release other than the newest | Build tables | [Parquet for one weekly release](../parquet/build-your-own.md#parquet-for-one-weekly-release) |
| A slice as records to share, archive or load with the GA4GH libraries | Mini-bundle | [Cut a mini-bundle](../parquet/build-your-own.md#cut-a-mini-bundle) |
| Prove a set of tables matches its bundle | Build tables, then `verify` | [Verify a set of tables](../parquet/build-your-own.md#verify-a-set-of-tables) |
| Every record of a release, or to stay current week by week | JSON bundle | [Get the Data](../data-access/download.md), [Keep Your Data Current](../data-access/keep-current.md) |
| Follow a variant's classifications across releases | Bundles of each release | [Track Change Over Time](track-change.md) |

Three questions settle most choices:

- **Which release?** The published Parquet is the newest release only. For any other release, build the tables
  from that release's bundle, or cut a mini-bundle from it. [Previous Releases](../data-access/previous-releases.md)
  lists what each line keeps.
- **How big a machine?** Querying a few published tables, building from a delta and cutting a mini-bundle all
  run on a laptop. Building all 20 tables from a full bundle needs about 10 GiB of memory and 30 GB of free disk,
  or a selection instead.
- **Rows or records?** Parquet rows are for analysis: joins, counts, exports. When the result must carry the
  records as ClinVar-GKM published them, with every identifier and pointer intact, cut a mini-bundle.

---

## The pages in this section

- [Build Your Own Tables and Mini-Bundles](../parquet/build-your-own.md): the full guide to `gkm-bundle-parquet`,
  with measured runs on a delta and on a full bundle.
- [Your First Dataset](first-dataset.md): one submitter's submissions from a weekly delta, as tables, a DuckDB
  query and a mini-bundle, in about five minutes.
- [CLI Reference](cli-reference.md): every command and option of `gkm-bundle-parquet` 2.0.0.
- [Recipes](../parquet/recipes.md): tested queries over the published Parquet, including a gene-panel subset, a
  VRS-keyed harmonization table, a conflicting-classification watchlist, one submitter's dataset and a flat
  per-SCV table.
