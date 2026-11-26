# ClinVar-GKM SCV Statement Profiles and the VA-Spec Community Profiles — Design

- **Status:** Draft for review (revised 2026-11-24: the VA-Spec community profiles are not changed)
- **Date:** 2026-11-23
- **ADR:** `docs/decisions/0015-clinvar-gkm-scv-statement-profiles.md` (0014 is taken by the dataset-retention ADR)
- **Target:** clinvar-gkm schema **1.3.0**, in the consolidated 1.3.0 rebuild

## Goal

1. Give each kind of guideline-based SCV its own **ClinVar-GKM statement profile**, modelled on the matching
   VA-Spec community profile, and have the bundle schema enforce it:

   | ClinVar statement type | Bundle proposition section | ClinVar-GKM profile | Modelled on (VA-Spec) |
   |---|---|---|---|
   | `GermlineClassification` (pathogenicity) | `propositionPathogenicity` | `ClinvarScvPathogenicityStatement` | `acmg-2015` `VariantPathogenicityStatement` |
   | `OncogenicityClassification` | `propositionOncogenicity` | `ClinvarScvOncogenicityStatement` | `ccv-2022` `VariantOncogenicityStatement` |
   | `SomaticClinicalImpact` | `propositionSomaticClinicalImpact` | `ClinvarScvClinicalSignificanceStatement` | `aac-2017` `VariantClinicalSignificanceStatement` |

2. **Correct the source codings** so ClinVar-GKM sits as close to the community profiles as ClinVar's data allows.
3. **Document every remaining difference**, with the number of records it affects, and refresh those numbers
   each release.

The VA-Spec community profiles are intentionally defined and are **not** changed. ClinVar-GKM does not claim
conformance to them; it states where and why it differs.

## Context

- At the statement level ClinVar-GKM has one generic profile, `ClinvarScvStatement`, for every SCV. Per-type
  profiles exist only for propositions (`ClinvarVariantPathogenicityProposition`, …). The docs do not compare
  ClinVar-GKM's statements with the community profiles.
- Measured on the 2026-11 full (schema 1.2.0), against the community profiles as they stand:

  | Community profile | SCVs | Not conformant | Why |
  |---|---|---|---|
  | ccv-2022 | 2,456 | 139 | no `specifiedBy` (all NOCP) |
  | aac-2017 | 1,752 | 1,752 | code `tier 1` (profile `tier i`); system `AMP/ASCO/CAP (AAC) Guidelines, 2017`; `classification.name` `Tier I - Strong` (profile const `Tier I`); 149 also lack `specifiedBy` |
  | acmg-2015 | 6,838,781 | ~401,500 | 400,832 no `specifiedBy`; 641 low-penetrance / risk-allele strengths under the ClinGen 2024 system (profile: ACMG 2015); 265 `vus-low/mid/high` (system `SVC v4`, not in the profile); 203 combined labels (system `ClinVar`) |

- Codes and systems come from the upstream lookup `clinvar_ingest.clinvar_clinsig_types`
  (`clinvar-ingest-bq-tools/scripts/dataset-preparation/00-setup-translation-tables.sql`, hand-run). One
  `code_system` column serves both the classification and the strength coding. A pending, unpushed upstream branch
  `feat/vus-strength` (38545a1) gives VUS-high/mid/low the strengths `high`/`mid`/`low` (a 1.3.0 decision), and the
  local docs branch `docs/vus-strength-1.3.0` (1d60339) documents it.
- The lookup table and the `gkm_*` procedures are shared with the live 1.2 line.

## Decisions

