# submittedCondition/Set CURIE De-pointer — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or
> superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In the `submittedCondition` / `submittedConditionSet` SCV extensions, change the four string fields
`condition`, `conditionSet`, `normalized_match`, `direct_match` from JSON pointers (`#/condition/clinvar.trait:NNN`)
to bare CURIEs (`clinvar.trait:NNN`) — a **content-only** change (no field/type/shape change, no schema version
bump) — while keeping `proposition.object` and all downstream condition linkage byte-identical.

**Architecture:** Strip the `#/…` prefix at the **producer** (`gkm-scv-condition-proc.sql`), then **re-wrap** the
CURIE back into a pointer at the three downstream sites that consume these fields as `proposition.object` /
condition references (`gkm-scv-statement-proc.sql` ×2, `gkm-rcv-statement-proc.sql` ×1). Update the schema-source
field descriptions in lockstep, regenerate `json/` + bundle + docs, then oracle-gate a full rebuild and
re-extract the examples.

**Tech Stack:** BigQuery dynamic SQL stored procedures (bash 3.2 orchestration), ga4gh.gkm metaschema
(`make` / `y2md`), Zensical docs, `extract-example.py`.

**Scope note:** This plan is Part A only (the de-pointer). The versioning-policy *infrastructure* (root
manifest, `/v1/` mirror, bundle-level `schema_version` field, RSS/Atom feed, Home-page indicator, release-notes
generation — per ADR 0004) is **separate follow-on work**, not built here. `schema_version` could ride this
same rebuild if desired (see Task 7 note), but is not required for the de-pointer.

**Oracle invariant (gate):** every BQ-touching change must be byte-identical full-vs-incremental and
delta-reconstructable. `oracle-scv-condition.sh`, `oracle-scv-statement.sh`, `oracle-rcv-statement.sh`, and
`oracle-delta-reconstruction.sh` must all report **0,0,0** before anything publishes. Nothing in this plan
touches live R2.

---

## File structure

- `src/procedures/gkm-scv-condition-proc.sql` — **producer**: STEP 10 builds the extension; strip prefixes here.
- `src/procedures/gkm-scv-statement-proc.sql` — **consumer** ×2: `obj_ref` (≈524–529) and the somatic
  `object`/`conditionQualifier` COALESCE (≈662–677); re-wrap CURIE→pointer. The condition-name join (≈729–733)
  needs no change (its `REPLACE('#/condition/','')` degrades to a no-op on bare CURIEs).
- `src/procedures/gkm-rcv-statement-proc.sql` — **consumer** ×1: `condition_concept` COALESCE (≈202–207); re-wrap.
- `schema/clinvar-gkm/clinvar-statement-source.yaml` — **schema source**: 5 description edits (4 pointer→CURIE +
  1 "Always null" nit). Regenerate `json/`, `def/`, bundle, and the `SubmittedConditionMapping` doc page.
- `examples/scv/**`, `examples/vcv/**`, `examples/rcv/**` — re-extracted from the rebuilt data.

---

## Chunk 1: Producer de-pointer + consumer re-wrap (audit-first)

### Task 1: Audit every consumer of the four fields

- [ ] **Step 1: Enumerate all read sites** so none is missed.

Run:
```bash
grep -rn "value_submitted_condition\(_set\)\?\.\(condition\|conditionSet\|normalized_match\|direct_match\)" src/procedures/
```
Expected hits to classify: `gkm-scv-statement-proc.sql` (obj_ref ~524, somatic object/conditionQualifier ~662,
condition-name join ~729), `gkm-rcv-statement-proc.sql` (~202). Classify each as **re-wrap** (used as a `#/…`
pointer) vs **safe** (strips the prefix, or reads `.name`/existence only — e.g. `gkm-rcv-proc.sql` names,
`gkm-vcv-proc.sql` existence, and the homogeneous STRUCT rebuilds at scv-statement ~998/~1130 which only pass the
whole struct through). Record the final re-wrap list before editing.

### Task 2: Producer — strip the prefixes

**File:** `src/procedures/gkm-scv-condition-proc.sql` (STEP 10 `base_conditions`, ≈1030–1056)

