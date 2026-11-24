# How Releases Work

Links: [Monthly Full Bundles](monthly-full.md) · [Weekly Full Bundles](weekly-full.md) · [Weekly Deltas](weekly-deltas.md) · [Parquet Files](parquet.md) · [Previous Releases](previous-releases.md)

ClinVar-GKM releases are hosted on Cloudflare R2 object storage. All downloads are free with no authentication required and no egress fees. The layout follows NCBI's ClinVar XML folder, with monthlies at the top, `weekly/` and `archive/YYYY/`; see [Directory Structure](#directory-structure) below and [How the layout mirrors NCBI](download.md#how-the-layout-mirrors-ncbi).

This page is the reference for the release schedule, the directory layout and when files move. To decide which files to download, see [Choose Your Data](../start/choose-your-data.md).

Distribution follows a **full + delta** model:

- An **official monthly full bundle** — a gzip-compressed JSON file — is published once a month, lined up with ClinVar's monthly release. It contains every variation, statement, proposition, condition, and supporting reference record.
- A **weekly full bundle** is published for every ClinVar weekly release, and kept for the current month only.
- A **weekly delta** is published for every ClinVar weekly release. Each delta carries only the records that were added or updated since the prior release, in the same section structure as the full bundle, alongside a manifest that lists per-section adds, updates, and deletes.

