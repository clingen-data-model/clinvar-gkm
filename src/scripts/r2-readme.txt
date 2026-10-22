ClinVar-GKM Data Distribution -- line v1/1.1 (schema 1.1.x)
==========================================================

ClinVar data transformed into the GA4GH GKM schema set (VRS, Cat-VRS, VA-Spec), as gzip-compressed keyed JSON
bundles. The layout follows NCBI's pub/clinvar/xml/ (monthly), xml/weekly_release/ and xml/archive/YYYY/, the
source of these bundles, plus a deltas/ folder. Every bundle has a <file>.sha256 sidecar (sha256sum -c format).

Version lines: v{major}/{major}.{minor}/. PATCH releases (1.1.x) extend this folder; a new MINOR starts v1/1.2/.
The bucket-root index.json lists every line, its status (current / frozen) and schema version. v1/1.0/ is the
frozen 1.0.1 generation.

Layout of this line (v1/1.1/)
-----------------------------

clinvar-gkm_YYYY-MM.json.gz
  The official monthly full bundle for ClinVar's monthly release YYYY-MM. It is built from the newest weekly
  release before ClinVar posted its monthly (ADR 0002), so 2026-10 holds the 2026-09-28 release. index.json gives
  each monthly's source_release.
clinvar-gkm_00-latest.json.gz
  The same bytes as the newest monthly.

weekly/clinvar-gkm_YYYY-MMDD.json.gz
  A full bundle for every weekly release of the CURRENT month. When the first release of a new month is posted,
  the finished month's weekly fulls are deleted (rebuild a past week from a monthly plus the deltas).
weekly/clinvar-gkm_00-latest_weekly.json.gz
  The same bytes as the newest weekly full: the most current full state.

deltas/clinvar-gkm-delta_YYYY-MMDD.json.gz            the current month's weekly deltas
deltas/clinvar-gkm-delta_YYYY-MMDD.manifest.json      each delta's manifest
deltas/YYYY-MM/...                                    earlier months of the current year
  A delta holds the records added or updated since the previous release, in the same section structure as the
  full bundle; its manifest lists the deleted keys and carries release, baseline_release (the previous
  release), compare_release, schema_version, sha256 and checkpoint_full {path, release}: the official monthly to
  replay it onto (release = that monthly's source release).

archive/YYYY/clinvar-gkm_YYYY-MM.json.gz              prior years' monthlies (moved at the first release of a
archive/YYYY/deltas/YYYY-MM/...                       new year), and their deltas

parquet/<section>.parquet, parquet/manifest.json
  ONE Parquet set (one typed file per section), rebuilt from the newest release and overwritten every release.
  manifest.json gives the build date, source release, builder and every file's size and sha256. Parquet is
  derived from the bundles; there is no Parquet in archives.

index.json   machine-readable listing of everything above (with sha256 and source releases)
feed.xml     Atom feed of the monthlies and deltas

Reconstructing a state
----------------------

Take the official monthly named by the first delta's checkpoint_full (or any monthly whose source_release is on
or before a delta's baseline_release), then replay the contiguous deltas after it in release order: for each,
check baseline_release equals the release you hold, delete the manifest's deleted keys, then upsert its records
section by section.

Quick start
-----------

  curl -O https://data.clinvar-gkm.org/v1/1.1/clinvar-gkm_00-latest.json.gz
  curl -O https://data.clinvar-gkm.org/v1/1.1/weekly/clinvar-gkm_00-latest_weekly.json.gz
  curl -s https://data.clinvar-gkm.org/v1/1.1/index.json

Documentation: https://dataexchange.clinicalgenome.org/clinvar-gkm/
Source: https://github.com/clingen-data-model/clinvar-gkm