- [ ] **Step 1: Edit the four expressions.**

```sql
-- conditionSet: ts.id is already `clinvar.traitset:NNN` — drop the FORMAT wrapper
IF(scm.rcv_trait_count > 1, ts.id, NULL) AS conditionSet,
-- condition: strip the #/condition/ prefix off the first concept (robust no-op if already bare)
IF(scm.rcv_trait_count = 1, REGEXP_REPLACE(ts.concepts[SAFE_OFFSET(0)], r'^#/condition/', ''), NULL) AS condition,
...
-- direct_match / normalized_match: emit the bare CURIE
IF(scm.mapped_trait_id IS DISTINCT FROM scm.normalized_trait_id,
   FORMAT('clinvar.trait:%s', scm.mapped_trait_id), NULL) AS direct_match,
FORMAT('clinvar.trait:%s', scm.normalized_trait_id) AS normalized_match,
```

- [ ] **Step 2: `bash -n`-equivalent sanity** — grep the file to confirm no `#/condition/` / `#/conditionSet/`
  literal remains in STEP 10 (`grep -n "#/condition" src/procedures/gkm-scv-condition-proc.sql`).

### Task 3: Consumers — re-wrap CURIE → pointer (preserve output)

For each re-wrap site, replace the bare 4-field `COALESCE(...)` with per-field pointer reconstruction so the
emitted `proposition.object` / condition reference is **unchanged**:

```sql
COALESCE(
  IF(scs.extensions.value_submitted_condition.condition        IS NOT NULL, '#/condition/'    || scs.extensions.value_submitted_condition.condition,        NULL),
  IF(scs.extensions.value_submitted_condition.conditionSet     IS NOT NULL, '#/conditionSet/' || scs.extensions.value_submitted_condition.conditionSet,     NULL),
  IF(scs.extensions.value_submitted_condition_set.condition    IS NOT NULL, '#/condition/'    || scs.extensions.value_submitted_condition_set.condition,    NULL),
  IF(scs.extensions.value_submitted_condition_set.conditionSet IS NOT NULL, '#/conditionSet/' || scs.extensions.value_submitted_condition_set.conditionSet, NULL)
)
```

- [ ] **Step 1:** `gkm-scv-statement-proc.sql` ≈524–529 — `obj_ref`.
- [ ] **Step 2:** `gkm-scv-statement-proc.sql` ≈662–667 (inside `TO_JSON(...)` for `object`) **and** ≈671–676
  (for `conditionQualifier`) — both COALESCEs.
- [ ] **Step 3:** `gkm-rcv-statement-proc.sql` ≈202–207 — `condition_concept`.
- [ ] **Step 4:** Leave the condition-name join (`gkm-scv-statement-proc.sql` ≈729–733) as-is; add a one-line
  comment that the `REPLACE('#/condition/','')` is now a defensive no-op on bare CURIEs.

---

## Chunk 2: Schema source + regenerate (lockstep)

### Task 4: Update the 5 field descriptions

**File:** `schema/clinvar-gkm/clinvar-statement-source.yaml`

- [ ] **Step 1:** `SubmittedConditionMapping.direct_match` (≈194–196) — "JSON pointer reference to the directly
  matched condition (e.g., `#/condition/clinvar.trait:123`)…" → "The CURIE of the directly matched condition
  (e.g., `clinvar.trait:123`; the key of the corresponding `#/condition/` bundle entry). Present only when the
  direct match differs from the normalized match."
- [ ] **Step 2:** `SubmittedConditionMapping.normalized_match` (≈200–201) → CURIE wording (`clinvar.trait:456`).
- [ ] **Step 3:** `ExtensionSubmittedCondition.value.condition` (≈244–245) → CURIE wording (`clinvar.trait:123`).
- [ ] **Step 4:** `ExtensionSubmittedConditionSet.value.conditionSet` (≈276–277) → CURIE wording
  (`clinvar.traitset:123`).
