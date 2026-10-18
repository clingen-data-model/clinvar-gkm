# Bundle Record and Download Metrics Plan

> **Status: proposed (2026-10-18).** Governed by
> [ADR 0008](../../decisions/0008-bundles-are-the-public-record.md). Written against `main` @ `ed2eede` and `1.0`
> @ `b6ce46e`. Every live R2 write is a separately user-confirmed step.
>
> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development or superpowers:executing-plans.
> Steps use checkbox (`- [ ]`) syntax.

**Goal:** Treat the JSON bundles as the public record. Measure downloads, keep every superseded generation,
let users identify the generation they hold, label Parquet as derived, and have a runbook ready for the first
`/v2/` line.

---

## Tasks at a glance

| # | Task | When | Branch | Status |
| --- | --- | --- | --- | --- |
| 1 | Daily download-stats collection | now | `main` | this PR |
| 2 | 1.0.1 bundle archive | before the 1.1.0 republish | — (R2 only) | in progress |
| 3 | sha256, `status` / `superseded_by`, archive pointer in manifests | at the 1.1.0 republish | `1.0` | to do |
| 4 | "Parquet is derived" doc notes | with task 3 | `main` | to do |
| 5 | Parquet rebuild tool | with ADR 0007 Workstream 1 | `main`, then `1.0` | to do |
| 6 | `/v2/` line runbook | before the first post-GA breaking change | `main` | to do |
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

## 2. 1.0.1 bundle archive (in progress)

Another session is copying the 1.0.1 JSON bundles to `archive/1.0.1/` before the 1.1.0 republish rewrites
`/v1/`. The archive mirrors the live paths under it (`archive/1.0.1/v1/deltas/2026-0706/…`) and carries a
`MANIFEST.json` (sha256 per file) and a `README.txt`.

- [ ] Confirm the archive holds the 4 dated monthly fulls, the 15 dated deltas and their `manifest.json`
  files, and record whether the `00-latest` copies are included.
- [ ] Verify each `MANIFEST.json` sha256 against the live `/v1/` object before the 1.1.0 overwrite.
- [ ] Record the archive in the 1.1.0 changelog entry and the completion notice: where it is, what it holds,
  and that it is the 1.0.1 generation.

---

## 3. Manifest and index changes (on `1.0`, at the 1.1.0 republish)

Today no published file carries a checksum. `v1/index.json` lists monthly fulls as
`{name, path, size, modified, latest}`, delta entries as `{release, path, manifest, modified, parquet,
latest}` with no bundle size or hash, and the root manifest hard-codes `"schema": "1.0.0"` (it still says
`1.0.0` live, though 1.0.1 shipped).

**Why sidecars, not object metadata:** the uploaders copy every object of 2 GB or more (every monthly full
and its `00-latest` pointer) with `aws s3 cp --copy-props none`, because R2 lacks `GetObjectTagging`. That copy
drops user metadata, so a checksum stored as metadata would be lost. A `<file>.sha256` sidecar
(`sha256sum -c` format) survives every copy.

Exact changes:

- [ ] **`upload-gkm-to-r2.sh`.** Before `r2_upload "${BUNDLE_FILE}" "datasets/${MONTHLY_FILE}"` (line ~350),
  hash the local bundle once and upload `datasets/${MONTHLY_FILE}.sha256`; after the `00-latest` copy, upload
  `datasets/clinvar-gkm_00-latest.json.gz.sha256` (same hash, its own file name). The year-rollover move to
  `archives/{yyyy}/` (line ~264) moves the sidecar with its bundle.
- [ ] **`upload-gkm-delta-to-r2.sh`.** In the Python patch that sets `manifest.checkpoint_full` (line ~228),
  also set `manifest.bundle = {"path", "size", "sha256"}` from the local delta bundle and
  `manifest.parquet = {section: {"size", "sha256"}}` from the local Parquet files. Upload
  `${PREFIX}/${DELTA_NAME}.sha256` next to the bundle and copy it to `00-latest` with the latest name.
  `build-delta-manifest.py` stays BigQuery-only; it never sees the files.
- [ ] **`generate-r2-index.sh`.**
    - `build_file_array`: add `"sha256"` to each monthly entry, read from its sidecar (`aws s3 cp …/<file>.sha256 -`),
      `null` when there is none. `r2_ls_with_size` matches only `.json.gz`, so sidecars never become entries.
    - `build_deltas_array`: add `"bundle": {"path", "size", "sha256"}` from the delta's sidecar and listing.
    - `datasets.parquet` and each delta: add `"derived": true`, and add a top-level
      `"parquet_note": "Derived from the bundle; may be regenerated (ADR 0008)."`.
    - Per-line index top level: `"schema_version"`, `"status"`, `"superseded_by"`, `"eol"`, from
      `LINE_STATUS` / `SUPERSEDED_BY` / `LINE_EOL` env vars (defaults `current`, `null`, `null`).
    - Root manifest: replace the hard-coded `"schema": "1.0.0"` with `SCHEMA_VERSION` read from
      `assemble-gkm-dicts.py` (overridable by env); add `"superseded_by": null` to each version; add
      `"archives": [{"version": "1.0.1", "path": "archive/1.0.1/", "manifest": "archive/1.0.1/MANIFEST.json",
      "readme": "archive/1.0.1/README.txt"}]`, built by listing `archive/`. The additions are additive, so
      `manifest_version` stays `1`.
