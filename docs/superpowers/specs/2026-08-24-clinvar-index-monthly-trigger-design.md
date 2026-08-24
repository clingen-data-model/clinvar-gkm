# ClinVar-Index-Driven Monthly Full Trigger — Design

**Status:** approved 2026-08-24. Supersedes the `schema_on` calendar-month-boundary trigger for monthly full bundles.

## Problem

The monthly full bundle was triggered by our own release cadence: run-release Stage 5 detected a
calendar-month boundary (`schema_on(DATE).prev_release_date` in a different month) and published the
*prior* release as that month's full. This drifts from ClinVar's authoritative monthly cadence and
mislabels months. ClinVar names a monthly `ClinVarVCVRelease_YYYY-MM.xml.gz` for the calendar month it
is **released in** (early that month, reflecting ~prior-month data), so a monthly should map to the last
of *our* builds **before** ClinVar's monthly cut — not to the last calendar-month release.

## Rule

For ClinVar monthly `_YYYY-MM` with Released datetime `T` (column 3 of the FTP index at
`https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/`):

> our monthly full `clinvar-gkm_YYYY-MM` = the most recent of **our** builds with release date strictly
> before `T`, re-exported (not rebuilt) into the `YYYY-MM` monthly slot.

The `YYYY-MM` **label comes from ClinVar's filename**, decoupled from the source build's own month.
ClinVar's monthly XML is only a **trigger signal** — we never ingest it.

### Grounded example (real index datetimes)

| ClinVar monthly | Released `T` | Source build (max ours `< T`) | Our full |
| --- | --- | --- | --- |
| `_2026-06` | 2026-06-04 00:07:42 | none (our data starts 06-27) | — (no June full) |
| `_2026-07` | 2026-07-02 00:07:31 | **06-27** | `clinvar-gkm_2026-07` |
| `_2026-08` | 2026-08-06 00:07:26 | **08-04** | `clinvar-gkm_2026-08` |

## Mechanism (ongoing) — run-release Stage 5

Replace the `schema_on` month-boundary block with:

1. Scrape the ClinVar index; parse `ClinVarVCVRelease_YYYY-MM.xml.gz` rows (ignore the sibling
   `.xml.gz.md5` rows); take the newest month `CV_MONTH` and its Released datetime `CV_DT` (col 3).
2. **Stateless check:** if `datasets/clinvar-gkm_${CV_MONTH}.json.gz` already exists in R2 → nothing to
   do. Otherwise `CV_MONTH` is unprocessed. (Loop over any missing month for catch-up; normally 0 or 1.)
3. Resolve `SOURCE_DATE` = newest of our `clinvar_YYYY_MM_DD_${VER}` datasets with date `< CV_DT`
   (strict earlier date; ClinVar monthlies land ~00:07 early-month so a same-date weekly collision is
   unlikely — refine to datetime only if it ever occurs).
4. Publish the full: `release-gkm.sh ${SOURCE_DATE} ${VER} --month-label=${CV_MONTH}`.
5. Keep existing guards: pruned source dataset → warn+skip; a retroactive-full failure is non-fatal to
   the weekly delta.

So ClinVar `_2026-08` (Aug 6) is picked up by the first weekly run after Aug 6 (08-08), which builds the
`2026-08` full from 08-04 **before** publishing 08-08's own delta (so the delta's `checkpoint_full`
auto-resolves to the new `2026-08`).

## Label decoupling

`upload-gkm-to-r2.sh` and `release-gkm.sh` gain `--month-label=YYYY-MM`. When set, the monthly slot
filename + dated Parquet dir use the label's `YEAR-MM`; bundle content still comes from the source
`export_date` dataset. Absent, behavior is unchanged (label = source date's month).

## One-time re-align (gated R2 mutation)

Existing live fulls were published under the old rule (`2026-06`=06-27, `2026-07`=07-27). Re-align to:

1. Publish `2026-07` from **06-27** (`--month-label=2026-07`) — overwrites the old `2026-07`(07-27) slot.
2. Publish `2026-08` from **08-04** (`--month-label=2026-08`) last, so `00-latest` → 2026-08.
3. Delete the `2026-06` slot (`datasets/clinvar-gkm_2026-06.json.gz` + `datasets/parquet/2026-06/`).
4. Patch `checkpoint_full` → `2026-08` in the `08-08` & `08-16` delta manifests (`deltas/2026-0808/`,
   `deltas/2026-0816/`, and `deltas/00-latest/` mirror). Deltas 07-06…08-04 keep label `2026-07`, now
   correctly resolving to 06-27 content (this also fixes a latent bug: the old `2026-07`=07-27 full sat
   *after* the 07-06…07-20 deltas, so they were not replayable onto it).
5. Regenerate `index.json`.

## Correctness notes

- No June full is expected/correct — our earliest build (06-27) postdates ClinVar's June cut.
- The full is a re-export of already-built `gkm_dict_*` tables, not a pipeline rebuild.
- `index.json` does not carry `checkpoint_full`; it lives only in per-delta `manifest.json`.
