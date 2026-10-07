# Downloads — split into a nav group, approachable hub, R2 dates, weekly Parquet browsing

- **Date:** 2026-10-07
- **Status:** Draft (design)
- **Scope target:** `1.0` release branch (part of the 1.0.1 RC)
- **Primary files:** `docs/data-access/*.md` (split of `download.md`), `zensical.toml` (nav),
  `docs/assets/js/r2-browser.js` (new shared browser), `src/scripts/generate-r2-index.sh`
  (+ the `index.json` it produces)

## 1. Problem

The Downloads page is one long scroll serving three audiences at once (returning users who want the
latest or an older release, first-timers learning the full+delta model, power users wanting
copy-paste recipes). The right-hand TOC is overloaded. The "Browse All Releases" widget — the thing
returning users most want — is buried, and shows no indication of **when** each artifact reached R2.
Weekly Parquet deltas exist on R2 (`deltas/<YYYY-MMDD>/parquet/<section>.parquet`) but are not
browsable because `index.json` only enumerates the monthly Parquet sets.

## 2. Goals

- **Split Downloads into a left-nav group of child pages** (like the existing "Data Guide" / "Data
  Model" sections), so each topic is its own page with its own manageable TOC.
- Make the group landing an approachable **hub**: the three latest download types (monthly full,
  weekly delta, Parquet full set) with R2 dates + direct links + links into each type's page.
- Give each type page a **browser scoped to that type**, with cross-links to the sibling pages.
- Surface **weekly Parquet deltas** in a browser on the Parquet page.
- Add the **R2 availability date** (object `LastModified`, date only, UTC) to every browsable entry.
- Collapse curl / Python / DuckDB recipes behind one-line expanders; keep concepts visible.
- Provide a visible reference for **reconstituting a full Parquet view as of any week in a month**,
  with the involved scripts in expandable subsections.

## 3. Non-goals (YAGNI)

- No change to the release/upload pipeline beyond `generate-r2-index.sh`.
- No change to the full+delta model, the R2 directory layout, or object naming.
- No consolidation of the currently nav-orphaned `data-access/index.md` and
  `data-access/output-files.md` (left as-is except for migrating their stale links — see §5.7).
- The hub reads `index.json`; it does not issue per-file HEAD requests.

## 4. Current state (verified 2026-10-07)

- Nav: `{ Downloads = "data-access/download.md" }` — a single top-level page. `data-access/` also has
  `examples.md` (under Data Guide) and `index.md` + `output-files.md` (both **not** in nav).
- `index.json` (built by `src/scripts/generate-r2-index.sh`, called by both uploaders) entry shapes:
  monthly `{name,path,size,latest}`; parquet set `{release,path,latest}`; delta
  `{release,path,manifest,latest}`; top-level `updated_at`. **No per-entry date.**
- `aws s3 ls` returns `DATE TIME SIZE NAME` for files; the generator discards the date. Delta and
  Parquet-set entries are directories (`PRE name/`) with no date — a representative inner file must
  be listed to date them.
- Weekly Parquet exists (`deltas/00-latest/parquet/scv.parquet`, `deltas/2026-0928/parquet/scv.parquet`
  → HTTP 206); it is the changed-rows delta form, not a complete set. No "weekly full" Parquet.
- The inline browser script in `download.md` fetches `index.json` once, rendering Monthly, Weekly
  Deltas, Parquet Month Sets, Archives into one `#r2-tree`.
- **Inbound deep links to migrate** (strict build enforces): `#consumer-replay-model` from
  `index.md`, `output-files.md`, `getting-started.md`; `#weekly-deltas` from `output-files.md`,
  `export.md`; `#parquet-files` from `export.md`, `user-story-audit.md` (×2).

## 5. Design

### 5.1 Nav group + page map

Convert the single Downloads nav entry into a group with a bare index page (the hub) plus titled
child pages — the same shape the repo already uses for "Data Model":

```toml
{ Downloads = [
  "data-access/download.md",                              # section index — the hub
  { "Monthly Full Bundles" = "data-access/monthly-full.md" },
  { "Weekly Deltas"        = "data-access/weekly-deltas.md" },
  { "Parquet Files"        = "data-access/parquet.md" },
  { "How Releases Work"    = "data-access/release-model.md" },
] },
```

Page responsibilities:

| Page | File | Contents |
|------|------|----------|
| **Downloads** (hub) | `download.md` (rewritten) | 1–2 line intro; **Latest Release** hub (3 latest types + R2 dates + direct links + links into each type page); "new here? → How Releases Work"; short **Directory Structure**; **Feedback**. Deliberately short. |
| **Monthly Full Bundles** | `monthly-full.md` (new) | Browser (monthly fulls + archived monthly); sibling cross-links; collapsed curl/Python download recipes. |
| **Weekly Deltas** | `weekly-deltas.md` (new) | Browser (delta releases + dates); Delta Bundle + the **canonical `manifest.json` field table**; **Consumer Replay Model** (visible); collapsed recipes (download a delta; rebuild the current full JSON from deltas). Owns `#weekly-deltas`, `#consumer-replay-model`. |
| **Parquet Files** | `parquet.md` (new) | Two browsers (monthly full sets; weekly Parquet deltas); **reconstitute a full Parquet view for any week in a month** (visible reference); collapsed DuckDB/pandas query recipes and rebuild scripts. |
| **How Releases Work** | `release-model.md` (new) | Conceptual: full+delta model, the month-start-baseline note, release cadence. Links to the canonical `manifest.json` field table on **Weekly Deltas** rather than duplicating it. |

### 5.2 Latest Release (hub)

A compact table, rendered by the shared browser. **Data source per type:** the `latest:true`
entries in `index.json` are the `00-latest` *aliases* and carry no human release label (monthly
`name` is `clinvar-gkm_00-latest.json.gz`; delta/parquet `release` is `"latest"`). So for the
**Release** column the browser selects the newest **dated** entry (`release != "latest"`, max
`release`) of each type; its `modified` fills **R2 available**; the stable `00-latest` alias URL fills
**Download**.

| Type | Release | R2 available | Download | Browse all |
|------|---------|--------------|----------|------------|
| Monthly full | `2026-10` | `2026-10-05` | latest `.json.gz` | → Monthly Full Bundles |
| Weekly delta | `2026-10-04` | `2026-10-06` | latest delta + manifest | → Weekly Deltas |
| Parquet (full) | `2026-10` | `2026-10-05` | latest set | → Parquet Files |

"Browse all" are page links to the child pages. Date cells are blank if `index.json` lacks
`modified` (pre-regeneration — graceful fallback).

### 5.3 Per-type pages

Each type page: (1) opens with a **browser scoped to its type**, (2) carries a one-line **sibling
cross-link row** (page links), (3) ends with **collapsed** recipes (`???`, one-line summaries).
Archives render inside the relevant type browser (archived monthly fulls on Monthly Full Bundles;
archived Parquet sets on Parquet Files). Deltas are not archived by year.

### 5.4 Parquet page (two browsers + reconstitution reference)

- **Monthly full sets** browser — from `index.json.datasets.parquet` (+ archived); composes the 22
  section files per set (all present in a full set); shows the set `modified` date. (When moving this
  content, fix the current page's stale "Available Parquet files (20 sections)" wording to 22.)
- **Weekly Parquet deltas** browser — from `index.json.deltas`, one group per delta with a non-empty
  `parquet` list, composing `deltas/<dir>/parquet/<section>.parquet` for only the sections present
  that week (from the new per-delta `parquet` field — no 404 links); shows the delta `modified` date;
  a note states it is changed-rows delta Parquet, not a full set.
- **Reconstitution reference (visible):** "Rebuild a full Parquet view as of any week in a month" —
  bootstrap from the checkpoint monthly full set, then apply each weekly delta Parquet (added/updated
  rows) **and** the manifest's `sections.<s>.deleted` ids, oldest→newest, up to the chosen week.
  3–4 sentences + a small flow description, linking to the expanders.
- **Collapsed recipes:** "apply one week" (DuckDB upsert), "chain to a specific week" (Python) —
  generalized from the current "Applying Deltas (keeping a Parquet set current)" code so the target
  week is a parameter; plus DuckDB/pandas query recipes.

### 5.5 Collapsible pattern

Material collapsible call-outs (`???`, collapsed by default) wrap **code only**; headings and prose
stay visible so deep links land on visible targets and first-timers see the concept before opting
into the script. `pymdownx.details` is already enabled.

### 5.6 Shared browser component

Replace the inline `download.md` script with one shared `docs/assets/js/r2-browser.js`, loaded via
`extra_javascript` and **guarded to no-op when no mount is present** (so it is harmless on non-Downloads
pages). Each page places a mount element with a type attribute, e.g.
`<div class="r2-browser" data-r2-type="monthly"></div>`; supported types: `latest`, `monthly`,
`deltas`, `parquet-monthly`, `parquet-weekly`. The script fetches `index.json` once per page and
renders the requested view. It preserves the current CORS/network/HTTP error handling and the
`<noscript>` fallback.

### 5.7 Link migration

Two classes of inbound reference must be updated. `--strict` catches class (a) (broken page paths)
but NOT class (b): because `download.md` still exists, bare links to it stay "valid" while pointing
at content that has moved off the short hub.

**(a) Anchored links** — re-home to the child page that now owns the anchor:

| File:line | From | To |
|-----------|------|----|
| `getting-started.md:8` | `data-access/download.md#consumer-replay-model` | `data-access/weekly-deltas.md#consumer-replay-model` |
| `data-access/index.md:10` | `download.md#consumer-replay-model` | `weekly-deltas.md#consumer-replay-model` |
| `data-access/output-files.md:30` | `download.md#consumer-replay-model` | `weekly-deltas.md#consumer-replay-model` |
| `data-access/output-files.md:60` | `download.md#weekly-deltas` | `weekly-deltas.md` |
| `pipeline/export.md:119` | `../data-access/download.md#parquet-files` | `../data-access/parquet.md` |
| `pipeline/export.md:164` | `../data-access/download.md#weekly-deltas` | `../data-access/weekly-deltas.md` |
| `user-story-audit.md:19,121` | `data-access/download.md#parquet-files` | `data-access/parquet.md` |

(`export.md` is under `pipeline/`, so its on-disk links carry a leading `../` — reflected above.)

**(b) Bare / prose references** — re-home or reword each (not caught by `--strict`):

| File:line | Issue | Action |
|-----------|-------|--------|
| `docs/index.md:159` | "[Downloads] for the directory layout, the manifest shape, and the consumer replay model" | point manifest → `release-model.md`, replay → `weekly-deltas.md` |
| `data-access/index.md:25` | "[Downloads] for the consumer replay model and the full Parquet list" | → `weekly-deltas.md` and `parquet.md` (so `index.md` migrates two refs, not one) |
| `user-story-audit.md:130` | bare "[Downloads] (the Parquet section …" | → `parquet.md` |
| `pipeline/export.md:170` | prose describes one "Browse All Releases" browser on the Downloads page | reword: browsers are now per-type on the child pages |

The month-start-baseline admonitions keep pointing at the Consumer Replay Model (now `weekly-deltas.md`).

## 6. `index.json` schema changes

Additive, backward-compatible (browser tolerates absence):

- Every **file** entry (monthly, archived monthly): add `"modified":"YYYY-MM-DD"` (UTC).
- Every **Parquet set** entry (monthly, archived): add `"modified":"YYYY-MM-DD"`.
- Every **delta** entry: add `"modified":"YYYY-MM-DD"` and `"parquet":["scv","allele",…]` — the
  section names present under `deltas/<dir>/parquet/` that week (empty array if none).

`modified` = the `aws s3 ls` date column (UTC); for directory entries, the newest date among the
directory's immediate files.

## 7. `generate-r2-index.sh` changes

Bash 3.2 only (no `mapfile`/associative arrays — per `.claude/rules/scripts.md`); build JSON by hand.

- `r2_ls_with_size`: `awk '/\.json\.gz$/ {print $1, $3, $4}'` (DATE SIZE NAME); `build_file_array`
  parses the date and writes `modified`.
- New `r2_newest_date_under(prefix)`: `aws s3 ls <prefix>` → keep lines whose `$1` matches
  `YYYY-MM-DD` (skips `PRE` dir lines) → `sort | tail -1 | awk '{print $1}'` (return just the date).
- New `r2_parquet_sections_under(prefix)`: `aws s3 ls <prefix>` → `*.parquet` basenames minus suffix.
- `build_parquet_array`: set `modified` per set via `r2_newest_date_under`.
- `build_deltas_array`: per delta dir, `modified` via `r2_newest_date_under "deltas/<dir>/"` and
  `parquet` via `r2_parquet_sections_under "deltas/<dir>/parquet/"`.

Cost: one extra `ls` per Parquet set, two per delta dir — read-only, at index-generation time.

## 8. Browser JS behavior (`r2-browser.js`)

- Read `data-r2-type` from each `.r2-browser` mount; fetch `index.json` once; render that view.
- `latest`: the §5.2 hub table — per type, the newest **dated** entry (`release != "latest"`, max
  `release`) supplies the Release label + `modified`; the `latest:true` `00-latest` alias supplies the
  Download URL.
- `monthly`: monthly fulls + archived monthly, with `modified`.
- `deltas`: delta releases with `modified`.
- `parquet-monthly`: monthly Parquet sets + archived, with `modified`.
- `parquet-weekly`: per-delta Parquet groups from `deltas[].parquet`, with `modified`.
- Append `modified` only when present; render nothing when absent. Preserve CORS/network/HTTP error
  handling and `<noscript>`.

## 9. Verification

- **Generator:** `generate-r2-index.sh --dry-run` (reads live R2 read-only; writes candidate to
  `/tmp`, upload gated). Confirm `modified` on monthly/delta/parquet/archive entries and per-delta
  `parquet` lists — validates the awk/`ls` parsing against real bucket output with no R2 write.
- **Browser + nav:** `zensical serve` with a local `index.json` carrying `modified`/`parquet`;
  confirm the group appears in the left nav, each page's browser renders (incl. weekly Parquet), the
  hub table + dates + cross-links work, and a date-less `index.json` degrades gracefully.
- **Links:** `zensical build --strict` → "No issues found". `--strict` validates page existence but
  NOT `#fragment` targets (per `reference_zensical_rawhtml_link_rewriting`), and stale **bare** links
  to the still-present `download.md` pass silently. So ALSO: (a) `grep -rnoE "download\.md" docs/` and
  re-home/reword every §5.7(b) reference; (b) manually open each migrated `#consumer-replay-model` /
  `#weekly-deltas` anchor to confirm it resolves on its new page.

## 10. Rollout

- Branch `docs/downloads-approachable-redesign` off `1.0`; PR into `1.0` as part of the 1.0.1 RC.
  Independent of the held search-fix PR #120, **except** both edit `zensical.toml` `extra_javascript`
  (search PR removes `keyboard-shortcuts.js`; this PR adds `r2-browser.js`) — a trivial line-level
  merge to reconcile on `1.0`.
- **Live-R2 caveat:** new dates and the weekly-Parquet browser only populate once `index.json` is
  **regenerated and re-uploaded** to R2 — a live-R2 write that per `.claude/rules/scripts.md` needs
  explicit user confirmation. Docs/JS/generator ship first; the browser degrades gracefully against
  today's date-less `index.json` until a confirmed regeneration (next release, or a one-off).

## 11. Open questions

- Page split granularity: four child pages + hub as above — or fold "How Releases Work" into the hub?
  (Assumed separate page, per "too lengthy for one TOC".)
- `???` collapsed-by-default vs `???+` expanded-by-default for recipes. (Assumed collapsed.)
- Hub dates blank until the first `index.json` regeneration — acceptable? (Assumed yes.)
