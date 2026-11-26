# ClinVar-GKM SCV Statement Profiles Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or
> superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Three ClinVar-GKM SCV statement profiles (pathogenicity, oncogenicity, clinical significance), modelled on
the unchanged VA-Spec community profiles and enforced by the bundle schema; corrected source codings; and documented,
counted differences from the community profiles.

**Spec:** [`superpowers/specs/2026-11-23-scv-statement-profile-conformance-design.md`](../specs/2026-11-23-scv-statement-profile-conformance-design.md)

**Architecture:** clinvar-gkm adds three profiles (`ClinvarScvStatement` + restated community rules minus documented
differences) selected in the bundle schema by proposition section, plus a release-time script that measures each
SCV against the unchanged community profiles. Upstream `clinvar_clinsig_types` gets corrected codes and systems (a
strength keeps its classification's system, so no new column); the SCV proc adds the canonical tier name. Nothing touches BigQuery before the 1.3.0 cut-over (the
lookup and the procs are shared with the live 1.2 line). No va-spec change.

**Tech stack:** gkm metaschema YAML → JSON Schema 2020-12 (`make -C schema/clinvar-gkm docs`), jsonschema-rs via
`validate-bundle.sh` (validator of record), pytest, BigQuery SQL procedures, Zensical docs.

**Ground rules:** branch + PR per repo; no Claude attribution in commits; announce any billable GCP action with an
estimate and wait for a yes; revert generator `$defs` reorder churn; docs change in the same PR as behaviour.

**Branches:**
- clinvar-gkm: `feat/scv-statement-profiles` in this worktree, based on `docs/vus-strength-1.3.0` once that branch is
  rebased onto `origin/main` (both edit `classifications.md`, `vcv-statements.md`, `vcv-aggregation-rules.md`).
- clinvar-ingest-bq-tools: `fix/clinsig-types-guideline-codings` stacked on `feat/vus-strength` (38545a1, worktree
  `~/Development/clinvar-ingest-bq-tools.worktrees/vus-strength`).
- All 1.3.0 branches stay local / unmerged until the 1.3.0 batch is ready.

---

## Chunk 1: Schema — three SCV statement profiles

### Task 1.1: Set up

- [ ] **Step 1:** rebase `docs/vus-strength-1.3.0` onto `origin/main` (in its own worktree; resolve nothing
  beyond its 3 files). Then in this worktree: `git switch -c feat/scv-statement-profiles docs/vus-strength-1.3.0`
  and bring over the spec/plan files (`git add superpowers/ && git commit -m "Spec and plan: SCV statement profiles"`).
- [ ] **Step 2:** `git submodule update --init submodules/va-spec` (pin unchanged);
  `./src/scripts/validate-bundle.sh --check-setup` → both engines ready.
- [ ] **Step 3:** `pytest -q src/scripts/tests` → all pass; record the count.

### Task 1.2: Failing tests

**Files:** Modify `src/scripts/tests/test_validate_bundle_rs.py` (new block after
`test_engines_agree_inside_the_layered_profiles`)

