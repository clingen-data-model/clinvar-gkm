# Output File

ClinVar-GKM is published as **gzip-compressed JSON files** in the bundle format — a **monthly full bundle** containing all data for a release, plus a **weekly delta** carrying only the records changed since the prior release. Typed **Parquet files** (one per bundle section) accompany both for analytical workloads.

---

## File Format

The release file is a `.json.gz` file. The decompressed content is a single JSON object with named bundle sections at the root level — each section is a keyed collection of objects of the same class.

```bash
# Decompress and inspect the top-level keys
gunzip -c clinvar-gkm_00-latest.json.gz | python3 -c "
import json, sys
data = json.load(sys.stdin)
for key in data:
    print(f'{key}: {len(data[key]):,} entries')
"
```

See [Output Format](../output-reference/overview.md) for the full bundle structure, section inventory, and reference patterns.

---

## File Naming Convention

### Latest Release

!!! tip "Monthly full or weekly full?"
    `clinvar-gkm_00-latest.json.gz` reflects the **last release of the _previous_ month** — e.g. the `2026-10` monthly is built from the `2026-09-28` release, the last one before ClinVar's October monthly cut. For the current week, use `clinvar-gkm_00-latest_weekly.json.gz` — see [Weekly Full Bundles](weekly-full.md).

Stable filenames that always point to the newest official monthly and the newest weekly full:

```text
clinvar-gkm_00-latest.json.gz               (newest official monthly)
weekly/clinvar-gkm_00-latest_weekly.json.gz (newest weekly full)
```

The `00-` prefix ensures these sort before dated files in directory listings, as in NCBI's `ClinVarVCVRelease_00-latest.xml.gz`.

### Monthly Full Bundles

Official monthly full bundles include the year and month:

```text
clinvar-gkm_yyyy-mm.json.gz                 (current year, at the top of the line folder)
archive/yyyy/clinvar-gkm_yyyy-mm.json.gz    (prior years)
```

For example, `clinvar-gkm_2026-10.json.gz` for ClinVar's October 2026 monthly release.

### Weekly Full Bundles

Weekly full bundles include the ClinVar release year, month, and day, and are kept for the current month only:

```text
weekly/clinvar-gkm_yyyy-mmdd.json.gz
```

For example, `weekly/clinvar-gkm_2026-1018.json.gz` for the October 18, 2026 release.

### Weekly Deltas

Each weekly delta is a bundle and a manifest named with the ClinVar release year, month, and day:

```text
deltas/clinvar-gkm-delta_yyyy-mmdd.json.gz          (current month)
deltas/clinvar-gkm-delta_yyyy-mmdd.manifest.json
deltas/yyyy-mm/clinvar-gkm-delta_yyyy-mmdd.*        (earlier months of the current year)
archive/yyyy/deltas/yyyy-mm/clinvar-gkm-delta_*     (prior years)
```

For example, `deltas/clinvar-gkm-delta_2026-1018.json.gz` for the October 18, 2026 release, which moves to `deltas/2026-10/` when November's first release is published. The delta bundle carries only added and updated records; deletes and per-section change counts are recorded in the accompanying manifest. See [Weekly Deltas](weekly-deltas.md) for the delta model and replay recipe.

Every bundle has a `<file>.sha256` sidecar. All paths are relative to the line folder, `https://data.clinvar-gkm.org/v1/1.1/`.

---

## Working with the File

### Python

```python
import gzip
import json

with gzip.open('clinvar-gkm_00-latest.json.gz', 'rt') as f:
    bundle = json.load(f)

# Look up a specific variation
variant = bundle['variation']['clinvar:10']
print(variant['name'])

# Resolve a reference
allele_ref = variant['members'][0]  # e.g., "#/allele/ga4gh:VA.abc123"
section, key = allele_ref.lstrip('#/').split('/', 1)
allele = bundle[section][key]
```

### Command Line

```bash
# Count entries per section
gunzip -c clinvar-gkm_00-latest.json.gz | python3 -c "
import json, sys
data = json.load(sys.stdin)
for key in data:
    print(f'{key}: {len(data[key]):,}')
"

# Extract a single variation as pretty-printed JSON
gunzip -c clinvar-gkm_00-latest.json.gz | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(json.dumps(data['variation']['clinvar:10'], indent=2))
"
```

---

## Sections Included

Each release file contains the following bundle sections:

| Section | Content |
| --- | --- |
| `sequenceReference` | VRS reference sequences with refget accessions |
| `location` | VRS sequence locations with coordinates |
| `allele` | VRS alleles with state and expressions |
| `copyNumberCount` | Copy number count variants |
| `copyNumberChange` | Copy number change variants |
| `gene` | Gene MappableConcepts |
| `variation` | Cat-VRS categorical variants |
| `condition` | Trait and disease concepts |
| `conditionSet` | Multi-condition groupings |
| `therapy` | Drug therapies (content-addressed, referenced by therapeutic propositions) |
| `therapyGroup` | Combination (multi-drug) therapy groups |
| `submitter` | Submitting organizations |
| `propositionPathogenicity` | Pathogenicity propositions (germline; SCV, VCV, RCV) |
| `propositionOncogenicity` | Oncogenicity propositions (SCV, VCV, RCV) |
| `propositionSomaticClinicalImpact` | Somatic clinical impact propositions: Clinical Significance (SCV, VCV, RCV), and the Diagnostic, Prognostic and Therapeutic Response propositions that SCV evidence lines target |
| `propositionClinvarCustom` | ClinVar custom propositions: the 9 `Clinvar*` types plus `ClinvarUndefinedProposition` (SCV, VCV, RCV) |
| `evidenceLine` | Evidence lines (SCV, VCV, and RCV) |
| `scv` | Submitted classification statements |
| `vcv` | Variation-level aggregate statements |
| `rcv` | Condition-level aggregate statements |

See [Data Model](../output-reference/classes/index.md) for class descriptions and relationship diagrams.
