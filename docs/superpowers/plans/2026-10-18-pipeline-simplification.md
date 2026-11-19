# Pipeline Simplification Plan

> **Status: proposed (2026-10-18), for team review.** Governed by
> [ADR 0007](../../decisions/0007-pipeline-principles-and-simplification.md). Work starts **after the 1.1.0
> release** ships. Written against `main` @ `567272c` and `1.0` @ `6606d3d` (identical `src/`), with the PR stack
> as of 2026-10-18.
>
> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development or superpowers:executing-plans.
> Steps use checkbox (`- [ ]`) syntax. Each workstream is one or more reviewable PRs. Run `/catchup` before
> starting one. Every live BigQuery rebuild and every R2 write is a separately user-confirmed step.

**Goal:** Fewer moving parts and fewer places for the same fact to drift, with no change to published output
unless a change is intended and announced. The pipeline keeps transforming ClinVar into GKM; it does so with one
definition per concept, one source for every artifact and one gate before publish.

**Rule for every workstream:** a simplification that is not meant to change output must **prove** that it does
not. The full-vs-incremental oracles and `oracle-delta-reconstruction.sh` report `0,0,0`, and the bundle and
Parquet built before and after are byte-identical, or differ only in a listed, intended way.

**Sources:** sizes and line references were measured on the tree above. Counts and costs are quoted from the PRs
that measured them; each is cited where it is used. Effort figures are rough working-day estimates for one
person and are there to rank the work, not to schedule it.

---

## 1. Already delivered or in progress in 1.1.0