The monthlies and the deltas are the durable record. A consumer that wants the state at any week takes a monthly full and replays the deltas after it; see [Rebuild a past week](weekly-deltas.md#rebuild-a-past-week) and the [manifest field reference](weekly-deltas.md#manifestjson).

!!! warning "The official monthly is a month-start baseline, not the current week"
    `clinvar-gkm_00-latest.json.gz` reflects the **last release of the _previous_ month** — e.g. the `2026-10` monthly is built from the `2026-09-28` release, the last one before ClinVar's October monthly cut. For the current week, use the newest [weekly full](weekly-full.md), or replay the deltas onto the monthly.

---

## Release Cadence

A **weekly release** is published for every ClinVar XML release, typically within 1-2 days of it. It writes the weekly full `weekly/clinvar-gkm_YYYY-MMDD.json.gz`, refreshes `weekly/clinvar-gkm_00-latest_weekly.json.gz`, and writes the delta `deltas/clinvar-gkm-delta_YYYY-MMDD.json.gz` with its manifest. All paths are under the line folder, `v1/1.2/`.

An **official monthly full** is published once a month, lined up with ClinVar's monthly VCV release. When ClinVar posts `ClinVarVCVRelease_YYYY-MM.xml.gz` at its [XML index](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/) (early in month `YYYY-MM`), our `clinvar-gkm_YYYY-MM` full is built from the most recent weekly release **before** ClinVar's monthly cut datetime — so e.g. the `2026-07` monthly comes from the `2026-06-27` release. That release is published as the monthly's `source_release` in `index.json`. The upload writes `clinvar-gkm_YYYY-MM.json.gz` and refreshes the `clinvar-gkm_00-latest.json.gz` pointer. Each delta manifest's `checkpoint_full` names the official monthly that precedes the delta.

Every bundle has a `.sha256` checksum sidecar. From 1.1.0, a monthly or delta file is never rewritten; see the exceptions below.

## Directory Structure

The root `index.json` is a thin **version manifest** that lists the release lines and points to each line's index. Each line has its own folder, `v{major}/{major}.{minor}/`; the current line is `1.2`, served under `v1/1.2/`, with its release index at `v1/1.2/index.json`.

```text
index.json                                    version manifest (each line -> its index)
v1/
  1.2/                                        current line
    index.json                                release index for the line
    feed.xml                                  Atom feed of the line's releases
    README.txt                                plain-text guide to the line
    clinvar-gkm_00-latest.json.gz             newest official monthly full (stable URL)
    clinvar-gkm_YYYY-MM.json.gz               official monthly fulls, current year
    weekly/
      clinvar-gkm_00-latest_weekly.json.gz    newest weekly full (stable URL)
      clinvar-gkm_YYYY-MMDD.json.gz           weekly fulls, CURRENT MONTH ONLY
    deltas/
      clinvar-gkm-delta_YYYY-MMDD.json.gz     current month's weekly deltas
      clinvar-gkm-delta_YYYY-MMDD.manifest.json
      YYYY-MM/                                earlier months of the current year
    archive/
      YYYY/
        clinvar-gkm_YYYY-MM.json.gz           monthly fulls from prior years
        deltas/YYYY-MM/                       deltas from prior years
    parquet/
      {section}.parquet                       ONE Parquet dataset, the latest (built from the bundle; overwritten every release)
      manifest.json                           build date, source release, builder, per-file sha256
      table-spec.json                         every table's columns, types and derivations
  1.1/                                        frozen line: the 1.1.x releases (monthlies, deltas, MANIFEST.json; no weekly fulls, no Parquet)
  1.0/                                        frozen line: the 1.0.1 generation (bundles, delta manifests, MANIFEST.json; no Parquet)
```

Every bundle has a `<file>.sha256` sidecar (`sha256sum -c` format), like NCBI's `.md5` files. The `00-` prefix of the stable names sorts them before the dated files in a directory listing, as in NCBI's `ClinVarVCVRelease_00-latest.xml.gz`. Scripts that need a dated file should look up its current path in the line's `index.json`, because dated files move at month and year ends (below).

## Month and Year Rollover

| When | What happens |
| --- | --- |
| The first release of a **new month** is published | The finished month's deltas move from `deltas/` into `deltas/YYYY-MM/`. The finished month's **weekly fulls are deleted**, as NCBI deletes its weekly releases, except the newest: it is kept until the new month's official monthly is published (the monthly is normally a copy of it), then deleted. |
| The first release of a **new year** is published | The finished year's monthlies move into `archive/YYYY/`, and its delta folders into `archive/YYYY/deltas/YYYY-MM/`. |

A move changes a file's folder, never its bytes, name or checksum. Deleting the weekly fulls is the one deliberate exception to "published bundles are never removed": every deleted week can be rebuilt exactly from a monthly plus deltas ([Rebuild a past week](weekly-deltas.md#rebuild-a-past-week)).

## Parquet

**Parquet is derived from the bundle.** One Parquet dataset is published, at `v1/1.2/parquet/`, rebuilt from the newest weekly release and **overwritten every release**. Its `manifest.json` gives the build date, the release and dataset it was built from, the builder, the schema version, and every file's size and sha256. No Parquet is kept per month, per delta, in `archive/` or in frozen lines. Past Parquet is rebuilt from the monthly bundles with [`gkm-bundle-parquet`](https://github.com/clingen-data-model/gkm-bundle-parquet) ([PyPI](https://pypi.org/project/gkm-bundle-parquet/)), the separate tool that builds the published set; see [Build Your Own Tables and Mini-Bundles](../parquet/build-your-own.md). See [Parquet Files](parquet.md).

## Version Lines

Each version line has its own folder: `v1/1.2/` for 1.2.x. A PATCH release (1.2.x) only adds new dated files to `v1/1.2/`. A new MINOR — including a content-only correction that must rewrite published bundles — starts `v1/1.3/`, and a new MAJOR starts `v2/2.0/`.

A new line starts with one **checkpoint monthly**: the first full built with the new schema, published as the official monthly of the ClinVar monthly it is the source of (ADR 0002). Its deltas run forward from it; the first delta's `baseline_release` is the checkpoint's `source_release`. Earlier releases are not republished into the new line. 1.2.0 started `v1/1.2/` this way.

The line it replaces is **frozen** and kept indefinitely: its monthlies, `00-latest` copy, deltas and archive stay unchanged at their paths, and it gains a `MANIFEST.json` (every file's size and sha256) and a `README.txt`. Its weekly fulls and its Parquet set are deleted at the freeze, because neither is a record: any week is rebuilt from a monthly plus deltas, and Parquet is rebuilt from a bundle. `v1/1.1/` (schema 1.1.0, the 1.1.x releases) is frozen with `superseded_by: "v1/1.2"`; the 1.0.1 generation is the frozen line `v1/1.0/`, with bundles and delta manifests only. The root `index.json` lists every line and its status; [Previous Releases](previous-releases.md) lists the frozen lines and their files, and [Versioning & Releases](../reference/versioning.md) explains the version numbers.
