# Working in Python

ClinVar-GKM records are GA4GH objects, so the GA4GH Python reference implementations read them directly:
[vrs-python](https://github.com/ga4gh/vrs-python) (`ga4gh.vrs`),
[cat-vrs-python](https://github.com/ga4gh/cat-vrs-python) (`ga4gh.cat_vrs`),
[va-spec-python](https://github.com/ga4gh/va-spec-python) (`ga4gh.va_spec`), and the
[GKM Toolkit](https://ga4gh.github.io/gkm-starter-kit/latest/tools/gkm-toolkit/) (`ga4gh.gkm`) from the
[GKM Starter Kit](https://ga4gh.github.io/gkm-starter-kit/). This page loads records from a bundle and from
Parquet, follows their `#/section/id` pointers, builds the libraries' pydantic models from them, and
serializes the models back to JSON.

It assumes the bundle layout described in [Output Format](output-reference/overview.md) and
[ID References](output-reference/id-references.md), and, for the Parquet section, the `data` column described in
[The 22 Tables](parquet/tables.md#the-data-column).

!!! info "Tested with"
    Every code block on this page was run on **2026-10-22**, with Python 3.12, against 1.1.0 data: the
    sample bundle, the 2026-10-18 weekly delta, and the Parquet dataset built from 2026-10-18. Versions:
    `ga4gh.gkm` 0.4.1, `ga4gh.vrs` 2.4.0a6, `ga4gh.cat_vrs` 0.8.0a6, `ga4gh.va_spec` 0.5.0a7,
    `pydantic` 2.14.1, `duckdb` 2.0.0, `ijson` 3.6.0. Outputs are trimmed where marked with `…`.

---

## Install

ClinVar-GKM 1.1.0 is written to **VRS 2.1.1**, **Cat-VRS 1.1.1**, **VA-Spec 1.1.0** and **GKM-Core 1.3.0**.
The library releases that implement those versions are, as of this writing, **pre-releases**. The GKM Toolkit
pins them, so installing it installs the right set:

| Package | Version | Implements | Provides |
| --- | --- | --- | --- |
| `ga4gh.gkm` | 0.4.1 | — | `load_bundle`, `Bundle.resolve`/`export`, `validate_bundle_schema` |
| `ga4gh.vrs` | 2.4.0a6 | VRS 2.1.1, GKM-Core 1.3.0 | `Allele`, `SequenceLocation`, `SequenceReference`, `CopyNumberCount`, `CopyNumberChange`; `ga4gh_identify` |
| `ga4gh.cat_vrs` | 0.8.0a6 | Cat-VRS 1.1.1 | `CategoricalVariant` and its constraints |
| `ga4gh.va_spec` | 0.5.0a7 | VA-Spec 1.1.0 | `Statement`, `EvidenceLine`, the proposition classes, `Agent`, `ConditionSet`, `TherapyGroup` |

`ga4gh.gkm` requires Python 3.11 or later.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -q "ga4gh.gkm==0.4.1" "ga4gh.vrs==2.4.0a6" "ga4gh.cat_vrs==0.8.0a6" "ga4gh.va_spec==0.5.0a7"
pip install -q duckdb ijson    # for the Parquet and streaming examples
```

!!! warning "The latest stable releases do not read 1.1.0 data"
    A plain `pip install ga4gh.vrs ga4gh.cat_vrs ga4gh.va_spec` installs the latest *stable* releases:
    `ga4gh.vrs` 2.3.3, `ga4gh.cat_vrs` 0.7.2 and `ga4gh.va_spec` 0.4.4. They implement VRS 2.0.1,
    Cat-VRS 1.0.0 and VA-Spec 1.0.1 and reject most 1.1.0 records. VRS records and submitters still load;
    genes, conditions, nearly every variation, and every proposition, evidence line and statement fail. For
    example:

    ```text
    Statement: contributions.0.contributor
      Input should be a valid dictionary or instance of Agent [type=model_type, input_value='#/submitter/clinvar.submitter:196472', input_type=str]
    VariantPathogenicityProposition: subjectVariant
      Field required [type=missing, …]
    CategoricalVariant: constraints.0.DefiningAlleleConstraint.relations.0.type
      Extra inputs are not permitted [type=extra_forbidden, input_value='MappableConcept', input_type=str]
    ```

    Install the versions in the table above until stable releases catch up with the 1.1.0 schemas.

Check what is installed and which schema versions the toolkit accepts:

```python
from importlib.metadata import version
from ga4gh.gkm.bundles import supported_gkm_versions

for package in ("ga4gh.gkm", "ga4gh.vrs", "ga4gh.cat_vrs", "ga4gh.va_spec"):
    print(f"{package:14} {version(package)}")
print(supported_gkm_versions())
```

```text
ga4gh.gkm      0.4.1
ga4gh.vrs      2.4.0a6
ga4gh.cat_vrs  0.8.0a6
ga4gh.va_spec  0.5.0a7
{'gkm-core': '1.3.0', 'vrs': '2.1.1', 'cat-vrs': '1.1.1', 'va-spec': '1.1.0'}
```

---

## Get the example files

The examples use three small files:

- **`nch-igm-bundle.json.gz`** (1.6 MB): a self-contained 1.1.0 sub-bundle of every SCV from one submitter
  (IGM Clinical Laboratory, Nationwide Children's Hospital) and everything those SCVs reference, cut from
  the 2026-10-18 release with [Sub-Bundle Extraction](pipeline/sub-bundle.md). Every pointer in it
  resolves inside the file.
- **`clinvar-gkm-delta_2026-1018.json.gz`** (24 MB): the published 2026-10-18 [weekly delta](data-access/weekly-deltas.md).
- **`clinvar-gkm-bundle.schema.json`**: the 1.1.0 bundle schema, from the `1.1.0` tag. Its `$id` does not
  resolve, so it is fetched from GitHub.

```bash
curl -sLO https://github.com/clingen-data-model/clinvar-gkm/raw/main/nch-igm-bundle.json.gz
curl -sO https://data.clinvar-gkm.org/v1/1.1/deltas/clinvar-gkm-delta_2026-1018.json.gz
curl -sLO https://raw.githubusercontent.com/clingen-data-model/clinvar-gkm/1.1.0/schema/clinvar-gkm/clinvar-gkm-bundle.schema.json
```

The full bundles are about 4.8 GB compressed. Don't `json.load` one; see [Large bundles](#large-bundles).

---

## Load a bundle and follow pointers

A bundle is one JSON object whose sections map an id to a record. `json.load` is enough to read one:

```python
import gzip
import json

with gzip.open("nch-igm-bundle.json.gz", "rt") as f:
    bundle = json.load(f)

print(bundle["schema_version"])
print({section: len(records) for section, records in bundle.items() if isinstance(records, dict)})


def resolve(pointer):
    """Return the record that a '#/section/id' pointer names."""
    section, key = pointer.removeprefix("#/").split("/", 1)
    return bundle[section][key]
```

```text
1.1.0
{'sequenceReference': 24, 'location': 1913, 'allele': 2027, 'copyNumberChange': 1, 'gene': 460, 'variation': 2032, 'condition': 390, 'conditionSet': 33, 'submitter': 1, 'propositionPathogenicity': 943, 'propositionSomaticClinicalImpact': 2994, 'propositionClinvarCustom': 3, 'evidenceLine': 1497, 'scv': 2443}
```

Records point to each other with `#/section/id` strings. Follow one SCV down to its reference sequence:
statement → proposition → variation → defining allele → location → sequence reference.

```python
scv = bundle["scv"]["clinvar.submission:SCV000864262.1"]
proposition = resolve(scv["proposition"])
variation = resolve(proposition["subject"])
allele = resolve(variation["constraints"][0]["allele"])
location = resolve(allele["location"])
sequence = resolve(location["sequenceReference"])

print(scv["classification"]["name"], "|", resolve(scv["contributions"][0]["contributor"])["name"])
print(proposition["type"], proposition["predicate"], "->", resolve(proposition["object"])["name"])
print(variation["id"], variation["name"])
print(allele["id"], allele["name"])
print(location["id"], location["start"], location["end"])
print(sequence["refgetAccession"], sequence["name"])
```

```text
Benign | Institute for Genomic Medicine (IGM) Clinical Laboratory, Nationwide Children's Hospital
VariantPathogenicityProposition isCausalFor -> not specified
clinvar:599425 NM_018486.3(HDAC8):c.20C>T (p.Pro7Leu)
ga4gh:VA.yXEFCuYP7t_V3ALpYIMvWTy4PhfvT8ts NC_000023.11:g.72572742G>A
ga4gh:SL.sk5GccwF1vh_M4zGnjDYkoYNGrRKc6uW 72572741 72572742
SQ.w0WZEvgJF0zf_P4yyTzjjv9oW1z61HHP NC_000023.11
```

!!! note "A delta is not self-contained"
    A weekly delta carries only the records that changed, so its pointers can name records that are only in
    the full bundle it applies to. The 2026-10-18 delta, for example, has no `sequenceReference` section.
    Resolve a delta's pointers against the full bundle after [applying the delta](data-access/weekly-deltas.md).

---

## Into the GA4GH models

Each section's records validate as one class from the libraries. A pointer string is accepted wherever a
field allows a reference: the models type it as `iriReference`, and its `.root` holds the pointer.

### VRS alleles and their identifiers

```python
from ga4gh.core import ga4gh_identify
from ga4gh.vrs import models as vrs

vrs_allele = vrs.Allele(**allele)
print(type(vrs_allele.location).__name__, vrs_allele.location.root)


def content(record):
    """A record without its stored identifiers."""
    return {k: v for k, v in record.items() if k not in ("id", "digest")}


# Recompute the VRS identifier from content alone: inline the location and its sequence reference
fresh = vrs.Allele(**content(allele) | {"location": content(location) | {"sequenceReference": sequence}})
print(ga4gh_identify(fresh), ga4gh_identify(fresh) == allele["id"])
```

```text
iriReference #/location/ga4gh:SL.sk5GccwF1vh_M4zGnjDYkoYNGrRKc6uW
ga4gh:VA.yXEFCuYP7t_V3ALpYIMvWTy4PhfvT8ts True
```

`ga4gh_identify` needs the location inline: the allele's digest is computed over its location's digest, and
the location's over its sequence reference. Recomputed this way, all 2,027 allele ids and the one
`copyNumberChange` id in the sample match the published ids.

### Cat-VRS categorical variants

A `variation` record is a Cat-VRS `CategoricalVariant`. Its defining constraint points to an `allele` (or, for
copy-number variants, a `location`) record:

```python
from ga4gh.cat_vrs import models as catvrs

categorical = catvrs.CategoricalVariant(**variation)
constraint = categorical.constraints[0].root
print(type(constraint).__name__, constraint.allele.root)
print([relation.primaryCoding.code.root for relation in constraint.relations])
print({e.name: e.value for e in categorical.extensions if isinstance(e.value, str)})
```

```text
DefiningAlleleConstraint #/allele/ga4gh:VA.yXEFCuYP7t_V3ALpYIMvWTy4PhfvT8ts
['liftover_to', 'transcribed_to']
{'categoricalVariationType': 'CanonicalAllele', 'definingVrsVariationType': 'Allele', 'clinvarVariationType': 'single nucleotide variant', 'clinvarSubclassType': 'SimpleAllele', 'clinvarCytogeneticLocation': 'Xq13.1'}
```

### VA-Spec propositions and statements

```python
from ga4gh.va_spec import base as va

pathogenicity = va.VariantPathogenicityProposition(**proposition)
statement = va.Statement(**scv)
print(pathogenicity.predicate, pathogenicity.subject.root, pathogenicity.object.root)
print(statement.direction, statement.strength.name, statement.classification.primaryCoding.code.root)
print(statement.proposition.root)
print([e.name for e in statement.extensions])
```

```text
isCausalFor #/variation/clinvar:599425 #/condition/clinvar.trait:16789
disputes Definitive benign
#/propositionPathogenicity/SCV000864262-PATH
['clinvarScvId', 'clinvarScvVersion', 'submittedCondition', 'clinvarScvReviewStatus', 'submittedScvLocalKey', 'submissionLevel']
```

Records in the `scv`, `vcv` and `rcv` sections load as `Statement`, and `evidenceLine` records as
`EvidenceLine`. The ClinVar-GKM statement profiles (`ClinvarScvStatement`, `ClinvarVcvStatement`,
`ClinvarRcvStatement`) add no top-level fields to VA-Spec's `Statement`; their ClinVar-specific content is in
`extensions`.

### Extensions and ClinVar-specific types

- **Extensions** load as GKM-Core `Extension` objects. `name` is a string; `value` keeps whatever JSON the
  record holds, including the structured values such as `submittedCondition` and `clinvarHgvsList`. The
  libraries don't interpret them. [Statement extensions](output-reference/scv-statements.md) and
  [Variations](output-reference/cat-vrs.md) document each one.
- **ClinVar custom propositions** have no class in va-spec-python. The `propositionClinvarCustom` section
  holds ClinVar's own germline proposition types (`ClinvarOtherProposition`, `ClinvarRiskFactorProposition`,
  …), which extend VA-Spec's `SubjectVariantProposition`. That base class accepts them, but it ignores fields
  it doesn't declare, so their qualifiers (`geneContextQualifier`, `modeOfInheritanceQualifier`) are
  dropped:

```python
custom = bundle["propositionClinvarCustom"]["SCV002072498-OTH"]
print(custom["type"], hasattr(va, custom["type"]))

generic = va.SubjectVariantProposition(**custom)
print(generic.type, sorted(set(custom) - set(generic.model_dump(exclude_none=True))))
```

```text
ClinvarOtherProposition False
ClinvarOtherProposition ['geneContextQualifier']
```

Keep custom propositions as dicts, or read the qualifiers from the dict, when you need them. Every
other section loads without loss; see [Round trip](#round-trip).

---

## Load with the GKM Toolkit

The toolkit's `load_bundle` checks every pointer, validates the bundle against its producer schema, and
returns a `Bundle` whose records are typed models with their pointers resolved. It requires the producer
schema. With `ga4gh.gkm` 0.4.1, the ClinVar-GKM bundle schema fails:

```python
from ga4gh.gkm.bundles import load_bundle

try:
    with gzip.open("nch-igm-bundle.json.gz", "rt") as f:
        load_bundle(f, schema="clinvar-gkm-bundle.schema.json")
except Exception as error:
    print(type(error).__name__, error)
```

```text
BundleSerializationError Bundle JSON Schema reference could not be resolved locally: Unresolvable: https://w3id.org/clingen/schema/clinvar-gkm/1.1.0/json/ClinvarGeneContextQualifier
```

The toolkit resolves `$ref`s offline, and only to the GA4GH schemas of its installed libraries. The
ClinVar-GKM profile schemas (`https://w3id.org/clingen/schema/clinvar-gkm/…`) are not among them, and 0.4.1
has no way to add them. To load the bundle, replace each profile `$ref` with an open object schema. Sections
whose schema is a GA4GH class keep their validation; profile-typed sections (`variation`, `scv`, `vcv`, `rcv`,
`propositionClinvarCustom`, part of `evidenceLine`) are not validated on load. They are still typed by their
`type` field. [Validate a bundle](#validate-a-bundle) checks them in full.

```python
import io


def open_profiles(node):
    """Replace each ClinVar-GKM profile $ref with an open object schema."""
    if isinstance(node, dict):
        if node.get("$ref", "").startswith("https://w3id.org/clingen/"):
            return {"type": "object"}
        return {key: open_profiles(value) for key, value in node.items()}
    if isinstance(node, list):
        return [open_profiles(value) for value in node]
    return node


with open("clinvar-gkm-bundle.schema.json") as f:
    consumer_schema = open_profiles(json.load(f))

with gzip.open("nch-igm-bundle.json.gz", "rt") as f:
    kit = load_bundle(f, schema=io.StringIO(json.dumps(consumer_schema)))

for name in kit:
    types = sorted({type(record).__name__ for record in kit[name].values()})
    print(f"{name:33} {len(kit[name]):5}  {', '.join(types)}")
```

```text
sequenceReference                    24  SequenceReference
location                           1913  SequenceLocation
allele                             2027  Allele
copyNumberChange                      1  CopyNumberChange
gene                                460  MappableConcept
variation                          2032  CategoricalVariant
condition                           390  MappableConcept
conditionSet                         33  ConditionSet
submitter                             1  Agent
propositionPathogenicity            943  VariantPathogenicityProposition
propositionSomaticClinicalImpact   2994  VariantClinicalSignificanceProposition, VariantDiagnosticProposition
propositionClinvarCustom              3  dict
evidenceLine                       1497  EvidenceLine
scv                                2443  Statement
```

Loading the 1.6 MB sample takes about 40 seconds and holds every record twice, compact and expanded. Use
`load_bundle` for sub-bundles and small extracts, not for full bundles or deltas.

Typed records come back with their pointers already resolved. `resolve` follows a pointer, and `export`
serializes a record: with its pointers (`deep=False`, the default) or with every reachable record inlined
(`deep=True`):

```python
typed = kit.scv["clinvar.submission:SCV000864262.1"]
subject = typed.proposition.subject
print(type(typed).__name__, type(typed.proposition).__name__, type(subject).__name__, subject.name)
print(type(kit.resolve("#/allele/" + allele["id"])).__name__)

shallow = kit.export(typed)
deep = kit.export(typed, deep=True)
print(shallow["proposition"])
print(deep["proposition"]["subject"]["constraints"][0]["allele"]["location"]["sequenceReference"]["refgetAccession"])
print(len(json.dumps(shallow)), len(json.dumps(deep)))

standalone = va.Statement(**deep)
print(type(standalone.proposition.subject.constraints[0].root.allele.location.sequenceReference).__name__)
```

```text
Statement VariantPathogenicityProposition CategoricalVariant NM_018486.3(HDAC8):c.20C>T (p.Pro7Leu)
Allele
#/propositionPathogenicity/SCV000864262-PATH
SQ.w0WZEvgJF0zf_P4yyTzjjv9oW1z61HHP
2426 10434
SequenceReference
```

A deep export is a standalone VA-Spec statement that any VA-Spec consumer can read without the bundle.
The toolkit has the same gap as va-spec-python for custom propositions: `propositionClinvarCustom` records stay
dicts, and a statement's inline custom proposition is a base `Proposition` without its qualifiers. `export`
restores them from the bundle.

---

## From Parquet

Every [Parquet table](parquet/tables.md) has a `data` column holding each record's complete JSON as a string,
exactly as in the bundle, so `json.loads(data)` gives the same record the bundle does. Read a few rows
remotely with DuckDB, and build the models:

```python
import duckdb

P = "https://data.clinvar-gkm.org/v1/1.1/parquet"

rows = duckdb.sql(f"SELECT id, location_id, data FROM '{P}/allele.parquet' LIMIT 3").fetchall()
for allele_id, location_id, data in rows:
    print(allele_id, vrs.Allele(**json.loads(data)).name)
```

```text
ga4gh:VA.gaVM-oJ-UMO3cZMxe8-U0ktIKu7YvQK4 NC_000015.10:g.78513242G>A
ga4gh:VA.plnkuDHIFWLbLgn729ZU4dZlFhtM1Jco NC_000016.10:g.31224570C>A
ga4gh:VA.0Om9Ephu36fbTCIM_H4ushaqsJGXPOes NC_000017.11:g.41715616G>A
```

Inside `data`, references are bundle pointers; the typed columns carry the bare id (`location_id`). Follow a
reference by looking the id up in the table its prefix names (see
[Ids tell you where to look](parquet/tables.md#ids-tell-you-where-to-look)). Here, the alleles' locations and
sequence references, and the same identifier check as above:

```python
def by_id(table, ids, columns="id, data"):
    """Fetch the rows of one table whose id is in ids, keyed by id."""
    marks = ", ".join("?" * len(ids))
    query = f"SELECT {columns} FROM '{P}/{table}.parquet' WHERE id IN ({marks})"
    return {row[0]: row[1:] for row in duckdb.execute(query, list(ids)).fetchall()}


locations = by_id("location", [location_id for _, location_id, _ in rows], "id, sequence_reference_id, data")
sequences = by_id("sequenceReference", [sequence_id for sequence_id, _ in locations.values()])

for allele_id, location_id, data in rows:
    sequence_id, location_data = locations[location_id]
    inline = content(json.loads(location_data)) | {"sequenceReference": json.loads(sequences[sequence_id][0])}
    recomputed = ga4gh_identify(vrs.Allele(**content(json.loads(data)) | {"location": inline}))
    print(allele_id, recomputed == allele_id)
```

```text
ga4gh:VA.gaVM-oJ-UMO3cZMxe8-U0ktIKu7YvQK4 True
ga4gh:VA.plnkuDHIFWLbLgn729ZU4dZlFhtM1Jco True
ga4gh:VA.0Om9Ephu36fbTCIM_H4ushaqsJGXPOes True
```

The same pattern links a proposition to its statement and its variant. `scv.proposition_id` and
`variation.id` are the join keys ([Joining Tables](parquet/joining.md) covers every hop):

```python
(prop_id, prop_data), = duckdb.sql(
    f"SELECT id, data FROM '{P}/propositionClinvarCustom.parquet' "
    "WHERE type = 'ClinvarRiskFactorProposition' AND gene_context_id IS NOT NULL LIMIT 1"
).fetchall()
(scv_data,), = duckdb.execute(
    f"SELECT data FROM '{P}/scv.parquet' WHERE proposition_id = ?", [prop_id]).fetchall()
risk = json.loads(prop_data)
variant_id = risk["subject"].removeprefix("#/variation/")
(variant_data,) = by_id("variation", [variant_id])[variant_id]

print(prop_id, risk["predicate"], risk["geneContextQualifier"]["name"])
print(va.Statement(**json.loads(scv_data)).classification.name)
print(catvrs.CategoricalVariant(**json.loads(variant_data)).name)
```

```text
SCV000821694-RF isRiskFactorFor APC
risk factor
NM_000038.6(APC):c.3920T>A (p.Ile1307Lys)
```

!!! warning "Remote reads of big tables are slow"
    The files are not sorted by id, so a filter reads the filtered column from every row group, one HTTP
    request each. On 2026-10-22, a `LIMIT 3` read of a large table took 10–25 seconds, an id lookup in
    `location` 10–20 seconds, and the proposition → statement → variant lookup above 60–90 seconds in all.
    The CDN allows 250 requests per 10 seconds per client. For anything beyond a handful of lookups, download
    the tables you need and query them locally ([Working at Scale](parquet/performance.md#local-or-remote)).

---

## Round trip

`model_dump(mode="json", exclude_none=True)` serializes a model back to JSON. Records carry no `null` fields
(except the open bound of a VRS `Range`, which survives), so `exclude_none=True` loses nothing. Compare every
record of the sample bundle with its round trip:

```python
from collections import Counter

from ga4gh.core.models import MappableConcept

MODELS = {
    "sequenceReference": vrs.SequenceReference, "location": vrs.SequenceLocation, "allele": vrs.Allele,
    "copyNumberCount": vrs.CopyNumberCount, "copyNumberChange": vrs.CopyNumberChange,
    "gene": MappableConcept, "condition": MappableConcept, "therapy": MappableConcept,
    "conditionSet": va.ConditionSet, "therapyGroup": va.TherapyGroup, "submitter": va.Agent,
    "variation": catvrs.CategoricalVariant, "evidenceLine": va.EvidenceLine,
    "scv": va.Statement, "vcv": va.Statement, "rcv": va.Statement,
}


def model_for(section, record):
    if section.startswith("proposition"):
        return getattr(va, record["type"], va.SubjectVariantProposition)
    return MODELS[section]


tally = Counter()
for section, records in bundle.items():
    if isinstance(records, dict):
        for record in records.values():
            dumped = model_for(section, record)(**record).model_dump(mode="json", exclude_none=True)
            tally[section, "identical" if dumped == record else "differs"] += 1
for (section, result), n in tally.items():
    print(f"{section:33} {result:9} {n:5}")
```

```text
sequenceReference                 identical    24
location                          identical  1913
allele                            identical  2027
copyNumberChange                  identical     1
gene                              identical   460
variation                         identical  2032
condition                         identical   390
conditionSet                      identical    33
submitter                         identical     1
propositionPathogenicity          identical   943
propositionSomaticClinicalImpact  identical  2994
propositionClinvarCustom          identical     2
propositionClinvarCustom          differs       1
evidenceLine                      identical  1497
scv                               differs    2443
```

Every record comes back identical except in two cases:

- **Contribution dates.** VA-Spec 1.1.0 types `Contribution.date` as a date-time. The records carry a date
  (`"2019-01-22"`); the model parses it as midnight and writes it back with a time:

    ```python
    dumped = statement.model_dump(mode="json", exclude_none=True)
    print(scv["contributions"][0]["date"], "->", dumped["contributions"][0]["date"])
    ```

    ```text
    2019-01-22 -> 2019-01-22T00:00:00
    ```

    Every SCV has contribution dates, so every SCV differs in those fields only. Compare dates by their
    first ten characters, or restore them after dumping.
- **ClinVar custom propositions** loaded with `SubjectVariantProposition` lose their qualifiers, as
  shown [above](#extensions-and-clinvar-specific-types). Those without a qualifier round-trip identically.

The same sweep over the 2026-10-18 delta (215,170 records, including `vcv` and `rcv`) gives the same result.
All 18,138 SCVs differ only in contribution dates; 41 of the 201 custom propositions lose
`geneContextQualifier`, one of them also `modeOfInheritanceQualifier`. Every other record is identical.

The toolkit's export round-trips the same way. Its typed records carry the same date normalization:

```python
exported = kit.export()
print([section for section in bundle if exported.get(section) != bundle[section]])
```

```text
['scv']
```

Key order is not preserved: the models write fields in class-definition order. Compare parsed objects, not
strings.

---

## Large bundles { #large-bundles }

A full bundle is about 4.8 GB compressed, and a `json.load` of one does not fit in 16 GB of memory. Three ways
to work with it:

- **Stream it.** [`ijson`](https://pypi.org/project/ijson/) reads one record at a time; `kvitems(f, "scv")`
  yields each `(id, record)` of a section. Build a model per record, keep what you need, and memory stays
  flat. One pass reads the whole file.
- **Query the Parquet** for the latest release, and fetch the `data` of just the records you need, as above.
- **Cut a sub-bundle.** The [Sub-Bundle Extraction](pipeline/sub-bundle.md) tool, which made the sample
  above, extracts a self-contained bundle for a list of statements. It reads the project's BigQuery tables,
  not a published file, so it needs access to those datasets.

Streaming the delta's `scv` section, for example, to count classifications:

```python
import ijson

classifications = Counter()
with gzip.open("clinvar-gkm-delta_2026-1018.json.gz", "rb") as f:
    for scv_id, record in ijson.kvitems(f, "scv", use_float=True):
        classifications[va.Statement(**record).classification.name] += 1
print(sum(classifications.values()), classifications.most_common(4))
```

```text
18138 [('Uncertain significance', 9724), ('Likely benign', 2766), ('Likely pathogenic', 2482), ('Pathogenic', 2337)]
```

`use_float=True` makes ijson return floats instead of `Decimal`.

---

## Going further

### Validate a bundle { #validate-a-bundle }

The toolkit's `validate_bundle_schema` accepts a prepared validator. Give it a `referencing` registry that
fetches each referenced schema from its `$id` (the GA4GH and ClinVar-GKM class schemas resolve through
[w3id.org](https://w3id.org/)), and it validates every section against the full ClinVar-GKM profiles. Records
are validated as published, pointers included:

```python
import functools

import requests
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from ga4gh.gkm.bundles.schema_validation import validate_bundle_schema


@functools.cache
def fetch(uri):
    return Resource.from_contents(requests.get(uri, timeout=30).json())


with open("clinvar-gkm-bundle.schema.json") as f:
    schema = json.load(f)
validator = Draft202012Validator(schema, registry=Registry(retrieve=fetch))

# The first 25 records of each section; raises BundleValidationError on the first violation
part = {"schema_version": bundle["schema_version"]} | {
    section: dict(list(records.items())[:25]) for section, records in bundle.items() if isinstance(records, dict)
}
validate_bundle_schema(part, schema, validator=validator)
print("valid:", sum(len(records) for records in part.values() if isinstance(records, dict)), "records")
```

```text
valid: 279 records
```

The first call fetches about 75 schema documents. Strict validation is CPU-bound: the whole sample
(14,761 records) took about 5 minutes on one core, and `variation` records are the slowest. The release
gates validate every published record with `validate_bundle_schema` and a local copy of the same schemas; see
[Release Validation](reference/release-validation.md).
A streaming, multi-process validator with a `gkm-validate-bundle` command is proposed for the toolkit in
[ga4gh/gkm-starter-kit#128](https://github.com/ga4gh/gkm-starter-kit/pull/128); it is not yet released.
The toolkit's own documentation covers
[schema validation](https://ga4gh.github.io/gkm-starter-kit/latest/tools/gkm-toolkit/api/schema-validation/)
and [containers](https://ga4gh.github.io/gkm-starter-kit/latest/tools/gkm-toolkit/api/containers/).

### See it applied

- [Harmonizing by VRS Identity](user-story.md): match your variants to ClinVar by recomputed VRS identifier.
- [Auditing a Submitter's Footprint](user-story-audit.md): one submitter's SCVs, end to end.
- The GKM Starter Kit's [user stories](https://ga4gh.github.io/gkm-starter-kit/latest/user-stories/) from other
  GKM data producers.
