# Working in Python

ClinVar-GKM records are GA4GH objects, so the GA4GH Python reference implementations read them directly:
[vrs-python](https://github.com/ga4gh/vrs-python) (`ga4gh.vrs`),
[cat-vrs-python](https://github.com/ga4gh/cat-vrs-python) (`ga4gh.cat_vrs`) and
[va-spec-python](https://github.com/ga4gh/va-spec-python) (`ga4gh.va_spec`), collected with other tools in the
[GKM Starter Kit](https://ga4gh.github.io/gkm-starter-kit/). This page loads records from a bundle and from
Parquet, follows their `#/section/id` pointers, builds the libraries' pydantic models from them, and
serializes the models back to JSON.

It assumes the bundle layout described in [Output Format](output-reference/overview.md) and
[ID References](output-reference/id-references.md), and, for the Parquet section, the `data` column described in
[The 22 Tables](parquet/tables.md#the-data-column).

!!! info "Tested with"
    Every code block on this page was run on **2026-10-22**, with Python 3.12, against 1.1.0 data: the
    sample bundle, the 2026-10-18 weekly delta, and the Parquet dataset built from 2026-10-18. Versions:
    `ga4gh.vrs` 2.4.0a6, `ga4gh.cat_vrs` 0.8.0a6, `ga4gh.va_spec` 0.5.0a7, `ga4gh.gkm` 0.4.1,
    `pydantic` 2.14.1, `duckdb` 2.0.0, `ijson` 3.6.0, and the ClinVar-GKM schema tree at tag `1.1.0`.

---

## Install

ClinVar-GKM 1.1.0 is written to **VRS 2.1.1**, **Cat-VRS 1.1.1**, **VA-Spec 1.1.0** and **GKM-Core 1.3.0**.
The library releases that implement exactly those versions are, as of this writing, **pre-releases**:

| Package | Version | Implements | Provides |
| --- | --- | --- | --- |
| `ga4gh.vrs` | 2.4.0a6 | VRS 2.1.1, GKM-Core 1.3.0 | `Allele`, `SequenceLocation`, `SequenceReference`, `CopyNumberCount`, `CopyNumberChange`; `ga4gh_identify` |
| `ga4gh.cat_vrs` | 0.8.0a6 | Cat-VRS 1.1.1 | `CategoricalVariant` and its constraints |
| `ga4gh.va_spec` | 0.5.0a7 | VA-Spec 1.1.0 | `Statement`, `EvidenceLine`, the proposition classes, `Agent`, `ConditionSet`, `TherapyGroup` |
| `ga4gh.gkm` | 0.4.1 | — | the GKM Toolkit; `validate_bundle_schema` for [validating a bundle](#validate-a-bundle) |

The latest stable releases (`ga4gh.vrs` 2.3.3, `ga4gh.cat_vrs` 0.7.2, `ga4gh.va_spec` 0.4.4) implement older
schema versions (VRS 2.0.1, Cat-VRS 1.0.0, VA-Spec 1.0.1) and reject most 1.1.0 records, so pin the
pre-releases. The libraries require Python 3.10 or later, and `ga4gh.gkm` 3.11 or later. `ga4gh.gkm` 0.4.1 pins
the same three pre-releases.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -q "ga4gh.vrs==2.4.0a6" "ga4gh.cat_vrs==0.8.0a6" "ga4gh.va_spec==0.5.0a7" "ga4gh.gkm==0.4.1"
pip install -q duckdb ijson    # for the Parquet and streaming examples
```

Check what is installed and which schema versions the libraries implement:

```python
from importlib.metadata import version

from ga4gh.cat_vrs import CATVRS_VERSION
from ga4gh.core import CORE_VERSION
from ga4gh.va_spec import VASPEC_VERSION
from ga4gh.vrs import VRS_VERSION

for package in ("ga4gh.vrs", "ga4gh.cat_vrs", "ga4gh.va_spec", "ga4gh.gkm"):
    print(f"{package:14} {version(package)}")
print(f"VRS {VRS_VERSION}, Cat-VRS {CATVRS_VERSION}, VA-Spec {VASPEC_VERSION}, GKM-Core {CORE_VERSION}")
```

```text
ga4gh.vrs      2.4.0a6
ga4gh.cat_vrs  0.8.0a6
ga4gh.va_spec  0.5.0a7
ga4gh.gkm      0.4.1
VRS 2.1.1, Cat-VRS 1.1.1, VA-Spec 1.1.0, GKM-Core 1.3.0
```

---

## Get the example files

The examples use two small files:

- **`nch-igm-bundle.json.gz`** (1.6 MB): a self-contained 1.1.0 sub-bundle of every SCV from one submitter
  (IGM Clinical Laboratory, Nationwide Children's Hospital) and everything those SCVs reference, cut from
  the 2026-10-18 release with [Sub-Bundle Extraction](pipeline/sub-bundle.md). Every pointer in it
  resolves inside the file.
- **`clinvar-gkm-delta_2026-1018.json.gz`** (24 MB): the published 2026-10-18 [weekly delta](data-access/weekly-deltas.md).

```bash
curl -sLO https://github.com/clingen-data-model/clinvar-gkm/raw/main/nch-igm-bundle.json.gz
curl -sO https://data.clinvar-gkm.org/v1/1.1/deltas/clinvar-gkm-delta_2026-1018.json.gz
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

Each section's records, except the ClinVar custom propositions, validate as one class from the libraries. A pointer string is accepted wherever a
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
- **ClinVar custom propositions** have no class in va-spec-python yet. The `propositionClinvarCustom` section
  holds ClinVar's own germline proposition types (`ClinvarOtherProposition`, `ClinvarRiskFactorProposition`,
  …). Work with them as plain JSON, as the bundle and the Parquet `data` column provide them. Every other
  section loads into a library class without loss; see [Round trip](#round-trip).

---

## The GKM Toolkit

The [GKM Toolkit](https://ga4gh.github.io/gkm-starter-kit/latest/tools/gkm-toolkit/) (`ga4gh.gkm`) validates a
producer's bundle against that producer's schemas. That is its intended way to validate producer data: you supply
the schemas, and it checks every record against them. Validation works on ClinVar-GKM 1.1.0 bundles today; the
toolkit's loader does not yet read them (see [Loading bundles](#loading-bundles)).

### Validate a bundle { #validate-a-bundle }

The 1.1.0 release was validated this way: `validate_bundle_schema` with a `validator=` whose `referencing`
registry holds the ClinVar-GKM 1.1.0 schemas and the GA4GH schemas they reference, taken from the
`schema/` tree of this repository at tag `1.1.0`. [Release Validation](reference/release-validation.md) lists
the results, and its [verification reports](reference/release-validation.md#verification-reports) record, per
published file, the schemas and tool versions used.

Get the schema tree. The GA4GH schemas come in through the `va-spec` submodule:

```bash
git clone -q --depth 1 --branch 1.1.0 --recurse-submodules --shallow-submodules \
    https://github.com/clingen-data-model/clinvar-gkm.git clinvar-gkm-1.1.0
```

Register every schema in the tree by its `$id`, then validate:

```python
import os
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from ga4gh.gkm.bundles import BundleValidationError
from ga4gh.gkm.bundles.schema_validation import validate_bundle_schema

# Every schema in the 1.1.0 tree, keyed by $id: ClinVar-GKM's own and the GA4GH schemas they reference
schemas = {}
for directory, _, files in os.walk("clinvar-gkm-1.1.0/schema", followlinks=True):
    for name in files:
        try:
            document = json.loads(Path(directory, name).read_text())
        except (ValueError, UnicodeDecodeError):
            continue  # Makefiles and YAML sources
        if isinstance(document, dict) and "$id" in document:
            schemas[document["$id"]] = Resource.from_contents(document)
print(sorted(Counter("/".join(uri.split("/")[5:7]) for uri in schemas).items()))

bundle_schema = json.loads(Path("clinvar-gkm-1.1.0/schema/clinvar-gkm/clinvar-gkm-bundle.schema.json").read_text())
validator = Draft202012Validator(bundle_schema, registry=Registry().with_resources(schemas.items()))

validate_bundle_schema(bundle, bundle_schema, validator=validator)  # raises BundleValidationError on a violation
print("valid:", sum(len(records) for records in bundle.values() if isinstance(records, dict)), "records")

broken = json.loads(json.dumps({"schema_version": "1.1.0", "scv": {scv["id"]: scv}}))
broken["scv"][scv["id"]]["direction"] = "sideways"  # not a VA-Spec direction
try:
    validate_bundle_schema(broken, bundle_schema, validator=validator)
except BundleValidationError as error:
    print(error)
```

```text
[('cat-vrs/1.1.1', 16), ('clinvar-gkm/1.1.0', 28), ('gkm-core/1.3.0', 11), ('va-spec/1.1.0', 40), ('vrs/2.1.1', 26)]
valid: 14761 records
Bundle does not match its JSON Schema at scv/clinvar.submission:SCV000864262.1/direction: 'sideways' is not one of ['supports', 'neutral', 'disputes']
```

Records are validated as published, `#/…` pointers included, against the full ClinVar-GKM profiles. The whole
sample, 14,761 records, took about 2 minutes on one core; `variation` records are the slowest.

The same schemas resolve by `$id` through [w3id.org](https://w3id.org/), so a registry can fetch them on demand
instead of reading a local tree. The bundle schema itself can be fetched the same way, from
`https://w3id.org/clingen/schema/clinvar-gkm/1.1.0/clinvar-gkm-bundle.schema.json`. Fetching makes one request
per schema, so validate a slice, here the first 25 records of each section:

```python
import functools

import requests


@functools.cache
def fetch(uri):
    return Resource.from_contents(requests.get(uri, timeout=30).json())


fetching = Draft202012Validator(bundle_schema, registry=Registry(retrieve=fetch))
part = {"schema_version": bundle["schema_version"]} | {
    section: dict(list(records.items())[:25]) for section, records in bundle.items() if isinstance(records, dict)
}
validate_bundle_schema(part, bundle_schema, validator=fetching)
print("valid:", sum(len(records) for records in part.values() if isinstance(records, dict)), "records;",
      fetch.cache_info().currsize, "schemas fetched")
```

```text
valid: 279 records; 74 schemas fetched
```

`validate_bundle_schema` takes a whole bundle in memory. For multi-GB full bundles, the release used a streaming,
multi-process wrapper around it; that wrapper is proposed for the toolkit, as `gkm-validate-bundle`, in
[ga4gh/gkm-starter-kit#128](https://github.com/ga4gh/gkm-starter-kit/pull/128), which is not yet released.

### Loading bundles { #loading-bundles }

!!! note "The toolkit's loader needs upstream updates for ClinVar-GKM 1.1.0"
    The toolkit's loader tools (`load_bundle`, `Bundle.resolve`, `Bundle.export` and its model conversion) do
    not yet read ClinVar-GKM 1.1.0 bundles. They need updating upstream in two ways:

    1. **The most recent GKM spec versions**, which 1.1.0 data uses: GKM-Core 1.3.0, VRS 2.1.1, Cat-VRS 1.1.1
       and VA-Spec 1.1.0. `ga4gh.gkm` 0.4.1 matches these only through the pre-release libraries above, and
       it accepts a schema version only when it equals the installed library's.
    2. **A way to handle producer-specific classes outside VA-Spec.** The loader resolves schema references
       only against the GA4GH schemas it ships, cannot be given a producer's schemas, and converts records
       only to GA4GH model classes. ClinVar-GKM extends them in `schema/clinvar-gkm/`: the ten custom
       propositions (`ClinvarAffectsProposition` … `ClinvarUndefinedProposition`), `ClinvarGeneContextQualifier`,
       the statement profiles `ClinvarScvStatement`, `ClinvarVcvStatement` and `ClinvarRcvStatement`, the
       variant profile `ClinvarCategoricalVariant` (with `ClinvarCanonicalAllele`,
       `ClinvarCategoricalCnvChange`, `ClinvarCategoricalCnvCount` and `ClinvarNonConstrainedVariant`) and
       `ClinvarSomaticEvidenceLine`. `load_bundle` stops at the first of these references.

    Until then, use the model libraries for the standard classes and plain JSON for the extended ones, as on
    this page. Related work: [ga4gh/gkm-starter-kit#128](https://github.com/ga4gh/gkm-starter-kit/pull/128).

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
    `location` 10–20 seconds, and the proposition → statement → variant lookup above 40–125 seconds in all.
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
        return getattr(va, record["type"])
    return MODELS[section]


tally = Counter()
for section, records in bundle.items():
    if isinstance(records, dict) and section != "propositionClinvarCustom":  # plain JSON, no library class
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
evidenceLine                      identical  1497
scv                               differs    2443
```

Every record comes back identical except for one field:

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

The same sweep over the 2026-10-18 delta (215,170 records, including `vcv` and `rcv`) gives the same result:
all 18,138 SCVs differ only in contribution dates, and every other record, apart from the plain-JSON custom
propositions, is identical.

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

### Validation

[Validate a bundle](#validate-a-bundle) shows the toolkit validating against the ClinVar-GKM schemas, as the
release does; [Release Validation](reference/release-validation.md) lists the release results and links the
published verification reports. The model libraries also validate each record against its GA4GH class as they
load it, as in every example on this page.

### See it applied

- [Harmonizing by VRS Identity](user-story.md): match your variants to ClinVar by recomputed VRS identifier.
- [Auditing a Submitter's Footprint](user-story-audit.md): one submitter's SCVs, end to end.
- The GKM Starter Kit's [user stories](https://ga4gh.github.io/gkm-starter-kit/latest/user-stories/) from other
  GKM data producers.
