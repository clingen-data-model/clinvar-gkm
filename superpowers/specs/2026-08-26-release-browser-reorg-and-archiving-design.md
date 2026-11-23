# Release Browser Reorganization + Weekly Parquet + Archiving — Design

**Status:** design draft 2026-08-26 (roadmap item). Implementation is a future, separately-planned effort.

## Goal

Make the **"Browse All Releases"** widget on the Downloads page present every distributed artifact in a clear
2×2 structure, add the **weekly (delta) Parquet** sets that are published but not yet browsable, and define an
**archiving** scheme for weekly deltas (prior months) and monthly fulls (prior years) so the live listing stays
manageable as history accumulates.

## Current state

- **Widget** (`docs/data-access/download.md`, `#r2-browser` script) renders four flat sections from
  `index.json`: *Monthly Full Bundles*, *Weekly Deltas*, *Parquet Month Sets*, *Archived Releases*. It fetches
  `index.json` and composes known section files under each Parquet month path.
- **`index.json`** (built by `generate-r2-index.sh`) carries `datasets.monthly`, `datasets.parquet` (dated
  month sets + `00-latest`), `deltas` (per-release dirs with `{release, path, manifest}`), and `archives`
  (prior-year monthly + parquet).
- **Delta Parquet already exists** on R2 at `deltas/<yyyy-mmdd>/parquet/<section>.parquet` (and
  `deltas/00-latest/parquet/`), but `index.json`'s `deltas` entries do **not** expose it, so the widget can't
  show it.
- **Archiving today:** `upload-gkm-to-r2.sh` moves *prior-year* monthly bundles + dated Parquet month sets to
  `archives/{yyyy}/…` at year rollover. There is **no** archiving of weekly deltas by month.

## Part A — Reorganize the browser into a 2×2

Target top-level grouping (each collapsible):

```
Bundles/
  Monthly (Full)     → datasets/clinvar-gkm_YYYY-MM.json.gz  (+ 00-latest)
  Weekly (Deltas)    → deltas/YYYY-MMDD/clinvar-gkm-delta_*.json.gz + manifest.json  (+ 00-latest)
Parquet/
  Monthly (Full)     → datasets/parquet/YYYY-MM/<section>.parquet  (+ 00-latest)
  Weekly (Deltas)    → deltas/YYYY-MMDD/parquet/<section>.parquet   (+ 00-latest)
Archived/            → prior-year Bundles/Parquet + prior-month Weekly (see Part C)
```

This is a pure widget-rendering change (regroup the same data) plus the index additions in Part B.

## Part B — Weekly Parquet (the dynamic/hierarchical challenge)

Weekly Parquet is inherently larger and more nested than the monthly sets: **20 sections × every weekly
release**. A flat render would be unwieldy, so:

1. **Index:** extend each `deltas[]` entry in `index.json` with a `parquet` marker — either a boolean
   `hasParquet` plus the section list is composed client-side (sections are a stable, known set, as already
   done for monthly Parquet), or an explicit `parquetPath`. Minimal change: add `parquetPath:
   "deltas/YYYY-MMDD/parquet/"` and reuse the known-section composition the widget already does for monthly.
2. **Render lazily / collapsed:** under *Parquet → Weekly (Deltas)*, show one collapsed node per release
   (`YYYY-MMDD`); expanding a release lists its 20 section files (composed from the known section list + the
   entry's `parquetPath`). Only the expanded release's file list is built, keeping the DOM small.
3. **Group by month:** nest weekly entries under a `YYYY-MM` node so a year of weeklies stays navigable
   (Weekly → 2026-08 → 2026-0822 → sections). This same month grouping is what Part C archives against.

**Open question for the plan:** whether to verify each delta actually has Parquet (some early deltas may
predate delta-Parquet) — either trust the `parquetPath` marker written at publish time, or have
`generate-r2-index.sh` probe. Prefer the publish-time marker (no probing cost).

## Part C — Archiving

Two retention moves, mirroring the existing year-rollover pattern:

- **Weekly deltas from prior months → archive.** When a delta from a new month is published, move the
  previous months' `deltas/YYYY-MMDD/` trees under `archives/{yyyy}/deltas/YYYY-MMDD/` (or keep them in place
  but mark them archived in the index and collapse them in the widget). Keep the current month + `00-latest`
  live. The delta **chain must stay reconstructable**, so archiving only relocates/relabels — it never
  deletes — and the manifest `checkpoint_full` pointers remain valid (they reference `datasets/…`, unaffected).
- **Monthly sets & bundles from prior years → archive.** Already implemented for monthly bundles + dated
  Parquet at year rollover; extend the same move to any newly-archived weekly-delta trees, and ensure
  `index.json`'s `archives` block represents all four artifact kinds (monthly bundle, monthly parquet, weekly
  bundle, weekly parquet) per archived period.

**Decision needed in the plan:** archive *layout* — relocate objects to `archives/…` (clean live tree, but a
server-side copy per rollover) vs. leave objects in place and drive archived/live purely from `index.json`
grouping (no copies, but the live prefixes keep growing). Recommendation: **index-driven grouping** for weekly
deltas (cheap, non-destructive, keeps the chain trivially intact) and keep **physical relocation** for
prior-year monthly (matches today's behavior), revisiting if the delta count per year becomes large.

## Implementation touchpoints (for the future plan)

- `generate-r2-index.sh` — add `parquetPath` to `deltas[]`; add month grouping + archived/live partition;
  represent all four artifact kinds under `archives`.
- `upload-gkm-delta-to-r2.sh` / `upload-gkm-to-r2.sh` — write the delta `parquetPath` marker; apply the
  month-boundary delta archiving decision; extend year-rollover archiving to weekly trees.
- `download.md` `#r2-browser` script — the 2×2 grouping, lazy per-release Parquet expansion, month nesting.
- `download.md` prose + directory-structure section — document the new browser layout and archive scheme.

## Phasing

1. **A + index marker** (regroup browser into 2×2, expose weekly Parquet via `parquetPath`) — mostly a widget
   + `generate-r2-index.sh` change; low risk.
2. **B lazy/month-nested weekly Parquet** — widget hierarchy refinement.
3. **C archiving** — index-driven weekly-delta archiving + extend year-rollover; retention decisions above.

## Non-goals

- No change to what is published or to the delta/monthly cadence — this is browsing/organization + retention.
- No deletion of any artifact; archiving relocates or relabels only.
