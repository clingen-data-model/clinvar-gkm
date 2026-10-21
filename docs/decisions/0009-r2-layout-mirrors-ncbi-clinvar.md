# 0009 — R2 layout mirrors NCBI ClinVar

- **Status:** Proposed
- **Date:** 2026-10-20
- **Amends:** [ADR 0004](0004-schema-versioning-and-release-management.md) §4 (directories per version line),
  [ADR 0005](0005-r2-custom-domain-and-cdn.md) (cache rules, path allowlist, layout note),
  ADR 0006 (on PR #146) Decision 2 (1.1.0 ships under `v1/1.1/`, not in place in `/v1/`), [ADR 0008](0008-bundles-are-the-public-record.md) (a), (c), (e)
- **Plan:** [`docs/superpowers/plans/2026-10-18-bundle-record-and-metrics.md`](../superpowers/plans/2026-10-18-bundle-record-and-metrics.md)

## Context

The published bundles are built from NCBI's ClinVar XML releases. NCBI publishes them in a layout ClinVar users
already know:

| NCBI path | What it holds |
| --- | --- |
| [`pub/clinvar/xml/`](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/) | the current year's monthly releases (`ClinVarVCVRelease_YYYY-MM.xml.gz`) and `ClinVarVCVRelease_00-latest.xml.gz` |
| [`xml/weekly_release/`](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/weekly_release/) | the current month's weekly full releases and `00-latest_weekly`; earlier weeks are removed |
| [`xml/archive/YYYY/`](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/archive/) | the monthly releases of prior years |

Every file has an `.md5` sidecar, and every file name carries its date.

The ClinVar-GKM layout under `/v1/` grew differently: `datasets/` for monthly fulls, `deltas/<YYYY-MMDD>/`
directories each holding a bundle and a `manifest.json`, dated Parquet sets under `datasets/parquet/`, a
prior-year `archives/` folder, and a superseded generation copied to a root `archive/1.0.1/`
([ADR 0008](0008-bundles-are-the-public-record.md) (c)). Three problems came with it:

- **No weekly full.** A user who wanted the current week had to download the monthly full and replay deltas.
- **No place for a new MINOR.** ADR 0004 §4 keys directories by MAJOR only, so the 1.1.0 republish would have
  rewritten `/v1/` in place (ADR 0006) and pushed the 1.0.1 generation out to `archive/1.0.1/`.
- **Two replay defects.** Every delta manifest's `checkpoint_full` named the newest monthly (`2026-10`), not the
  monthly its chain starts from, and nothing published which release a monthly full was built from. The
  documented replay also compared months, so it skipped deltas from the checkpoint's own month.

## Decision

### 1. Version folders

Each version line has its own folder, `v{major}/{major}.{minor}/`, starting with `v1/1.1/`:

- PATCH releases (1.1.x) keep adding to the same folder.
- A new MINOR starts a new folder (`v1/1.2/`); a new MAJOR starts `v2/2.0/`.
- A folder that a newer line replaces is **frozen**: nothing is added to it, moved in it or deleted from it.
- The 1.0.1 generation, archived on 2026-10-18 to `archive/1.0.1/`, moves to the frozen line **`v1/1.0/`**.

The root `index.json` lists the lines; each line has its own `index.json` and `feed.xml`.

### 2. The layout of a line

```text
v1/1.1/
  clinvar-gkm_YYYY-MM.json.gz              official monthly full (ADR 0002), current year
  clinvar-gkm_YYYY-MM.json.gz.sha256
  clinvar-gkm_00-latest.json.gz            newest official monthly
  weekly/
    clinvar-gkm_YYYY-MMDD.json.gz          weekly FULL bundle, current month only
    clinvar-gkm_00-latest_weekly.json.gz   newest weekly full
  deltas/
    clinvar-gkm-delta_YYYY-MMDD.json.gz    current month's deltas
    clinvar-gkm-delta_YYYY-MMDD.json.gz.sha256
    clinvar-gkm-delta_YYYY-MMDD.manifest.json
    YYYY-MM/                               earlier months of the current year
  archive/YYYY/
    clinvar-gkm_YYYY-MM.json.gz            prior years' monthly fulls
    deltas/YYYY-MM/                        prior years' deltas
  parquet/                                 ONE Parquet dataset, overwritten every release
    {section}.parquet
    <manifest file>                        build date, source release, tool version
```

- **Checksums.** Every bundle has a `<file>.sha256` sidecar in `sha256sum -c` format, the counterpart of NCBI's
  `.md5`.
- **Monthlies.** The official monthly `clinvar-gkm_YYYY-MM` is chosen as ADR 0002 says: the newest build
  before ClinVar's `ClinVarVCVRelease_YYYY-MM` datetime. Its **`source_release`** (the release it was built
  from) is published in the line's `index.json`.
- **Weekly fulls are new.** A full bundle is published for every weekly release. Only the current month's are
  kept.
