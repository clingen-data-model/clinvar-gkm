# 0008 — Bundles are the public record: immutability, archives, version lines and download metrics

- **Status:** Proposed
- **Date:** 2026-10-18
- **Plan:** [`docs/superpowers/plans/2026-10-18-bundle-record-and-metrics.md`](../superpowers/plans/2026-10-18-bundle-record-and-metrics.md)
- **Amended:** 2026-10-20 by [ADR 0009](0009-r2-layout-mirrors-ncbi-clinvar.md) (R2 layout mirrors NCBI ClinVar):
  (a) weekly fulls are an exception to immutability; (c) archives are `archive/YYYY/` inside a line, and the
  1.0.1 generation becomes the frozen line `v1/1.0/`; (e) one overwritten Parquet dataset, none in archives.

## Context

Every corrective release so far has rewritten the published files under `/v1/` in place: the 1.0.0
re-release, 1.0.1, and next the 1.1.0 republish (ADR 0006, on #146). Each rewrite replaced the bytes behind
the same URLs. Anyone who downloaded an earlier generation now holds files that no longer exist anywhere, and
nothing tells them which generation they have.

Before deciding how much machinery that problem deserves, we need to know whether anyone is downloading the
data. What we know today:

- **Analytics exist only from 2026-10-14.** Cloudflare GraphQL Analytics (`httpRequestsAdaptiveGroups`, per
  path, Free plan) covers `data.clinvar-gkm.org` from the day it started serving
  ([ADR 0005](0005-r2-custom-domain-and-cdn.md)). The zone rejects queries older than "4w3d", so it keeps about
  31 days. Earlier traffic went to the `r2.dev` URL, which has no per-path analytics and is now disabled.
- **No complete full-bundle download so far.** From 2026-10-14 to 2026-10-18, excluding our own IP:

    | Path | Requests | Clients | Served | Reading |
    | --- | --- | --- | --- | --- |
    | `v1/datasets/clinvar-gkm_00-latest.json.gz` | 18 | 8 IP/UA pairs | 1.09 GB | about 0.2 of one 4.8 GB full: at most a partial download |
    | dated monthly fulls (each) | 2–4 | — | 0 bytes | HEAD requests or link checks |
    | `v1/deltas/00-latest/…` delta | 12 | — | 0.03 GB | about 1–2 delta downloads |
    | old flat-root `/datasets/…` | 7 | — | 0 bytes | stale links |

- **Parquet is not yet stable.** The Parquet tables are re-derived from the BigQuery dict tables by separate
  SQL ([ADR 0007](0007-pipeline-principles-and-simplification.md), Workstream 1), and their layout changed in
  1.0.1 and changes again in 1.1.0. The JSON bundles are the canonical output (ADR 0007, principle 2).
- **The 1.0.1 bundles are being archived** to `archive/1.0.1/` (the `v1/` paths mirrored below it), with a
  `MANIFEST.json` (sha256 per file) and a `README.txt`, before the 1.1.0 republish rewrites `/v1/`. Under
  ADR 0009 this generation moves to the frozen line folder `v1/1.0/`.
- **No subscribers yet.** The email list `clinvar-gkm@broadinstitute.org` has no members, and the schema has
  not been declared GA.

## Decision

### (a) The JSON bundles are the public record

The monthly full and delta JSON bundles are the published record of ClinVar-GKM. **From the 1.1.0 republish
on, a published bundle file is immutable:** the bytes behind a dated bundle path are never replaced without
the previous bytes being kept, as described in (c). The mutable pointers are not records: `index.json`, the
root manifest, `feed.xml` and every `00-latest` path keep moving to the newest release.

Two amendments from [ADR 0009](0009-r2-layout-mirrors-ncbi-clinvar.md):

- **Weekly full bundles are not records.** The current month's weekly fulls under `weekly/` are a convenience
  copy and are **deleted at month rollover**, as NCBI deletes its weekly releases. This is a deliberate
  exception to immutability. The records are the official monthlies and the deltas, from which any past week
  can be rebuilt exactly.
- **Moves change the path, not the bytes.** At month and year rollover, deltas and monthlies move into
  `deltas/YYYY-MM/` and `archive/YYYY/`. Their bytes, names and sha256 stay the same.

This **closes the ADR 0004 §5 in-place exception after 1.1.0**, which ADR 0006 extended to cover the 1.1.0
reorganization. Closing it is, in effect, **declaring GA**: from then on every breaking change follows the
ADR 0004 MAJOR-line and RFC process. **This is the maintainer's decision to confirm** when this ADR is
accepted. Until it is confirmed, the 1.x line is still pre-GA.

### (b) A breaking change opens a new line

A breaking schema change after 1.1.0 opens a new line, `v2/2.0/` (ADR 0009 §1), built in full (every monthly full and every
delta in the window being republished) alongside `/v1/`. The old line is then **frozen**: no new releases, and
its files stay downloadable and unchanged. It carries a switch-over notice:

- in its `index.json` and in the root manifest: `"status": "superseded"`, `"superseded_by": "2"` and an end
  date (`eol`, the date the line stopped receiving releases);
- on the email list and in GitHub Discussions *Announcements*.

**Open point:** ADR 0004 §3 keeps the prior line fully live (new monthlies and deltas) for 6 months before
it freezes. The maintainer's stated aim here is to *stop* the previous line at the switch-over. The
maintainer chooses one when accepting this ADR: freeze at the switch-over (this ADR then amends ADR 0004 §3)
or keep the 6-month live window and freeze at its end.

### (c) A replaced generation is kept as a frozen line folder

*Amended by [ADR 0009](0009-r2-layout-mirrors-ncbi-clinvar.md).* Each version line has its own folder,
`v{major}/{major}.{minor}/`. A republish that replaces a line's bundles (a new MINOR) publishes into a new
folder, and the folder it replaces is **frozen** in place: nothing is added, moved or deleted, and it is listed
from the root manifest with its status. A frozen folder carries:

- a `MANIFEST.json` listing every file with its size and sha256;
- a `README.txt` saying what the generation is, which release replaced it and why.

The 1.0.1 generation, first copied to `archive/1.0.1/` on 2026-10-18, moves to **`v1/1.0/`**. There is no root
`archive/<version>/` folder any more: `archive/YYYY/` now means the prior-year archive **inside** a line
(`v1/1.1/archive/YYYY/`, monthlies plus `deltas/YYYY-MM/`). How a content-only correction that must rewrite
bundles is published is an open point in ADR 0009 §5.

### (d) Every manifest carries sha256 per file

Every manifest that lists a bundle (the per-line `index.json`, each delta manifest and each frozen line's
`MANIFEST.json`) gives its size and sha256, and every bundle has a `<file>.sha256` sidecar. A user can then tell which generation a local copy belongs to by
hashing it, without relying on dates or file names.

### (e) Parquet is derived, not a record

Parquet is a convenience view of a bundle, not a record:

- The docs and the manifests label it **"derived from the bundle; may be regenerated"**.
- *Amended by [ADR 0009](0009-r2-layout-mirrors-ncbi-clinvar.md).* **One Parquet dataset** is published per
  line, at `v1/1.1/parquet/`, rebuilt from the newest release and **overwritten every release**. A manifest
  file beside it states the build date, the source release and the tool version. There is no Parquet in
  `archive/YYYY/`, in frozen line folders (`v1/1.0/` has none) or per delta. This reverses the 2026-10-18 decision
  to keep one Parquet set per archived generation.
- A **versioned Parquet rebuild tool**, [`clinvar-gkm-parquet`](https://github.com/clingen-data-model/clinvar-gkm-parquet)
  (planned), builds the Parquet tables from a published bundle. It is versioned on its own cadence, declares
  which bundle `schema_version`s it accepts, and the pipeline pins a version of it (ADR 0007, Workstream 1), so
  a user can rebuild the Parquet of any monthly with the tool version that matches.
- **Caveat:** the 1.0.x Parquet was produced by BigQuery SQL from the dict tables, not from the bundle, so it
  cannot be reproduced bit-for-bit. So is the 1.1.0 Parquet, since Workstream 1 starts after 1.1.0 ships. The
  tool can rebuild the content of those sets from their bundles, not their bytes.

### (f) Download metrics decide how far to go

A daily collector stores per-path request counts, bytes served and distinct-client counts for
`data.clinvar-gkm.org` (no IP addresses). Estimated complete downloads of a bundle = bytes served ÷ its size.

Archive retention and how seriously to run parallel version lines are decided from these numbers, not
assumed. Review triggers:

- **Keep and promote an archive** if any archived generation shows **N** or more estimated complete downloads
  in a calendar month; consider a citable copy (for example a DOI) for it.
- **Run the next breaking change as a full parallel line** (the ADR 0004 §3 live window) if dated bundles of
  the current line show **N** or more estimated complete downloads a month in total; otherwise a freeze at the
  switch-over is enough.
- **Review archive retention yearly.** Archives are kept until a review decides otherwise.

**N is the maintainer's decision.** The first review is 60 days after collection starts (plan, task 7).

### (g) Announcements

An **advance notice** before a republish or a switch-over is required only once the email list has
subscribers, or after GA, whichever comes first. Until then a completion notice is enough. 1.1.0 used a
completion notice only (changelog, GitHub Release notes, Discussions); this amends the advance-notice
requirement in ADR 0006's consequences.

## Consequences

- **Storage.** One frozen generation of bundles is about 24 GB (19 dated bundles, 19.3 GB, plus the
  `00-latest` copies, 4.8 GB): about $0.36 a month at R2's $0.015/GB-month. Only one Parquet dataset exists
  under (e), so dropping the dated Parquet sets saves about 65 GB. Weekly fulls add at most about 24 GB at the
  end of a month (ADR 0009). A parallel `v2/2.0/` line roughly doubles the live footprint while both exist.
- **Operations.** Each republish that replaces a line gains steps: freeze the old line folder, write and
  verify its `MANIFEST.json`, write its `README.txt`. Month and year rollovers move and delete files, and
  each move or delete is followed by a CDN purge of the old paths (ADR 0009). The uploaders and
  `generate-r2-index.sh` gain sha256, `status` / `superseded_by`, each monthly's `source_release` and a
  pointer to frozen lines. A daily GitHub Actions job collects the download stats
  (secrets `CF_ANALYTICS_TOKEN`, `CF_ZONE_ID`); a missed day can be collected again only within the 31-day
  retention.
- **For users.** A monthly or delta file keeps the same bytes and name, though its folder changes at month
  and year rollover; a weekly full is gone after its month, and is rebuilt from a monthly plus deltas; a
  superseded generation stays available as a frozen line folder (`v1/1.0/`); a checksum tells them which
  generation they hold; a frozen line says what replaced it and from when; and they can rebuild Parquet from
  any monthly with `clinvar-gkm-parquet`.
- **Metric limits.** Cloudflare's adaptive sampling makes counts estimates. Distinct clients are counted per
  day by IP, so NAT undercounts and roaming clients overcount. Bytes ÷ size counts two half downloads as one.
  Traffic before 2026-10-14 is not measurable.
- **Harder:** once GA is confirmed, a mistake in a published bundle can no longer be fixed quietly. It needs
  a frozen generation and a completion notice (non-breaking), or a new line (breaking).