1. **Three ClinVar-GKM statement profiles**, each a `ClinvarScvStatement` plus the community profile's
   classification, strength and direction rules, restated (not `$ref`'d — a reference cannot be relaxed), minus the
   documented differences.
2. **Selection by proposition section.** SCV records carry no statement-type field; the proposition pointer's
   section is the ClinVar statement type. The bundle schema selects the profile; other SCVs
   (`propositionClinvarCustom`) stay on `ClinvarScvStatement`.
3. **Data corrections (source lookup):** `tier 1`…`tier 4` → `tier i`…`tier iv`; system
   `AMP/ASCO/CAP (AAC) Guidelines, 2017` → `AMP/ASCO/CAP Guidelines, 2017`; `SVC v4` →
   `ACMG/AMP/CAP/ClinGen SVCv4.0`. A strength is coded in the same system as its classification:
   low-penetrance / risk-allele strengths stay under `ClinGen Low Penetrance and Risk Allele Recommendations, 2024`
   (as today), and VUS-high/mid/low strengths fall under SVCv4. So the single `code_system` column still
   serves both codings; no new column.
4. **Canonical tier name on the coding:** somatic clinical impact SCVs carry `classification.primaryCoding.name`
   `Tier I`…`Tier IV`; `classification.name` stays ClinVar's label (`Tier I - Strong`).
5. **Documented differences, not hidden ones:** a comparison page, an ADR, and a release-time script that counts
   the records that do not conform to each unchanged community profile, by reason.

## Design

### 1. Profiles (`schema/clinvar-gkm/clinvar-statement-source.yaml`)

Each profile is `allOf: [$ref ClinvarScvStatement, <constraints>]`. Constraints (systems abbreviated:
ACMG = `ACMG Guidelines, 2015`, LP = `ClinGen Low Penetrance and Risk Allele Recommendations, 2024`,
SVCv4 = `ACMG/AMP/CAP/ClinGen SVCv4.0`, CCV = `ClinGen/CGC/VICC Guidelines for Oncogenicity, 2022`,
AMP = `AMP/ASCO/CAP Guidelines, 2017`):

**`ClinvarScvPathogenicityStatement`**
- `proposition` pattern `^#/propositionPathogenicity/`.
- `classification.primaryCoding` required, one of:
  ACMG {`pathogenic`, `likely pathogenic`, `uncertain significance`, `likely benign`, `benign`};
  LP {`pathogenic, low penetrance`, `likely pathogenic, low penetrance`, `established risk allele`,
  `likely risk allele`, `uncertain risk allele`};
  SVCv4 {`vus-high`, `vus-mid`, `vus-low`} — *difference*;
  `ClinVar` {`benign/likely benign`, `pathogenic/likely pathogenic`} — *difference* (the lookup's
  `pathogenic/Likely pathogenic` is lower-cased at the source, so SCV and aggregate codes now agree).
- `strength`, when present: `primaryCoding` required, one of ACMG {`definitive`, `likely`};
  LP {`definitive`, `likely`} — *difference* (the community profile codes every strength under ACMG 2015);
  SVCv4 {`high`, `mid`, `low`} — *difference*.

**`ClinvarScvOncogenicityStatement`**
- `proposition` pattern `^#/propositionOncogenicity/`.
- `classification.primaryCoding` required: CCV {`oncogenic`, `likely oncogenic`, `uncertain significance`,
  `likely benign`, `benign`}. (The lookup also has an `onco` `b/lb` row under `ClinVar`; no SCV carries it today.
  It is not allowed: such an SCV would fail validation and must be decided on before release.)
- `strength`, when present: CCV {`definitive`, `likely`}.

**`ClinvarScvClinicalSignificanceStatement`**
- `proposition` pattern `^#/propositionSomaticClinicalImpact/`.
- `classification.primaryCoding` required: AMP {`tier i`, `tier ii`, `tier iii`, `tier iv`}, with `name` required.
- `strength`, when present: AMP {`strong`, `potential`}.
- Per tier (as the community profile): `tier i` → `primaryCoding.name` `Tier I`, strength `strong`, direction
  `supports`; `tier ii` → `Tier II`, `potential`, `supports`; `tier iii` → `Tier III`, no strength, `neutral`;
  `tier iv` → `Tier IV`, no strength, `disputes`. The community profile puts the name const on
  `classification.name` — *difference*.

All three: `specifiedBy` optional (as in `ClinvarScvStatement`) — *difference*: the community profiles require
it; ClinVar submissions often name no assertion method.

**Coding with a name.** `ClinvarScvClassification.primaryCoding` is a `ClinvarTermCoding`, which forbids `name`.
Add `ClinvarClassificationCoding` (`ClinvarCoding` with `iris: false`, `name` allowed) to
`clinvar-concept-source.yaml` and use it for `ClinvarScvClassification.primaryCoding`. Aggregates keep
`ClinvarTermCoding`.

**Selection (`clinvar-gkm-bundle.schema.json`, `scv` section).** Keep `$ref ClinvarScvStatement` and add three
`if`/`then`s on the `proposition` pattern, each `then` referencing the profile. Selection lives in the bundle
schema, so `ClinvarScvStatement` does not reference its own refinements.

**Version:** `schema_version` 1.3.0 (correction rule from the 1.1.0 release policy; signed off 2026-11-24), batched with
the other 1.3.0 schema changes.

### 2. Data corrections

**Upstream** — stacked on `feat/vus-strength`, one PR:

| Rows | Column | From | To |
|---|---|---|---|
| sci `t1`–`t4` | `classification_code` | `tier 1`…`tier 4` | `tier i`…`tier iv` |
| sci `t1`–`t4` | `code_system` | `AMP/ASCO/CAP (AAC) Guidelines, 2017` | `AMP/ASCO/CAP Guidelines, 2017` |
| path `vus-h/m/l` | `code_system` | `SVC v4` | `ACMG/AMP/CAP/ClinGen SVCv4.0` |
| path `p/lp` (combined) | `classification_code` | `pathogenic/Likely pathogenic` | `pathogenic/likely pathogenic` |

The system's short name is **SVCv4** (no year), used in prose next to ACMG 2015, CCV 2022 and AMP/ASCO/CAP 2017.
Codings carry only the full name in `system`, like the other guidelines; no CURIE goes in the data.

Also fix the `clingen-stage` block (it drops `code_system` and joins `clinvar_proposition_types` before that table
exists). Apply in BigQuery only at the 1.3.0 cut-over.

**clinvar-gkm procedures** — `gkm-scv-statement-proc.sql`: emit `primaryCoding.name` `Tier <ROMAN>` for tier codes; evidence-line `CASE` `'tier 1'`/`'tier 2'` →
`'tier i'`/`'tier ii'`. VCV/RCV procs need no code change (they join the lookup on `label`; single-label
aggregates pick up the corrected codes).

### 3. Documentation

- **Comparison page** `docs/profiles/community-profiles.md` (nav: Mapping & Vocabularies), one section per
  community profile: a table of each constraint — proposition type, classification codes and systems, strength,
  direction rules, `specifiedBy`, the tier name, evidence lines — with the community rule, the ClinVar-GKM rule,
  and why they differ; then a generated **record counts** block between
  `<!-- community-conformance:start -->` / `<!-- community-conformance:end -->` markers. Linked from
  `docs/reference/gks-standards.md`, `docs/profiles/index.md`, `statement-types.md` and `classifications.md`.
- **ADR 0015** — ClinVar-GKM profiles its own SCV statements on the community profiles and documents the
  differences rather than claiming conformance; alternatives considered (change the community profiles; document
  only).
- Corrected codes and systems in `classifications.md`, the output-reference statement pages, examples, changelog
  and release notes.

### 4. Per-release counts (`src/scripts/community-profile-conformance.py`)

Streams a bundle's `scv` section (the assembler's one-record-per-line layout), validates every SCV in the three
sections against the **unchanged** VA-Spec community profile with jsonschema-rs, and reports per profile: SCVs,
conformant, and not conformant grouped by reason (missing `specifiedBy`, classification code/system, strength
code/system, tier name on `classification.name`, other). `--write-docs` replaces the marked block in the
comparison page. Run on each monthly full; its output goes in the release's docs PR.

