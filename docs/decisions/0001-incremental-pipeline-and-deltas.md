# 0001 — Incremental pipeline with carry-forward + delta publishing

- **Status:** Accepted
- **Date:** 2026-08-09
- **Spec:** `docs/superpowers/specs/2026-08-06-incremental-gks-downstream-and-deltas-design.md`

## Context

Reprocessing every ClinVar release from scratch is expensive — the two costliest stages (variation identity
and VRS resolution) recompute ~4.5M variants weekly even though ~0.3% change. Consumers also wanted just the
changes, not a full re-download each week.

## Decision

Make the pipeline **incremental by default**: recompute only the records that changed since the prior release
and **carry the rest forward**, gated by a `gkm_pipeline_version` stamp (full rebuild on version-invalidating
changes). The delta is a byproduct of incremental compute — `gkm_change_log` + `gkm_delta_build` produce the
A/U/D manifest and delta payloads, published to R2 as weekly delta bundles + Parquet alongside the monthly full.

- Merge primitive for the dict/identity layers: **UNION-CTAS** (`base WHERE NOT impacted UNION ALL recomputed`).
- `gkm_vrs` carry-forward uses a zero-copy **CLONE** of the prior release + `DELETE`/`INSERT` of the changed
  subset (with a deep-copy fallback when BigQuery's depth-3 clone chain fills).

## Consequences

- Large slot-time win on variation identity + vrsify; the dict aggregates are roughly break-even on cost — the
  **delta product**, not slot-time, justifies making them incremental too.
- Correctness is enforced by **oracles**: full-vs-incremental (per table) and delta-reconstruction must be
  `0,0,0` before publish. This requires deterministic output (total-order `ORDER BY`, single-representative
  picks instead of `ANY_VALUE`).
- Consumers reconstruct current state = latest monthly full + replay contiguous weekly deltas.
