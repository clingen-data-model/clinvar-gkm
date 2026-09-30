# Therapy dictionary + `#/therapy/` references — Phase-2 Plan

> **For agentic workers:** REQUIRED: use superpowers:subagent-driven-development or
> superpowers:executing-plans to implement. Steps use checkbox (`- [ ]`) tracking.
> **Status: DEFERRED / not started.** Blocked on the upstream va-spec dependency (Task 0).

**Goal:** Stop re-embedding therapy values in `vartherapy-proposition` objects. Introduce a
deduplicated `therapy` bundle section and have therapeutic-response propositions reference
`#/therapy/{id}` (single therapy) and `TherapyGroup.concepts` reference `#/therapy/{id}` (combination),
mirroring how `conditionSet.concepts` already references `#/condition/`.

**Architecture:** Add one global dedup dictionary (`gkm_dict_therapy`) built alongside the existing
condition dicts, plus a new bundle section. The `vartherapy` proposition proc changes from embedding a
`Therapy` MappableConcept / `TherapyGroup` ConceptSet to emitting iriReferences into the new section.
Everything else (delta model, parquet, docs, validators) extends the existing conditionSet pattern.

**Tech stack:** BigQuery stored procedures (`src/procedures/gkm-scv-statement-proc.sql`, and the
condition proc `gkm-scv-condition-proc.sql` as the template for a global dedup dict), the export/bundle
scripts (`src/scripts/export-gkm-dicts.sh`, `parquet-schemas/`), the delta procs
(`gkm-change-log-proc.sql`, `gkm-delta-proc.sql`, `oracle-delta-reconstruction.sh`,
`build-delta-manifest.py`), and the docs.

---

## Why this is Phase-2 (context)

As of 2026-09-30, **conditions are already reference-based** — `gkm_dict_condition_set.concepts` emits
`#/condition/clinvar.trait:{id}` and proposition `object` uses `#/condition/`//`#/conditionSet/`.
**Therapies are still embedded**: `gkm-scv-statement-proc.sql` (~line 578-617) builds a `therapy`
struct (MappableConcept) or a `TherapyGroup` (ConceptSet, ≥2 members) **inline** in the vartherapy
proposition object; there is **no `therapy` bundle section**. See
[[project_conceptset_irirefs]] for the full analysis.

The upstream va-spec base `ConceptSet.concepts` now allows `iriReference` (gkm-core `e6e5c1a`), and the
`ConditionSet`/`TherapyGroup` subtype relaxation is prepared (see Task 0). Once that lands, `TherapyGroup`
may hold `#/therapy/` references — the schema precondition for this plan.

---

## Task 0: Upstream dependency (BLOCKER)

- [ ] va-spec `TherapyGroup.concepts` must permit `iriReference` (prepared 2026-09-30 in
  `submodules/va-spec/schema/va-spec/domain-entities-source.yaml`: `oneOf` += `$refCurie:
  gkm.core:iriReference`; regenerated json verified, `LostIriReferenceWarning` cleared). Land the
  upstream va-spec PR, then bump the clinvar-gkm `submodules/va-spec` gitlink to include it.
- [ ] Confirm the generated va-spec `TherapyGroup` in the bumped submodule contains `iriReference`.

## Task 1: Decide therapy identity / dedup key

- [ ] A `Therapy` is a MappableConcept (name + optional primaryCoding + mappings). Unlike conditions
  (which have a stable `clinvar.trait:{id}`), ClinVar drug therapies have **no native id**. Choose a
  dedup key: **recommended** = content digest over the canonical therapy JSON (name + coding + mappings),
  keyed `clinvar.therapy:{digest}` — same digest approach VRS/content-addressing uses. Document the
  canonicalization (drop `id`, sort keys — BQ JSON sorts keys; `SHA256(TO_JSON_STRING(...))`).
- [ ] Define the id namespace/prefix (`clinvar.therapy:`) and add it to the identifier table in
  `docs/output-reference/id-references.md`.

