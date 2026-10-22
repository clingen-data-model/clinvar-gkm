# 0009 — R2 layout mirrors NCBI ClinVar

- **Status:** Proposed
- **Date:** 2026-10-20
- **Amends:** [ADR 0004](0004-schema-versioning-and-release-management.md) §4 (directories per version line) and
  §1 (a content-only correction that rewrites bundles takes a MINOR line, §5 below),
  [ADR 0005](0005-r2-custom-domain-and-cdn.md) (cache rules, path allowlist, layout note),
  ADR 0006 (on PR #146) Decision 2 (1.1.0 ships under `v1/1.1/`, not in place in `/v1/`), [ADR 0008](0008-bundles-are-the-public-record.md) (a), (c), (e)
- **Plan:** [`docs/superpowers/plans/2026-10-18-bundle-record-and-metrics.md`](../superpowers/plans/2026-10-18-bundle-record-and-metrics.md)
- **Decided:** 2026-10-21 (maintainer): §5 is no longer open. A content-only correction that rewrites published
  bundles is released as a new MINOR line folder; a PATCH only adds new dated files.
- **Amended:** 2026-10-21 to match the layout code merged on `1.0` (PR #182: `r2_layout.py`, `r2-rollover.sh`,
  `cf-rules.sh`, `run-release.sh`): the finished month's newest weekly full is kept until the new month's
  monthly is published (§2, §3, §4); `weekly/` is not cached as immutable (Consequences); file names, the root
  and line `index.json`, `checkpoint_full` and the Parquet manifest fields (§1, §2).

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

- A PATCH release (1.1.x) only **adds** new dated files to the current line folder. It never rewrites a
  published file (§5).
- A new MINOR starts a new folder (`v1/1.2/`); a new MAJOR starts `v2/2.0/`.
- A folder that a newer line replaces is **frozen** and kept indefinitely
  ([ADR 0008](0008-bundles-are-the-public-record.md) (b)): nothing is added to it, moved in it or deleted from it.
- The 1.0.1 generation, archived on 2026-10-18 to `archive/1.0.1/`, moves to the frozen line **`v1/1.0/`**.

The bucket-root `index.json` lists the lines: `manifest_version: 2`, `current` (the current line, `"v1/1.1"`)
and `versions`, keyed by line name (`"1.1"`, `"1.0"`). Each entry gives `line`, `major`, `minor`, `status`
(`"current"` or `"frozen"`), `schema`, `superseded_by` (the line that replaced it, such as `"v1/1.1"`, or
`null`), `index` and `feed`. There is no `eol` field. Consumers pick the entry whose status is `"current"`.

Each line has its own `index.json` and `feed.xml`. A line's `index.json` carries the same `line`, `status`,
`superseded_by` and `schema_version`, plus `current_month`, `latest_release`, `datasets.monthly[]`,
`datasets.weekly[]`, `deltas[]`, `archives` (keyed by year) and `parquet` (§2).

### 2. The layout of a line

```text
v1/1.1/
  index.json, feed.xml, README.txt
  clinvar-gkm_YYYY-MM.json.gz              official monthly full (ADR 0002), current year
  clinvar-gkm_YYYY-MM.json.gz.sha256
  clinvar-gkm_00-latest.json.gz            newest official monthly (same bytes), + .sha256
  weekly/
    clinvar-gkm_YYYY-MMDD.json.gz          weekly FULL bundle of the current month (§3), + .sha256
    clinvar-gkm_00-latest_weekly.json.gz   newest weekly full (same bytes), + .sha256
  deltas/
    clinvar-gkm-delta_YYYY-MMDD.json.gz    current month's deltas
    clinvar-gkm-delta_YYYY-MMDD.json.gz.sha256
    clinvar-gkm-delta_YYYY-MMDD.manifest.json
    YYYY-MM/                               earlier months of the current year
  archive/YYYY/
    clinvar-gkm_YYYY-MM.json.gz            prior years' monthly fulls, + .sha256
    deltas/YYYY-MM/                        prior years' deltas
  parquet/                                 ONE Parquet dataset, overwritten every release
    {section}.parquet
    manifest.json
```

A frozen line keeps the shape it was frozen with. `v1/1.0/` holds the monthlies 2026-07 to 2026-10 and
`clinvar-gkm_00-latest.json.gz` at the top, every delta under `deltas/YYYY-MM/`, and `MANIFEST.json`,
`README.txt`, `index.json` and `feed.xml`. It has no `weekly/` and no `parquet/`.

- **Checksums.** Every bundle (dated, `00-latest`, weekly and delta) has a `<file>.sha256` sidecar in
  `sha256sum -c` format (`<sha256>  <file name>`), the counterpart of NCBI's `.md5`. The line's `index.json`
  repeats each bundle's `sha256` and `size`.
- **Monthlies.** The official monthly `clinvar-gkm_YYYY-MM` is chosen as ADR 0002 says: the newest build
  before ClinVar's `ClinVarVCVRelease_YYYY-MM` datetime. `run-release.sh` publishes it as a server-side copy of
  that release's weekly full, or re-exports it from BigQuery if the weekly full is gone. Each monthly's
  **`source_release`** (the release it was built from) is published in the line's `index.json`, next to its
  `release` (the `YYYY-MM` label). The `00-latest` copy is an entry with `latest: true` and the `release` it
  equals.
- **Weekly fulls are new.** A full bundle is published for every weekly release. Only the current month's are
  kept, plus the finished month's newest one until the new month's official monthly is published (§3).
- **Deltas** keep their manifests, now named `clinvar-gkm-delta_YYYY-MMDD.manifest.json` beside the bundle.
  Each manifest gains `schema_version`, `bundle` `{name, path, size, sha256}`, `sha256` and
  **`checkpoint_full`**: the newest official monthly whose `source_release` is on or before the delta's
  `baseline_release`, so a replay can start from it. Its shape is `{path, release, month, sha256}`, where
  `release` is the monthly's `source_release` (comparable with `baseline_release`) and `month` is its `YYYY-MM`
  label.
- **Parquet** is one dataset, rebuilt and overwritten every release from the newest release.
  `parquet/manifest.json` beside it gives `derived: true`, `build_date`, `source_release`, `dataset`, `builder`
  (`"BigQuery export"` until the tool ships), `table_spec_version`, `schema_version`, a `note`, and `files[]`
  with each file's `name`, `size` and `sha256`. The line's `index.json` summarizes it under `parquet`. No
  Parquet is kept anywhere else: not per month, not per delta, not in `archive/` and not in frozen line
  folders. Past Parquet is rebuilt from the bundles with the `clinvar-gkm-parquet` tool (planned; until it
  ships, the 1.1.0 Parquet is exported by BigQuery).
- **Cleanup.** Everything on R2 outside a published line and the root `index.json` is deleted: the old
  `v1/datasets/`, `v1/deltas/` and dated Parquet trees, and `archive/1.0.1/` once it has moved to `v1/1.0/`.

### 3. Rollover triggers

`run-release.sh` runs `r2-rollover.sh` before a release's weekly uploads and again after its monthly step. The
plan comes from `r2_layout.py` (`plan_rollover`) and is idempotent: when the line already matches the layout,
nothing happens.

| Trigger | What moves or goes |
| --- | --- |
| The first release dated in a **new month** | The finished month's deltas (bundle, `.sha256`, manifest) move from `deltas/` into `deltas/YYYY-MM/`. The finished month's weekly fulls and their sidecars are **deleted** from `weekly/`, **except the newest**, which is kept until the new month's official monthly is published: it is that monthly's ADR 0002 source candidate, and the monthly is a server-side copy of it. The rollover that runs after the monthly is published deletes it. |
| The first release dated in a **new year** | The finished year's monthlies and sidecars move from the line's top level into `archive/YYYY/`, and its `deltas/YYYY-MM/` folders move into `archive/YYYY/deltas/YYYY-MM/`. The month rollover runs too. |

A move never changes a file's bytes, name or checksum, only its folder. The `00-latest` pointers stay at their
paths and are rewritten every release.

### 4. Weekly fulls are deleted: an exception to immutability

[ADR 0008](0008-bundles-are-the-public-record.md) (a) makes a published bundle immutable. **Weekly fulls are a
deliberate exception:** they are a convenience copy of the current month, deleted at month rollover (the
newest one once the next official monthly is published), as NCBI deletes its weekly releases. Nothing is lost:
the official monthly is built from the newest release before ClinVar's monthly (ADR 0002), normally the
finished month's last weekly, and any past week can be rebuilt exactly from a monthly plus deltas:

1. Take the newest official monthly whose `source_release` ≤ the week W.
2. Apply, in release order, every delta whose `release` is later than that `source_release` and ≤ W.
3. Check the chain: the first delta's `baseline_release` equals the monthly's `source_release`, and each later
   delta's `baseline_release` equals the previous delta's `release`.

The monthlies and the deltas are the durable record.

### 5. Content-only corrections open a new MINOR line

*Decided 2026-10-21 by the maintainer.* A correction that must rewrite published bundles without changing the
schema shape (a content-only change, which ADR 0004 §1 does not count as a schema version change) is released
as a **new MINOR line folder**: for example, 1.2.0 is published into `v1/1.2/`, and `v1/1.1/` is frozen and kept
(ADR 0008 (b), (c)). A **PATCH** (1.1.x) only ever **adds** new dated files to the current line folder and never
rewrites one. This amends ADR 0004 §1 for that case: a release that rewrites published bundles takes a MINOR
number even when the schema shape is unchanged. The new line's schema `$id` version and every bundle's `schema_version` move to
that MINOR (for example `1.2.0`) as well (*decided 2026-10-22*), so a bundle's `schema_version` always names
the line folder it was published in.

## Consequences

- **Familiar for ClinVar users.** The monthly, `weekly/` and `archive/YYYY/` folders and the `00-latest` /
  `00-latest_weekly` names match NCBI's. `deltas/` has no NCBI counterpart and is our addition.
- **URLs move; bytes do not.** A delta URL changes when its month rolls over, and a monthly URL changes when its
  year rolls over. File names and `.sha256` stay the same, so a downloaded copy can still be identified. Scripts
  should resolve paths through the line's `index.json`, not hard-code them. A `path` written into an older delta
  manifest (`checkpoint_full.path`) can point at a monthly's pre-move location; resolve it by its release. The
  delta manifests in the frozen `v1/1.0/` keep their 1.0.1 bytes, so their paths name the old `v1/datasets/`
  and `v1/deltas/` keys and their `checkpoint_full` always says `2026-10`; use that line's `index.json`
  (each monthly's `source_release`) instead.
- **CDN purges.** `r2-rollover.sh` purges every path it moved or deleted, or the edge would keep serving a
  moved small file for up to the 1-month immutable TTL ([ADR 0005](0005-r2-custom-domain-and-cdn.md)).
  `run-release.sh` purges the `parquet/` prefix after every Parquet rebuild. The one-time 1.1.0 migration
  (`republish-v1.sh`) ends with a full purge; each of its steps is user-confirmed, with a dry run first. The
  rollover itself runs inside `run-release.sh`; `--dry-run` or `--listing` shows its plan first.
- **Cache rules.** `src/scripts/cf-rules.sh` holds the expressions (`show` is read-only; `apply` is a
  user-confirmed step). Three cache rules, in this order; the last matching rule wins:
  1. **"R2 immutable artifacts"** matches every path on `data.clinvar-gkm.org`: edge 1 month, browser 1 day.
     In effect it covers whatever rules 2 and 3 do not: dated monthlies, deltas, delta manifests and `.sha256`
     sidecars outside `weekly/`, everything in `archive/YYYY/`, and frozen line folders' bundles and
     `MANIFEST.json`. These are write-once at their path; a rollover moves them to new keys and purges the old
     ones.
  2. **"R2 mutable pointers"** bypasses the cache for any path containing `00-latest` (which also matches
     `clinvar-gkm_00-latest_weekly.json.gz`), ending in `/index.json`, `/feed.xml` or `/README.txt`, or
     containing `/weekly/`. Weekly fulls and their sidecars are **not** cached as immutable, because the
     rollover deletes them.
  3. **"Latest Parquet"** matches any path under `/v1/` containing `/parquet/` (the dataset and its
     `manifest.json`): edge 1 day, browser 1 hour (ADR 0005), purged after every rebuild. It replaces the rule
     that matched `/v1/datasets/parquet/00-latest/`, which no longer exists.

  Bundles larger than 512 MB are never cached on the Free plan (ADR 0005), so these rules matter mostly for
  sidecars, manifests, indexes and Parquet.
- **Path allowlist.** Every published path stays under `/v1/`, so the WAF path allowlist needs no new prefix.
  `/archive/` can be dropped from it once `archive/1.0.1/` has moved (`cf-rules.sh apply --drop-archive`).
- **Storage.** Weekly fulls add up to five bundles of about 4.8 GB each at the end of a month, about $0.36 a
  month at most. Dropping the dated Parquet sets saves about 65 GB.
- **Tools that read the layout** (the docs download browser, the DuckDB console, `generate-r2-index.sh`, the
  uploaders, `clinvar-gkm-parquet`) change with it.
- **ADR 0008** is amended: the immutability exception for weekly fulls, archives as `archive/YYYY/` inside a
  line, the 1.0.1 generation as `v1/1.0/`, and one overwritten Parquet dataset with no Parquet in archives.