- [ ] **Step 1: write the tests** (the `scv` fixture in `fixtures/profile-records.json` is a not-provided SCV with
no `specifiedBy`, so every passing case also shows `specifiedBy` is optional):
```python
def scv_as(section, code, system, *, name=None, coding_name=None, strength=None, direction="supports"):
    """The fixture SCV re-pointed at a proposition section with the given classification coding."""
    record = copy.deepcopy(PROFILE_RECORDS["scv"])
    record["proposition"] = f"#/{section}/SCV000090483-X"
    record["direction"] = direction
    coding = {"code": code, "system": system}
    if coding_name:
        coding["name"] = coding_name
    record["classification"]["name"] = name or code
    record["classification"]["primaryCoding"] = coding
    record.pop("strength", None)
    if strength:
        record["strength"] = {"type": "MappableConcept", "conceptType": "Strength", "name": strength[0].title(),
                              "primaryCoding": {"code": strength[0], "system": strength[1]}}
    return record


def without_coding(record):
    del record["classification"]["primaryCoding"]
    return record


ACMG, LP, V4 = ("ACMG Guidelines, 2015", "ClinGen Low Penetrance and Risk Allele Recommendations, 2024",
                "ACMG/AMP/CAP/ClinGen SVCv4.0")
CCV, AMP = "ClinGen/CGC/VICC Guidelines for Oncogenicity, 2022", "AMP/ASCO/CAP Guidelines, 2017"
PATH, ONCO, SCI = "propositionPathogenicity", "propositionOncogenicity", "propositionSomaticClinicalImpact"

STATEMENT_PROFILE_CASES = {
    # tag: (record, passes)
    "0": (scv_as(PATH, "pathogenic", ACMG, strength=("definitive", ACMG)), True),
    "1": (scv_as(PATH, "vus-high", V4, strength=("high", V4), direction="neutral"), True),
    "2": (scv_as(PATH, "vus-high", "SVC v4", direction="neutral"), False),  # old system
    "3": (scv_as(PATH, "benign/likely benign", "ClinVar", direction="disputes"), True),  # combined label
    "4": (scv_as(PATH, "vus-high", ACMG, direction="neutral"), False),  # code not in that system
    "5": (scv_as(PATH, "likely risk allele", LP, strength=("likely", LP)), True),  # strength in its own system
    "6": (scv_as(PATH, "likely risk allele", LP, strength=("likely", CCV)), False),  # strength system not allowed
    "7": (scv_as(ONCO, "benign", CCV, strength=("definitive", CCV), direction="disputes"), True),
    "8": (scv_as(ONCO, "benign", ACMG, strength=("definitive", ACMG), direction="disputes"), False),
    "9": (scv_as(SCI, "tier i", AMP, name="Tier I - Strong", coding_name="Tier I", strength=("strong", AMP)), True),
    "10": (scv_as(SCI, "tier 1", "AMP/ASCO/CAP (AAC) Guidelines, 2017", strength=("strong", AMP)), False),
    "11": (scv_as(SCI, "tier i", AMP, coding_name="Tier II", strength=("strong", AMP)), False),
    "12": (scv_as(SCI, "tier iii", AMP, coding_name="Tier III", direction="neutral"), True),
    "13": (scv_as(SCI, "tier iii", AMP, coding_name="Tier III", strength=("strong", AMP), direction="neutral"), False),
    "14": (scv_as(SCI, "tier i", AMP, strength=("strong", AMP)), False),  # no canonical name on the coding
    "15": (without_coding(scv_as(PATH, "pathogenic", ACMG)), False),  # classification must be coded
}
SCV_KEY = "clinvar.submission:SCV0000905{:0>2}.1"


def test_scv_statements_are_held_to_their_profiles(tmp_path, rs):
    bundle = {"schema_version": VERSION,
              "scv": {SCV_KEY.format(tag): record for tag, (record, _) in STATEMENT_PROFILE_CASES.items()}}
    failing = sorted(f"scv/{SCV_KEY.format(tag)}" for tag, (_, ok) in STATEMENT_PROFILE_CASES.items() if not ok)
    code, out = validate(write(tmp_path, assembled(bundle)))
    assert code == 1 and failing_keys(out) == failing, out


def test_engines_agree_on_the_scv_statement_profiles(tmp_path, rs, toolkit):
    bundle = {"schema_version": VERSION,
              "scv": {SCV_KEY.format(tag): record for tag, (record, _) in STATEMENT_PROFILE_CASES.items()}}
    path = write(tmp_path, assembled(bundle))
    assert failing_keys(validate(path, "rs")[1]) == failing_keys(validate(path, "toolkit")[1])
```
- [ ] **Step 2:** `pytest -q src/scripts/tests/test_validate_bundle_rs.py -k "held_to_their_profiles or statement_profiles"`
  Expected: FAIL. Today 9, 11, 12, 13 fail (each carries a `name` on the coding, which `ClinvarTermCoding` forbids);
  the expected failures 2, 4, 6, 8, 10, 14, 15 pass. After Tasks 1.3–1.5 the failing set is exactly
  {2, 4, 6, 8, 10, 11, 13, 14, 15}.

### Task 1.3: Coding with a name

**Files:** Modify `schema/clinvar-gkm/clinvar-concept-source.yaml` (after `ClinvarTermCoding`, ~L74),
`schema/clinvar-gkm/clinvar-statement-source.yaml` (`ClinvarScvClassification.primaryCoding`, ~L533)

- [ ] **Step 1:** add
```yaml
  ClinvarClassificationCoding:
    maturity: trial use
    description: >-
      The coding of a ClinVar SCV classification: a ClinvarCoding with its code, its system and, when the
      guideline defines one, the term's canonical name (e.g. 'Tier I' for 'tier i'). No IRIs.
    allOf:
      - $ref: "#/$defs/ClinvarCoding"
      - type: object
        properties:
          iris: false
```
- [ ] **Step 2:** `ClinvarScvClassification.primaryCoding`: `$refCurie: clinvar-gkm:ClinvarTermCoding` →
  `$refCurie: clinvar-gkm:ClinvarClassificationCoding`, and in `ClinvarScvClassification`'s description replace
  "a ClinvarTermCoding" with "a ClinvarClassificationCoding".

### Task 1.4: The three profiles

**Settled (2026-11-24):** the VUS system is `ACMG/AMP/CAP/ClinGen SVCv4.0` (short name SVCv4). These consts
and the upstream lookup (Chunk 3) both hard-code it, so they must match exactly.

**Files:** Modify `schema/clinvar-gkm/clinvar-statement-source.yaml` (new section after `ClinvarScvStatement`, ~L872)

