# Versioning & Releases

How the ClinVar-GKM bundle schema and its data releases are versioned, how breaking changes roll out, and how
to stay informed.

## Two things are versioned

- **The schema** — the shape of the bundle (its fields, types, and references). It carries a
  [semantic version](https://semver.org) `MAJOR.MINOR.PATCH`.
- **The data releases** — the periodic bundles themselves: a **monthly full** plus **weekly deltas**, each
  dated. Every release conforms to a specific schema version.

## What the schema version means

| Change | Version bump | What it means for you |
| --- | --- | --- |
| **MAJOR** (`2.0.0`) | Breaking | A bundle valid under the old version may no longer validate or parse the same way — a field was removed, renamed, retyped, restructured, or made required. You may need to update your code. |
| **MINOR** (`1.1.0`) | Additive | New optional fields/sections/values only. Old consumers keep working unchanged. |
| **PATCH** (`1.0.1`) | Cosmetic | No change to valid instances — documentation, metadata, or generator fixes. |

A change to a **string value's format** that leaves the schema shape untouched (same fields and types) is
**not** a schema version change — it is recorded in the release notes.

!!! note "Upstream standards are insulated"
    ClinVar-GKM builds on the GA4GH GKM schemas (VRS, Cat-VRS, VA-Spec). When one of those bumps, the
    ClinVar-GKM version changes **only by the actual effect on the bundle we emit** — not automatically. An
    upstream major release that doesn't change any field we emit is not a major change for ClinVar-GKM.

## How breaking changes roll out

When a breaking (**MAJOR**) change ships, it starts a **new release line**. The previous line does **not** stop
immediately:

- The prior line stays **fully live** — monthly fulls and weekly deltas keep being produced — for a
  **6-month deprecation window**.
- After the window it **freezes**: archived and immutable (still downloadable, no new data). The window ends on
  a **fixed date**, published as `eol` in the manifest.
- **At most two major lines** run at once (the current one and the one before it).

This gives you six months of fresh data on the old shape while you migrate.

!!! info "The published schema always matches the data"
    The schema in [`schema/clinvar-gkm/`](https://github.com/clingen-data-model/clinvar-gkm/tree/main/schema/clinvar-gkm)
    is the source of truth and is updated in the same change as any adjustment to the emitted bundle — so a
    given release's data always validates against its stated schema version, and the published examples are
    validated against it.

## Finding and pinning a version

Each major line lives under its own path (`/v2/…`) with its own `index.json`. A small **root manifest** at the
bucket root tells you what's current, what's deprecated, and when each line ends:

```json
{
  "active": ["1", "2"],
  "versions": {
    "1": {"schema": "1.4.2", "status": "deprecated", "eol": "2027-04-01", "index": "/v1/index.json"},
    "2": {"schema": "2.0.0", "status": "current",    "eol": null,          "index": "/v2/index.json"}
  }
}
```

To **pin** to a major version, read releases from that line's `index.json` and ignore the others. To **track
the latest**, follow the line whose `status` is `current`. Every bundle also carries a top-level
`schema_version` field, so you can confirm a file's exact version from the file itself.

## Release notes

- Every **monthly full** ships a downloadable **release-notes** document alongside its files — what ClinVar
  changed, record counts, and notable anomalies. Weekly deltas reference the current monthly's notes.
- Each major line keeps a running **CHANGELOG** of every schema change (MAJOR/MINOR/PATCH) with dates and
  migration pointers.

## Stay informed & have a say

!!! tip "Subscribe"
    - **Watch the GitHub repository** (Custom → Releases & Discussions) for release announcements and change
      proposals.
    - **Subscribe to the release feed** (RSS/Atom, generated from `index.json`) in any feed reader.
    - *An email subscription list, for consumers who prefer not to use GitHub, is planned — not yet available.*

Before any breaking change (after the schema reaches **GA**), we open a **Request for Comment (RFC)** — a
proposal with its rationale and migration impact — notify subscribers, and hold a **minimum 4-week comment
window** so affected consumers can weigh in before the change is finalized.

!!! info "Initial-stabilization period"
    The schema is newly published and still stabilizing. Until we declare **general availability (GA)**,
    corrective breaking fixes may ship **in place** on the current line, announced through the channels above
    (without a formal RFC). Once GA is declared, every breaking change follows the full rollout and RFC process
    described here.

The full decision record is [ADR 0004](../decisions/0004-schema-versioning-and-release-management.md).
