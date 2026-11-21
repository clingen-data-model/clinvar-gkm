# Versioning & Releases

How the ClinVar-GKM bundle schema and its data releases are versioned, how breaking changes roll out, and how
to stay informed.

## Two things are versioned

- **The schema** — the shape of the bundle (its fields, types, and references). It carries a
  [semantic version](https://semver.org) `MAJOR.MINOR.PATCH`.
- **The data releases** — the periodic bundles themselves: a **monthly full**, **weekly fulls** and **weekly
  deltas**, each dated. Every release conforms to a specific schema version.

## What the schema version means

| Change | Version bump | Where it is published | What it means for you |
| --- | --- | --- | --- |
| **MAJOR** (`2.0.0`) | Breaking | A new line folder, `v2/2.0/` | A bundle valid under the old version may no longer validate or parse the same way — a field was removed, renamed, retyped, restructured, or made required. You may need to update your code. |
| **MINOR** (`1.2.0`) | Additive, or a correction that rewrites published bundles | A new line folder, `v1/1.2/` | New optional fields, sections or values, or corrected content in republished bundles. Old consumers keep working unchanged. |
| **PATCH** (`1.1.1`) | Cosmetic | The current line folder | No change to valid instances, and no published file is rewritten — only new dated files are added. |

A change to a **string value's format** that leaves the schema shape untouched (same fields and types) is
**not** a schema version change — it is recorded in the [Changelog](changelog.md). A content-only correction
that must **rewrite published bundles** is still released as a new MINOR line, even when the schema shape is
unchanged. The new line's schema `$id` version and every bundle's `schema_version` move to that MINOR too, so a
bundle's `schema_version` always names the line folder it was published in. A PATCH never rewrites a published file.

!!! note "Upstream standards are insulated"
    ClinVar-GKM builds on the GA4GH GKM schemas (VRS, Cat-VRS, VA-Spec). When one of those bumps, the
    ClinVar-GKM version changes **only by the actual effect on the bundle we emit** — not automatically. An
    upstream major release that doesn't change any field we emit is not a major change for ClinVar-GKM.

## 1.1.0 and general availability

**1.1.0 is generally available (GA).** It was a breaking change — the proposition sections were renamed —
released as a MINOR under the initial-stabilization exception
([ADR 0006](../decisions/0006-ship-1.1.0-in-place-under-v1.md)). It was published into a new line folder,
`v1/1.1/`, and the 1.0.1 generation became the frozen line `v1/1.0/` (ADR 0009). The stabilization period ends
with 1.1.0:

- **Published files are immutable.** The bytes behind a published monthly or delta are never replaced. A
  rollover can move a file to a new folder without changing its name, bytes or checksum. Weekly full bundles
  are the one exception: they are deleted after their month, and any past week can be rebuilt from a monthly
  plus deltas. The `index.json` files, `feed.xml` and every `00-latest` path are pointers that move with each
  release.
- **Every later breaking change opens a new MAJOR line** (`v2/2.0/`), with the RFC process below.

See the [1.1.0 changelog](changelog.md#110) for the migration notes.

## 1.2.0: a new MINOR line

1.2.0 narrows the ClinVar profiles to exactly what the pipeline writes, a MINOR change. It is published into a
new line folder, `v1/1.2/`, and `v1/1.1/` is frozen with `"superseded_by": "v1/1.2"`:

- **The new line starts with a checkpoint.** `v1/1.2/` begins with one monthly full built with the 1.2.0
  pipeline, the official monthly of the ClinVar month it is the source of (ADR 0002). Weekly fulls and deltas
  run forward from it, so the first delta's `baseline_release` is the checkpoint's `source_release`. Earlier
  releases are not republished into the new line; they stay in `v1/1.1/` as 1.1.0.
- **The frozen line keeps its records.** `v1/1.1/` keeps its monthlies, `00-latest` copy and deltas, unchanged,
  and gains a `MANIFEST.json` and a `README.txt`. Its weekly fulls and its Parquet set are deleted at the
  freeze: neither is a record ([ADR 0008](../decisions/0008-bundles-are-the-public-record.md) (e),
  [ADR 0009](../decisions/0009-r2-layout-mirrors-ncbi-clinvar.md) §4).

## How breaking changes roll out

A breaking (**MAJOR**) change opens a new line folder, `v2/2.0/`, built in full — every monthly full and delta
in the published window — alongside `v1/`. At the switch-over:

- The prior line is **frozen**: it gets no new releases, and its files stay downloadable and unchanged.
- A frozen line is **kept indefinitely**. There is no end-of-life date, no `deprecated` status and no deletion
  window.
- The root manifest and the line's own `index.json` mark it `"status": "frozen"` with `"superseded_by"` naming
  the line that replaced it, and the frozen folder carries a `MANIFEST.json` (size and sha256 per file) and a
  `README.txt` saying what replaced it and why.

Only one line is `current` at a time; frozen lines accumulate. A new MINOR line (for example `v1/1.2/`)
freezes the line it replaces in the same way, but starts from a checkpoint monthly instead of a full
republish (see [1.2.0](#120-a-new-minor-line)), and the frozen line drops its weekly fulls and Parquet.

!!! info "The published schema always matches the data"
    The schema in [`schema/clinvar-gkm/`](https://github.com/clingen-data-model/clinvar-gkm/tree/main/schema/clinvar-gkm)
    is the source of truth and is updated in the same change as any adjustment to the emitted bundle — so a
    given release's data always validates against its stated schema version, and the published examples are
    validated against it.

## Finding and pinning a version

Each version line lives in its own folder, `v{major}/{major}.{minor}/` (`v1/1.2/`, later `v2/2.0/`), with its
own `index.json`. PATCH releases add new dated files to their line's folder; a new MINOR or MAJOR starts a new
folder, and the line it replaces is frozen and kept indefinitely, its records unchanged (the 1.1.x releases are
the frozen line `v1/1.1/`, the 1.0.1 generation `v1/1.0/`). Inside
a line the layout mirrors NCBI's ClinVar FTP site; see [Downloads](../data-access/download.md#directory-structure).
A small **root manifest** at the bucket root, `index.json`, lists every line, its status and schema version,
and where its own `index.json` and feed are. Its shape, as published for 1.2.0:

```json
{
  "manifest_version": 2,
  "updated_at": "2026-11-30T00:00:00Z",
  "base_url": "https://data.clinvar-gkm.org",
  "current": "v1/1.2",
  "versions": {
    "1.2": {"line": "v1/1.2", "major": 1, "minor": 2, "status": "current", "schema": "1.2.0",
            "superseded_by": null, "index": "v1/1.2/index.json", "feed": "v1/1.2/feed.xml"},
    "1.1": {"line": "v1/1.1", "major": 1, "minor": 1, "status": "frozen", "schema": "1.1.0",
            "superseded_by": "v1/1.2", "index": "v1/1.1/index.json", "feed": "v1/1.1/feed.xml"},
    "1.0": {"line": "v1/1.0", "major": 1, "minor": 0, "status": "frozen", "schema": "1.0.1",
            "superseded_by": "v1/1.1", "index": "v1/1.0/index.json", "feed": "v1/1.0/feed.xml"}
  }
}
```

`versions` is keyed by `{major}.{minor}`; paths are relative to `base_url`. A line is `current` or `frozen`;
there is no `eol` field.

To **pin** to a line, read releases from that line's `index.json` and ignore the others. To **track the
latest**, follow the line whose `status` is `current`. Every bundle also carries a top-level
`schema_version` field, so you can confirm a file's exact version from the file itself.

## Versions of these docs

The documentation is versioned by release line, like the data: `1.1` describes the `v1/1.1/` line, `1.2` the
`v1/1.2/` line, and so on. A patch release updates its line's docs in place. Choose a version from the selector
next to the site name in the header; the selector keeps you on the same page when it exists in the other
version.

- **The latest release** is the default. The site root, and any link without a version in it, opens the same
  page in the latest release. Its header is indigo.
- **An older release** has a grey header and a notice that it is not the current version, with a link to the
  same page in the latest release. It shows the site as it was last built for that line.

Unreleased changes are not published as a docs version: the docs change with a release. A link to the former
`dev` version (`…/clinvar-gkm/dev/<page>/`) opens the same page in the latest release.

The download tables and the live query console in each version read that version's data line: the `1.1` docs
list the files in `v1/1.1/`, the `1.2` docs those in `v1/1.2/`. On a frozen line the weekly full bundles and the
Parquet set are deleted, so those tables and the console say so and link to the latest docs (the console says so
on any frozen line, even before the deletion). Each version lists the frozen lines older than its own on
[Previous Releases](../data-access/previous-releases.md) and on the Get the Data landing page: the latest release
lists every frozen line, the `1.1` docs only `1.0`.

The repository link at the right of the header names the source each version was built from, and its links to
repository files point there too: the release tag (such as `1.1.0`). The
`1.1` docs are built from the `main` commit that documented 1.1.0 (`036bec2`), plus their Previous Releases page
(the branch `docs/line-1.1`), because the `1.1.0` tag was cut without them, so their repository-file links point
at that branch's commit.

To link to a page in whatever release is latest, use a link without a version, such as
`https://dataexchange.clinicalgenome.org/clinvar-gkm/reference/changelog/`. To pin a link to one version,
include it: `…/clinvar-gkm/1.1/reference/changelog/`. The decision record is
[ADR 0011](../decisions/0011-versioned-documentation.md).

## Release notes

- The [Changelog](changelog.md) records every schema change (MAJOR/MINOR/PATCH) and every data re-release,
  with dates and migration pointers.
- Each tagged release is listed on [GitHub Releases](https://github.com/clingen-data-model/clinvar-gkm/releases)
  with its source.
- Each weekly delta's manifest gives its per-section added, updated and deleted counts; see
  [Weekly Deltas](../data-access/weekly-deltas.md).

## Stay informed & have a say

!!! tip "Subscribe"
    - **Watch the GitHub repository** (Custom → Releases & Discussions) for release announcements and change
      proposals.
    - **Subscribe to the release feed** (Atom, each line's `feed.xml`, e.g. `https://data.clinvar-gkm.org/v1/1.2/feed.xml`) in any feed reader.
    - **Join the email list** [clinvar-gkm@broadinstitute.org](https://groups.google.com/a/broadinstitute.org/g/clinvar-gkm), a Google Group for release announcements, change notices and RFCs about
      the repository, the data releases, tools and documentation. No GitHub account needed; see
      [Stay Informed](../stay-informed.md) for how to join.

Before any breaking change, we open a **Request for Comment (RFC)** — a proposal with its rationale and
migration impact — send subscribers an advance notice, and hold a **minimum 4-week comment window** so
affected consumers can weigh in before the change is finalized. Every republish into a new line and every
switch-over is announced in advance.

The decision records are [ADR 0004](../decisions/0004-schema-versioning-and-release-management.md) (schema
versioning and release management), [ADR 0006](../decisions/0006-ship-1.1.0-in-place-under-v1.md) (1.1.0
under the stabilization exception), and ADR 0008 (bundles are the public record) and ADR 0009 (R2 layout
mirrors NCBI ClinVar), proposed in [PR #168](https://github.com/clingen-data-model/clinvar-gkm/pull/168).
