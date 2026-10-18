# How Releases Work

Links: [Monthly Full Bundles](monthly-full.md) · [Weekly Deltas](weekly-deltas.md) · [Parquet Files](parquet.md)

ClinVar-GKM releases are hosted on Cloudflare R2 object storage. All downloads are free with no authentication required and no egress fees.

Distribution follows a **full + delta** model:

- The complete **monthly full bundle** — a gzip-compressed JSON file — is published once a month. It contains every variation, statement, proposition, condition, and supporting reference record for that release.
- A **weekly delta** is published for every ClinVar release. Each delta carries only the records that were added or updated since the prior release, in the same section structure as the full bundle, alongside a `manifest.json` that lists per-section adds, updates, and deletes.

A consumer that wants the current state takes the latest monthly full and replays the weekly deltas published since it. See the [Consumer Replay Model](weekly-deltas.md#consumer-replay-model) for the replay model, and the [`manifest.json` field reference](weekly-deltas.md#manifestjson) on the Weekly Deltas page.

!!! warning "The monthly full is a month-start baseline, not the current week"
    `clinvar-gkm_00-latest.json.gz` reflects the **last release of the _previous_ month** — e.g. the `2026-10` full is built from the `2026-09-28` release, the last one before ClinVar's October monthly cut. It does **not** include the current month's weekly changes. To get the current weekly state, apply the latest delta on top of it — see the [Consumer Replay Model](weekly-deltas.md#consumer-replay-model).

---

## Release Cadence

A **weekly delta** is published for every ClinVar release, typically within 1-2 days of each ClinVar XML release. Each delta lands under `deltas/<YYYY-MMDD>/` and is mirrored at `deltas/00-latest/`.

A **monthly full bundle** is published once a month, aligned to ClinVar's own monthly VCV releases. When ClinVar posts `ClinVarVCVRelease_YYYY-MM.xml.gz` at its [XML index](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/) (early in month `YYYY-MM`), our `clinvar-gkm_YYYY-MM` full is built from the most recent weekly release **before** ClinVar's monthly cut datetime — so e.g. the `2026-07` full comes from the `2026-06-27` release, the last one before ClinVar's `_2026-07` cut. That upload writes `datasets/clinvar-gkm_YYYY-MM.json.gz` and refreshes the `datasets/clinvar-gkm_00-latest.json.gz` pointer. Each delta manifest's `checkpoint_full` records which monthly full its chain replays onto.

**Parquet is derived from the bundle and regenerated each release.** Only the latest state is published, at `datasets/parquet/00-latest/`, rebuilt from every weekly release; there are no per-month or per-delta Parquet sets. When a release rewrites the published files in place, the previous generation, including the one Parquet set built from its latest bundle, is kept under `archive/<version>/`.

At year boundaries, the prior year's monthly full bundles are moved to `archives/{YYYY}/`. All monthly archives are retained indefinitely.

There is no weekly full bundle — weekly changes are distributed as deltas only. Consumers that need the full weekly state reconstruct it by replaying deltas onto the latest monthly full, as shown in the [Consumer Replay Model](weekly-deltas.md#consumer-replay-model).