- [ ] **Step 1: `ClinvarScvPathogenicityStatement`** (each profile is written out in full; no shared fragments):
```yaml
  ClinvarScvPathogenicityStatement:
    maturity: trial use
    description: >-
      A ClinVar SCV statement about a variant's pathogenicity, modelled on the VA-Spec ACMG 2015
      VariantPathogenicityStatement. Its classification is coded under the ACMG 2015 guidelines, the ClinGen 2024
      low-penetrance and risk-allele recommendations, the SVCv4 VUS sub-tiers, or (for ClinVar's
      combined labels) ClinVar; a strength is coded in its classification's system. It differs from the
      community profile in four ways: specifiedBy is optional; the SVCv4 VUS sub-tiers and their strengths (high,
      mid, low) are allowed; low-penetrance and risk-allele strengths are coded under the ClinGen 2024
      recommendations, not ACMG 2015; and ClinVar's combined labels are allowed. See the Community Profiles page.
    allOf:
      - $ref: "#/$defs/ClinvarScvStatement"
      - type: object
        properties:
          proposition:
            $refCurie: gkm.core:iriReference
            pattern: "^#/propositionPathogenicity/"
          classification:
            type: object
            required: [primaryCoding]
            properties:
              primaryCoding:
                type: object
                oneOf:
                  - properties:
                      system: {const: "ACMG Guidelines, 2015"}
                      code: {enum: [pathogenic, likely pathogenic, uncertain significance, likely benign, benign]}
                  - properties:
                      system: {const: "ClinGen Low Penetrance and Risk Allele Recommendations, 2024"}
                      code:
                        enum:
                          - "pathogenic, low penetrance"
                          - "likely pathogenic, low penetrance"
                          - established risk allele
                          - likely risk allele
                          - uncertain risk allele
                  - properties:
                      system: {const: "ACMG/AMP/CAP/ClinGen SVCv4.0"}
                      code: {enum: [vus-high, vus-mid, vus-low]}
                  - properties:
                      system: {const: ClinVar}
                      code: {enum: [benign/likely benign, pathogenic/likely pathogenic]}
          strength:
            type: object
            required: [primaryCoding]
            properties:
              primaryCoding:
                type: object
                oneOf:
                  - properties:
                      system: {const: "ACMG Guidelines, 2015"}
                      code: {enum: [definitive, likely]}
                  - properties:
                      system: {const: "ClinGen Low Penetrance and Risk Allele Recommendations, 2024"}
                      code: {enum: [definitive, likely]}
                  - properties:
                      system: {const: "ACMG/AMP/CAP/ClinGen SVCv4.0"}
                      code: {enum: [high, mid, low]}
```
  (Same-file references use `$ref: "#/$defs/…"`, as at L863-865; `proposition` is narrowed with
  `$refCurie: gkm.core:iriReference` + `pattern`, as at L776-778, so the generated page keeps the type.)
- [ ] **Step 2: `ClinvarScvOncogenicityStatement`** — same shape: proposition `^#/propositionOncogenicity/`;
  classification one system `ClinGen/CGC/VICC Guidelines for Oncogenicity, 2022`, codes
  `[oncogenic, likely oncogenic, uncertain significance, likely benign, benign]`; strength same system,
  `[definitive, likely]`. Description names the one difference (`specifiedBy` optional).
- [ ] **Step 3: `ClinvarScvClinicalSignificanceStatement`** — proposition `^#/propositionSomaticClinicalImpact/`;
  classification `primaryCoding` required with `required: [name]`, system `AMP/ASCO/CAP Guidelines, 2017`, codes
  `[tier i, tier ii, tier iii, tier iv]`; strength system AMP, `[strong, potential]`; then four conditionals:
```yaml
      - if:
          properties:
            classification:
              properties:
                primaryCoding: {properties: {code: {const: tier i}}, required: [code]}
              required: [primaryCoding]
          required: [classification]
        then:
          properties:
            classification:
              properties:
                primaryCoding: {properties: {name: {const: Tier I}}}
            strength:
              properties:
                primaryCoding: {properties: {code: {const: strong}}, required: [code]}
              required: [primaryCoding]
            direction: {const: supports}
          required: [strength]
```
  `tier ii`: `Tier II`, `potential`, `supports`, strength required. `tier iii`: `Tier III`, `strength: false`,
  `neutral`. `tier iv`: `Tier IV`, `strength: false`, `disputes`. Description names the differences
  (`specifiedBy` optional; the canonical tier name is on `primaryCoding.name`, `classification.name` is ClinVar's
  label).
- [ ] **Step 4:** add a sentence to `ClinvarScvStatement`'s description: SCVs in the pathogenicity, oncogenicity and
  somatic-clinical-impact sections are further held to the three profiles above.

### Task 1.5: Selection in the bundle schema

**Files:** Modify `schema/clinvar-gkm/clinvar-gkm-bundle.schema.json` (`properties.scv.patternProperties`)

- [ ] **Step 1:** replace the pattern's value with (use the bundle's current `$id` version; it becomes `1.3.0` in
  Task 1.7):
