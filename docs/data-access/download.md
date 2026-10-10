# Downloads

ClinVar-GKM is distributed as a monthly full bundle plus weekly deltas (JSON + typed Parquet), free from Cloudflare R2 — no authentication, no egress fees. New here? See [How Releases Work](release-model.md).

---

## Latest Release

!!! warning "The monthly full is a month-start baseline, not the current week"
    `clinvar-gkm_00-latest.json.gz` reflects the **last release of the _previous_ month** — e.g. the `2026-10` full is built from the `2026-09-28` release, the last one before ClinVar's October monthly cut. It does **not** include the current month's weekly changes. To get the current weekly state, apply the latest delta on top of it — see the [Consumer Replay Model](weekly-deltas.md#consumer-replay-model).

<div class="r2-browser" data-r2-type="latest"></div>

<noscript>
The interactive release table needs JavaScript. Without it, fetch the release index directly:
<code>curl -s https://pub-f0ad0e0dac0345408dcc95bda20beb42.r2.dev/index.json | python3 -m json.tool</code>
— or grab the latest full and delta:
<code>curl -O https://pub-f0ad0e0dac0345408dcc95bda20beb42.r2.dev/datasets/clinvar-gkm_00-latest.json.gz</code>
</noscript>

Browse history and archives: [Monthly Full Bundles](monthly-full.md) · [Weekly Deltas](weekly-deltas.md) · [Parquet Files](parquet.md).

---

## Directory Structure

```text
datasets/
  clinvar-gkm_00-latest.json.gz              latest monthly full bundle (stable URL)
  clinvar-gkm_YYYY-MM.json.gz                monthly full bundles (current year)

datasets/parquet/00-latest/
  {section}.parquet                          typed Parquet for the latest monthly full (stable URL)

datasets/parquet/YYYY-MM/
  {section}.parquet                          typed Parquet for a specific monthly full (current year)

deltas/00-latest/
  clinvar-gkm-delta_00-latest.json.gz        latest weekly delta bundle (stable URL)
  manifest.json                              latest delta manifest
  parquet/{section}.parquet                  typed Parquet for the latest delta

deltas/YYYY-MMDD/
  clinvar-gkm-delta_YYYY-MMDD.json.gz        weekly delta bundle (added + updated records)
  manifest.json                              per-release change manifest
  parquet/{section}.parquet                  typed Parquet for the changed records

archives/{YYYY}/
  clinvar-gkm_YYYY-MM.json.gz                monthly full bundles from prior years
  parquet/YYYY-MM/{section}.parquet          typed Parquet month sets from prior years

index.json                                   release index (datasets, archives, deltas)
```

---

## Feedback

This project is in active development and we welcome community feedback. If you encounter data quality issues, have questions about the output format, or want to suggest improvements:

- Open an issue on [GitHub](https://github.com/clingen-data-model/clinvar-gkm/issues)
- Include the release date and specific records involved