- [ ] **Step 5 (nit):** `ExtensionSubmittedCondition.value.conditionSet` (≈248) — replace "Always null for
  single-condition submissions…" with: "Usually null for single-condition submissions; when a single-trait
  submission maps to a multi-trait RCV it holds the CURIE of that condition set (e.g., `clinvar.traitset:123`)."

### Task 5: Regenerate artifacts + docs

- [ ] **Step 1:** `cd schema/clinvar-gkm && make` — regenerates `json/`, `def/`, `clinvar-gkm-bundle.schema.json`.
  Confirm **no `$id` version change** (content-only): `git diff --stat schema/clinvar-gkm/json | head`; the only
  diffs should be descriptions.
- [ ] **Step 2:** `make docs` — regenerates `output-reference/classes/*.md`. Confirm
  `output-reference/classes/SubmittedConditionMapping.md` now says CURIE.
- [ ] **Step 3:** `zensical build --strict` — expect "No issues found".
- [ ] **Step 4:** Commit Chunks 1–2 together (proc + schema + regenerated artifacts move in lockstep).

---

## Chunk 3: Deploy, rebuild, oracle-gate

### Task 6: Deploy the changed procedures

- [ ] **Step 1:** Redeploy the three edited procs to the working BQ project (follow the existing deploy path used
  for proc changes; confirm exact command before running). No release/publish yet.

### Task 7: Full rebuild + oracle gates (0,0,0)

- [ ] **Step 1:** Rebuild a debug/test dataset for a recent release date against the redeployed procs (do **not**
  publish; do **not** touch R2). Confirm the exact rebuild entrypoint/flags before running (per the
  `project_pipeline_vetting_paused` oracle-first pattern: redeploy → rebuild baseline → run SCV oracle → expand).
- [ ] **Step 2:** Run the targeted oracle first — `src/scripts/oracle-scv-condition.sh` — expect **0,0,0**.
- [ ] **Step 3:** Run `oracle-scv-statement.sh`, `oracle-rcv-statement.sh` — expect **0,0,0** (proves the
  re-wrapped `proposition.object` / condition linkage is byte-identical).
- [ ] **Step 4:** Run `oracle-delta-reconstruction.sh <baseline> <compare> <version>` — expect "all sections
  0,0,0".
- [ ] **Step 5:** If any oracle is non-zero, stop and diagnose (most likely a missed/incorrect re-wrap site) —
  do not proceed.

> **Note (optional, same rebuild):** if we decide to also land the accepted bundle-level `schema_version` field
> now, it is added at bundle assembly + a schema-source edit (additive) and can ride this rebuild. Otherwise it
> stays in the separate policy-infrastructure plan.

---

## Chunk 4: Re-extract examples, validate, document, PR

### Task 8: Re-extract the examples from rebuilt data

- [ ] **Step 1:** Re-run `extract-example.py` for the scv/vcv/rcv examples against the rebuilt dataset; confirm
  the `submittedCondition` fields now show bare CURIEs and `proposition.object` is still a `#/…` pointer.
- [ ] **Step 2:** QC sweep (0 `value_*`, 0 nulls, 0 empty arrays) and confirm the condition-bloat drop.

### Task 9: Validate + document + land

- [ ] **Step 1:** Validate all examples against `schema/clinvar-gkm/json` under va-spec 1.1.0 (plan #115 gate).
- [ ] **Step 2:** `zensical build --strict`.
- [ ] **Step 3:** Update `examples/readme.md`; remove the "Outdated example files" note from
  `docs/reference/known-issues.md`.
- [ ] **Step 4:** Add a release-note entry describing the content-only CURIE change (per ADR 0004 §6) for the
  next release.
- [ ] **Step 5:** Open the PR (target branch TBD with maintainer — see below); reference #115.

---

## Open items to confirm before execution

1. **Target branch** — the de-pointer touches procs + schema + docs + examples. Its own branch off `main` (dev)
   vs. `1.0` (release line)? (The in-flight examples work sits on `chore/refresh-examples-jsonc`.)
2. **Exact deploy + rebuild commands/dataset** — confirm the proc-deploy path and the debug-rebuild entrypoint.
3. **`schema_version` field** — ride this rebuild, or defer to the policy-infrastructure plan?