- [ ] **`r2-readme.txt`.** Describe `archive/<version>/`, the `.sha256` sidecars and the Parquet note.
- [ ] **CDN.** No rule change: `archive/…` and dated sidecars fall under the immutable rule, and
  `…00-latest….sha256` under the bypass rule (ADR 0005).
- [ ] Gate: `generate-r2-index.sh --dry-run` output validates with `jq`, and every monthly and delta entry has a
  64-hex `sha256` after the republish.

---

## 4. "Parquet is derived" doc notes (on `main`, with task 3)

- [ ] **`docs/data-access/parquet.md`.** Add a note under the title: Parquet is derived from the bundle, may
  be regenerated, and is not archived; the bundle is the record. Line 8 says prior-year Parquet month sets are
  "retained indefinitely"; reword it to match ADR 0008 (e).
- [ ] **`docs/parquet/index.md`.** One line in "Start Here" with the same point and a link to the rebuild tool
  (task 5) once it exists.
- [ ] **`docs/reference/versioning.md`.** New section "The public record": bundles immutable from 1.1.0,
  archived generations under `archive/<version>/`, sha256 in every manifest, how to check a local copy
  (`sha256sum -c`), Parquet is derived. Update the root-manifest example with `superseded_by` and
  `archives`. Update the "Initial-stabilization period" admonition once GA is confirmed (ADR 0008 (a)).
- [ ] Related pages with the same "retained indefinitely" claim for Parquet: `docs/data-access/index.md`,
  `docs/data-access/release-model.md`. Check both.
- [ ] `zensical build --clean --strict` and `python src/scripts/check-site-links.py` pass.

---

## 5. Parquet rebuild tool (with ADR 0007 Workstream 1)

ADR 0008 (e) needs a tool a user can run on a **published bundle**. Workstream 1 of the
[simplification plan](2026-10-18-pipeline-simplification.md#3-workstream-1-parquet-built-from-the-bundle-output)
recommends option (A): DuckDB builds the Parquet from per-section NDJSON
(`{"id": <key>, "record": <cleaned record>}`) that the assembler writes, which holds the same bytes as the
bundle. The two fit together if the tool and the pipeline share the DuckDB SQL and differ only in where the
NDJSON comes from:

- **Pipeline:** assembler → per-section NDJSON → shared DuckDB SQL → Parquet.
- **Tool:** published bundle → streaming splitter (the `stream_keys.py` pattern, Workstream 1 option (B)) →
  the same per-section NDJSON → the same DuckDB SQL → Parquet.

Steps:

- [ ] Land Workstream 1 with the DuckDB SQL in one directory that both paths import.
- [ ] Add the splitter and a CLI, e.g. `src/parquet-rebuild/rebuild-parquet <bundle.json.gz> <out_dir>`,
  pinned per release by the git tag (`git checkout <tag>`; or `pipx install` from the tag).
- [ ] Gate (added to Workstream 5's release gate): the tool run on the published bundle and the pipeline's
  Parquet are equal, `EXCEPT ALL` in both directions = 0 rows per table, with the same schema.
- [ ] Docs: a "Rebuild Parquet from a bundle" page linked from task 4's notes.
- [ ] **Decision:** which bundles the tool accepts. Parquet published before Workstream 1 (1.0.x, and 1.1.0,
  whose Parquet is also built by BigQuery SQL) cannot be reproduced bit-for-bit. Options: the tool accepts
  only bundles from its first tagged release on; or it also reads the 1.0.x section layout
  (`var*-proposition`) and rebuilds those archives in the 1.1.0 table shape.

---

## 6. `/v2/` line runbook

A runbook for ADR 0008 (b), to write before the first breaking change after GA. It covers:

- [ ] The RFC (ADR 0004 §8) and its 4-week window.
- [ ] Building `/v2/` in full with `R2_PREFIX=v2/` (the uploaders and `generate-r2-index.sh` already read it;
  `run-release.sh` needs it passed through and a per-line stop rule).
- [ ] `generate-r2-index.sh`: the root manifest lists more than one line (today it hard-codes the single `v1`
  entry); `active` becomes `["1", "2"]` and then `["2"]`.
- [ ] Freezing `/v1/`: `LINE_STATUS=superseded`, `SUPERSEDED_BY=2`, `LINE_EOL=<date>` written to
  `v1/index.json` and the root manifest; no more `/v1/` uploads.
- [ ] The switch-over notice: email list, Discussions *Announcements*, the feed, the changelog.
- [ ] CDN check: the ADR 0005 cache rules match by `00-latest` / `index.json` / `feed.xml`, not by `v1/`, so they
  already cover `/v2/`; verify with `cf-cache-status`.
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
