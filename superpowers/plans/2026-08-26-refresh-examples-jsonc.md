# Refresh `examples/*.jsonc` to Current Bundle Output — Plan

**Goal:** Update all annotated example files under `examples/` so they match the structures the pipeline
currently produces, and validate each against the published schema. Tracked by
[issue #115](https://github.com/clingen-data-model/clinvar-gkm/issues/115).

**Why:** The examples were last updated 2026-06-12 and predate the four-section proposition refactor and the
va-spec 1.1.0 conformance work. Known drift: `classification`/`confidence`/`strength` shown in an older form
instead of `MappableConcept` structs (with `primaryCoding`); propositions shown inline instead of in the
datatype-homogeneous sections (`varcond-`/`vartumor-`/`vartherapy-`/`varcustom-proposition`) with
group-qualified `#/{group}-proposition/{id}` references; `objectCondition` now a `ConditionSet` (bare
`Condition` when single); predicate / `objectTherapy` / CustomProposition-type alignment.

**Scope (39 files):** `examples/cat-vrs` (2), `examples/scv` (6, incl. `.json`), `examples/vcv` (10),
`examples/rcv` (24, incl. the `RCV006253*-S-SCI` somatic set).

## Approach

Each example is an **annotated, self-contained** record for a specific accession/id. Regenerate the record
content from **current output** and re-apply concise annotations. Current output is authoritative — the source
is the latest bundle (`clinvar-gkm_00-latest.json.gz`) or the `gkm_dict_*` BigQuery tables for the release the
example is keyed to.

### Task 1 — Extraction helper

- [ ] Write `src/scripts/extract-example.py`: given a section + key (e.g. `vcv VCV000012582.63-G-PATH-CP`),
  pull the record from the current bundle and **resolve its `#/`-referenced nested objects** (proposition,
  condition/conditionSet, allele/location/sequenceReference, evidence lines) into a single self-contained,
  pretty-printed object — the raw material for an example.
- [ ] Verify it round-trips one known record end to end.

### Task 2 — Establish the canonical shape per statement type

- [ ] From a real current record of each kind (pathogenicity, oncogenicity, somatic clinical impact `sci`,
  therapeutic response, drug response, association, risk factor, protective, not-provided, custom), capture the
  current shape of `classification`, `strength`, `confidence` (MappableConcept), `direction`, the proposition
  section + predicate/subject/object, and the extensions. This becomes the per-type checklist.

### Task 3 — Regenerate examples, one category at a time

For **cat-vrs → scv → vcv → rcv** (simplest first):

- [ ] Regenerate each file's record content from current output via Task 1.
- [ ] Re-apply the annotations (the `// …` comments) to the refreshed structure; keep them concise and correct.
- [ ] Preserve each file's illustrative intent (the statement type / scenario the filename encodes).
- [ ] Note any example whose keyed accession no longer exists in current data and choose a current equivalent.

### Task 4 — Validate

- [ ] Validate every refreshed example against `schema/clinvar-gkm/json` under va-spec 1.1.0 (reuse the
  conformance-validation approach used elsewhere in the repo). Zero failures.
- [ ] `mkdocs build --strict` still passes (the docs link to these files but do not embed them).

### Task 5 — Close out

- [ ] Update `examples/readme.md` if the set or conventions changed.
- [ ] Reference the refreshed examples from the relevant docs pages (already linked) — confirm links resolve.
- [ ] Remove the "Outdated example files" note from `docs/reference/known-issues.md` and close issue #115.

## Notes

- The upcoming VCV/RCV aggregate extensions (`reviewStarRating`, `aggregateSignificance`,
  `significanceBreakdown` — spec at `docs/superpowers/specs/2026-08-26-vcv-rcv-clinsig-star-extensions-design.md`)
  are **not yet in output**; regenerate against what is actually published, and refresh the VCV/RCV examples
  again once that work ships.
- Do the regeneration against a **single, fixed release** so all examples are internally consistent.