The 1.1.0 release (ADR 0006, in #146) already applies parts of ADR 0007. This plan builds on it and does not
redo it.

| Item | Principle | PR | State |
| --- | --- | --- | --- |
| Canonical proposition type → section function `clinvar_ingest.gkm_proposition_section`, replacing 11 copies of the CASE; fails loudly on an unmapped type | 2 | plan #155 §2.3, PR 1 | planned for 1.1.0 |
| Uniform `#/` references: 7,474,404 VCV proposition objects and 336,975 `vcv-` set members re-wrapped | 2 | #160 | draft |
| Bare-reference guard: `validate-proposition-conformance.sh` exits non-zero on any bare value in 23 reference fields | 3 | #160 | draft |
| Total order on every aggregate and pick that reaches an output | 4 | #161 | draft |
| One `gkm_dict_allele` row per allele id (duplicate key that flipped between builds) | 4 | #157 | draft |
| Release gates: reference integrity, expected-diff against snapshots, both oracles, gkm-toolkit on every bundle, bundle ↔ Parquet | 3, 4 | plan #155 §6.4 | planned for 1.1.0 |
| Parquet `extensions` placeholder cleanup and a `bundle_cleanup` UDF that matches the assembler | 2 | #143 | draft |
| One consolidated full rebuild of all 16 datasets instead of patching published files | 5 | plan #155 §6 | planned for 1.1.0 |

---

## 2. Workstreams at a glance

In order of value. Each has a decision that must be made before its implementation starts.

| # | Workstream | Principle | Rough effort | Decision needed |
| --- | --- | --- | --- | --- |
| 1 | [Parquet built from the bundle output](#3-workstream-1-parquet-built-from-the-bundle-output) | 2 | 5–8 days | source of the build, where it runs, `condition.parquet` columns |
| 2 | [One canonical definition per concept](#4-workstream-2-one-canonical-definition-per-concept) | 2, 4 | 3–5 days | SQL UDFs vs generated fragments; where the Python section list comes from |
| 3 | [Re-evaluate incremental vs full per procedure](#5-workstream-3-re-evaluate-incremental-vs-full-per-procedure) | 4 | 1–2 days + 4–6 weeks of data; then 2–5 days per procedure group | which procedures stay incremental |
| 4 | [Input contract checks](#6-workstream-4-input-contract-checks) | 1 | 2–4 days | fail vs log per check; where issues are logged |
| 5 | [One release gate command](#7-workstream-5-one-release-gate-command) | 3, 4 | 4–6 days | which checks run weekly vs only on procedure changes |
| 6 | [Artifact restraint](#8-workstream-6-artifact-restraint) | 2, 5 | 1–2 days, plus porting #151 | registry format; lookup files from Parquet only |

Workstreams 2 and 4 are independent of the others. Workstream 5 runs the checks that 1, 2 and 4 add, so it lands
in stages. Workstream 3 needs data collected over several weekly releases, so its measurement should start
first even though its decision comes later.

---

## 3. Workstream 1: Parquet built from the bundle output

### Problem

Today `release-gkm.sh` runs four steps:

1. `export-gkm-dicts.sh` exports every `gkm_dict_*` table twice: as NDJSON for the bundle, and as Parquet. 21
   tables go through `EXPORT DATA` with a `parquet-schemas/*.sql` file each; `condition` goes through a raw
   `bq extract`, so its columns are the untyped camelCase table columns.
2. `assemble-gkm-dicts.py` downloads the NDJSON one section at a time and runs each record through
   `strip_empty` and `collapse_ext_values` (`gkm_json_cleanup.py`). It streams the cleaned records straight into
   the bundle; they are not written anywhere else.
3. The Parquet shards are downloaded and merged with DuckDB.
4. Upload.

The Parquet SQL therefore re-derives each table from the dict tables, in parallel to the bundle. The same cleanup
is implemented three times:

| Implementation | Where |
| --- | --- |
| Python `strip_empty` + `collapse_ext_values` | `gkm_json_cleanup.py` (the bundle) |
| BigQuery JS UDF `collapse_ext_values` | `export-gkm-dicts.sh` `COLLAPSE_UDF` (NDJSON proposition and extension exports, and the Parquet SQL) |
| BigQuery `JSON_STRIP_NULLS(remove_empty => TRUE)` | 7 struct-table `data` columns (`scv`, `vcv`, `rcv`, `variation`, the three evidence-line tables) and `export_ndjson_ext_collapse` |

#143 adds a fourth, the `bundle_cleanup` UDF, to make the Parquet match. It found the placeholder elements in
`scv` and `evidenceLine` `extensions`, and that `JSON_STRIP_NULLS` on the key/value tables would have broken the
VRS `Range` nulls in 65,964 `location` rows. Any new cleanup rule has to be added in every copy, or Parquet and
the bundle disagree again.

### Approach

Build the Parquet from the records the assembler has already cleaned.

- **Recommended (A):** the assembler also writes each section's cleaned records as NDJSON (one
  `{"id": <key>, "record": <cleaned record>}` per line, the same bytes it writes into the bundle). A new step
  replaces steps 1-Parquet and 3: DuckDB reads those files and writes the 22 tables. Each table is one DuckDB
  `SELECT` that derives its typed columns from `record` and sets `data` to the record verbatim. The 21
  BigQuery `parquet-schemas/*.sql` files become DuckDB SQL files of the same shape. DuckDB is already a release
  dependency: step 3 uses it to merge the shards.
- **(B):** DuckDB reads the assembled bundle. A monthly full bundle is a single JSON object of about 4.8 GB, so
  this needs a streaming splitter first (the `stream_keys.py` pattern in §7). That rebuilds the NDJSON of (A)
  with an extra pass.
- **(C):** load the cleaned NDJSON back into BigQuery and keep `EXPORT DATA`. This keeps the Parquet build in
  BigQuery if local resources are the constraint, at the cost of a load step.

Deltas use the same path with the delta NDJSON. The NDJSON export from BigQuery stays as it is.

- [ ] Add the per-section cleaned-NDJSON output to `assemble-gkm-dicts.py` (behind a flag first).
- [ ] Port the 21 `parquet-schemas/*.sql` files to DuckDB over the cleaned NDJSON, with explicit column types.
  Carry over #143's typed columns and #155's shared proposition schema.
- [ ] Replace step 3 of `release-gkm.sh` and `release-gkm-delta.sh` with the DuckDB build; drop the Parquet
  half of `export-gkm-dicts.sh`, `COLLAPSE_UDF` from the Parquet path and the `bundle_cleanup` UDF.
- [ ] Update `.claude/rules/scripts.md` "Publish-layer cleanup" (the "mirror the same collapse in the
  typed-Parquet `data` columns" rule goes away) and the Parquet docs.

### How to measure success

- On every artifact of the published 1.1.0 set (4 monthly fulls and 15 deltas), the new Parquet has the same
  schema (column names, types and order) as the published Parquet, and DuckDB `EXCEPT ALL` in both directions
  returns 0 rows for every table. The only allowed differences are listed in advance: the latent
  `JSON_STRIP_NULLS` difference in §9.3, if any record has it.
- The bundle ↔ Parquet gate (§7) passes: per table, the id set equals the bundle section's, and `data` equals
  the bundle record.
- `grep` finds no `JSON_STRIP_NULLS` or `collapse_ext_values` in the Parquet path.

### Risks

- **Type drift.** DuckDB infers JSON types differently from BigQuery (INT64, nested STRUCT field order, JSON vs
  VARCHAR). Declare every column type; the schema comparison above catches the rest.
- **Local resources.** A monthly full is 4.8 GB and its Parquet set about 12 GB, against about 15 GB free on the
  build machine (#155 §6.6). The build may need a VM or the Cloud Run job.
- **File layout.** Row-group size, sort order and compression change the number of HTTP requests a remote query
  makes (#151 measures lookups in requests). Pin the writer settings and compare request counts for the
  console's example queries.
- **Release time.** Assembly takes about 1.5–2.5 h per full today (#155 §6.6). Measure the new step on one full
  before switching.

### Decision needed

- **Source:** (A) cleaned NDJSON from the assembler (recommended), (B) the bundle, or (C) BigQuery reload.
- **Where it runs:** the build machine, a VM, or the Cloud Run job.
- **`condition.parquet`:** keep the current untyped camelCase columns (no consumer change), or give it typed
  snake_case columns like the other 21 tables (a breaking column change under ADR 0004).

---

## 4. Workstream 2: One canonical definition per concept

### Problem

The same concept is spelled out in many places. Measured on the tree above:

| Concept | Copies today | Where |
| --- | --- | --- |
| Pointer construction (`'#/<section>/' ‖ id`) | 73 lines with a `'#/` literal in 5 procedures | `gkm-scv-statement-proc.sql` 23, `gkm-rcv-statement-proc.sql` 20, `gkm-vcv-statement-proc.sql` 19, `gkm-catvar-proc.sql` 10, `gkm-scv-condition-proc.sql` 1. Most common targets: `evidenceLine` 11, `conditionSet` 11, `condition` 10, `variation` 8, a computed section 8 |
| Pointer stripping (`REGEXP_REPLACE(…, r'^#/[^/]+/', '')`) | 30 lines | 26 in 16 of the 21 `parquet-schemas/*.sql` files; `gkm-scv-condition-proc.sql`; `validate-proposition-conformance.sh` (2); `extract-example.py` |
| Proposition type → section | 12 CASE sites + 4 `WHERE` filters | procedures: `gkm-vcv-statement-proc.sql` :223, :296, :374; `gkm-rcv-statement-proc.sql` :270, :343, :421; `gkm-scv-statement-proc.sql` :521, :1070. Scripts: `export-gkm-dicts.sh` `PROP_GROUP_CASE`, `build-delta-manifest.py` `GROUP_SECTION_CASE`, `validate-proposition-conformance.sh` :72, :92. Parquet: the four `var*-proposition.sql` filters |
| Bundle section list | 4 hand-kept lists | `assemble-gkm-dicts.py` `SECTIONS`, `build-delta-manifest.py` table → section map, `sub-bundle.py`, the bundle schema |
| Tracked output tables | 2 arrays with a "Keep in sync" comment | `gkm-change-log-proc.sql` `tracked`, `gkm-delta-proc.sql` `tables` |
| Accession from a proposition id | `SPLIT(key, '-')[OFFSET(0)]` | `gkm-vcv-statement-proc.sql` :708, :710; `gkm-rcv-statement-proc.sql` :702, :704 |

The copies already differ. `build-delta-manifest.py` still reads `COALESCE($.customPropositionType, $.type)`,
while the export CASE reads only `$.type`. The Parquet `WHERE` filters drop an unmapped type silently while the
NDJSON export raises (#155 §2.3).

### Approach

- **Pointers:** two persistent SQL UDFs in `clinvar_ingest`, versioned under `src/procedures/`:
  `gkm_ref(section, id)` returns `#/<section>/<id>` and raises on a NULL or empty part; `gkm_ref_id(ref)`
  returns the bare id and raises on a value that is not a pointer. Use SQL UDFs, not JavaScript, so BigQuery
  inlines them.
- **Type → section:** #155's `gkm_proposition_section` (1.1.0). This workstream only checks that no copy came
  back.
- **Section list and tracked tables:** one checked-in definition that every consumer reads. For SQL, a function
  that returns the tracked-table array; for Python, one module that the assembler, the delta manifest,
  `sub-bundle.py` and `extract-example.py` import. A test checks the module against the bundle schema's
  section properties.
- **Accession from an id:** replace the `SPLIT` with an explicit accession column, or a join through the
  statement. This depends on Workstream 3: if the VCV/RCV statement procedures stop carrying forward, the parse
  goes away with the carry-forward.
- **Pointer stripping in Parquet:** goes away with Workstream 1 if the Parquet SQL moves to DuckDB; otherwise the
  Parquet SQL calls `gkm_ref_id`.

- [ ] Add `gkm_ref` / `gkm_ref_id` and a tracked-tables function; deploy them before the procedures.
- [ ] Replace each site in the table above. One PR per procedure keeps the oracle runs small.
- [ ] Add a CI grep guard: no `'#/` literal and no `^#/` regex outside the shared definitions.

### How to measure success

- The full-vs-incremental oracles and `oracle-delta-reconstruction.sh` report `0,0,0`.
- Dict-table fingerprints (`BIT_XOR(FARM_FINGERPRINT(TO_JSON_STRING(row)))`, the #161 method) and the assembled
  10-11 bundle are byte-identical before and after.
- The CI guard passes, and a seeded `'#/` literal makes it fail.

### Risks

- The UDFs live in `clinvar_ingest`, which the upstream project also uses. Use the `gkm_` prefix.
- Every procedure change moves the pipeline `gate_key`, so the first run after deploy is a full rebuild of the
  current dataset (about 0.21 TiB, #155 §6.3). No backfill is needed, because output does not change.
- A raising UDF fails a weekly run on bad data that used to pass silently. That is intended (principle 1), but
  the first runs need watching.

### Decision needed

- Persistent SQL UDFs (recommended) or SQL fragments generated into the procedure files at build time.
- Python section list: a hand-kept module checked against the bundle schema (recommended), or generated from the
  bundle schema.

---

## 5. Workstream 3: Re-evaluate incremental vs full per procedure

### Problem

[ADR 0001](../../decisions/0001-incremental-pipeline-and-deltas.md) made the pipeline incremental by default. It
records that the large slot-time win is in variation identity and vrsify, that the dict aggregates are roughly
break-even on cost, and that the delta product justified making them incremental too.

The incremental machinery is a large share of the pipeline:

| Part | Size |
| --- | --- |
| Upstream table diffs (`dataset-diff*.sql`) | 4 files, 414 lines |
| Changed-set procedures (`gkm-scv-changed`, `gkm-rcvvcv-changed`, `variation-vrs-changed`) | 3 files, 722 lines |
| Full/incremental branches inside the procedures (impacted filters, UNION-CTAS merges, the `gkm_vrs` `CLONE` with its depth-3 fallback) | 8 procedures |
| Version gate (`gkm-pipeline-version-proc.sql`, `gate_key` in `run-release.sh`) | 1 procedure + script logic |
| Proposition id parsing in the VCV/RCV carry-forward | 4 sites (§4) |
| Full-vs-incremental oracles (`oracle-catvar.sh`, `oracle-scv-condition.sh`, `oracle-scv-statement.sh`, `oracle-rcv.sh`, `oracle-rcv-statement.sh`, `oracle-vcv.sh`, `oracle-vcv-statement.sh`, `gkm-oracle-compare-proc.sql`) | 8 files; they exist because there are two modes |

Two of the four defect classes in ADR 0007 came from here: non-determinism showed up as incremental ≠ full, and
the delta model depends on the proposition id format.

The deltas do not depend on the carry-forward. `gkm_change_log` finds Added/Updated/Deleted records by diffing
each published `gkm_dict_*` table against the prior release, and `gkm_delta_build` materializes the A/U rows.
That already is "computing deltas by diffing outputs". A procedure that always rebuilds in full still produces
correct deltas, as long as its output is deterministic. `gkm-change-log-proc.sql`, `gkm-delta-proc.sql`,
`build-delta-manifest.py` and `oracle-delta-reconstruction.sh` stay in either mode.

**What a full rebuild costs.** From #155 §6.3 (the #132 rebuild of the 16 datasets on 2026-10-11, from
`INFORMATION_SCHEMA.JOBS`): about 0.21 TiB billed, 11–12 min wall clock and 14 slot-hours per dataset for the
downstream `gkm_*` stage; about 3.4 TiB for all 16, about $21 at on-demand $6.25/TiB. That is about $1.30 per
weekly release. This covers the downstream procedures only; variation identity and vrsify (with its external VRS
resolution) are not in it. The cost of the incremental runs per procedure has not been measured.

### Approach

Measure first; decide per procedure afterwards.

- [ ] For 4–6 consecutive weekly releases, record per procedure, in both modes: bytes billed, slot-ms and wall
  clock from `INFORMATION_SCHEMA.JOBS` (child jobs of each `CALL`, grouped by procedure). The full-mode runs that
  the full-vs-incremental oracles already do provide the full side; where an oracle does not cover a procedure,
  build it in full into a scratch dataset.
- [ ] Record vrsify separately: VRS resolution time and request volume, full vs incremental.
- [ ] Record the maintenance side for the same period: lines in incremental-only paths per procedure, and the
  defects and oracle exceptions caused by incremental mode (for example #157 and the 1.0.1 allele exceptions).
- [ ] Write the results and a recommendation into an ADR that amends or supersedes ADR 0001.
- [ ] For each procedure moved to full-only: remove its incremental branch, its changed-set inputs if nothing else
  reads them, and its full-vs-incremental oracle.

### How to measure success

- The decision is recorded with the numbers behind it.
- For each procedure moved to full-only, its output equals the incremental output on the measured weeks
  (byte-identical tables), and `oracle-delta-reconstruction.sh` reports `0,0,0` on the published deltas.

### Risks

- **Shadow cost.** A full downstream build is about $1.30 per dataset, so 6 weeks of shadow builds cost about
  $8 at on-demand rates. Variation identity and vrsify in full mode cost much more and may not be worth shadowing
  every week.
- **Hidden order dependence.** `gkm_change_log` compares rows with `canonicalize_json` when the raw bytes differ,
  so array-order drift does not show up as a change. Once outputs are deterministic (#161), that tolerance hides
  regressions instead of noise. Consider comparing raw bytes only and treating any order-only `U` as a defect.
- **Weekly wall clock.** Full mode adds minutes per release for the downstream stage, not hours.

### Decision needed

- Which procedures stay incremental. The likely shape is incremental for variation identity and vrsify, full for
  the downstream dict procedures, but that must come from the measurement.
- Whether `gkm_change_log` keeps its order-insensitive comparison.

---

## 6. Workstream 4: Input contract checks

### Problem

The pipeline trusts its upstream inputs. In 1.1.0 four input problems reached the output or nearly did:

| Input problem | Measured | Effect | Handling in ClinVar-GKM |
| --- | --- | --- | --- |
| `clinvar_ingest.entrez_gene` is missing gene ids used by `gene_association` | 64,854 ids, 230,303 variations (10-11) | 37 SCV propositions lose gene context (09-28) | none; upstream refresh requested |
| `rcv_mapping` lists SCVs absent from the VCV data | 2–3 a week; 2 in 10-11 | 4 RCV propositions with no `object` from 10-04 (#158) | #158 joins first and picks with a total order |
| Malformed HGVS in ClinVar's VCV XML (no sequence-type letter) | 16 expressions, 14 variations (10-11) | `hgvs.?` syntax failed schema validation | #145 keeps the original in an extension |
| `single_gene_variation` counts gene rows, not distinct genes | 55 haplotypes/genotypes (09-28) | 63 SCV propositions without gene context | none; upstream fix requested |

The `rcv_mapping` difference is not a bug: it is a faithful parse of ClinVar's RCV XML, which runs out of sync
with the VCV XML. Consumers must join `rcv_mapping` SCVs to the VCV-side data.

Upstream issues (tracked together in
[clingen-data-model/clinvar-gkm#164](https://github.com/clingen-data-model/clinvar-gkm/issues/164)):

- [clingen-data-model/clinvar-ingest-bq-tools#38](https://github.com/clingen-data-model/clinvar-ingest-bq-tools/issues/38):
  `single_gene_variation` counts gene rows instead of distinct genes (`COUNT` vs `COUNT DISTINCT`)
- [clingen-data-model/clinvar-ingest-bq-tools#39](https://github.com/clingen-data-model/clinvar-ingest-bq-tools/issues/39):
  `clinvar_ingest.entrez_gene` is stale; 64,854 gene ids are missing
- [clingen-data-model/clinvar-gkm#163](https://github.com/clingen-data-model/clinvar-gkm/issues/163): report to
  ClinVar (by email) of the 16 malformed HGVS expressions in the VCV XML

### Approach

One read-only procedure, `gkm_input_contract(on_date)`, that `run-release.sh` calls before the `gkm_*` stage.
Each check has a fixed action: **fail** stops the run; **log** records the rows and continues.

| Check | Action | Expected today |
| --- | --- | --- |
| Every SCV in `rcv_mapping` exists in `clinical_assertion`, or is logged | log | 2–3 a week |
| Every gene id the run uses is in `clinvar_ingest.entrez_gene` | log | 64,854 `gene_association` ids missing (10-11) until the refresh |
| Every HGVS expression has a sequence-type letter | log; fail if a form appears that #145's repair rules do not handle | 16 |
| No duplicate natural keys in the consumed input tables | fail | 0 |
| No duplicate keys in any `gkm_dict_*` / `delta_gkm_dict_*` output (after the run; the #157 scan) | fail | 0 after #157 |

Logged rows go to `clinvar_ingest.validation_issues_log`, the existing table in clinvar-ingest-bq-tools, so
upstream and ClinVar-GKM issues are in one place. A count that jumps well above its usual level should fail
rather than log; the thresholds come from the first weeks of data.

- [ ] Confirm the `validation_issues_log` schema and write access with the clinvar-ingest-bq-tools owners.
- [ ] Write `gkm_input_contract` and call it from `run-release.sh` before stage 4.
- [ ] Run it read-only on all 16 published-release datasets and record the baseline counts.

### How to measure success

- On the 16 datasets, the checks reproduce the counts above.
- A seeded violation per check (negative control) fails or logs as specified.
- Output does not change: the checks are read-only, so the oracles stay `0,0,0`.

### Risks

- A check that fails too eagerly blocks a weekly release on an upstream change that the pipeline handles. Start
  with log, promote to fail per check once the baseline is known.
- `validation_issues_log` belongs to another project. Writing to it needs that team's agreement.

### Decision needed

- Fail or log, per check (the table above is the proposal).
- Log to `clinvar_ingest.validation_issues_log` (recommended) or to a ClinVar-GKM table.

---

## 7. Workstream 5: One release gate command

### Problem

The gates exist, but as separate scripts that a maintainer runs by hand in the right order; #155 §6.4 lists
them for 1.1.0. Some of the most useful checks from the 1.1.0 work are not in the repo at all: agents
wrote them into a session scratchpad. A gate that has to be remembered gets skipped.

### Approach

`src/scripts/release-gate.sh <date> [--delta] --bundle <path> --parquet-dir <dir>` runs every check in order,
cheapest first, writes a pass/fail report with counts to the staging directory, and exits non-zero on any
failure. `release-gkm.sh` and `release-gkm-delta.sh` call it between assembly and upload, using the staging stop
(`--no-upload`) that #155 PR 4 adds, so a failure blocks publish.

1. References: `validate-proposition-conformance.sh` (bare-reference guard from #160, reference integrity from
   #155 PR 1; both exit non-zero).
2. Duplicate keys over every `gkm_dict_*` / `delta_gkm_dict_*` table.
3. Full-vs-incremental oracles: the seven `oracle-*.sh` scripts, `0,0,0` (scope set by Workstream 3).
4. `oracle-delta-reconstruction.sh`, `0,0,0`.
5. gkm-toolkit `validate_bundle_schema` with the strict registry on the **staged real bundles**, full and delta
   (`validate-schema-conformance.py`, extended).
6. Bundle ↔ Parquet recompute: per table, the id set and `data` equal the bundle section.
7. Monthly only: the published full plus its deltas reconstructs the next full.

**Scratch tools to promote.** These were written during the 1.1.0 work and are not in the repo. Each needs its
hard-coded worktree paths replaced by arguments, `bash -n` / `shellcheck` (bash 3.2), and a test or negative
control.

| Tool (scratchpad) | What it does | Promote as |
| --- | --- | --- |
| `determinism/genchain.py`, `genscript.py`, `gen_vi.py` | Turn a procedure's `EXECUTE IMMEDIATE` step bodies into a read-only CTE chain or temp-table script, so a procedure can be run against real data without writing tables | `src/scripts/tools/proc-chain.py` (dry-run harness; used by #157, #160, #161) |
| `determinism/build_cond.sh`, `build_vrcv.sh` | Two no-cache runs of a procedure chain compared by `BIT_XOR(FARM_FINGERPRINT(TO_JSON_STRING(row)))` | `oracle-determinism.sh` |
| `allele-dedup/scope.sh` | Duplicate-key scan of every `gkm_dict_*` / `delta_gkm_dict_*` table across the 16 datasets | gate check 2 |
| `allele-dedup/gen_allele_check.py` | Extracts one procedure step verbatim as a read-only `SELECT` | fold into `proc-chain.py` |
| `allele-dedup/toolkit_check.py`, `mini_bundle.py`, `validate_new.py` | gkm-toolkit validation with relaxed and strict registries, with a negative control | fold into `validate-schema-conformance.py` (gate check 5) |
| `parquet-audit/bin/stream_keys.py`, `stream_small.py` | Stream a multi-GB bundle line by line: per-section key lists, a sub-bundle of the small sections | `src/scripts/tools/bundle-stream.py` |
| `parquet-audit/bin/cmp_delta.py`, `cmp_full_small.py`, `scv_ext.py` | Compare Parquet rows and `data` with the bundle records | gate check 6 |
| `verify/bin/verify.py`, `run_schema.sh`, `stream_pick.py`; `verify/run.sh` | Run a `parquet-schemas/*.sql` file against a dataset and compare old/new output with the bundle | interim only; obsolete after Workstream 1 |
| `backfill102/verify_patch.sh` | Expected-diff of rebuilt tables against snapshots (#155 §6.4) | `oracle-expected-diff.sh` |

`parquet-audit/bin/probe.py`, `probe2.py` and `cmp_sim.py` are one-off probes and are not worth keeping.

- [ ] Promote the tools above (one PR each for the harness, the determinism check and the bundle tools).
- [ ] Write `release-gate.sh` and wire it into both release scripts before the upload step.
- [ ] Record each check's run time and bytes billed on one weekly release and one monthly full.

### How to measure success

- The gate passes on the published 1.1.0 set (4 fulls and 15 deltas).
- Each check has a negative control that makes the gate fail.
- No release script can reach the upload step without a passing gate report for the same artifacts.

### Risks

- **Cost and time.** #155 estimates the oracles and gates for the 16-dataset rebuild at about 2 TiB, about $12,
  over several hours. A weekly run is smaller, but has not been measured; the full-vs-incremental oracles are the
  expensive part.
- **Gate fatigue.** A gate that fails on known, accepted exceptions (such as the allele cross-version shift, §9.4)
  gets bypassed. Exceptions must be listed in the gate with an expiry, not skipped by hand.

### Decision needed

- Whether the full-vs-incremental oracles run on every weekly release, or only when the `gate_key` moves (a
  procedure changed). This depends on Workstream 3.
- Whether the gate report is published with the release notes.

---

## 8. Workstream 6: Artifact restraint

### Problem

Every published artifact needs building, gating, documenting and keeping. Today R2 holds, per ADR 0004:

- per monthly set: one bundle and 22 Parquet tables (21 typed, plus the raw `condition` extract);
- per weekly delta: a delta bundle, delta Parquet and the A/U/D manifest; currently 4 monthly fulls and 15
  deltas (#155 §6.4);
- aliases (`00-latest`), the `/v1/` layout plus the flat-root mirror kept for backward compatibility, the root
  manifest, `index.json` and `feed.xml`.

Planned: a family of six sorted lookup files, with a seventh on hold (#151). #155 replaces the four proposition
tables with four new ones, so the table count stays at 22.

### Approach

- **Lookup files are a thin layer over the published Parquet.** They are built only from the published Parquet
  set, with DuckDB, never from the BigQuery dict tables. Then they are recomputable from the bundle by
  construction (principle 2). The #151 prototypes are BigQuery SQL against the dict tables and would need porting.
- **Every published artifact has an entry in a checked-in registry:** path pattern, owner, what it derives from,
  its gate, its docs page, whether it ships in deltas, and its retention. A new artifact is added to the registry
  in the same PR that creates it.
- The release gate (Workstream 5) fails on any path in `index.json` that is not in the registry.
- Review the existing set for retirement candidates, starting with the flat-root mirror (ADR 0004 §4) and, if
  Workstream 1 types it, the raw `condition` extract.

- [ ] Write the registry for today's artifacts.
- [ ] Add the registry check to `release-gate.sh`.
- [ ] Port the #151 prototypes to DuckDB over the published Parquet before that work is built.

### How to measure success

- Every path in `index.json` matches a registry entry, and the gate enforces it.
- Lookup files rebuilt from the published Parquet equal the #151 prototype output on the 2026-10 set.

### Risks

- A registry nobody updates becomes another copy that drifts. The gate check is what keeps it honest.
- Building lookup files outside BigQuery needs the same local resources as Workstream 1.

### Decision needed

- Registry format and location (a YAML file next to the release scripts, or a docs page).
- Lookup files built from the published Parquet only (recommended), which means porting #151 first.
- Whether and when to retire the flat-root mirror; this is a consumer-facing change under ADR 0004.

---

## 9. Small known follow-ups found during 1.1.0

Each is small and independent of the workstreams. None changes published data today except §9.4.

### 9.1 `variation_identity.mappings` keyed by the xref id

`variation-identity-proc.sql` builds `mappings` in the `xm_ctes` CTE `x` with `x.id as variation_id` (:114,
full mode), and the incremental merge repeats it (:1054). `variation_xref` has a `variation_id` column, but the
CTE uses the xref id in its place, so `mappings` is grouped by xref id and joined to whichever variation has that
id, or to none. No downstream procedure reads it: `gkm-catvar-proc.sql` builds its own `temp_catvar_mappings`.
Fix the key, or drop the column.

### 9.2 SCV mode-of-inheritance join could duplicate keys

`gkm-scv-statement-proc.sql` Step 3 builds `temp_moi_qualifiers` with one row per SCV **per**
`ModeOfInheritance` attribute (about :441–:474) and `LEFT JOIN`s it by `scv_id` (about :540 and :686). An SCV
with two such attributes would emit two rows with the same proposition key. There are 0 such SCVs today. Pick one
attribute with a total order, or fail loudly; the duplicate-key gate (§7, check 2) would catch it either way.

### 9.3 `JSON_STRIP_NULLS` in the struct-table Parquet `data` columns

`scv.sql`, `vcv.sql`, `rcv.sql`, `variation.sql`, `evidenceLine.sql`, `vcv_evidenceLine.sql` and
`rcv_evidenceLine.sql` build `data` with `JSON_STRIP_NULLS(…, remove_empty => TRUE)`. Unlike the assembler's
`strip_empty`, it drops `{}` list elements, so a `[{}]` that the bundle keeps would become `[]` or be dropped in
Parquet. It is latent: the producing procedures emit `NULL`, not `[{}]` (`sql-procedures.md`). Workstream 1
removes it; until then, #143's `bundle_cleanup` UDF could replace it.

### 9.4 Allele cross-version SPDI shift

Documented in `docs/reference/known-issues.md`: when the VRS line advanced at 2026-08-29, some allele and SPDI
digests shifted. Keys are unchanged and every `#/allele/` reference resolves, but delta reconstruction of those
alleles across 08-22 → 08-29 is not exact; it is an accepted exception to the delta-reconstruction oracle. Decide
whether to keep it as a documented exception (listed in the gate, §7) or to recompute the affected alleles in a
future rebuild.

---

## 10. Not proposed

- **Content-shared propositions.** Deferred in #155 §3.B: about 4.7% size saving, against breaking the VCV/RCV
  carry-forward and every consumer that reads the level from the id.
- **Rewriting the procedures in another language or engine.** The defects in ADR 0007 come from duplication and
  missing checks, not from BigQuery SQL.