```json
{
  "allOf": [
    {"$ref": "https://w3id.org/clingen/schema/clinvar-gkm/1.2.0/json/ClinvarScvStatement"},
    {"if": {"properties": {"proposition": {"pattern": "^#/propositionPathogenicity/"}}, "required": ["proposition"]},
     "then": {"$ref": "https://w3id.org/clingen/schema/clinvar-gkm/1.2.0/json/ClinvarScvPathogenicityStatement"}},
    {"if": {"properties": {"proposition": {"pattern": "^#/propositionOncogenicity/"}}, "required": ["proposition"]},
     "then": {"$ref": "https://w3id.org/clingen/schema/clinvar-gkm/1.2.0/json/ClinvarScvOncogenicityStatement"}},
    {"if": {"properties": {"proposition": {"pattern": "^#/propositionSomaticClinicalImpact/"}}, "required": ["proposition"]},
     "then": {"$ref": "https://w3id.org/clingen/schema/clinvar-gkm/1.2.0/json/ClinvarScvClinicalSignificanceStatement"}}
  ]
}
```
- [ ] **Step 2:** `make -C schema/clinvar-gkm docs`; revert pure `$defs` reorder churn. Create
  `docs/output-reference/classes/{ClinvarClassificationCoding,ClinvarScvPathogenicityStatement,ClinvarScvOncogenicityStatement,ClinvarScvClinicalSignificanceStatement}.md`
  from `schema/clinvar-gkm/md/` by hand (the `docs` target only refreshes pages that already exist). Class pages
  are deliberately kept out of the nav (`zensical.toml:118-122`): link the new pages from
  `docs/output-reference/classes/statements.md`, `classes/concepts.md` and `classes/index.md` (L11, L101) instead.
- [ ] **Step 3:** `pytest -q src/scripts/tests/test_validate_bundle_rs.py` → PASS, including the two new tests (the
  toolkit test needs `--check-setup --engine toolkit` ready; make it run before the PR). `pytest -q src/scripts/tests`
  → all pass.
- [ ] **Step 4: commit** "Add ClinVar-GKM SCV statement profiles for pathogenicity, oncogenicity and clinical significance"
  (`schema`, `src/scripts/tests`, `docs/output-reference/classes`).

### Task 1.6: Real-data check (no BigQuery) — before any BigQuery work

Source: the 2026-11 monthly full (session copy, may be gone:
`/private/tmp/claude-503/-Users-lbabb-Development-gks-clinvar-gks/b47fc43d-f593-42d0-a761-77b28a475091/scratchpad/data/clinvar-gkm_2026-11.json.gz`;
else download it from R2). Filter and patch scripts live in the session scratchpad, not the repo.

- [ ] **Step 1: filter:** every `scv` record in `propositionOncogenicity` / `propositionSomaticClinicalImpact`;
  2,000 `propositionPathogenicity` SCVs spread over its four systems (ACMG, LP, `SVC v4`, `ClinVar`); 200
  `propositionClinvarCustom`; 500 `vcv`, 500 `rcv`. Write it as an unpatched sample.
- [ ] **Step 2: patch** a copy: `tier N` → `tier <roman>`; `(AAC)` system → AMP; add `primaryCoding.name`
  `Tier <ROMAN>`; `SVC v4` → SVCv4; VUS-x strength `high/mid/low` under SVCv4; `pathogenic/Likely pathogenic` → lower case (LP/risk-allele records stay as they are). Set
  `schema_version` to the bundle schema's const in both copies.
- [ ] **Step 3:** `validate-bundle.sh <patched>` → 0 failures; `--engine toolkit` → same. `validate-bundle.sh
  <unpatched>` → failures only on SCI, VUS-x and capital-L combined-label records.
- [ ] **Step 4 (after Chunk 2):** `community-profile-conformance.py <patched>` → reasons match the spec's expected
  differences (ccv: `no specifiedBy` only; aac: `no specifiedBy`, `classification name`; acmg: `no specifiedBy`,
  `classification coding` for VUS-x and combined labels, `strength coding` for VUS-x and LP/risk-allele).

### Task 1.7: Version 1.3.0 — gated

- [ ] **Step 1:** 1.3.0 is signed off (2026-11-24). The first 1.3.0 schema branch ready to land does the bump; if
  another branch has bumped already, rebase onto it and skip Step 2.
- [ ] **Step 2:** bump the 5 `schema/clinvar-gkm/*-source.yaml` `$id`s, `clinvar-gkm-bundle.schema.json` (all `$id`s /
  `$ref`s and `schema_version.const`) and `src/scripts/assemble-gkm-dicts.py:75` to `1.3.0`;
  `grep -rn "clinvar-gkm/1.2.0" schema/clinvar-gkm/*.yaml schema/clinvar-gkm/*.json` → 0; regenerate; tests pass;
  commit.

---

## Chunk 2: Community-profile conformance counts

