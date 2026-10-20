ClinVar-GKM Data Distribution
==============================

This bucket contains ClinVar data transformed into GA4GH GKS format
(VRS, Cat-VRS, VA-Spec). The full dataset is a gzip-compressed keyed JSON
bundle. Per-release weekly
deltas ship the records that changed since the prior release so consumers
can stay current without re-downloading the full set every week.

Distribution model
------------------

  * Full bundle: published MONTHLY (the last release of each month).
  * Weekly deltas: published EVERY release (added/updated records + a manifest
    of deletes), in the same section structure as the full bundle.
  * Parquet: a derived convenience, not a release record. Only the LATEST state
    is published (one typed file per section), rebuilt from the newest release
    every release. It is recomputable from the bundle.
  * Every bundle has a <file>.sha256 sidecar (sha256sum -c format).

To reconstruct the latest state: download the most recent monthly full, then
replay the contiguous weekly deltas published after it (apply each delta's
manifest deletes, then upsert its records — section by section).

Directory Structure
-------------------

datasets/
  Monthly full bundles for the current year.
  clinvar-gkm_00-latest.json.gz  — always the most recent monthly full.
  clinvar-gkm_yyyy-mm.json.gz    — monthly full for a specific month.

datasets/parquet/00-latest/
  The latest derived Parquet, one file per section (<section>.parquet), rebuilt
  every release from the newest release's data. source.json names the release it
  was built from. There are no dated Parquet sets.

deltas/
  Per-release weekly deltas.
  deltas/yyyy-mmdd/
    clinvar-gkm-delta_yyyy-mmdd.json.gz — added + updated records (same
                                          section structure as the full bundle).
    manifest.json                       — release/baseline/compare stamps,
                                          checkpoint_full pointer, and per-section
                                          added/updated counts + deleted keys.
  deltas/00-latest/                     — mirror of the most recent delta.

archives/
  Prior years' monthly full bundles, organized by year (archives/yyyy/).

index.json
  Machine-readable listing of the monthly fulls (with sha256), the latest
  Parquet set, archives, and delta releases.

../archive/<version>/ (bucket root)
  Superseded generations of the whole line, e.g. archive/1.0.1/: every bundle,
  delta manifest and index of that generation, plus the one Parquet set built
  from its latest bundle, with a MANIFEST.json (sha256 per file) and README.txt.

Quick Start
-----------

Download the latest monthly full:
  curl -O https://data.clinvar-gkm.org/datasets/clinvar-gkm_00-latest.json.gz

Fetch the latest weekly delta + its manifest:
  curl -O https://data.clinvar-gkm.org/deltas/00-latest/manifest.json

Documentation: https://clingen-data-model.github.io/clinvar-gkm/
Source: https://github.com/clingen-data-model/clinvar-gkm
