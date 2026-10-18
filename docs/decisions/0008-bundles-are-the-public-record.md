# 0008 — Bundles are the public record: immutability, archives, version lines and download metrics

- **Status:** Proposed
- **Date:** 2026-10-18
- **Plan:** [`docs/superpowers/plans/2026-10-18-bundle-record-and-metrics.md`](../superpowers/plans/2026-10-18-bundle-record-and-metrics.md)

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
  `MANIFEST.json` (sha256 per file) and a `README.txt`, before the 1.1.0 republish rewrites `/v1/`.
- **No subscribers yet.** The email list `clinvar-gkm@broadinstitute.org` has no members, and the schema has
  not been declared GA.

## Decision

### (a) The JSON bundles are the public record

The monthly full and delta JSON bundles are the published record of ClinVar-GKM. **From the 1.1.0 republish
on, a published bundle file is immutable:** the bytes behind a dated bundle path are never replaced without
the previous bytes being kept, as described in (c). The mutable pointers are not records: `index.json`, the
root manifest, `feed.xml` and every `00-latest` path keep moving to the newest release.

This **closes the ADR 0004 §5 in-place exception after 1.1.0**, which ADR 0006 extended to cover the 1.1.0
reorganization. Closing it is, in effect, **declaring GA**: from then on every breaking change follows the
ADR 0004 MAJOR-line and RFC process. **This is the maintainer's decision to confirm** when this ADR is
accepted. Until it is confirmed, the 1.x line is still pre-GA.

### (b) A breaking change opens a new line

A breaking schema change after 1.1.0 opens a new line, `/v2/…`, built in full (every monthly full and every
delta in the window being republished) alongside `/v1/`. The old line is then **frozen**: no new releases, and
its files stay downloadable and unchanged. It carries a switch-over notice:

- in its `index.json` and in the root manifest: `"status": "superseded"`, `"superseded_by": "2"` and an end
  date (`eol`, the date the line stopped receiving releases);
- on the email list and in GitHub Discussions *Announcements*.

**Open point:** ADR 0004 §3 keeps the prior line fully live (new monthlies and deltas) for 6 months before
it freezes. The maintainer's stated aim here is to *stop* the previous line at the switch-over. The
maintainer chooses one when accepting this ADR: freeze at the switch-over (this ADR then amends ADR 0004 §3)
or keep the 6-month live window and freeze at its end.

### (c) Non-breaking corrections archive the generation they replace

A correction that does not break the schema but must rewrite published bundles (a MINOR or PATCH republish)
first copies the generation it replaces to `archive/<version>/`, mirroring the original paths, with:

- a `MANIFEST.json` listing every archived file with its size and sha256;
- a `README.txt` saying what the generation is, which release replaced it and why.

This is the procedure used for 1.0.1. The archive is immutable and is listed from the root manifest (see the
plan, task 3).

### (d) Every manifest carries sha256 per file

Every manifest that lists a bundle (the per-line `index.json`, each delta `manifest.json` and each archive
`MANIFEST.json`) gives its size and sha256. A user can then tell which generation a local copy belongs to by
hashing it, without relying on dates or file names.

### (e) Parquet is derived, not a record

Parquet is a convenience view of a bundle, not a record:

- The docs and the manifests label it **"derived from the bundle; may be regenerated"**. Parquet sets are not
  archived; when a generation is archived, only its bundles are kept.
- A **versioned Parquet rebuild tool** builds the Parquet tables from a published bundle. It is the same code
  the pipeline uses to build them (ADR 0007, Workstream 1), and each release tag pins it, so a user can
  regenerate the Parquet of a prior release with the method used at that time.
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

- **Storage.** One archived generation of bundles is about 24 GB (19 dated bundles, 19.3 GB, plus the
  `00-latest` copies, 4.8 GB): about $0.36 a month at R2's $0.015/GB-month. A whole `/v1/` generation
  including Parquet is about 89 GB, about $1.34 a month; Parquet is not archived under (e). A parallel `/v2/`
  line roughly doubles the live footprint while both exist.
- **Operations.** Each rewrite of published bundles gains a step before upload: copy to `archive/<version>/`,
  write and verify `MANIFEST.json`, write `README.txt`. The uploaders and `generate-r2-index.sh` gain sha256,
  `status` / `superseded_by` and an archive pointer. A daily GitHub Actions job collects the download stats
  (secrets `CF_ANALYTICS_TOKEN`, `CF_ZONE_ID`); a missed day can be collected again only within the 31-day
  retention.
- **For users.** A bundle URL they cite or script against keeps meaning the same bytes; a superseded
  generation stays available under `archive/`; a checksum tells them which generation they hold; a frozen line
  says what replaced it and from when; and they can rebuild Parquet from any bundle with the tool pinned to
  that release.
- **Metric limits.** Cloudflare's adaptive sampling makes counts estimates. Distinct clients are counted per
  day by IP, so NAT undercounts and roaming clients overcount. Bytes ÷ size counts two half downloads as one.
  Traffic before 2026-10-14 is not measurable.
- **Harder:** once GA is confirmed, a mistake in a published bundle can no longer be fixed quietly. It needs
  an archived generation and a completion notice (non-breaking), or a new line (breaking).
