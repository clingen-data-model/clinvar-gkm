# 0007 — Pipeline principles and simplification

- **Status:** Proposed
- **Date:** 2026-10-18
- **Plan:** [`docs/superpowers/plans/2026-10-18-pipeline-simplification.md`](../superpowers/plans/2026-10-18-pipeline-simplification.md)

## Context

ClinVar-GKM exists to give the public community reliable, high-quality ClinVar data that significantly lowers
the barrier to understanding, access, use and interoperability. The pipeline has to transform ClinVar into the
GA4GH GKM schema set (VRS, Cat-VRS, VA-Spec) and stay maintainable by a small team, with as few points of
failure as possible.

**Size today** (`main` @ `567272c`; `src/` is identical on `1.0` @ `6606d3d`):

| Part | Count | Lines |
| --- | --- | --- |
| BigQuery procedures and functions (`src/procedures/*.sql`) | 22 files | about 9,300 |
| Release scripts (`src/scripts/`, top level) | 31 files | about 5,000 |
| Parquet export SQL (`src/scripts/parquet-schemas/*.sql`) | 21 files | 193 |
| Oracle and validation scripts (`oracle-*.sh`, `validate-*`) | 10 files | — |

The 1.1.0 work found defects that fall into four classes. None of them is a one-off; each class comes from how
the pipeline is built.