`jsonschema_rs` and `orjson` exist only in the uv environment `validate-bundle.sh` builds (`RS_VERSION="0.61.1"`),
not in `venv/3.12`. Run this chunk's tests and script with:

```bash
RS_PY=(uv run --no-project --quiet --python 3.12 --with "jsonschema-rs==0.61.1" --with orjson --with pytest)
"${RS_PY[@]}" python -m pytest -q src/scripts/tests/test_community_profile_conformance.py
"${RS_PY[@]}" python src/scripts/community-profile-conformance.py <bundle.json.gz>
```

Load the hyphenated scripts the way `test_assemble_gkm_dicts.py:14-16` does:

```python
import importlib.util
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]


def load_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
```

### Task 2.1: Load the community profile schemas

`load_resources` (`src/scripts/validate-bundle-rs.py:49-68`) walks only directories named `json`; the community
profiles live one level down (`schema/va-spec/json/acmg-2015/…`).

**Files:** Modify `src/scripts/validate-bundle-rs.py:49-68` (walk + docstring L10, L51); Test
`src/scripts/tests/test_community_profile_conformance.py` (new; it needs the uv environment above)

- [ ] **Step 1: failing test** (with `load_script` from the chunk header):
```python
validate_bundle_rs = load_script("validate_bundle_rs", "validate-bundle-rs.py")


def test_load_resources_includes_the_community_profiles():
    ids = {i for i, _ in validate_bundle_rs.load_resources(SCRIPTS.parents[1] / "schema")}
    assert any(i.endswith("/json/acmg-2015/VariantPathogenicityStatement") for i in ids)
```
- [ ] **Step 2:** `"${RS_PY[@]}" python -m pytest -q src/scripts/tests/test_community_profile_conformance.py` → FAIL
  (assertion, not an import error).
- [ ] **Step 3:** in `load_resources` replace
```python
        if os.path.basename(dirpath) != "json":
            continue
```
with
```python
        # a module's json/ directory, or a profile directory inside it (va-spec json/acmg-2015/, …)
        if "json" not in (os.path.basename(dirpath), os.path.basename(os.path.dirname(dirpath))):
            continue
```
  Update `validate-bundle-rs.py`'s docstrings (L10, L51), which say the walk mirrors `load_registry` in
  `validate-schema-conformance.py`: either apply the same change there or say the rs walk also loads profile
  directories (prefer the same change, so both engines see the same schema set).
- [ ] **Step 4:** run → PASS; `pytest -q src/scripts/tests` passes (the bundle validator only gains resources).
- [ ] **Step 5:** check whether the installed jsonschema-rs fetches unknown `https://` `$ref`s over the network. If
  it does, give `Registry`/validators a retriever that raises, with a test that an unknown `$ref` fails.
- [ ] **Step 6: commit** "Load the VA-Spec community profile schemas into the rs registry".

### Task 2.2: The counts script

**Files:**
- Create: `src/scripts/community-profile-conformance.py`
- Test: `src/scripts/tests/test_community_profile_conformance.py`

