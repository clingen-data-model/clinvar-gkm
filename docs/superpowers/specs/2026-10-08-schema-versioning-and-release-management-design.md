# Schema Versioning & Release Change-Management — Design

- **Status:** Draft for review
- **Date:** 2026-10-08
- **ADR:** `docs/decisions/0004-schema-versioning-and-release-management.md`
- **Public page:** `docs/reference/versioning.md`

## Goal

Give ClinVar-GKM a durable contract for how the **bundle schema** and the **data releases** are versioned, how
breaking changes roll out, and how interested consumers are notified and consulted — so the model can evolve
without silently breaking downstream users or forcing a full reprocessing every time.

## Context

- The clinvar-gkm **schema is already `1.0.0`**, baked into `$id` URIs
  (`https://w3id.org/clingen/schema/clinvar-gkm/1.0.0/…`) across the `*-source.yaml` sources and
  `clinvar-gkm-bundle.schema.json`. The `1.0` git branch is the release line; `main` is dev.
- **Releases are dated**, not schema-versioned: monthly fulls (`clinvar-gkm_YYYY-MM`) + weekly deltas, tracked
  in a single root `index.json` (`{description, updated_at, base_url, datasets, archives, deltas}`). There is
  **no machine-readable schema-version signal** in the index, the R2 path, or the bundle today.
- Upstream schemas are pinned in the sources: va-spec 1.1.0, cat-vrs 1.1.1, vrs 2.1.
- `DATASET_VERSION` (e.g. `v2_6_0`) is the **upstream clinvar-ingest input** version — unrelated to the GKM
  schema version.

This policy is written now (forward-looking governance). The change that prompted it — the
`submittedCondition`/`submittedConditionSet` CURIE de-pointer — turned out to be **content-only** (string
values change `#/section/CURIE` → bare `CURIE`; no field/type/shape change), so it does **not** bump the schema
and does **not** exercise the breaking-change machinery. The policy governs the first *breaking* change after
GA.

## Decisions

### 1. Semantic versioning of the bundle schema

The clinvar-gkm bundle schema carries a `MAJOR.MINOR.PATCH` version.

| Level | Meaning | Examples |
|---|---|---|
| **MAJOR** `x.0.0` | Breaking — an existing valid bundle may no longer validate/parse the same way | remove/rename a field, change a field's type or meaning, repoint a `$ref` incompatibly, restructure a section, make an optional field required |
| **MINOR** `x.y.0` | Additive & backward-compatible | add a new optional field/section/extension, add enum values, relax a constraint, loosen cardinality |
| **PATCH** `x.y.z` | No change to valid instances | description/doc fixes, comment edits, generator fixes that don't alter emitted data, metadata |

