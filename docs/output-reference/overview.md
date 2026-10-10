# Output "Bundle" Format Overview

The ClinVar-GKM release file uses a **bundle format** — a single JSON object with named sections at the root level. A bundle is a dictionary-style approach to organizing a large amount of data across heterogeneous classes in a single file, where each section is a keyed collection of objects of the same class. The key is the object's unique identifier, and the value is the complete object.

This design eliminates duplication (a sequence reference shared by thousands of locations appears once), keeps individual objects compact, and enables efficient lookups by ID.

---

## Structure

```json
{
  "sequenceReference": { "<key>": { ... }, ... },
  "location":          { "<key>": { ... }, ... },
  "allele":            { "<key>": { ... }, ... },
  "copyNumberCount":   { "<key>": { ... }, ... },
  "copyNumberChange":  { "<key>": { ... }, ... },
  "gene":              { "<key>": { ... }, ... },
  "variation":         { "<key>": { ... }, ... },
  "condition":         { "<key>": { ... }, ... },
  "conditionSet":      { "<key>": { ... }, ... },
  "therapy":           { "<key>": { ... }, ... },
  "therapyGroup":      { "<key>": { ... }, ... },
  "submitter":            { "<key>": { ... }, ... },
  "varcond-proposition":  { "<key>": { ... }, ... },
  "vartumor-proposition": { "<key>": { ... }, ... },
  "vartherapy-proposition": { "<key>": { ... }, ... },
  "varcustom-proposition": { "<key>": { ... }, ... },
  "evidenceLine":         { "<key>": { ... }, ... },
  "scv":               { "<key>": { ... }, ... },
  "vcv":               { "<key>": { ... }, ... },
  "rcv":               { "<key>": { ... }, ... }
}
```

---

## Sections

### Variation Data Sections

These sections contain the VRS and Cat-VRS variant data:

**`sequenceReference`** — Reference sequences (chromosomes, transcripts) with refget accessions, molecule type, and assembly information. Keyed by refget accession (e.g., `SQ.0iKlIQk2oZLoeOG9P1riRU6hvL5Ux8TV`).

**`location`** — Sequence locations with start/end coordinates. Each location references its sequence via `#/sequenceReference/{key}`. Keyed by VRS location ID (e.g., `ga4gh:SL.Eg_6kV6Bb4FMjm9kEolHZ_4NhU8lBEsZ`).

**`allele`** — VRS alleles with state, expressions (SPDI, HGVS, gnomAD), and copy number data. Each allele references its location via `#/location/{key}`. Keyed by VRS allele ID (e.g., `ga4gh:VA.ELQCnIBGqaTl0AEE0Az18XZ2cgIHAQIY`).

**`copyNumberCount`** — VRS CopyNumberCount records for copy number variants with absolute copy counts. Each references its location via `#/location/{key}`. Keyed by VRS ID.

**`copyNumberChange`** — VRS CopyNumberChange records for copy number variants with relative change types (gain, loss). Each references its location via `#/location/{key}`. Keyed by VRS ID.

**`gene`** — Gene MappableConcepts with NCBI Gene primaryCoding and HGNC mapping. Keyed by `ncbigene:{gene_id}` (e.g., `ncbigene:3077`).

**`variation`** — ClinVar variations with their defining constraints, cross-references, HGVS expressions, and gene associations. Most variations are represented as CanonicalAlleles with a defining VRS allele (via `#/allele/`); copy number variants use a defining location (via `#/location/`); complex variants use a generalized representation. Keyed by `clinvar:{variation_id}` (e.g., `clinvar:10`).

### Supporting Data Sections

These sections contain the condition, therapy, submitter, and proposition reference data:

**`condition`** — Trait and disease concepts from ClinVar, with MedGen primary coding and cross-references to OMIM, MONDO, HPO, Orphanet, and MeSH. Keyed by `clinvar.trait:{trait_id}` (e.g., `clinvar.trait:9580`).

