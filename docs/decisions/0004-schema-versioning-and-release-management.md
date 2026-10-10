# 0004 — Schema versioning & release change-management

- **Status:** Proposed
- **Date:** 2026-10-08
- **Spec:** `docs/superpowers/specs/2026-10-08-schema-versioning-and-release-management-design.md`

## Context

The clinvar-gkm bundle schema is already `1.0.0` (in its `$id` URIs), but releases are dated, not
schema-versioned, and nothing — not the `index.json`, the R2 path, nor the bundle — carries a machine-readable
schema version. As the model evolves we need a contract that lets consumers pin a version, keeps prior releases
flowing during a migration, and consults affected users *before* a breaking change — without forcing a full
reprocessing on every change.

## Decision

Adopt semantic versioning of the bundle schema and a release change-management policy (full detail in the
spec):

1. **Semver** on the bundle schema — MAJOR = breaking, MINOR = additive/backward-compatible, PATCH = no change
   to valid instances. A content-only change (e.g. a string value's format) is not a schema version change.
2. **Upstream bumps are insulated** — our level reflects the actual effect on the bundle we emit, not the
   upstream (va-spec/cat-vrs/vrs) bump level.
3. **Breaking change ⇒ new MAJOR line.** The prior line stays fully live (monthly + weekly) for a **6-month**
   window, then freezes (archived, immutable). The window end is a **fixed calendar date** (successor GA +
   6 months) in the manifest. **At most two lines** run concurrently (N, N-1).
4. **R2 layout:** per-major dirs `/v{major}/…`, each with its own `index.json`; a thin **root manifest** lists
   active versions, their schema, status, and EOL. Existing 1.x is **mirrored into `/v1/` now** (flat
   originals retained for backward compatibility).
5. **Initial-stabilization window:** until a maintainer-declared GA, the 1.0.x line may take corrective
   breaking fixes **in place** (announced, not RFC'd). After GA, the full MAJOR/parallel-line/RFC machinery
   governs every breaking change.
6. **Release notes** per data release + a per-major **CHANGELOG**, co-located with each line's files.
7. **Subscribe/consult** via GitHub Discussions *Announcements* (releases + RFCs), a **Google Group** (email,
   for non-GitHub consumers), and an RSS/Atom feed from `index.json`.
8. **Breaking-Change RFC:** before any post-GA MAJOR — proposal + rationale + migration impact, notify the
   registry, **4-week** minimum comment window.
9. **Schema in lockstep:** `schema/clinvar-gkm/` is the source of truth. Every output change moves the schema
   with it in the same PR — definitions for shape changes, field descriptions for content-only changes —
   regenerates `json/` + the bundle schema (+ docs), bumps the `$id` version per (1) when the shape changes,
   and re-validates the examples. The `$id` version is the authoritative version string the manifest reports.

## Consequences

- Consumers can pin a major line and keep receiving fresh data for 6 months after a breaking change; a
  machine-readable root manifest tells them what's current, deprecated, and when each line ends.
- The orchestrator and `generate-r2-index.sh` gain per-major output paths, a root manifest, a feed, and a
  stop-rule for frozen lines; release-notes/CHANGELOG generation is added. These are specced but not built
  here, and every live-R2 write stays a separately user-confirmed step.
- Breaking changes cost ~2× pipeline/storage during a window and require a 4-week RFC post-GA — a deliberate
  trade for consumer stability.
- The prompting change (the `submittedCondition` CURIE de-pointer) is content-only, so it ships under the
  stabilization window without a version bump; this policy governs the first *breaking* change after GA.
- Accepted additions: a bundle-level `schema_version` field (bundles self-identify) and a Home-page release
  indicator reading the root manifest. The email list (Google Group) is planned but on hold — no public
  sign-up until it is stood up.