A *content/semantic* change that does not alter the JSON schema (e.g. a string value's format) is **not** a
schema version change; it is recorded in the release notes and, pre-GA, may ship in place.

### 2. Upstream dependency bumps are insulated

When an upstream schema we pin (va-spec / cat-vrs / vrs) changes, our version level reflects the **actual
effect on the clinvar-gkm bundle we emit**, not the upstream bump level. An upstream MAJOR that does not change
any field we emit is a MINOR (or PATCH) for us; it is MAJOR for us only if our emitted bundle shape breaks.

### 3. Breaking change ⇒ a new MAJOR release line, with a deprecation window

- A MAJOR bump starts a **new release line**. The prior line stays **fully live** — monthly fulls + weekly
  deltas keep being produced — for a **6-month deprecation window**, then **freezes** (archived, immutable: no
  new data, still downloadable). The window end is a **fixed calendar date** (the successor line's GA date +
  6 months), published as `eol` in the root manifest — not a rolling/relative value.
- **At most two lines** run concurrently (N and N-1). A further MAJOR cannot start until the oldest live line
  has frozen, bounding steady-state cost to 2× worst case.

### 4. R2 layout: per-major directories + a root manifest

- Canonical path becomes `/v{major}/…`; each line has its own `/v{major}/index.json` (the current index
  shape, scoped to that line).
- A thin **root manifest** `/index.json` lists active versions:

  ```json
  {
    "manifest_version": 1,
    "updated_at": "2026-10-08T00:00:00Z",
    "base_url": "https://pub-….r2.dev",
    "active": ["1", "2"],
    "versions": {
      "1": {"schema": "1.4.2", "status": "deprecated", "eol": "2027-04-01", "index": "/v1/index.json"},
      "2": {"schema": "2.0.0", "status": "current",    "eol": null,          "index": "/v2/index.json"}
    }
  }
  ```

- Existing 1.x releases are **mirrored into `/v1/` now** (copied into the per-major layout; the flat root
  objects are retained so current hard-coded URLs keep working), and new 1.x releases publish under `/v1/`.
  The root manifest is authoritative from here on. (The one-time mirror is a live-R2 write — a separately
  user-confirmed step.)

### 5. Initial-stabilization window (how 1.0.x behaves now)

Until a maintainer-declared **GA**, the 1.0.x line is in an **initial-stabilization window**: corrective
breaking fixes may ship **in place** (announced via release notes, not RFC'd), because adoption is still
early. GA is declared explicitly by maintainers (recorded in the CHANGELOG and announced to the Google Group +
GitHub Discussions). **After GA**, the full MAJOR / parallel-line / RFC machinery (§3, §8) governs every
breaking change.

### 6. Release notes + per-major CHANGELOG

- **Per-data-release notes**: each monthly full ships a downloadable notes doc (what ClinVar changed, record
  counts, notable anomalies), co-located with that release's files. Weekly deltas reference the current
  monthly's notes.
- **Per-major `CHANGELOG`**: a running changelog at the per-major dir records every MAJOR/MINOR/PATCH schema
  change for that line, with dates and migration pointers.

### 7. Subscribe & be notified

- **GitHub Discussions → *Announcements*** is the canonical channel for release announcements **and**
  Breaking-Change RFCs (extends ADR 0003's Discussions-driven model). GitHub users subscribe by Watching.
- **Email list (planned — on hold):** a Google Group to reach non-GitHub consumers (news, events, forthcoming
  changes) is planned but **not yet stood up**. No sign-up link is published until it exists; name/owner TBD.
  GitHub Discussions + the feed are the active channels meanwhile.
- **RSS/Atom feed** generated from `index.json` (by extending `generate-r2-index.sh`, the same read-only pass)
  lets tooling subscribe without an account.

### 8. Breaking-Change RFC process (post-GA)

Before cutting any post-GA MAJOR:

1. Open an **RFC** (GitHub Discussion, *RFC* category): proposed change, rationale, and migration impact.
2. **Notify** the registry (Announcements + Google Group).
3. Hold a **minimum 4-week comment window** before finalizing.

Pre-GA stabilization fixes are exempt (announce-only).

### 9. The schema is the source of truth, kept in lockstep

The `schema/clinvar-gkm/` sources are the authoritative definition of the bundle. **No output change ships
without the schema moving with it**, in the same change/PR:

- **Shape changes** (add/remove/rename/retype a field, change a `$ref`) edit the `*-source.yaml` definitions.
- **Content/semantic changes** that leave the shape intact (e.g. a string value's format) still edit the
  relevant field **descriptions** so the published schema never misdescribes the data.
- Regenerate the artifacts (`make` → `json/`, `def/`, `clinvar-gkm-bundle.schema.json`; `make docs` → the
  generated class pages) — never hand-edit generated files.
- When the shape changes, **bump the `$id` version** across every source + the bundle schema per §1; the `$id`
  version is the authoritative version string this policy refers to (and the one the root manifest reports).
- **Re-validate the examples** against the regenerated schema as a release gate.

## Accepted additions

- **Bundle self-identification**: add a top-level `schema_version` string to the bundle so a consumer can
  determine the version from the file alone (not just the index). Added to the current 1.0.x line during
  stabilization; it reports the current version string.
- **Home-page release indicator** (backlog "Feature G"): a small Home-page widget reads the root manifest to
  show the current version, flag a new release, and link to its notes.

## Implementation touchpoints (not built by this spec)

- `src/scripts/generate-r2-index.sh` — emit the root manifest + per-line index; generate the RSS/Atom feed
  (read-only R2 pass; live regen remains a separate user-confirmed step).
- `src/scripts/run-release.sh` / `release-gkm*.sh` — per-major output paths; orchestrator stop-rule for a
  frozen line.
- Release-notes + CHANGELOG generation/templates, co-located on R2 per line.
- Docs: a public `reference/versioning.md`; Google-Group sign-up link; Home-page indicator.

## Out of scope / future

- The actual 2.0.0 cut (none pending — the de-pointer is content-only).
- Automated migration tooling between major lines.
- Any live-R2 write (every rollout step that touches live R2 is separately user-confirmed).

## Resolved (from review, 2026-10-08)

1. **Mirror existing 1.x into `/v1/` now** (one-time live-R2 copy; flat originals retained).
2. **EOL is a fixed calendar date** (successor GA + 6 months), published as `eol` in the manifest.
3. **Email list (Google Group) on hold** — planned but not yet stood up; no public sign-up until it exists.
4. Both **accepted additions** confirmed (`schema_version` field + Home-page release indicator).
5. Pre-existing **`conditionSet` "Always null" description** corrected in the de-pointer pass.