**`conditionSet`** — Multi-condition groupings with member condition references (`concepts` → `#/condition/`) and a membership operator (AND or OR). Keyed by `clinvar.traitset:{trait_set_id}` (e.g., `clinvar.traitset:1234`).

**`therapy`** — Individual drug therapies (Therapy MappableConcepts) referenced by therapeutic-response propositions. Content-addressed and deduplicated (therapies have no native ClinVar id). Keyed by `clinvar.therapy:{sha256}`.

**`therapyGroup`** — Combination (multi-drug) therapies (TherapyGroup ConceptSets) whose `concepts` reference member therapies via `#/therapy/`, with a membership operator. Content-addressed and deduplicated. Keyed by `clinvar.therapygroup:{sha256}`.

**`submitter`** — Submitting organizations with name and identifier. Keyed by `clinvar.submitter:{submitter_id}` (e.g., `clinvar.submitter:500139`).

**`varcond-proposition`, `vartumor-proposition`, `vartherapy-proposition`, `varcustom-proposition`** — Classification propositions defining what a statement asserts (proposition type, predicate, subject, object, qualifiers). Propositions are delivered in four datatype-homogeneous sections keyed by their (subject, object) signature so each is a fully-typed table:

- **`varcond-proposition`** — variant×condition (standard): `VariantPathogenicity`, `VariantClinicalSignificance`, `VariantDiagnostic`, `VariantPrognostic`; `subject` → `object`.
- **`vartumor-proposition`** — variant×tumorType (standard): `VariantOncogenicity`; `subject` → `object`.
- **`vartherapy-proposition`** — variant×therapy (standard): `VariantTherapeuticResponse`; `subject` → `object` where `object` references the therapy (`#/therapy/` single, or `#/therapyGroup/` combination), and the condition moves to `conditionQualifier` (`#/condition/` or `#/conditionSet/`).
- **`varcustom-proposition`** — custom variant×condition: the 10 `Clinvar*` types (e.g. `ClinvarRiskFactorProposition`, `ClinvarDrugResponseProposition`) — open subtypes of the VA-Spec `SubjectVariantProposition` base, each carrying its own real `type` name; `subject` → `object` with typed qualifiers (`geneContextQualifier`, `modeOfInheritanceQualifier`, `penetranceQualifier`).

Each contains SCV, VCV, and RCV propositions of that signature. Keyed by proposition ID (e.g., `SCV001234567-PATH` for SCVs, `VCV000012582.63-G-PATH-CP` for VCVs). A `#/{section}-proposition/{id}` pointer names the exact section a proposition lives in.

### Statement Sections

These sections contain the classification statements:

**`evidenceLine`** — Evidence line records referenced by statements via `hasEvidenceLines` arrays of `#/evidenceLine/` pointers. Merges SCV, VCV, and RCV evidence lines into a single section.

**`scv`** — Submitted classification statements. Each SCV carries a classification, strength, direction, proposition reference, contributions (with submitter references), evidence line references, citations, assertion method, and extensions with submitted condition provenance. Keyed by `clinvar.submission:{scv_id}.{version}`.

**`vcv`** — Variation-level aggregate classification statements. VCVs aggregate SCVs across a variation by classification, priority (somatic tiers), and submission level contribution. Evidence line references point to records in `#/evidenceLine/`. Keyed by the VCV layer ID.

**`rcv`** — Condition-level aggregate classification statements. RCVs follow the same aggregation structure as VCVs but are scoped to a specific RCV accession (variation + condition). Evidence line references point to records in `#/evidenceLine/`.

---

## JSON Pointer References

Objects reference each other using `#/{section}/{key}` strings instead of embedding full objects inline. This keeps the file compact and enables consumers to resolve references by looking up the key in the named section.

### Reference Patterns