- **Deltas** keep their manifests. Each manifest's **`checkpoint_full` names the official monthly that precedes
  the delta**, so a replay can start from it.
- **Parquet** is one dataset, rebuilt and overwritten every release from the newest release. A manifest file
  beside it states the build date, the source release and the tool version. No Parquet is kept anywhere else:
  not per month, not per delta, not in `archive/` and not in frozen line folders. Past Parquet is rebuilt from
  the bundles with the `clinvar-gkm-parquet` tool (planned; until it ships, the 1.1.0 Parquet is exported by
  BigQuery).
- **Cleanup.** Everything on R2 outside this layout is deleted: the old `v1/datasets/`, `v1/deltas/` and dated
  Parquet trees, and `archive/1.0.1/` once it has moved to `v1/1.0/`.

### 3. Rollover triggers

Both rollovers run as part of the release that triggers them.

| Trigger | What moves or goes |
| --- | --- |
| The first release dated in a **new month** | The finished month's deltas (bundle, `.sha256`, manifest) move from `deltas/` into `deltas/YYYY-MM/`. The finished month's weekly fulls and their sidecars are **deleted** from `weekly/`. |
| The first release dated in a **new year** | The finished year's monthlies and sidecars move from the line's top level into `archive/YYYY/`, and its `deltas/YYYY-MM/` folders move into `archive/YYYY/deltas/YYYY-MM/`. The month rollover runs too. |

A move never changes a file's bytes, name or checksum, only its folder. The `00-latest` pointers stay at their
paths and are rewritten every release.

### 4. Weekly fulls are deleted: an exception to immutability

[ADR 0008](0008-bundles-are-the-public-record.md) (a) makes a published bundle immutable. **Weekly fulls are a
deliberate exception:** they are a convenience copy of the current month, deleted at month rollover, as NCBI
deletes its weekly releases. Nothing is lost: the official monthly that follows is built from the month's last
release (ADR 0002), and any past week can be rebuilt exactly from a monthly plus deltas:

1. Take the newest official monthly whose `source_release` ≤ the week W.
2. Apply, in release order, every delta whose `release` is later than that `source_release` and ≤ W.
3. Check the chain: the first delta's `baseline_release` equals the monthly's `source_release`, and each later
   delta's `baseline_release` equals the previous delta's `release`.

The monthlies and the deltas are the durable record.

### 5. Open point

A correction that must rewrite published bundles but does not change the schema shape (content-only, a PATCH by
ADR 0004 §1) has no place in this layout: a PATCH adds to the current folder, and the folder's bundles are
immutable. **The maintainer decides** whether such a correction opens a new MINOR folder or is published as new
dated files only.

## Consequences

- **Familiar for ClinVar users.** The monthly, `weekly/` and `archive/YYYY/` folders and the `00-latest` /
  `00-latest_weekly` names match NCBI's. `deltas/` has no NCBI counterpart and is our addition.
- **URLs move; bytes do not.** A delta URL changes when its month rolls over, and a monthly URL changes when its
  year rolls over. File names and `.sha256` stay the same, so a downloaded copy can still be identified. Scripts
  should resolve paths through the line's `index.json`, not hard-code them. A `path` written into an older delta
  manifest (`checkpoint_full.path`) can point at a monthly's pre-move location; resolve it by its release.
- **CDN purges.** Every move and every delete is followed by a CDN purge of the old paths, or the edge keeps
  serving them for up to the 1-month immutable TTL ([ADR 0005](0005-r2-custom-domain-and-cdn.md)). The single
  Parquet dataset is overwritten every release, so it is purged every release too. Each move or delete is a
  confirmed runbook step with a dry run first.
- **Cache rules.** The ADR 0005 rules must match the new paths:
  - immutable (long edge TTL): dated monthlies, weekly fulls, deltas, manifests and sidecars, and everything in
    `archive/` and in frozen line folders;
  - always fresh (bypass): `index.json`, `feed.xml`, and any path containing `00-latest`, which now also matches
    `clinvar-gkm_00-latest_weekly.json.gz`;
  - the Parquet dataset and its manifest: short cache plus a purge every release, replacing the rule that
    matched `/v1/datasets/parquet/00-latest/`, which no longer exists.
  The exact expressions are written in the release runbook.
- **Path allowlist.** Every published path stays under `/v1/`, so the WAF path allowlist needs no new prefix.
  `/archive/` can be dropped from it once `archive/1.0.1/` has moved.
- **Storage.** Weekly fulls add up to five bundles of about 4.8 GB each at the end of a month, about $0.36 a
  month at most. Dropping the dated Parquet sets saves about 65 GB.
- **Tools that read the layout** (the docs download browser, the DuckDB console, `generate-r2-index.sh`, the
  uploaders, `clinvar-gkm-parquet`) change with it.
- **ADR 0008** is amended: the immutability exception for weekly fulls, archives as `archive/YYYY/` inside a
  line, the 1.0.1 generation as `v1/1.0/`, and one overwritten Parquet dataset with no Parquet in archives.
