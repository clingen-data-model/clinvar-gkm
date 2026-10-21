# Bundle Record and Download Metrics Plan

> **Status: proposed (2026-10-18).** Governed by
> [ADR 0008](../../decisions/0008-bundles-are-the-public-record.md). Written against `main` @ `ed2eede` and `1.0`
> @ `b6ce46e`. **Amended 2026-10-20** for [ADR 0009](../../decisions/0009-r2-layout-mirrors-ncbi-clinvar.md)
> (R2 layout mirrors NCBI ClinVar): tasks 2–6 follow the new layout. Every live R2 write is a separately
> user-confirmed step.
>
> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development or superpowers:executing-plans.
> Steps use checkbox (`- [ ]`) syntax.

**Goal:** Treat the JSON bundles as the public record. Measure downloads, keep every superseded generation,
let users identify the generation they hold, label Parquet as derived, and have a runbook ready for the first
`v2/2.0/` line.

---

## Tasks at a glance

| # | Task | When | Branch | Status |
| --- | --- | --- | --- | --- |
| 1 | Daily download-stats collection | now | `main` | this PR |
| 2 | 1.0.1 generation → frozen line `v1/1.0/` | before the 1.1.0 republish | — (R2 only) | archived; move to do |
| 3 | ADR 0009 layout; sha256, `source_release`, `checkpoint_full`, line status in manifests | at the 1.1.0 republish | `1.0` (`feat/r2-ncbi-layout`) | in progress |
| 4 | Layout and "Parquet is derived" doc notes | with task 3 | `main` (#146) | in progress |
| 5 | Parquet rebuild tool (`clinvar-gkm-parquet`) | after 1.1.0 | own repo | design (its PR #1) |
| 6 | `v2/2.0/` line runbook | before the first post-GA breaking change | `main` | to do |
| 7 | Metrics review | 60 days after collection starts | — | scheduled |

---

## 1. Daily download-stats collection

Delivered with this plan:

- `src/scripts/collect-download-stats.sh` queries Cloudflare GraphQL `httpRequestsAdaptiveGroups` for one UTC
  day (default yesterday, `--date YYYY-MM-DD`) on host `data.clinvar-gkm.org`. It writes
  `date,path,status,requests,bytes,distinct_clients` to a CSV. Client IPs are used only in memory to count
  distinct clients; they are never stored. `--bq` also loads the rows into
  `clingen-dev:clinvar_ingest.gkm_download_stats` (created if missing; a re-run replaces that day's rows).
  `CF_EXCLUDE_IPS` leaves out maintainer IPs.
- `src/scripts/summarize-download-stats.py` estimates complete downloads per bundle as 2xx bytes served ÷ the
  object's size, with separate tables for monthly fulls and deltas and a summary of every other file.
- `.github/workflows/download-stats.yml` runs daily at 03:23 UTC (and on `workflow_dispatch` with an optional
  `date`) and appends the day to `stats/YYYY-MM.csv` on the orphan branch `ops/download-stats`.
  `deploy-docs.yml` only runs on pushes to `main`, so these commits never deploy the site.

Steps after merge:

- [ ] Add the repository secrets `CF_ANALYTICS_TOKEN` and `CF_ZONE_ID` (and optionally `CF_EXCLUDE_IPS`).
- [ ] Backfill from 2026-10-14, the first day the custom domain served. Cloudflare keeps about 31 days, so
  **2026-10-14 must be collected by about 2026-11-13**:
  `gh workflow run download-stats.yml -f date=2026-10-14`, then 15, 16, 17 and 18. Start each run after the
  previous one finishes (`gh run watch`): the workflow's concurrency group keeps only one pending run and
  cancels an older pending one.
- [ ] Check the first scheduled run created `ops/download-stats` with `stats/2026-10.csv`.

---

## 2. 1.0.1 generation becomes the frozen line `v1/1.0/`

The 1.0.1 JSON bundles were copied to `archive/1.0.1/` on 2026-10-18 (40 objects, 24.3 GB: 5 fulls including
`00-latest`, 16 deltas and manifests, an `index.json` / `feed.xml` snapshot), with a `MANIFEST.json` (sha256
per file) and a `README.txt`. Under [ADR 0009](../../decisions/0009-r2-layout-mirrors-ncbi-clinvar.md) it
moves to the frozen line folder `v1/1.0/`, and `archive/1.0.1/` is deleted. The 1.0.1 generation keeps no
Parquet.

- [ ] Confirm the archive holds the 4 dated monthly fulls, the 15 dated deltas and their manifests, and
  record whether the `00-latest` copies are included.
- [ ] Verify each `MANIFEST.json` sha256 against the copied objects.
- [ ] Move `archive/1.0.1/` to `v1/1.0/` (dry run first, confirmed step), re-verify the sha256s, then delete
  `archive/1.0.1/` and purge it from the CDN. The `MANIFEST.json` paths and `README.txt` name `v1/1.0/`.
- [ ] Record the frozen line in the 1.1.0 changelog entry and the completion notice: where it is, what it holds,
  and that it is the 1.0.1 generation.

---

## 3. Layout, manifest and index changes (on `1.0`, at the 1.1.0 republish)

The publishing scripts are changed on `feat/r2-ncbi-layout` (base `1.0`) to write the ADR 0009 layout under
`v1/1.1/`. What they must produce, for the docs and the gates:

**Why sidecars, not object metadata:** the uploaders copy every object of 2 GB or more (every monthly full
and its `00-latest` pointer) with `aws s3 cp --copy-props none`, because R2 lacks `GetObjectTagging`. That copy
drops user metadata, so a checksum stored as metadata would be lost. A `<file>.sha256` sidecar
(`sha256sum -c` format) survives every copy and every move.

- [ ] **Monthlies** at the line's top level: `clinvar-gkm_YYYY-MM.json.gz` + `.sha256`, and
  `clinvar-gkm_00-latest.json.gz` + `.sha256`. The year rollover moves a year's monthlies and sidecars to
  `archive/YYYY/`.
- [ ] **Weekly fulls** in `weekly/`: `clinvar-gkm_YYYY-MMDD.json.gz` + `.sha256` for every release, and
  `clinvar-gkm_00-latest_weekly.json.gz` + `.sha256`. The month rollover deletes the finished month's.
- [ ] **Deltas** in `deltas/`: `clinvar-gkm-delta_YYYY-MMDD.json.gz`, its `.sha256` and its manifest. The month
  rollover moves the finished month to `deltas/YYYY-MM/`; the year rollover moves those folders to
  `archive/YYYY/deltas/YYYY-MM/`.
- [ ] **Delta manifest.** `checkpoint_full` names the official monthly that **precedes** the delta (today
  every manifest names `2026-10`, the newest monthly, so a replay can't find its base). Add
  `bundle = {"path", "size", "sha256"}`. `build-delta-manifest.py` stays BigQuery-only; the uploader patches
  the file fields.
- [ ] **Parquet** in `parquet/`: one dataset, overwritten every release, with a manifest file giving the build
  date, the source release and the tool version (`source.json` is replaced). No Parquet anywhere else.
- [ ] **`generate-r2-index.sh`** writes `v1/1.1/index.json`:
    - every monthly entry gets `sha256` (from its sidecar; `null` when there is none) and **`source_release`**,
      the release the monthly was built from (ADR 0002);
    - every delta entry gets `"bundle": {"path", "size", "sha256"}` and the path of its manifest, in whichever
      folder the delta now sits;
    - the weekly fulls, the `archive/YYYY/` contents and the Parquet dataset are listed;
    - the Parquet entry gets `"derived": true`, and the index a top-level
      `"parquet_note": "Derived from the bundle; may be regenerated (ADR 0008)."`;
    - top level: `"schema_version"`, `"status"`, `"superseded_by"`, `"eol"`, from `LINE_STATUS` /
      `SUPERSEDED_BY` / `LINE_EOL` env vars (defaults `current`, `null`, `null`).
- [ ] **Root manifest.** Replace the hard-coded `"schema": "1.0.0"` with `SCHEMA_VERSION` read from
  `assemble-gkm-dicts.py` (overridable by env). List each line folder (`v1/1.1/` current, `v1/1.0/` frozen
  with `superseded_by` and `eol`). It replaces the `"archives"` pointer to `archive/1.0.1/` planned earlier.
- [ ] **`r2-readme.txt`.** Describe the layout, the rollovers, the `.sha256` sidecars and the Parquet note.
- [ ] **CDN** ([ADR 0005](../../decisions/0005-r2-custom-domain-and-cdn.md#layout-change-adr-0009)): point the
  "Latest Parquet" cache rule at the `parquet/` folder; purge old paths after every move and delete and the
  Parquet folder after every release; drop `/archive/` from the path allowlist after the 1.0.1 move.
- [ ] **Cleanup:** delete the old `v1/datasets/`, `v1/deltas/` and dated Parquet trees (confirmed step, dry
  run first, then purge).
- [ ] Gate: `generate-r2-index.sh --dry-run` output validates with `jq`; every monthly entry has a 64-hex
  `sha256` and a `source_release`; every delta's `checkpoint_full` names the newest monthly whose
  `source_release` is earlier than the delta's `release`.

---

## 4. Layout and "Parquet is derived" doc notes (on `main`, with task 3)

Done on PR #146 for the ADR 0009 layout:

- [ ] **`docs/data-access/*`** (download, monthly full, weekly deltas, Parquet, release model, index): every
  path under `v1/1.1/`; the weekly-full deletion and how to rebuild a past week; the single Parquet dataset,
  its manifest file, and rebuilding past versions with `clinvar-gkm-parquet` (planned); a note on how the
  layout mirrors NCBI.
- [ ] **Delta replay recipe** (`weekly-deltas.md`): to rebuild week W, take the newest monthly whose
  `source_release` ≤ W, then apply the deltas whose `release` is later than that `source_release` and ≤ W,
  checking the chain. The old recipe compared months and skipped same-month deltas.
- [ ] **`docs/assets/js/r2-browser.js`** and **`docs/assets/duckdb-console.html`** read the new index and
  Parquet paths.
- [ ] **`docs/reference/versioning.md`.** New section "The public record": bundles immutable from 1.1.0 except
  weekly fulls, frozen lines such as `v1/1.0/`, sha256 sidecars, how to check a local copy
  (`sha256sum -c`), Parquet is derived. Update the root-manifest example. Update the "Initial-stabilization
  period" admonition once GA is confirmed (ADR 0008 (a)).
- [ ] `zensical build --clean --strict` and `python src/scripts/check-site-links.py` pass.

---

## 5. Parquet rebuild tool (`clinvar-gkm-parquet`)

ADR 0008 (e) needs a tool a user can run on a **published bundle**. It is
[`clinvar-gkm-parquet`](https://github.com/clingen-data-model/clinvar-gkm-parquet), a separate repo with its own
version cadence (design plan on its PR #1). Each tool version declares the bundle `schema_version`s it accepts
and the Parquet table spec it produces. Workstream 1 of the
[simplification plan](2026-10-18-pipeline-simplification.md#3-workstream-1-parquet-built-from-the-bundle-output)
then pins the tool so the pipeline and users build Parquet the same way.

Steps:

- [ ] Build the tool against the 1.1.0 BigQuery-exported Parquet as its oracle (`EXCEPT ALL` in both directions
  = 0 rows per table, with the same schema).
- [ ] The tool writes the Parquet manifest file (build date, source release, tool version) that the published
  `v1/1.1/parquet/` dataset carries.
- [ ] The tool reads inputs in the ADR 0009 layout: monthlies at the line's top level, `weekly/`, `deltas/`
  with its `YYYY-MM/` folders, and `archive/YYYY/`. To rebuild a past week it uses the replay rule in task 4,
  using `checkpoint_full` and each monthly's `source_release`.
- [ ] ClinVar-GKM pins a tool version and the release builds `parquet/` with it.
- [ ] Docs: a "Rebuild Parquet from a bundle" page linked from the Parquet page.
- [ ] **Decision:** which bundles the tool accepts. Parquet published before the tool (1.0.x, and 1.1.0,
  whose Parquet is built by BigQuery SQL) cannot be reproduced bit-for-bit. Options: the tool accepts only
  1.1.0 bundles and later; or it also reads the 1.0.x section layout (`var*-proposition`) in `v1/1.0/` and
  rebuilds it in the 1.1.0 table shape.

---

## 6. `v2/2.0/` line runbook

A runbook for ADR 0008 (b), to write before the first breaking change after GA. It covers:

- [ ] The RFC (ADR 0004 §8) and its 4-week window.
- [ ] Building `v2/2.0/` in full with `R2_PREFIX=v2/2.0/` (the uploaders and `generate-r2-index.sh` read it;
  `run-release.sh` needs it passed through and a per-line stop rule).
- [ ] `generate-r2-index.sh`: the root manifest lists more than one line (today it hard-codes the single `v1`
  entry); `active` becomes `["1", "2"]` and then `["2"]`.
- [ ] Freezing `v1/1.x/`: `LINE_STATUS=superseded`, `SUPERSEDED_BY=2`, `LINE_EOL=<date>` written to
  the line's `index.json` and the root manifest; no more uploads to it. The same steps freeze a line folder
  when a new MINOR opens (ADR 0009 §1).
- [ ] The switch-over notice: email list, Discussions *Announcements*, the feed, the changelog.
- [ ] CDN check: the ADR 0005 cache rules match by `00-latest` / `index.json` / `feed.xml`, not by `v1/`, so they
  already cover `v2/`; the latest-Parquet rule must also match `v2/2.0/parquet/`; verify with
  `cf-cache-status`.
- [ ] Docs: `reference/versioning.md`, the download pages and the console point at the current line.
- [ ] Depends on ADR 0008's open point: freeze at the switch-over, or keep ADR 0004 §3's 6-month live window.

---

## 7. Metrics review (60 days)

- [ ] **When:** 60 days after the first collected day. With the backfill from 2026-10-14, that is about
  **2026-12-13**.
- [ ] Run `summarize-download-stats.py` on `stats/2026-10.csv` … `stats/2026-12.csv` from `ops/download-stats`,
  per month.
- [ ] Decide N for ADR 0008 (f), then apply the triggers: archive retention and promotion, and freeze vs
  parallel window for the next breaking change (ADR 0008 (b)).
- [ ] Decide whether to keep collecting daily and whether to load the CSVs into BigQuery (`--bq`).
- [ ] Move ADR 0008 from Proposed to Accepted (or amend it) with the numbers.