| Pattern | Example | Resolves To |
| --- | --- | --- |
| `#/sequenceReference/{key}` | `#/sequenceReference/SQ.0iKlIQk2oZLoeOG9P1riRU6hvL5Ux8TV` | Sequence reference object |
| `#/location/{key}` | `#/location/ga4gh:SL.Eg_6kV6Bb4FMjm9kEolHZ_4NhU8lBEsZ` | Sequence location object |
| `#/allele/{key}` | `#/allele/ga4gh:VA.ELQCnIBGqaTl0AEE0Az18XZ2cgIHAQIY` | VRS allele object |
| `#/gene/{key}` | `#/gene/ncbigene:3077` | Gene object |
| `#/variation/{key}` | `#/variation/clinvar:10` | Categorical variant object |
| `#/condition/{key}` | `#/condition/clinvar.trait:9580` | Condition object |
| `#/conditionSet/{key}` | `#/conditionSet/clinvar.traitset:1234` | Condition set object |
| `#/submitter/{key}` | `#/submitter/clinvar.submitter:500139` | Submitter object |
| `#/varcond-proposition/{key}` | `#/varcond-proposition/SCV001234567-PATH` | Proposition object (variant×condition) |
| `#/vartumor-proposition/{key}` | `#/vartumor-proposition/SCV002345678-ONCO` | Proposition object (variant×tumorType) |
| `#/vartherapy-proposition/{key}` | `#/vartherapy-proposition/SCV003456789-TR` | Proposition object (variant×therapy) |
| `#/varcustom-proposition/{key}` | `#/varcustom-proposition/SCV004567890-RF` | Proposition object (custom) |
| `#/scv/{key}` | `#/scv/clinvar.submission:SCV001234567.1` | SCV statement object |
| `#/vcv/{key}` | `#/vcv/VCV000012582.63-G-PATH-CP` | VCV statement object |
| `#/rcv/{key}` | `#/rcv/RCV000012345.8-G-PATH-CP` | RCV statement object |

### Resolving References

To resolve a reference string like `#/allele/ga4gh:VA.abc123`:

1. Split on `/` — the second segment is the section name (`allele`), the third is the key (`ga4gh:VA.abc123`)
2. Look up the key in the named section of the root object
3. The value at that key is the resolved object

### Reference Depth

References are **one level deep** — a resolved object may itself contain references, but those are always to other root-level sections, never nested references within references. A consumer can fully resolve any object by following at most 2-3 hops (e.g., variation → allele → location → sequenceReference).

---

## MappableConcept Pattern

Several fields across statements use a **MappableConcept** structure — a typed object with a display name, optional primary coding, and optional extensions:

```json
{
  "conceptType": "Classification",
  "name": "Pathogenic",
  "primaryCoding": {
    "code": "pathogenic",
    "system": "ACMG Guidelines, 2015"
  },
  "extensions": [ ... ]
}
```

Fields that use this pattern:

- **`classification`** — the clinical significance label (`conceptType: "Classification"`)
- **`strength`** — the evidence strength (`conceptType: "Strength"`)
- **`evidenceOutcome`** — the evidence line outcome (`conceptType: "Outcome"`)
- **`strengthOfEvidenceProvided`** — the evidence line strength (`conceptType: "Strength"`)

The `conceptType` identifies the kind of concept. The `name` is the human-readable display value. The `primaryCoding` provides a machine-readable code and system when available. Not all instances carry `primaryCoding` — aggregate VCV/RCV classifications, for example, may only have `conceptType` and `name`.

---

## Bundle Schema