1. **Duplicated logic that drifted apart.**
    - The Parquet SQL re-derives every table from the BigQuery `gkm_dict_*` tables, so it had to copy the bundle
      assembler's cleanup. The copy was incomplete: typed `extensions` in `scv` and `evidenceLine` Parquet
      carried all-null placeholder elements that the bundle does not have (#143).
    - Two null-strip implementations exist: the assembler's `strip_empty` and BigQuery's `JSON_STRIP_NULLS`.
      Applying `JSON_STRIP_NULLS` to the key/value tables would have broken the VRS `Range` nulls in 65,964
      `location` rows (#143).
    - The proposition type → bundle section mapping is copied in 11 places: 8 procedure sites, the NDJSON export,
      the delta manifest and the conformance validator (#155 §2.3). The copies already differ in detail.
2. **Mixed reference forms.** Bare CURIEs and `#/section/key` pointers were both used for references: 7,811,379
   bare values in VCV proposition `object` and `vcv-` ConceptSet `concepts` on 2026-10-11 (#160). A Parquet
   column carried quoted pointers. Consumers and our own Parquet SQL strip pointers with regexes in many places.
3. **Incremental and full builds disagreed.**
    - Unordered aggregates made the procedures non-deterministic: two runs of unchanged SQL gave different
      fingerprints for `gkm_dict_variation`, the VCV/RCV aggregate tables, `variation_hgvs` and
      `variation_identity` (#161).
    - A duplicate allele key flipped between builds, so it showed up in weekly deltas (#157).
    - The VCV/RCV carry-forward parses the accession out of the proposition id (`SPLIT(key, '-')`), which ties
      the delta model to the id format (#155 §3.B).
4. **Upstream inputs trusted without checks.**
    - `clinvar_ingest.entrez_gene` is missing 64,854 gene ids that `gene_association` uses.
    - `rcv_mapping` lists SCVs that are absent from the VCV data, 2–3 a week. It is a faithful parse of
      ClinVar's RCV XML, which runs out of sync with the VCV XML. One stale SCV left four RCV propositions with
      no `object` (#158).
    - ClinVar's VCV XML carries 16 malformed HGVS expressions with no sequence-type letter (#145).
    - `single_gene_variation` counts gene-association rows instead of distinct genes, so 55 haplotypes and
      genotypes whose alleles share one gene get no gene.

Each fix so far has been local. Without a shared standard, the same classes will recur.

## Decision

These five principles are **normative**. Every change to the pipeline or the published data is measured against
them. A change that departs from one says so in its PR, with the reason; a lasting departure needs its own ADR.

1. **ClinVar fidelity.** Never alter or drop source data silently. A repair keeps the original value in an
   extension, and an inferred value is marked as inferred. Examples: `originalClinvarExpression` /
   `invalidClinvarExpression` (#145), `originalClinvarCitation` (#156), `geneContextSource` (#159), and
   `submittedCondition` kept as the submitted CURIE.
2. **One source of truth.** The JSON bundle is canonical. Every other published artifact (Parquet, lookup files)
   must be recomputable from the published bundle. Derived columns, join keys and lookup tables are allowed. A
   new fact goes into the bundle first and flows out from there.
3. **Conformance on real artifacts.** Validate the actual published bundles, full and delta, with the GA4GH
   gkm-toolkit against the strict schemas. A hand-built sample or a sub-bundle does not count: it can mask
   export and assembler bugs.
4. **Determinism.** The same input gives byte-identical output, and incremental output equals a full rebuild.
   Every aggregate, pick and array order that reaches an output uses a total order.
5. **Change published data only by rebuilding.** One consolidated rebuild and backfill per release, with the docs
   updated in lockstep. Published files are never patched in place.

### Rules these principles consolidate

These rules already exist. The principles state the intent behind them; the detailed rules stay where they
are.

| Principle | Existing rule | Where it lives |
| --- | --- | --- |
| 1 | ClinVar's submitted text is never altered or dropped | #144 plan, decision A1; #145 |
| 2 | The assembler (`assemble-gkm-dicts.py` + `gkm_json_cleanup.py`) is the single publish-layer cleanup point | `CLAUDE.md`; [`scripts.md`](https://github.com/clingen-data-model/clinvar-gkm/blob/main/.claude/rules/scripts.md) "Publish-layer cleanup & bundle conformance" |
| 2 | `schema/clinvar-gkm/` is the source of truth for the schema | [ADR 0004](0004-schema-versioning-and-release-management.md) §9 |
| 3 | Validate the real full and delta bundles with gkm-toolkit; `sub-bundle.py` output is not proof | `CLAUDE.md`; `scripts.md` "Conformance validation" |
| 3 | Validate the data a procedure produces, not just that the SQL runs | [`sql-procedures.md`](https://github.com/clingen-data-model/clinvar-gkm/blob/main/.claude/rules/sql-procedures.md) "Cat-VRS variant/constraint shapes" |
| 4 | Incremental procedures are byte-identical to a full rebuild; total-order `ORDER BY`; no `ANY_VALUE` for values the group key does not determine | `sql-procedures.md` "Determinism / correctness"; [ADR 0001](0001-incremental-pipeline-and-deltas.md) |
| 4 | Full-vs-incremental and delta-reconstruction oracles report `0,0,0` before publishing | `sql-procedures.md` |
| 5 | Settle every data decision, then run one consolidated rebuild and backfill; docs move with every PR | maintainer rule, applied in #144 and #155 |
| 5 | Never overwrite a published dated path without a CDN purge; every live R2 write is confirmed by a maintainer | `scripts.md` "Cloudflare R2"; [ADR 0005](0005-r2-custom-domain-and-cdn.md) |

## Consequences

The principles point the pipeline toward fewer moving parts. The
[simplification plan](../superpowers/plans/2026-10-18-pipeline-simplification.md) has the detail, the
measurements and the decisions still needed. In summary:

- **Generate Parquet from the bundle output.** Build the Parquet tables from the cleaned records the assembler
  writes, instead of re-deriving them from the dict tables in 21 SQL files. The copied cleanup and the
  placeholder class of bugs go away (principle 2).
- **One canonical definition per concept.** Pointer formatting, pointer stripping, the type → section mapping
  and the list of tracked tables each get one shared definition (principles 2 and 4).
- **Re-evaluate the incremental machinery with cost data.** Measure each procedure in full and incremental mode
  over several weeks before deciding where carry-forward pays for its complexity. The delta product does not
  depend on it: `gkm_change_log` already finds changes by diffing outputs (principle 4).
- **Input contract checks at the upstream boundary.** Check the inputs before each run. A violation fails the
  run or is logged; it is never silently absorbed (principle 1).
- **One release gate command.** The oracles, strict gkm-toolkit validation of the real bundles, the
  bundle-vs-Parquet recompute and the reference guard run as one command that blocks publish (principles 3
  and 4).
- **Restraint on new published artifacts.** Every new artifact needs a stated owner and gate, and derives from
  the bundle or the published Parquet (principles 2 and 5).

Other consequences:

- The in-flight 1.1.0 release already applies parts of this: the canonical type → section function (#155),
  uniform `#/` references with a bare-reference guard (#160), the determinism fixes (#161, #157) and the release
  gates in #155 §6.4. The simplification work starts after 1.1.0 ships.
- Principle 5 retires the patch-style backfill used for the 1.0.0 `conditionSet` repair and prepared for 1.0.2
  (#144). #155 had already moved 1.1.0 to a full rebuild.
- Rebuilds cost more than patches. The #155 estimate for a full rebuild of all 16 datasets is about 3.4 TiB
  billed, about $21 at on-demand rates. That is small next to the cost of an unverifiable patch.
- Reviewers gain a checklist: which principle does a change touch, and which gate proves it holds.
- Once accepted, `CLAUDE.md` should point to this ADR from its project context section.
