# 0002 — Monthly full bundle anchored to ClinVar's monthly index

- **Status:** Accepted
- **Date:** 2026-08-24
- **Spec:** `docs/superpowers/specs/2026-08-24-clinvar-index-monthly-trigger-design.md`

## Context

The monthly full bundle was triggered by our own weekly cadence (a `schema_on` calendar-month boundary),
publishing the prior release as "the month's full." That drifted from ClinVar's authoritative monthly cadence
and mislabeled months, because ClinVar names a monthly `_YYYY-MM` for the month it is *released in* (early that
month, reflecting ~prior-month data).

## Decision

Anchor the monthly full to **ClinVar's monthly VCV index**
(`https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/`). Our `clinvar-gkm_YYYY-MM` full = the most recent
**GKM-capable** build with release date strictly **before** ClinVar's `_YYYY-MM` Released datetime, re-exported
into the `YYYY-MM` slot. ClinVar's monthly XML is only a trigger signal — we never ingest it. A
`--month-label` flag decouples the published slot from the source release date.

## Consequences

- Our monthly labels line up 1:1 with ClinVar's; e.g. the `2026-07` full is built from our `2026-06-27` release.
- `run-release.sh` Stage 5 scrapes the index (bounded to months newer than the latest published full) instead
  of using `schema_on`; the full is a re-export of existing `gkm_dict_*` tables, not a rebuild.
- A one-time re-align moved existing fulls to the new scheme. Prior-month/prior-year retention is still an open
  design ([release browser + archiving spec](../superpowers/specs/2026-08-26-release-browser-reorg-and-archiving-design.md)).