## Task 2: Build `gkm_dict_therapy` (global dedup dict)

- [ ] In `gkm-scv-statement-proc.sql`, extract the per-SCV therapy MappableConcept(s) into a GLOBAL
  temp (like `temp_all_rcv_traits` / the condition dicts), dedup by the Task-1 key, and write
  `gkm_dict_therapy` (key = `clinvar.therapy:{digest}`, value = the Therapy MappableConcept). Global
  recompute every release (like `gkm_dict_condition` / `gkm_dict_submitter`) — never carried forward.
- [ ] Follow the incremental rules in the proc header: keep the feeding temps GLOBAL/unfiltered so the
  dedup dict sees therapies on unchanged SCVs too.

## Task 3: Emit references in the vartherapy proposition object

- [ ] Change the object construction (~line 578-617): single therapy → `#/therapy/{digest}`; combination
  → `TherapyGroup` whose `concepts` is an array of `#/therapy/{digest}` iriReferences (+ `membershipOperator`).
  Proposition `object` already permits `iriReference` (clinvar-proposition-source.yaml), so a single
  therapy can also be a bare `#/therapy/` ref.
- [ ] Verify the C3 incremental-merge column lists still line up (the EL/proposition merges enumerate columns).

## Task 4: Bundle assembly + parquet

- [ ] Add a `therapy` section to `export-gkm-dicts.sh` (extract `gkm_dict_therapy` → `therapy.ndjson.gz`)
  in the fixed section order (near `condition`/`conditionSet`); it is a key/value section.
- [ ] Add `parquet-schemas/therapy.sql` + wire `extract_parquet_typed therapy.parquet therapy.sql`.
- [ ] Update the section count in `docs/pipeline/export.md` (18 → 19) and the assembly order list.

## Task 5: Delta / change-log / oracle

- [ ] Track `gkm_dict_therapy` in `gkm-change-log-proc.sql` + `gkm-delta-proc.sql`.
- [ ] Add `"gkm_dict_therapy key"` to the `PAIRS` in `oracle-delta-reconstruction.sh`.
- [ ] Update `build-delta-manifest.py` to resolve therapy keys to the `therapy` section.

## Task 6: Docs + diagram + validators

- [ ] `docs/output-reference/id-references.md`: add `#/therapy/` reference pattern + the
  `vartherapy-proposition.object → #/therapy/` and `TherapyGroup.concepts → #/therapy/` rows.
- [ ] `docs/assets/diagrams/bundle-section-map.html`: add the `therapy` drawer + update vartherapy's
  `object` ref from `therapy (inline)` to `#/therapy/`.
- [ ] `docs/output-reference/classes/index.md` Supporting-classes table + data guide.
- [ ] Extend `validate-schema-conformance.py` (or a section validator) to cover the `therapy`,
  `therapyGroup`, and `conditionSet` sections (currently only propositions/statements/evidence lines
  are validated) — so reference-vs-embed compliance is actually checked going forward.

## Task 7: Vet

- [ ] Full-vs-incremental oracle + delta-reconstruction `0,0,0` (expect a one-time churn: every
  vartherapy proposition rewrites its object from inline therapy to `#/therapy/` refs, and new `therapy`
  section rows appear). Document the expected churn for consumers.

---

## Risks / open questions

- **Therapy identity churn:** a content digest changes if any therapy field (name/coding/mappings)
  changes — acceptable (same as VRS), but means the therapy dict is not stable across upstream ClinVar
  wording changes. Alternative: key on primaryCoding only (drops name-only therapies). Decide in Task 1.
- **Single vs group object shape:** confirm whether a single-therapy proposition object should be a bare
  `#/therapy/` ref or always a TherapyGroup of one — match the existing condition pattern (single =
  bare `#/condition/` ref; multi = `#/conditionSet/` ref).
- **Backward compatibility:** consumers currently read inline therapy; this is a breaking delivery change
  (a full vartherapy rewrite) — coordinate with the release/delta messaging.