- [ ] **Step 1: failing tests** — append to `test_community_profile_conformance.py`:
```python
import copy
import gzip
import json

conformance = load_script("community_profile_conformance", "community-profile-conformance.py")

COMMUNITY_SCI_OK = {  # what the aac-2017 profile wants
    "type": "Statement", "proposition": "#/propositionSomaticClinicalImpact/x", "direction": "supports",
    "specifiedBy": {"type": "Method", "name": "AMP/ASCO/CAP Guidelines, 2017"},
    "classification": {"type": "MappableConcept", "name": "Tier I",
                       "primaryCoding": {"code": "tier i", "system": "AMP/ASCO/CAP Guidelines, 2017"}},
    "strength": {"type": "MappableConcept",
                 "primaryCoding": {"code": "strong", "system": "AMP/ASCO/CAP Guidelines, 2017"}},
}
CLINVAR_SCI = copy.deepcopy(COMMUNITY_SCI_OK)  # what ClinVar-GKM emits after the 1.3.0 fixes
del CLINVAR_SCI["specifiedBy"]
CLINVAR_SCI["classification"]["name"] = "Tier I - Strong"
CLINVAR_SCI["classification"]["primaryCoding"]["name"] = "Tier I"

def test_conformant_record_has_no_reasons():
    assert conformance.reasons("aac-2017", COMMUNITY_SCI_OK) == set()


def test_clinvar_sci_record_differs_by_specifiedby_and_tier_name():
    assert conformance.reasons("aac-2017", CLINVAR_SCI) == {"no specifiedBy", "classification name"}


def test_report_counts_per_profile(tmp_path):
    records = {"clinvar.submission:SCV000090500.1": COMMUNITY_SCI_OK,
               "clinvar.submission:SCV000090501.1": CLINVAR_SCI}
    body = ",\n".join(f"    {json.dumps(k)}: {json.dumps(r, separators=(',', ':'))}" for k, r in records.items())
    bundle_path = tmp_path / "bundle.json.gz"
    with gzip.open(bundle_path, "wt") as f:  # the assembler's one-record-per-line layout
        f.write('{\n  "schema_version": "x",\n  "scv": {\n' + body + "\n  }\n}\n")
    report = conformance.report(bundle_path)
    assert report["aac-2017"] == {"scvs": 2, "conformant": 1,
                                  "reasons": {"no specifiedBy": 1, "classification name": 1}}
```
- [ ] **Step 2:** run → FAIL (module missing).
- [ ] **Step 3: implement** `community-profile-conformance.py`:
  - `PROFILES = {"propositionPathogenicity": ("acmg-2015", "VariantPathogenicityStatement"),
    "propositionOncogenicity": ("ccv-2022", "VariantOncogenicityStatement"),
    "propositionSomaticClinicalImpact": ("aac-2017", "VariantClinicalSignificanceStatement")}`
  - load each profile from `schema/va-spec/json/<community>/<Class>` and build one `jsonschema_rs.Draft202012Validator`
    per profile with the registry from `validate-bundle-rs.load_resources` (import it; do not copy the walk).
  - `reasons(community, record) -> set[str]`: map each error from `iter_errors`: a `required` error naming
    `specifiedBy` → `"no specifiedBy"`; instance path under `classification/primaryCoding` → `"classification coding"`;
    `classification/name` → `"classification name"`; under `strength` → `"strength coding"`; else `"other"`. (Check
    the jsonschema-rs error attributes — `instance_path`, `kind` — on the installed version before relying on them.)
  - `report(bundle_path) -> dict`: stream the `scv` section with the same one-record-per-line reader
    `validate-bundle-rs.py` uses; per profile count SCVs, conformant, and each reason once per record.
  - CLI: `community-profile-conformance.py <bundle.json.gz> [--json out.json] [--write-docs docs/profiles/community-profiles.md]`;
    `--write-docs` replaces the text between `<!-- community-conformance:start -->` and
    `<!-- community-conformance:end -->` with a table (profile, SCVs, conformant, per-reason counts) and the bundle's
    name and date, and fails if the markers are missing.
- [ ] **Step 4:** run → PASS. Also run the CLI on the unpatched sample from Task 1.6 and check the reasons
  against the spec's table (same reasons, proportional counts).
- [ ] **Step 5: commit** "Add a report of SCV conformance to the VA-Spec community profiles".

---

## Chunk 3: Upstream lookup (`~/Development/clinvar-ingest-bq-tools`)

**Do not run the script in BigQuery in this chunk** — it is applied at the 1.3.0 cut-over.

### Task 3.1: Correct `clinvar_clinsig_types`

**Files:** `scripts/dataset-preparation/00-setup-translation-tables.sql` (DDL L30–44, rows L45–99, stage block
L101–133); docs `docs/architecture/bigquery-schema.md:49-50`, `docs/architecture/data-pipeline.md:58-69`,
`docs/sql-scripts/dataset-preparation.md:25,65`

- [ ] **Step 1:** in the `vus-strength` worktree: `git switch -c fix/clinsig-types-guideline-codings feat/vus-strength`.
- [ ] **Step 2: corrections** (no DDL change: a strength keeps its classification's system, so `code_system` still
  serves both codings) — sci `t1`–`t4` `classification_code` → `'tier i'`, `'tier ii'`, `'tier iii'`,
  `'tier iv'` and `code_system` → `'AMP/ASCO/CAP Guidelines, 2017'`; path `vus-h/m/l` `code_system` →
  `'ACMG/AMP/CAP/ClinGen SVCv4.0'`. Leave `code`, `label`, `strength_code`, `strength_label` (VCV/RCV join on
  `label`). Also `classification_code` `'pathogenic/Likely pathogenic'` → `'pathogenic/likely pathogenic'`
  (approved 2026-11-24; the Task 1.4 profile enum already uses the lower-case form).
- [ ] **Step 3: stage block** — add `cst.code_system,` to its SELECT and move the `BEGIN … END;` block below the
  `clinvar_proposition_types` CREATE/INSERT it joins.
- [ ] **Step 4: check** — `grep -c "'tier [1-4]'\|SVC v4\|(AAC)\|pathogenic/Likely" scripts/dataset-preparation/00-setup-translation-tables.sql`
  → `0`; every VALUES row still has 13 values.
- [ ] **Step 5: dry run (free; say so first):** `bq query --use_legacy_sql=false --dry_run < …/00-setup-translation-tables.sql`
  → validated (any error is real: the table shape is unchanged).
- [ ] **Step 6:** update the three docs pages and `scripts/dataset-preparation/readme.md`; commit
  "clinvar_clinsig_types: AMP tier codes and system, SVCv4 VUS system, lower-case pathogenic/likely pathogenic"; PR stacked on
  `feat/vus-strength`, body: *merge any time, apply in BigQuery only at the clinvar-gkm 1.3.0 cut-over.*