Needs the profile schemas in the registry: `load_resources` (`validate-bundle-rs.py`) loads only directories named
`json`, so extend it to `json/<community>/` and refuse network retrieval.

### 5. What is not changed

- The VA-Spec community profiles and the va-spec submodule pin.
- VCV / RCV aggregate statements (they keep the ClinVar aggregate profiles).
- Evidence lines (`Level A/B` / `Level C/D` stay uncoded; ClinVar gives no single AMP level).

## Validation and gates

- Schema tests (`test_validate_bundle_rs.py`): planted SCVs per profile pass or fail as designed.
- Real-data check before any BigQuery work: a filtered sample of the 2026-11 full, patched to the corrected
  values, validates with 0 failures (rs and toolkit).
- 1.3.0 rebuild **in full** (incremental mode carries unchanged SCVs forward with their old codes), and the first
  1.3 delta diffs against a dataset rebuilt with the 1.3 procs (against a 1.2 baseline every coded SCV would differ
  by its new coding `name`); real full and
  delta = 0 failures; oracles 0,0,0; no `tier [1-4]`, `SVC v4` or `(AAC)` left; first community-conformance
  report published on the comparison page.

## Resolved questions (user, 2026-11-24)

1. **1.3.0** under the corrections rule. The bump goes with whichever 1.3.0 schema branch is ready first; the others
   rebase onto it (plan Task 1.7).
2. The VUS sub-tier system is **`ACMG/AMP/CAP/ClinGen SVCv4.0`**, short name **SVCv4** (no year); no CURIE in the data.
3. **Yes:** `pathogenic/Likely pathogenic` → `pathogenic/likely pathogenic` at the source, in the same upstream PR.
4. The counts script runs **by hand** at each monthly full for now; it is not a `run-release.sh` stage.
