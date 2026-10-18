# Strict-Mode Schema Validation (B1) Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or
> superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `validate-schema-conformance.py --no-relax` pass on real published data, so strict validation can
gate releases. Separate the generator/schema defects from genuine data defects. Only the data defects change
published data, so only they bear on the consolidated rebuild and backfill.

**Parent plan:** B1 in `2026-10-16-parquet-followups.md`. That plan assumed the fix belongs in gkm-metaschema.
The investigation below shows a clinvar-gkm source fix is enough, needs no generator release, and was verified
end to end.

**Answer to the backfill question:** the strict-mode failures are schema defects, not data defects, and fixing
them changes no published data. Checking real data turned up **one genuine data defect**: malformed citation
`Document`s on up to 3,872 SCVs in the 2026-10 full (Task 5). It fails **default (relaxed) validation too**,
so it was never a strict-only problem. It went unnoticed because only deltas were validated, and none of the
affected SCVs are in the 2026-10-11 delta. Fixing it changes published `scv` records, so it has to be decided
before the rebuild.

---

## Findings

All numbers come from the schema state of `fix/hgvs-invalid-expressions` (#142's 1.0.2 schemas plus the A1
`HgvsListItem` change), validated per section against `clinvar-gkm-bundle.schema.json`
`properties[section]`, with the registry from `load_registry`.

### Baseline: strict mode on the 2026-10-11 delta

| Section | Records | Strict failures | Reported error |
| --- | ---: | ---: | --- |
| `variation` | 15,758 | 15,758 | `Unevaluated properties are not allowed ('constraints', 'extensions', 'id', …)` |
| `varcustom-proposition` | 40 | 40 | `anyOf` (no branch valid) |
| `scv` | 11,647 | 11,647 | `Additional properties are not allowed ('classification', 'contributions', 'id', 'type', …)` |
| `vcv` | 18,797 | 18,797 | `Additional properties are not allowed ('classification', 'direction', 'id', …)` |
| `rcv` | 24,926 | 24,926 | same as `vcv` |
| the other 10 sections | 102,033 | 0 | |

### Root cause 1: closed `*Properties` mixins inside `allOf` (all five sections)

Each ClinVar profile is composed as `allOf: [<upstream base>, <ClinVar mixin>]`, with
`unevaluatedProperties: false` on the outer class. The outer closure is correct. The problem is the mixin.

```json
"ClinvarScvStatement": {
  "allOf": [
    { "$ref": "/ga4gh/schema/va-spec/1.1.0/json/Statement" },
    { "$ref": "#/$defs/ClinvarScvStatementProperties" }
  ],
  "unevaluatedProperties": false
},
"ClinvarScvStatementProperties": {
  "properties": { "proposition": …, "hasEvidenceLines": …, "extensions": … },
  "additionalProperties": false
}
```

`additionalProperties` only sees its own schema's `properties`. So the mixin rejects every property that the
base `Statement` supplies: `id`, `type`, `classification`, and the rest. Every SCV/VCV/RCV statement fails on
that branch. The variant and custom-proposition profiles fail the same way.

There are nine such mixins, all `protectedClassOf` `$defs`:

| Mixin | Schema |
| --- | --- |
| `ClinvarScvStatementProperties` | `ClinvarScvStatement` |
| `ClinvarAggregateStatementProperties` | `ClinvarAggregateStatement` (used by VCV and RCV) |
| `ClinvarGermlineCustomPropositionProperties` | `ClinvarGermlineCustomProposition` |
| `ClinvarSomaticEvidenceLineProperties` | `ClinvarSomaticEvidenceLine` |
| `ClinvarCategoricalVariantProperties`, `ClinvarCanonicalAlleleProperties`, `ClinvarAlleleProperties`, `ClinvarSequenceLocationProperties`, `ClinvarSequenceReferenceProperties` | `ClinvarCategoricalVariant` |

**Why the generator emits `false`:** the source YAML declares `additionalProperties: true` on 8 of the 9
mixins (`ClinvarGermlineCustomPropositionProperties` declares nothing). But gkm-metaschema
`source_proc.py` (lines ~906–913) overwrites it unconditionally: every **non-abstract** class in a `strict`
source gets `additionalProperties: false`, or `unevaluatedProperties: false` if it is composed. The authored
`true` is silently discarded. The same code leaves abstract classes open on purpose. Its comment notes that
even `additionalProperties: true` would be wrong on a mixin, because it marks every property as evaluated
and so disables the outer `unevaluatedProperties: false`.