---

## Chunk 4: clinvar-gkm SCV procedure (branch `feat/scv-statement-profiles`)

### Task 4.1: Emit the corrected codings

**Files:** `src/procedures/gkm-scv-statement-proc.sql` — Step 7 (~L1259–1265), Step 8 (~L1336–1366)

- [ ] **Step 1:** Step 8 classification coding (the strength coding is unchanged: it keeps
  `classif_and_strength_code_system`):
```sql
          IF(
            scv.classification_code IS NOT NULL,
            STRUCT(
              scv.classification_code as code,
              -- the guideline's canonical term name, where it defines one (AMP/ASCO/CAP 2017 tiers)
              IF(STARTS_WITH(scv.classification_code, 'tier '),
                 CONCAT('Tier ', UPPER(SUBSTR(scv.classification_code, 6))), NULL) as name,
              scv.classif_and_strength_code_system as system),
            null
          ) as primaryCoding,
```
- [ ] **Step 2:** Step 7: `WHEN 'tier 1'` → `WHEN 'tier i'`, `WHEN 'tier 2'` → `WHEN 'tier ii'`.
- [ ] **Step 3:** `grep -n "'tier [0-9]'" src/procedures/*.sql` → no hits.
- [ ] **Step 4:** confirm `gkm_json_cleanup.py` drops a NULL `name` inside `primaryCoding`; if no test covers it, add
  one to `src/scripts/tests/test_gkm_json_cleanup.py` (`{"code": "pathogenic", "name": None, "system": "…"}` → no
  `name`). Run → pass.
- [ ] **Step 5:** re-read `gkm-vcv-proc.sql:271-290` / `gkm-rcv-proc.sql:293-312`: `classif_codings` reads only
  `classification_code` + `code_system` and joins on `label` → no change.
- [ ] **Step 6: commit** "Canonical AMP tier names on the SCV classification coding; tier i evidence outcomes".

### Task 4.2: Scratch verification (billable — ask first)

- [ ] **Step 1:** estimate and announce the cost; wait for a yes.
- [ ] **Step 2: never write into a release dataset** (the procs write `{S}.gkm_dict_*` into the dataset they run on,
  `gkm-scv-statement-proc.sql:186-187, 1128-1495`). Create a scratch dataset; table-clone into it every input the
  SCV/VCV/RCV statement procs read from the latest release dataset; copy `clinvar_clinsig_types` into it with the
  Chunk 3 changes. The procs find their dataset through `clinvar_ingest.schema_on(on_date)` (L109, L131) and
  hard-code `clinvar_ingest.clinvar_clinsig_types` (L314): in the scratch copies of the procs, replace **both**
  (point the dataset resolution at the scratch dataset; point the lookup at the scratch copy) and rename the procs.
  Before any run, grep the deployed scratch proc text for `schema_on`, `clinvar_ingest.clinvar_clinsig_types` and
  release dataset names → only scratch references remain. Then run on the scratch dataset, full mode.
- [ ] **Step 3:** each → 0: SCVs coded `tier [1-4]`, `SVC v4`, `(AAC)`; SCVs whose strength system differs from
  their classification system; SCI SCVs whose `primaryCoding.name` ≠ `Tier <ROMAN>`; SCI evidence lines whose
  outcome name matches `^tier [0-9]` (tier iii / iv lines legitimately carry `tier iii` / `tier iv`, per
  `clinvar-evidence-source.yaml:169-171`).
- [ ] **Step 4:** drop the scratch dataset and procs; confirm nothing of ours is left running.

---

## Chunk 5: Docs, ADR, real-data check (branch `feat/scv-statement-profiles`)

### Task 5.1: Comparison page

**Files:** Create `docs/profiles/community-profiles.md`; modify `zensical.toml` (nav under Mapping & Vocabularies,
after Classifications), `docs/profiles/index.md` (Sections list), `docs/reference/gks-standards.md`,
`docs/profiles/statement-types.md`, `docs/profiles/classifications.md` (link + system column)

- [ ] **Step 1:** write the page (write-docs skill conventions; "What this page answers" abstract). For each of
  ACMG 2015 / CCV 2022 / AMP/ASCO/CAP 2017: a table with rows *Proposition*, *Classification codes and systems*,
  *Strength*, *Direction rules*, *specifiedBy*, *Tier name* (AMP only), *Evidence lines*, and columns
  *VA-Spec community profile*, *ClinVar-GKM profile* (linked class page), *Why*. The differences, exactly as in
  spec §1: `specifiedBy` optional (all three); VUS sub-tiers + High/Mid/Low strengths, low-penetrance / risk-allele
  strengths under the ClinGen 2024 system, and combined labels (ACMG);
  tier name on the coding, ClinVar's label as `classification.name` (AMP); evidence-line levels A/B, C/D not coded
  (AMP). Then "Record counts" with the empty markers block and one sentence saying it is regenerated each release.