The bundle structure described above is formalized as a JSON Schema, authored to the
[GKM Starter Kit](https://ga4gh.github.io/gkm-starter-kit/) bundle-schema conventions:

**JSON Schema:** [clinvar-gkm-bundle.schema.json](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/clinvar-gkm-bundle.schema.json){ target=_blank }

- **Draft 2020-12**, root `type: object` — each root property is one of the bundle sections, and
  `additionalProperties: false` rejects unknown sections.
- Each section is a keyed map whose keys are constrained by that section's id pattern
  (`patternProperties`) and whose values `$ref` the appropriate GA4GH class schema by **versioned
  [W3ID](https://w3id.org/) URI** — VRS, Cat-VRS, VA-Spec, and GKM-Core for the shared types, and the
  ClinVar-GKM subtypes (`ClinvarScvStatement`, `ClinvarCategoricalVariant`, the `Clinvar*Proposition`
  family, …) for the ClinVar-specific ones.
- No section is individually required, so the **same schema validates a monthly full bundle, a weekly
  delta, and a sub-bundle extract** — each carries only the sections it touches.

The schema constrains the bundle's *shape* (which sections may appear, how their keys are formed, and
what each value validates against). The starter-kit's companion invariant — that every `#/section/key`
pointer resolves within the bundle — is a producer-side guarantee, not expressible in JSON Schema alone.

### Validating with the GKM Toolkit

The [GKM Toolkit](https://ga4gh.github.io/gkm-starter-kit/latest/tools/gkm-toolkit/) (`ga4gh.gkm`)
validates a bundle against this schema directly. It
[resolves](https://ga4gh.github.io/gkm-starter-kit/latest/tools/gkm-toolkit/api/schema-resolution/) the
W3ID `$ref` URIs to the actual VRS / VA-Spec / GKM-Core class schemas and expands the bundle-local
`#/…` pointers before [validating](https://ga4gh.github.io/gkm-starter-kit/latest/tools/gkm-toolkit/api/schema-validation/),
so each section's objects are checked against their full class definition rather than their serialized
pointer strings:

```python
import json
from ga4gh.gkm.bundles.schema_validation import (
    prepare_bundle_schema,
    validate_bundle_schema,
)

schema = json.load(open("clinvar-gkm-bundle.schema.json"))

# Validate one bundle — raises on any violation, returns None on success.
bundle = json.load(open("clinvar-gkm_00-latest.json"))
validate_bundle_schema(bundle, schema)

# Or compile the validator once and reuse it across many bundles / deltas.
validator = prepare_bundle_schema(schema)
for path in ("clinvar-gkm_2026-06.json", "clinvar-gkm-delta_00-latest.json"):
    validate_bundle_schema(json.load(open(path)), schema, validator=validator)
```

See the GKM Toolkit [schema-validation](https://ga4gh.github.io/gkm-starter-kit/latest/tools/gkm-toolkit/api/schema-validation/)
and [schema-resolution](https://ga4gh.github.io/gkm-starter-kit/latest/tools/gkm-toolkit/api/schema-resolution/)
API references for exact signatures and options.

---

## Parquet Output

In addition to the JSON bundle, the assembler can produce **typed Parquet files** — one per bundle section — using the `--parquet-dir` flag. Parquet files use columnar storage with named, typed columns for each section's fields, making them suitable for analytical workloads, DuckDB, pandas, or Apache Spark.

See [Export & Distribute](../pipeline/export.md#parquet-output) for the full list of Parquet files and their schemas.

---

## Inlining References

The [GKM Toolkit](https://ga4gh.github.io/gkm-starter-kit/latest/tools/gkm-toolkit/) (`ga4gh.gkm`) converts the bundle's `#/…` references into **inlined output** at the level of detail you need. Load the bundle, then call [`Bundle.export()`](https://ga4gh.github.io/gkm-starter-kit/latest/tools/gkm-toolkit/api/containers/):

- `export(item, deep=True)` — **complete**: every reachable reference resolved inline, producing a standalone object (a reference that closes a cycle is kept as a pointer, since JSON cannot represent a cyclic value).
- `export(item)` (`deep=False`) — **minimal**: the object's local `#/…` pointers are preserved as-is.
- `export()` with no argument exports the whole bundle at the chosen depth.

See the GKM Toolkit's [schema resolution](https://ga4gh.github.io/gkm-starter-kit/latest/tools/gkm-toolkit/api/schema-resolution/) and [containers](https://ga4gh.github.io/gkm-starter-kit/latest/tools/gkm-toolkit/api/containers/) API for details.