**Minimal reproduction** (pure JSON Schema 2020-12, no project schemas):

```python
base  = {"$id": "urn:Base",  "type": "object", "additionalProperties": False,
         "properties": {"id": {"type": "string"}, "type": {"type": "string"}, "extensions": {"type": "array"}}}
mixin = {"$id": "urn:Mixin", "type": "object", "additionalProperties": False,      # <- the defect
         "properties": {"extensions": {"type": "array", "maxItems": 3}}}
profile = {"allOf": [{"$ref": "urn:Base"}, {"$ref": "urn:Mixin"}], "unevaluatedProperties": False}
# {"id": "x", "type": "Statement", "extensions": []}
#   -> "Additional properties are not allowed ('id', 'type' were unexpected)"
# Drop the mixin's additionalProperties: valid, and {"bogus": 1} is still rejected by the outer
# unevaluatedProperties.
```

### Root cause 2: `GeneListItem` describes an older record shape (`variation` only)

With root cause 1 fixed, the statement and proposition sections pass, but 15,756 of 15,758 variants still
fail. The reported error is misleading: `ClinvarCategoricalVariant` is a `oneOf` with
`unevaluatedProperties: false`. When every branch fails, no property counts as evaluated, so the outer error
lists every field. Testing one branch at a time narrows it to the `clinvarGeneList` extension.

| | Shape |
| --- | --- |
| Data, every gene-list item | `{"gene": "#/gene/ncbigene:242", "relationship_type": …, "source": …}` |
| `GeneListItem` schema | `entrez_gene_id`, `hgnc_id`, `symbol`, `relationship_type`, `source`, `iris`, plus `additionalProperties: false`. There is **no `gene`**. |

The data is the intended form. Gene details moved to the `gene` section, and the docs already describe the
`#/gene/` pointer (`output-reference/cat-vrs.md`, `id-references.md`). The schema was never updated, and relaxed
mode hid that by stripping `additionalProperties`. Across the 2026-10 monthly full, all **7,346,154** gene-list
items have `gene`, `relationship_type` and `source`. None is missing one, and none has a `gene` that isn't
a `#/gene/ncbigene:` pointer. This is a **schema defect**, not a data defect.

### Latent limitation: a closed upstream parent can't be extended

If a mixin adds a property its upstream base doesn't declare, the closed base rejects it. Only one case
exists: `ClinvarCanonicalAlleleProperties.definingContext`. cat-vrs `CanonicalAllele`
(`unevaluatedProperties: false`) over `CategoricalVariant` (`additionalProperties: false`) has no
`definingContext`. No record uses it (0 of 4,647,675 variants in 2026-10, and no procedure emits it), so it
causes no failures today. It would fail strict validation the first time it was populated.

### Prototype: corrected composition on real data

Neither gkm-metaschema nor any committed schema was changed. Two prototypes were run:

- **Programmatic transform:** strip the closure from every `allOf`-branch target, and point composed
  references at open copies of the upstream bases.
- **Source fix (the recommendation):** in a scratch copy of the four `*-source.yaml` files, mark the nine mixins
  `abstract: true`, remove their `additionalProperties: true`, and update `GeneListItem`. Then regenerate with
  the installed generator (`make -C schema/clinvar-gkm`) and validate with the **unmodified**
  `validate-schema-conformance.py` registry in strict mode (`relax=False`).

The two prototypes gave identical results. Opening only the mixins is enough: no upstream base has to be
opened, because no record uses a property its base lacks (see the latent limitation above).

