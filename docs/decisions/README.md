# Architecture Decision Records (ADRs)

One short, dated file per significant decision — why we chose an approach, not just what the code does. ADRs
are the shared, PR-reviewed record of the project's moving picture; `CLAUDE.md` points here rather than
importing them so they don't bloat every session's context.

## Conventions

- Filename: `NNNN-kebab-title.md` (zero-padded, monotonically increasing).
- Copy [`0000-template.md`](0000-template.md) to start.
- Keep it short. Link to the fuller design spec in `docs/superpowers/specs/` when there is one.
- Status: `Proposed` → `Accepted` → (later) `Superseded by NNNN`. Don't rewrite history — supersede.
- Land ADRs via PR review, like code.

## Index

- [0001 — Incremental pipeline with carry-forward + delta publishing](0001-incremental-pipeline-and-deltas.md)
- [0002 — Monthly full bundle anchored to ClinVar's monthly index](0002-monthly-full-anchored-to-clinvar-index.md)
- [0003 — Roadmap generated from label-authorized discussions](0003-roadmap-from-labeled-discussions.md)
- [0004 — Schema versioning & release change-management](0004-schema-versioning-and-release-management.md)
- [0005 — R2 distribution domain, CDN caching, and fee protection](0005-r2-custom-domain-and-cdn.md)
- [0007 — Pipeline principles and simplification](0007-pipeline-principles-and-simplification.md)
- [0008 — Bundles are the public record: immutability, archives, version lines and download metrics](0008-bundles-are-the-public-record.md)
