# How Releases Work

Links: [Monthly Full Bundles](monthly-full.md) · [Weekly Full Bundles](weekly-full.md) · [Weekly Deltas](weekly-deltas.md) · [Parquet Files](parquet.md)

ClinVar-GKM releases are hosted on Cloudflare R2 object storage. All downloads are free with no authentication required and no egress fees. The layout follows NCBI's ClinVar XML folder, with monthlies at the top, `weekly/` and `archive/YYYY/`; see [How the layout mirrors NCBI](download.md#how-the-layout-mirrors-ncbi).

Distribution follows a **full + delta** model:

- An **official monthly full bundle** — a gzip-compressed JSON file — is published once a month, lined up with ClinVar's monthly release. It contains every variation, statement, proposition, condition, and supporting reference record.
- A **weekly full bundle** is published for every ClinVar weekly release, and kept for the current month only.
- A **weekly delta** is published for every ClinVar weekly release. Each delta carries only the records that were added or updated since the prior release, in the same section structure as the full bundle, alongside a manifest that lists per-section adds, updates, and deletes.

The monthlies and the deltas are the durable record. A consumer that wants the state at any week takes a monthly full and replays the deltas after it; see [Rebuild a past week](weekly-deltas.md#rebuild-a-past-week) and the [manifest field reference](weekly-deltas.md#manifestjson).

!!! warning "The official monthly is a month-start baseline, not the current week"
    `clinvar-gkm_00-latest.json.gz` reflects the **last release of the _previous_ month** — e.g. the `2026-10` monthly is built from the `2026-09-28` release, the last one before ClinVar's October monthly cut. For the current week, use the newest [weekly full](weekly-full.md), or replay the deltas onto the monthly.

---

## Release Cadence

A **weekly release** is published for every ClinVar XML release, typically within 1-2 days of it. It writes the weekly full `weekly/clinvar-gkm_YYYY-MMDD.json.gz`, refreshes `weekly/clinvar-gkm_00-latest_weekly.json.gz`, and writes the delta `deltas/clinvar-gkm-delta_YYYY-MMDD.json.gz` with its manifest. All paths are under the line folder, `v1/1.1/`.

An **official monthly full** is published once a month, lined up with ClinVar's monthly VCV release. When ClinVar posts `ClinVarVCVRelease_YYYY-MM.xml.gz` at its [XML index](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/) (early in month `YYYY-MM`), our `clinvar-gkm_YYYY-MM` full is built from the most recent weekly release **before** ClinVar's monthly cut datetime — so e.g. the `2026-07` monthly comes from the `2026-06-27` release. That release is published as the monthly's `source_release` in `index.json`. The upload writes `clinvar-gkm_YYYY-MM.json.gz` and refreshes the `clinvar-gkm_00-latest.json.gz` pointer. Each delta manifest's `checkpoint_full` names the official monthly that precedes the delta.

Every bundle has a `.sha256` checksum sidecar. From 1.1.0, a monthly or delta file is never rewritten; see the exceptions below.

## Month and Year Rollover

| When | What happens |
| --- | --- |
| The first release of a **new month** is published | The finished month's deltas move from `deltas/` into `deltas/YYYY-MM/`. The finished month's **weekly fulls are deleted**, as NCBI deletes its weekly releases. |
| The first release of a **new year** is published | The finished year's monthlies move into `archive/YYYY/`, and its delta folders into `archive/YYYY/deltas/YYYY-MM/`. |

A move changes a file's folder, never its bytes, name or checksum. Deleting the weekly fulls is the one deliberate exception to "published bundles are never removed": every deleted week can be rebuilt exactly from a monthly plus deltas ([Rebuild a past week](weekly-deltas.md#rebuild-a-past-week)).

## Parquet

**Parquet is derived from the bundle.** One Parquet dataset is published, at `v1/1.1/parquet/`, rebuilt from the newest weekly release and **overwritten every release**. Its `manifest.json` gives the build date, the release it was built from and the version of the tool that built it. No Parquet is kept per month, per delta, in `archive/` or in frozen lines. Past Parquet is rebuilt from the monthly bundles with [`clinvar-gkm-parquet`](https://github.com/clingen-data-model/clinvar-gkm-parquet), a separate tool that is planned but not yet released. See [Parquet Files](parquet.md).

## Version Lines

Each version line has its own folder: `v1/1.1/` for 1.1.x. A new MINOR starts `v1/1.2/` and a new MAJOR starts `v2/2.0/`. The line it replaces is frozen, with its files kept unchanged. The 1.0.1 generation is the frozen line `v1/1.0/`, with bundles and delta manifests only (no Parquet). The root `index.json` lists every line and its status; see [Versioning & Releases](../reference/versioning.md).