| Data | Records | Strict, as published | Root cause 1 fixed | + `GeneListItem` fixed | Relaxed (today's default) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2026-10-11 delta, all 15 sections | 174,201 | 71,168 | 15,756 (`variation` only) | **0** | 0 |
| 2026-10 monthly-full sample (Parquet `data` column) | 35,464 | not run | not run | **4** | **4** (the same 4) |

The monthly-full sample came from the 2026-10 Parquet `data` columns: about 5,000 random rows per large
table plus stratified rows, covering every VCV/RCV id-suffix class (G/S, PATH/SCI/ONCO/…,
CP/NOCP/EP/PG/FLAG/Tn) and every SCV proposition type × guideline system × has-evidence-lines combination.

| Table | Sampled |
| --- | ---: |
| `scv` | 5,920 |
| `vcv` | 7,062 |
| `rcv` | 7,134 |
| `variation` | 5,600 |
| `varcond-proposition` | 2,634 |
| `varcustom-proposition` | 2,546 |
| evidence lines (all of `evidenceLine` plus samples of `vcv_`/`rcv_evidenceLine`) | 4,568 |

Negative checks under the source fix still behave as expected. A bogus top-level property is rejected in
`scv`, `vcv`, `rcv`, `variation`, `varcustom-proposition` and `evidenceLine`. A bogus key inside an SCV
extension is rejected. A gene-list item with a stale `symbol`, or with no `gene`, is rejected.

The regenerated JSON differs from the committed JSON by exactly 9 × (`additionalProperties: false` removed,
`abstract: true` added) plus the `GeneListItem` change. `y2md` class pages are unchanged.

### Remaining failures: classification

| Failure | Count | Class |
| --- | --- | --- |
| SCV `specifiedBy.reportedIn.doi` not a DOI | 3 in the sample; **3,808 SCVs** in the 2026-10 full | **Real data defect** (Task 5) |
| SCV `reportedIn[].doi` not a DOI | **62 SCVs** in the full | **Real data defect** (Task 5) |
| SCV `reportedIn[].urls[]` not a URL (`PMID:18563784`) | 1 in the sample; **2 SCVs** in the full | **Real data defect** (Task 5) |
| `definingContext` rejected by a closed upstream parent | 0 records | Known upstream limitation, latent (Task 3) |
| Misleading top-level `unevaluatedProperties` error when a `oneOf`/`allOf` branch fails | reporting only | Validator usability (Task 4) |

Bad DOI values in the full, from `SELECT … FROM scv.parquet`:

| Field | Values |
| --- | --- |
| `specifiedBy.reportedIn.doi` | `https` ×3,746, `doi.org/10.1002/humu.23630` ×52, then `doi:10.…`, `https://doi.org/10.…`, `DOI: 10.…`, a bare PMID (`25741868`), a PMC id (`PMC8832287`) |
| `reportedIn[].doi` | `doi:10.…`, `doi.org/10.…`, `https`, `doi/10.…`, `http://dx.doi.org/10.…`, `org/10.…`, `doi`, values with a trailing `.` |

The va-spec `Document` requires `doi` to match `^10.(\d+)(\.\d+)*/[\w\-\.]+` and `urls[]` to match
`^(https?|s?ftp)://`. The `"https"` DOI also produces the meaningless URL `https://doi.org/https`.

**Origin:** `gkm-scv-statement-proc.sql` Step 7b (`temp_scv_citations`, which feeds `reportedIn`) and Step 7c
(`temp_scv_method`, which feeds `specifiedBy.reportedIn`) copy ClinVar's citation `cid.id` into `doi` verbatim.
Their `ELSE` branch also puts `cid.curie` (7b) or `source:id` (7c) into `urls`, even when the value isn't a
URL.

---

## Recommendation: where the fix goes

| Option | Verdict |
| --- | --- |
| **A. clinvar-gkm source YAML:** mark the 9 mixins `abstract: true` and drop their `additionalProperties: true`; fix `GeneListItem` | **Recommended.** Verified end to end with the installed generator. It uses the generator's own documented rule (abstract classes are left open, concrete ones closed), so no metaschema release is needed. It also matches how va-spec composes its own profiles. |
| B. gkm-metaschema generator: honor or reject an authored class-level `additionalProperties`, and leave `protectedClassOf` mixins open | Worth doing upstream, but not blocking. File an issue: the silent overwrite of an authored `true` is a trap for every profile author. |
| C. clinvar-gkm post-processing step after `make` | Rejected. It is a second, hidden schema source, and the published JSON would still differ from what the YAML says. |
| D. Validator-only (today's `relax`) | Rejected as the fix. The published schemas are what consumers and the GA4GH gkm-toolkit validate against, so they must be correct as published. |

**Deterministic output (deferred):** `json.dump(..., sort_keys=False)` at `source_proc.py:482` lets `$defs`
come out in set order. The scratch regeneration reordered `$defs` in three files (`ClinvarAggregateStatement`,
`ClinvarCategoricalVariant`, `ClinvarScvStatement`) with no change in content. Switching to `sort_keys=True`
belongs in gkm-metaschema and stays deferred. It would also reorder `properties` in every emitted file, so it
should land as its own one-time-churn regeneration. Until then, follow the existing rule in `scripts.md`: revert
files whose JSON is semantically unchanged, and keep only the real diff.

---

## Task 1: Open the nine `*Properties` mixins (schema only)

**Files:** `schema/clinvar-gkm/clinvar-{statement,variant,proposition,evidence}-source.yaml`, regenerated
`schema/clinvar-gkm/json/*`. **Base:** `1.0`. If `1.0.2` isn't tagged yet, fold this into the same release
as #142 (as with B2/A3); otherwise it's a PATCH.

- [ ] In each of the nine mixins listed under root cause 1, add `abstract: true` and delete the class-level
  `additionalProperties: true` where present. Keep the property-level `additionalProperties` on nested objects,
  such as `ExtensionSubmittedCondition.value` and `SubmittedConditionMapping`.
- [ ] Run `make -C schema/clinvar-gkm`. Revert files that only reorder, by checking semantic equality with
  `json.load(a) == json.load(b)`.
- [ ] Confirm the semantic diff is exactly 9 × (`additionalProperties: false` → absent, `abstract: true`
  added).
- [ ] Do the version bump per `scripts.md` if this isn't riding in 1.0.2.

## Task 2: Make `GeneListItem` match the published shape (schema only)

- [ ] In `clinvar-variant-source.yaml`, replace `entrez_gene_id`, `hgnc_id`, `symbol` and `iris` with
  `gene: {$refCurie: gkm.core:iriReference}`, described as the `#/gene/` pointer. Keep `relationship_type`
  (enum) and `source`. Add `required: [gene, relationship_type, source]`; all 7,346,154 items in 2026-10 have
  all three. Rewrite the class description to match.
- [ ] Regenerate. Check that the regenerated `GeneListItem` class page and `output-reference/cat-vrs.md`
  `### GeneListItem` agree. That docs change goes in the paired `main` docs PR.

## Task 3: Decide on `ClinvarCanonicalAlleleProperties.definingContext`

- [ ] **Decision:** drop `definingContext` from the profile (recommended: it can never pass strict validation
  under cat-vrs 1.1.1's closed `CanonicalAllele`, and nothing emits it), or keep it and raise an upstream cat-vrs
  issue. Either way this changes no data.

## Task 4: Make strict validation usable and the default

**File:** `src/scripts/validate-schema-conformance.py`.

- [ ] Flip the default to strict, with a `--relax` opt-in kept for debugging. Rewrite the
  `relax_additional_properties` docstring: the old explanation ("the metaschema stamps it at every level") is
  superseded by root cause 1.
- [ ] When reporting a failure, drop `unevaluatedProperties` errors whenever the record also has any other
  error. When a branch fails, those errors only echo it and list every field; this is what made the
  `variation` failures unreadable.
- [ ] Optional: add a `--bundle` mode that validates each section of a bundle file against
  `clinvar-gkm-bundle.schema.json` `properties[section]`. Today that loop lives only in ad-hoc scratch
  scripts.

## Task 5: Fix malformed SCV citation `Document`s (data, changes published `scv`)

**File:** `src/procedures/gkm-scv-statement-proc.sql`, Steps 7b and 7c.

- [ ] **Investigate (read-only BigQuery):** find the raw ClinVar citation `source`/`id`/`url` behind the
  `"https"` DOIs (3,746 rows) and the `PMID:` URLs. Establish whether the bad value is in the ClinVar XML or
  comes from upstream clinvar-ingest parsing. If it is upstream, open an issue there as well.
- [ ] **DOI:** set `doi` to `REGEXP_EXTRACT(cid.id, r'(10\.\d+(?:\.\d+)*/[^\s]+?)\.?$')`. That strips the
  `https://doi.org/`, `doi.org/`, `dx.doi.org/`, `doi:` and `DOI:` (with its trailing space) prefixes and a trailing period. It is NULL
  when no DOI is present (`https`, `doi`, a PMID or PMC id). Build the `https://doi.org/%s` URL only from the
  normalized DOI.
- [ ] **URLs:** emit a `urls` entry only when it matches `^(https?|s?ftp)://`. Route PubMed-style sources
  (`PMID`, and others that turn up in the investigation) to `pmid` and a PubMed URL, rather than through the
  `ELSE` curie branch.
- [ ] **Empty documents:** if a citation `Document` ends up with no `pmid`, `doi` or `urls`, drop it. In 7c,
  set `specifiedBy.reportedIn` to NULL.
- [ ] **Determinism:** keep both steps byte-identical between full and incremental runs. They are computed
  globally and LEFT-JOINed into `gkm_dict_scv`, so the carry-forward invariant isn't at risk.
- [ ] **Data impact:** `gkm_dict_scv` is a **per-SCV carry-forward** output. An incremental run only recomputes
  changed SCVs, so the fix reaches the up-to-3,872 unchanged SCVs only if the SCV step runs in **full mode once**
  in the forward rebuild (the same pattern as A1's variant step). Expect the full-vs-incremental oracle to pass
  only after that full run, and the first delta afterwards to carry those SCVs as changes.

## Task 6: Upstream gkm-metaschema issue (no code in this repo)

- [ ] File an issue covering three things:
  - the class-level `additionalProperties` overwrite at `source_proc.py` ~906–913: honor or reject an authored
    value, and consider leaving `protectedClassOf` mixins open by default
  - the minimal `allOf` reproduction above, as a test case
  - `sort_keys=True` at line 482, still deferred

---

## Verification

- [ ] **Strict, delta:** strict mode on the real 2026-10-11 delta, all 15 sections, gives 0 failures, as the
  prototype did. Use the real published bundle, not a sub-bundle, and set `schema_version` to the schema
  `const`.
- [ ] **Strict, monthly full:** strict mode on the 2026-10 monthly-full sample (≥ 20,000 records, stratified as
  above) gives 0 failures once Task 5 data is in. Before Task 5, it should show exactly the Document failures.
- [ ] **Full-coverage scan:** a full-coverage scan of the Document fields over the whole monthly full (DuckDB
  regex on `scv.parquet` `specifiedBy`/`reportedIn`, as above) gives 0 bad `doi` and 0 bad `urls[]` after the
  rebuild.
- [ ] **gkm-toolkit:** `validate_bundle_schema` on the real published full and delta reports 0 failures, as
  `CLAUDE.md` requires.
- [ ] **Negative tests:** each of these must still fail.
  - a bogus top-level property on an `scv`, `vcv`, `rcv`, `variation`, `varcustom-proposition` or
    `evidenceLine` record
  - a bogus key inside an SCV extension
  - a gene-list item with `symbol`, or with no `gene`
  - B2's malformed allele constraint
- [ ] **Task 5 oracles:** the full-vs-incremental and delta-reconstruction oracles report 0,0,0 after the
  one full-mode SCV run.
- [ ] **Docs:** `zensical build --clean --strict` is clean for the paired docs PR.

## Effect on the consolidated release

| Change | JSON bundle | Parquet | Backfill past releases? |
| --- | --- | --- | --- |
| B1 Tasks 1–3: mixins, `GeneListItem`, `definingContext` | none (schema only) | none | **no** |
| B1 Task 4: validator | none | none | no |
| **B1 Task 5: SCV citation Documents** | up to 3,872 `scv` records in the 2026-10 full (earlier fulls not yet counted; deltas only where those SCVs changed) | `scv` typed `specifiedBy`/`reportedIn` columns + `data` | **Decide before the rebuild** (below) |

**Task 5 needs a backfill decision before the forward rebuild, following the parent plan's rule.**

- **Forward:** requires the SCV step in full mode once. The first post-fix delta then carries the corrected
  SCVs, so reconstruction stays consistent without touching past releases.
- **Past fulls:** they are non-conformant today, even under relaxed validation. Two options:
  - **(a) Leave them and document it.**
  - **(b) Patch the affected `scv` records in the same JSON backfill pass that A1 already does on every monthly
    full.** Recommended: the files are rewritten anyway, and the extra work is a few thousand records per full.
  - **Parquet:** re-exporting `scv` for every monthly set costs a lot more (about 3 GB per month). Leaving the
    past `scv` Parquet as it is would be reasonable; the JSON bundles are the conformance artifact.