- [ ] **Step 2:** link it from the four pages; `zensical build --clean --strict` + `check-site-links.py` → clean.

### Task 5.2: ADR 0015

**Files:** Create `docs/decisions/0015-clinvar-gkm-scv-statement-profiles.md` (format of 0013); add it to
`docs/decisions/README.md`.

- [ ] Context (ClinVar submissions cannot meet the community profiles as written; the profiles are intentionally
  defined); decision (spec Decisions 1–5); consequences (1.3.0; three new classes; per-release counts; aggregates
  untouched); alternatives (change the community profiles — rejected; document only — rejected: no enforcement).

### Task 5.3: Other pages

- [ ] `docs/output-reference/overview.md:193-201` (the scv section is now the three profiles, not only
  `ClinvarScvStatement`), `docs/profiles/classifications.md`, `docs/output-reference/scv-statements.md` (L49, L74; fix the stale
  evidenceOutcome `"tier 1"` at L228), `vcv-statements.md`, `rcv-statements.md`, `classes/evidence.md`,
  `pipeline/vcv-statements/vcv-aggregation-rules.md`, `pipeline/scv-statements/propositions.md`,
  `reference/glossary.md`, `parquet/tables.md` (incl. the new `classification.primaryCoding.name` field),
  `parquet/table-anatomy.md`, `data-access/examples.md`,
  `assets/diagrams/parquet-vcv-levels.html`, `reference/changelog.md` (1.3.0), `src/procedures/clinvar-fundamentals.md`.
- [ ] Lower-cased `pathogenic/likely pathogenic`: mark the `reference/known-issues.md` entry (~L82) resolved in
  1.3.0; drop the case-difference note in `vcv-aggregation-rules.md` (~L156, L180–181); reword the comments at
  `gkm-vcv-proc.sql:273-275` / `gkm-rcv-proc.sql:295-297` (the `LOWER()` stays as a safeguard — comment-only, ask
  before editing the SQL). The 1.3.0 changelog says SCV and aggregate codes now agree.
- [ ] Use the short name SVCv4 (no year) on the comparison page and in the ADR, next to ACMG 2015, CCV 2022 and AMP/ASCO/CAP 2017.
- [ ] `grep -rn "tier [1-4]\b\|SVC v4\|(AAC)\|pathogenic/Likely" docs src/procedures/*.md` → changelog history
  only; strict build clean.
- [ ] Commit "Document the ClinVar-GKM SCV statement profiles and their differences from the community profiles".

---

## Chunk 6: 1.3.0 cut-over and gates (with the 1.3.0 release runbook)

- [ ] **Step 0 (before cut-over):** compile the 1.3.0 `scv` table with gkm-bundle-parquet locally (it treats
  `if`/`then` as opaque) and confirm `classification.primaryCoding.name` comes through.
- [ ] **Step 1:** after the last 1.2 weekly build, apply the upstream lookup change in BigQuery (announce first).
  `00-setup-translation-tables.sql` recreates every lookup table, not just `clinvar_clinsig_types`: run only the
  `clinvar_clinsig_types` statements, or diff the script's other tables against the live ones first. Deploy the
  1.3.0 procs.
- [ ] **Step 2: FULL rebuild, not incremental.** Incremental mode carries unchanged SCVs forward
  (`gkm-scv-statement-proc.sql:7,129-168`) with their old codes; the gate_key change already forces a full rebuild
  (`gkm-pipeline-version-proc.sql:9-10`), and without it the merge's `UNION ALL` (L1495-1510) would fail on the new
  STRUCT shape. The first 1.3 delta's baseline must also be a dataset rebuilt with the 1.3 procs: the change log
  compares `TO_JSON_STRING` (`gkm-change-log-proc.sql:124-128`) and `canonicalize_json` keeps nulls
  (`dataset-diff-func.sql:35`), so against a 1.2 baseline every coded SCV gains `"name":null` and the delta would
  hold nearly every SCV.
- [ ] **Step 3:** `validate-bundle.sh` on the real full and delta → 0 failures; oracles (full-vs-incremental,
  `oracle-delta-reconstruction.sh`) → 0,0,0; gkm-toolkit on a stratified sample.
- [ ] **Step 4:** checks on the real full → 0: `tier [1-4]`, `SVC v4`, `(AAC)`; oncogenicity SCVs under `ClinVar`
  (if any, stop and decide before publishing).
- [ ] **Step 5:** `community-profile-conformance.py <full> --write-docs docs/profiles/community-profiles.md`; commit
  the counts with the release docs.
- [ ] **Step 6:** gkm-bundle-parquet accepts `schema_version` 1.3.0; regenerate examples
  (`examples/scv/*-S-SCI-*`, `*-S-ONCO*`, `*-G-PATH*`, `examples/vcv|rcv/*-S-SCI*`) with `extract-example.py`; release
  notes call out the corrected codes/systems for consumers filtering on `tier 1` or `SVC v4`.
