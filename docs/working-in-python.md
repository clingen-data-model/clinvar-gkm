# Working in Python

ClinVar-GKM records are GA4GH objects, so the GA4GH Python reference implementations read them directly:
[vrs-python](https://github.com/ga4gh/vrs-python) (`ga4gh.vrs`),
[cat-vrs-python](https://github.com/ga4gh/cat-vrs-python) (`ga4gh.cat_vrs`) and
[va-spec-python](https://github.com/ga4gh/va-spec-python) (`ga4gh.va_spec`), collected with other tools in the
[GKM Starter Kit](https://ga4gh.github.io/gkm-starter-kit/). This page loads records from a bundle and from
Parquet, follows their `#/section/id` pointers, builds the libraries' pydantic models from them, and
serializes the models back to JSON.

It assumes the bundle layout described in [Output Format](output-reference/overview.md) and
[ID References](output-reference/id-references.md), and, for the Parquet section, the tables described in
[The 20 Tables](parquet/tables.md).

!!! info "Tested with"
    Every code block on this page was run on **2026-11-21** with:

    - Python 3.14.5 (an earlier run, on 1.1.0 data, used 3.12.8), `ga4gh.vrs` 2.4.0a6, `ga4gh.cat_vrs`
      0.8.0a6, `ga4gh.va_spec` 0.5.0a7, `ga4gh.gkm` 0.4.1, `pydantic` 2.14.4, `duckdb` 1.5.4, `pyarrow`
      26.0.1, `ijson` 3.6.0, `requests` 2.34.2, `gkm-bundle-parquet` 2.0.0 (through uv 0.6.14), and the
      ClinVar-GKM schema tree at tag `1.2.0`.
    - **Bundle examples:** 1.2.0 data, the 2026-11-15 weekly delta.
    - **Parquet examples:** the published 2.0 tables at `v1/1.2/parquet/` (2026-11-15 release), and a mini-bundle
      cut from the 2026-11 full bundle.

    The Parquet files are written with DuckDB 1.5.4: the `duckdb_version` in their `manifest.json`.

!!! note "Prerequisites"
    - **Python 3.11 or later** (the model libraries need 3.10, `ga4gh.gkm` 3.11), with the packages in
      [Install](#install).
    - **git**, to get the schema tree for [Validate a bundle](#validate-a-bundle).
    - **[uv](https://docs.astral.sh/uv/getting-started/installation/)**, for `uvx gkm-bundle-parquet` in
      [Statements, propositions and variants](#statements-propositions-and-variants), or
      `pip install gkm-bundle-parquet==2.0.0` instead.
    - **Network access** to `data.clinvar-gkm.org` (the delta, and the Parquet tables, which the examples read
      remotely) and `w3id.org` (schemas fetched on demand).
    - **Data:** the 5 MB weekly delta from [Get the example files](#get-the-example-files). Only the
      `gkm-bundle-parquet select` example reads a full bundle: 4.9 GB compressed (68.5 GB decompressed), streamed
      from disk, about 10 minutes.

    Run the Python blocks in order, in one Python session: each block uses the names (`bundle`, `resolve`, `scv`,
    `vrs`, `rows`, …) defined by the blocks before it.

---

## Install

ClinVar-GKM 1.2.0, like 1.1.0, is written to **VRS 2.1.1**, **Cat-VRS 1.1.1**, **VA-Spec 1.1.0** and
**GKM-Core 1.3.0**, so the same library versions read both. The library releases that implement exactly those
versions are, as of this writing, **pre-releases**:

| Package | Version | Implements | Provides |
| --- | --- | --- | --- |
| `ga4gh.vrs` | 2.4.0a6 | VRS 2.1.1, GKM-Core 1.3.0 | `Allele`, `SequenceLocation`, `SequenceReference`, `CopyNumberCount`, `CopyNumberChange`; `ga4gh_identify` |
| `ga4gh.cat_vrs` | 0.8.0a6 | Cat-VRS 1.1.1 | `CategoricalVariant` and its constraints |
| `ga4gh.va_spec` | 0.5.0a7 | VA-Spec 1.1.0 | `Statement`, `EvidenceLine`, the proposition classes, `Agent`, `ConditionSet`, `TherapyGroup` |
| `ga4gh.gkm` | 0.4.1 | — | the GKM Toolkit; `validate_bundle_schema` for [validating a bundle](#validate-a-bundle) |

The latest stable releases (`ga4gh.vrs` 2.3.3, `ga4gh.cat_vrs` 0.7.2, `ga4gh.va_spec` 0.4.4) implement older
schema versions (VRS 2.0.1, Cat-VRS 1.0.0, VA-Spec 1.0.1) and reject most ClinVar-GKM records, so pin the
pre-releases. The libraries require Python 3.10 or later, and `ga4gh.gkm` 3.11 or later. `ga4gh.gkm` 0.4.1 pins
the same three pre-releases.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -q "ga4gh.vrs==2.4.0a6" "ga4gh.cat_vrs==0.8.0a6" "ga4gh.va_spec==0.5.0a7" "ga4gh.gkm==0.4.1"
pip install -q "duckdb==1.5.4" pyarrow ijson requests    # Parquet, streaming and schema-fetching examples
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

The bundle examples use one small file, **`clinvar-gkm-delta_2026-1115.json.gz`** (5 MB): the published
2026-11-15 [weekly delta](data-access/weekly-deltas.md), a 1.2.0 bundle of every record that changed that week.

Its path changes when its month ends (it moves to `deltas/2026-11/`), so the commands look it up in the line's
`index.json`:

```bash
DELTA=$(curl -fsS https://data.clinvar-gkm.org/v1/1.2/index.json | python3 -c '
import json, sys
print(next(d["bundle"]["path"] for d in json.load(sys.stdin)["deltas"] if d["release"] == "2026-11-15"))')
curl -fsO "https://data.clinvar-gkm.org/${DELTA}"
```

The full bundles are about 4.9 GB compressed (68.5 GB decompressed). Don't `json.load` one; see
[Large bundles](#large-bundles).

The repository also has **`nch-igm-bundle.json.gz`** (1.6 MB), a self-contained 1.1.0 sub-bundle of every SCV
from one submitter, cut with [Sub-Bundle Extraction](pipeline/sub-bundle.md), in which every pointer resolves
inside the file (`curl -fsLO https://github.com/clingen-data-model/clinvar-gkm/raw/main/nch-igm-bundle.json.gz`).
The same libraries read it; validate it against the schema tree at tag `1.1.0`, not `1.2.0`.

---

## Load a bundle and follow pointers

A bundle is one JSON object whose sections map an id to a record. `json.load` is enough to read one:

```python
import gzip
import json

with gzip.open("clinvar-gkm-delta_2026-1115.json.gz", "rt") as f:
    bundle = json.load(f)

print(bundle["schema_version"])
print({section: len(records) for section, records in bundle.items() if isinstance(records, dict)})


def resolve(pointer):
    """Return the record that a '#/section/id' pointer names."""
    section, key = pointer.removeprefix("#/").split("/", 1)
    return bundle[section][key]
```

```text
1.2.0
{'location': 176, 'allele': 230, 'copyNumberChange': 3, 'gene': 5, 'variation': 5471, 'condition': 190, 'conditionSet': 138, 'submitter': 10, 'propositionPathogenicity': 3399, 'propositionClinvarCustom': 325, 'evidenceLine': 6064, 'scv': 17562, 'vcv': 2941, 'rcv': 2548}
```

Records point to each other with `#/section/id` strings. Continuing from the block above (`bundle`,
`resolve`), follow one SCV down toward its reference sequence: statement → proposition → variation → defining
allele → location → sequence reference.

```python
scv = bundle["scv"]["clinvar.submission:SCV008145211.1"]
proposition = resolve(scv["proposition"])
variation = resolve(proposition["subject"])
allele = resolve(variation["constraints"][0]["allele"])
location = resolve(allele["location"])

print(scv["classification"]["name"], "|", resolve(scv["contributions"][0]["contributor"])["name"])
print(proposition["type"], proposition["predicate"], "->", resolve(proposition["object"])["name"])
print(variation["id"], variation["name"])
print(allele["id"], allele["name"])
print(location["id"], location["start"], location["end"])
print(location["sequenceReference"], "| sequenceReference section in the delta:", "sequenceReference" in bundle)

# The delta has no sequenceReference section. A sequenceReference key is the sequence's refget accession,
# and that, with the type, is all a VRS identifier uses of it (see the next section)
sequence = {"type": "SequenceReference", "refgetAccession": location["sequenceReference"].rsplit("/", 1)[1]}
```

```text
Likely pathogenic | Department of Ophthalmology, Seoul National University Bundang Hospital
VariantPathogenicityProposition isCausalFor -> RP1-related dominant retinopathy
clinvar:5042631 NM_006269.2(RP1):c.2238_2239del (p.Lys746_Ser747insTer)
ga4gh:VA.1Oo5_TVyd33l8M9QsAac-ULaZR86hDCx NC_000008.11:g.54626120_54626121del
ga4gh:SL.sF-Pr6l0-_uRAtk8bv9UzOPYvr6TK9IC 54626117 54626121
#/sequenceReference/SQ.209Z7zJ-mFypBEWLk4rNC6S_OxY5p7bs | sequenceReference section in the delta: False
```

!!! note "A delta is not self-contained"
    A weekly delta carries only the records that changed, so its pointers can name records that are only in
    the full bundle it applies to. The 2026-11-15 delta, for example, has no `sequenceReference` section, and
    57 of its alleles and copy-number changes point to a `location` that is only in the full bundle.
    Resolve a delta's pointers against the full bundle after [applying the delta](data-access/weekly-deltas.md).

---

## Into the GA4GH models

Each section's records, except the ClinVar custom propositions, validate as one class from the libraries. A pointer string is accepted wherever a
field allows a reference: the models type it as `iriReference`, and its `.root` holds the pointer.

### VRS alleles and their identifiers

Continuing from the pointer walk above (`allele`, `location`, `sequence`):

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
iriReference #/location/ga4gh:SL.sF-Pr6l0-_uRAtk8bv9UzOPYvr6TK9IC
ga4gh:VA.1Oo5_TVyd33l8M9QsAac-ULaZR86hDCx True
```

`ga4gh_identify` needs the location inline: the allele's digest is computed over its location's digest, and
the location's over its sequence reference, of which it uses only `type` and `refgetAccession`. Recomputed this
way, every `allele` and `copyNumberChange` id in the delta whose location is also in the delta (176 of 233)
matches the published id.

### Cat-VRS categorical variants

A `variation` record is a Cat-VRS `CategoricalVariant`. Its defining constraint points to an `allele` (or, for
copy-number variants, a `location`) record. Continuing with `variation` from the pointer walk:

```python
from ga4gh.cat_vrs import models as catvrs

categorical = catvrs.CategoricalVariant(**variation)
constraint = categorical.constraints[0].root
print(type(constraint).__name__, constraint.allele.root)
print([relation.primaryCoding.code.root for relation in constraint.relations])
print({e.name: e.value for e in categorical.extensions if isinstance(e.value, str)})
```

```text
DefiningAlleleConstraint #/allele/ga4gh:VA.1Oo5_TVyd33l8M9QsAac-ULaZR86hDCx
['liftover_to', 'transcribed_to']
{'categoricalVariationType': 'CanonicalAllele', 'definingVrsVariationType': 'Allele', 'clinvarVariationType': 'Deletion', 'clinvarSubclassType': 'SimpleAllele', 'clinvarCytogeneticLocation': '8q12.1'}
```

### VA-Spec propositions and statements

Continuing with `proposition` and `scv` from the pointer walk:

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
isCausalFor #/variation/clinvar:5042631 #/condition/clinvar.trait:66395
supports Likely likely pathogenic
#/propositionPathogenicity/SCV008145211-PATH
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
  …). Work with them as plain JSON, as the bundle provides them. Every other
  section loads into a library class without loss; see [Round trip](#round-trip).

---

## The GKM Toolkit

The [GKM Toolkit](https://ga4gh.github.io/gkm-starter-kit/latest/tools/gkm-toolkit/) (`ga4gh.gkm`) validates a
producer's bundle against that producer's schemas. That is its intended way to validate producer data: you supply
the schemas, and it checks every record against them. Validation works on ClinVar-GKM 1.2.0 and 1.1.0 bundles
today; the toolkit's loader does not yet read them (see [Loading bundles](#loading-bundles)).

### Validate a bundle { #validate-a-bundle }

Call `validate_bundle_schema` with a `validator=` whose `referencing` registry holds the ClinVar-GKM 1.2.0
schemas and the GA4GH schemas they reference, taken from the `schema/` tree of this repository at tag `1.2.0`
(for a 1.1.0 bundle, use tag `1.1.0`). The release checks use the same schemas;
[Release Validation](reference/release-validation.md) lists the results, and its
[verification reports](reference/release-validation.md#verification-reports) record, per
published file, the schemas and tool versions used.

Get the schema tree. The GA4GH schemas come in through the `va-spec` submodule:

```bash
git -c advice.detachedHead=false clone -q --depth 1 --branch 1.2.0 --recurse-submodules --shallow-submodules \
    https://github.com/clingen-data-model/clinvar-gkm.git clinvar-gkm-1.2.0
```

Register every schema in the tree by its `$id`, then validate the delta (`bundle`, and `scv` from the pointer
walk):

```python
import os
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from ga4gh.gkm.bundles import BundleValidationError
from ga4gh.gkm.bundles.schema_validation import validate_bundle_schema

# Every schema in the 1.2.0 tree, keyed by $id: ClinVar-GKM's own and the GA4GH schemas they reference
schemas = {}
for directory, _, files in os.walk("clinvar-gkm-1.2.0/schema", followlinks=True):
    for name in files:
        try:
            document = json.loads(Path(directory, name).read_text())
        except (ValueError, UnicodeDecodeError):
            continue  # Makefiles and YAML sources
        if isinstance(document, dict) and "$id" in document:
            schemas[document["$id"]] = Resource.from_contents(document)
print(sorted(Counter("/".join(uri.split("/")[5:7]) for uri in schemas).items()))

bundle_schema = json.loads(Path("clinvar-gkm-1.2.0/schema/clinvar-gkm/clinvar-gkm-bundle.schema.json").read_text())
validator = Draft202012Validator(bundle_schema, registry=Registry().with_resources(schemas.items()))

# The first 100 records of each section: the whole delta takes about 17 minutes (see below)
part = {"schema_version": bundle["schema_version"]} | {
    section: dict(list(records.items())[:100]) for section, records in bundle.items() if isinstance(records, dict)
}
validate_bundle_schema(part, bundle_schema, validator=validator)  # raises BundleValidationError on a violation
print("valid:", sum(len(records) for records in part.values() if isinstance(records, dict)), "records")

broken = json.loads(json.dumps({"schema_version": "1.2.0", "scv": {scv["id"]: scv}}))
broken["scv"][scv["id"]]["direction"] = "sideways"  # not a VA-Spec direction
try:
    validate_bundle_schema(broken, bundle_schema, validator=validator)
except BundleValidationError as error:
    print(error)
```

```text
[('cat-vrs/1.1.1', 16), ('clinvar-gkm/1.2.0', 76), ('gkm-core/1.3.0', 11), ('va-spec/1.1.0', 40), ('vrs/2.1.1', 26)]
valid: 1118 records
Bundle does not match its JSON Schema at scv/clinvar.submission:SCV008145211.1/direction: 'sideways' is not one of ['supports', 'neutral', 'disputes']
```

Records are validated as published, `#/…` pointers included, against the full ClinVar-GKM profiles. The
1,118-record slice takes about 30 seconds on one core; the whole delta, 39,062 records, validates in about 17
minutes (pass `bundle` instead of `part`).

The same schemas resolve by `$id` through [w3id.org](https://w3id.org/), so a registry can fetch them on demand
instead of reading a local tree. The bundle schema itself can be fetched the same way, from
`https://w3id.org/clingen/schema/clinvar-gkm/1.2.0/clinvar-gkm-bundle.schema.json`. Fetching makes one request
per schema, so validate a slice, here the first 25 records of each section. This continues from the block above
(`bundle_schema`, `Resource`, `Draft202012Validator`):

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
valid: 293 records; 104 schemas fetched
```

`validate_bundle_schema` takes a whole bundle in memory. For multi-GB full bundles, the release used a streaming,
multi-process wrapper around it; that wrapper is proposed for the toolkit, as `gkm-validate-bundle`, in
[ga4gh/gkm-starter-kit#128](https://github.com/ga4gh/gkm-starter-kit/pull/128), which is not yet released.
That wrapper takes hours on a full bundle (about 17 h on 64 cores for a 1.2.0 full), so the release validates every
bundle with [jsonschema-rs](https://pypi.org/project/jsonschema-rs/) instead (`src/scripts/validate-bundle.sh`):
the same bundle schema, registry and per-record document, in minutes. Its tests check that it fails the same records
as the toolkit, and each version release also runs the toolkit on a sample of a full; see
[Release Validation](reference/release-validation.md).

### Loading bundles { #loading-bundles }

!!! note "The toolkit's loader needs upstream updates for ClinVar-GKM bundles"
    The toolkit's loader tools (`load_bundle`, `Bundle.resolve`, `Bundle.export` and its model conversion) do
    not yet read ClinVar-GKM 1.1.0 or 1.2.0 bundles. They need updating upstream in two ways:

    1. **The most recent GKM spec versions**, which 1.1.0 and 1.2.0 data use: GKM-Core 1.3.0, VRS 2.1.1,
       Cat-VRS 1.1.1 and VA-Spec 1.1.0. `ga4gh.gkm` 0.4.1 matches these only through the pre-release libraries above, and
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

The [Parquet tables](parquet/tables.md) have no `data` column: every property of a record is its own typed
column, named after the bundle property, and a reference is the bare id of the record it names, not a `#/…` pointer (see
[No `data` column](parquet/migrating-from-1.1.md#no-data-column)). How close a row is to its bundle record
decides how to get a model from it:

- **The VRS tables** (`allele`, `location`, `sequenceReference`): a row without its NULL columns is the bundle
  record, with bare-id references, apart from the few columns noted below. It builds the model directly.
- **Every other table** keeps values in a table's shape: extension values in `value_<kind>` slots, list
  references as `{id, section}` STRUCTs, a `_section` column beside a reference, some nested values as JSON text.
  Query those tables for what you need, then take the records themselves from the bundle.

[Build Your Own Tables and Mini-Bundles](parquet/build-your-own.md) covers `gkm-bundle-parquet`, the tool that
builds the tables and cuts mini-bundles.

### VRS records from rows

Read rows as dictionaries through pyarrow, drop the NULLs, and build the models (`vrs` is imported in
[VRS alleles and their identifiers](#vrs-alleles-and-their-identifiers)). Here, the alleles of three
variants: `variation.members` gives each member's id and the table it is in.

```python
import duckdb

P = "https://data.clinvar-gkm.org/v1/1.2/parquet"


def strip_nulls(value):
    """A row, or a STRUCT or list inside it, without its NULL fields."""
    if isinstance(value, dict):
        return {k: strip_nulls(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [strip_nulls(v) for v in value]
    return value


def rows(query, params=()):
    """Run a query; return each row as a dict of column name to value, without NULLs."""
    table = duckdb.execute(query, list(params)).to_arrow_table()
    return [strip_nulls(row) for row in table.to_pylist()]


def by_id(table, ids, columns="*"):
    """Fetch the rows of one table whose id is in ids, keyed by id."""
    marks = ", ".join("?" * len(ids))
    query = f"SELECT {columns} FROM '{P}/{table}.parquet' WHERE id IN ({marks})"
    return {row["id"]: row for row in rows(query, ids)}


variants = by_id("variation", ["clinvar:10", "clinvar:12582", "clinvar:51592"], "id, members")
alleles = by_id("allele", [m["id"] for v in variants.values() for m in v["members"] if m["section"] == "allele"])
for allele_id, row in alleles.items():
    model = vrs.Allele(**row)
    print(allele_id, model.name, model.location.root)
```

```text
ga4gh:VA.Apas_jvqBJU7l4DGHGlvTGRY3BBh-UR9 NC_000013.11:g.32338445A>C ga4gh:SL.Gga5J2ccypatzYD5tBIeQEU9K4sPXc6J
ga4gh:VA.ELQCnIBGqaTl0AEE0Az18XZ2cgIHAQIY NC_000006.12:g.26090951C>G ga4gh:SL.Eg_6kV6Bb4FMjm9kEolHZ_4NhU8lBEsZ
ga4gh:VA.LDaqvF3c3y1IG8wF4mORiRfB--9Jjfzp NC_000012.12:g.25245350C>T ga4gh:SL.qaHcVvdl8j0lpLRt49hE-bFI81128Mk9
```

The allele's `location` is a bare id. Follow it, and the location's `sequenceReference`, and recompute the
identifiers as [above](#vrs-alleles-and-their-identifiers), with `content` and `ga4gh_identify` from there:

```python
# The record's own properties: start_min, start_max, end_min and end_max are derived columns
locations = by_id("location", [row["location"] for row in alleles.values()],
                  'id, type, digest, sequenceReference, start, "end"')
# extensions keeps its values in value_<kind> slots; the identifier doesn't use it
sequences = by_id("sequenceReference", [row["sequenceReference"] for row in locations.values()],
                  "* EXCLUDE (extensions)")

for allele_id, row in alleles.items():
    location_row = locations[row["location"]]
    inline = content(location_row) | {"sequenceReference": sequences[location_row["sequenceReference"]]}
    recomputed = ga4gh_identify(vrs.Allele(**content(row) | {"location": inline}))
    print(allele_id, recomputed == allele_id)
```

```text
ga4gh:VA.Apas_jvqBJU7l4DGHGlvTGRY3BBh-UR9 True
ga4gh:VA.ELQCnIBGqaTl0AEE0Az18XZ2cgIHAQIY True
ga4gh:VA.LDaqvF3c3y1IG8wF4mORiRfB--9Jjfzp True
```

- **Ranges.** A location whose `start` or `end` is a VRS Range has NULL in that column. The bounds are in
  `start_min` and `start_max` (`end_min`, `end_max`), and the record's value is `[start_min, start_max]`, with
  `null` for an open bound. Copy-number locations are the usual case.
- **Sequence references.** `id` is the record's bundle key, which the record itself doesn't carry, and
  `extensions` keeps its values in `value_<kind>` slots.
- **Checked.** In a build of the 2026-10-31 delta, every `allele` row (16,557) and `location` row (11,127), read
  this way, equals its bundle record with the record's `#/…` pointers cut to bare ids.

### Statements, propositions and variants

For the other tables, query the columns. The proposition → statement → variant walk from the bundle examples,
from the tables (`scv.proposition` and `variation.id` are the join keys; [Joining Tables](parquet/joining.md)
covers every hop), with `rows`, `by_id` and `P` from the block above:

```python
prop_row = rows(f"""
    SELECT id, subject, predicate, geneContextQualifier.name AS gene
    FROM '{P}/propositionClinvarCustom.parquet'
    WHERE subject = 'clinvar:10' AND type = 'ClinvarRiskFactorProposition'
      AND geneContextQualifier.primaryCoding IS NOT NULL
    ORDER BY id LIMIT 1""")[0]
scv_row = rows(f"SELECT id, classification.name AS classification FROM '{P}/scv.parquet' WHERE proposition = ?",
               [prop_row["id"]])[0]
variant_row = by_id("variation", [prop_row["subject"]], "id, name")[prop_row["subject"]]

print(prop_row["id"], prop_row["predicate"], prop_row["gene"])
print(scv_row["id"], scv_row["classification"])
print(variant_row["id"], variant_row["name"])
```

```text
SCV001142520-RF isRiskFactorFor HFE
clinvar.submission:SCV001142520.1 risk factor
clinvar:10 NM_000410.4(HFE):c.187C>G (p.His63Asp)
```

To load these records into the library models, take them from the bundle the tables were built from: the
weekly full of the manifest's `source_release`, which is `weekly/clinvar-gkm_00-latest_weekly.json.gz` while the
tables are current. `gkm-bundle-parquet select` cuts a mini-bundle from it: the SCV and every record it points
to, directly or through other records, so every pointer in it resolves inside the file.

`select` reads the whole bundle, 4.9 GB compressed, so download it once and pass the local path; `--full` also
takes a URL, but then streams the whole file on every run. `uvx` comes with
[uv](https://docs.astral.sh/uv/getting-started/installation/); without it, `pip install gkm-bundle-parquet==2.0.0`
and run `gkm-bundle-parquet` in its place. `--out` must not exist yet: delete it to run again.

```bash
curl -fO https://data.clinvar-gkm.org/v1/1.2/weekly/clinvar-gkm_00-latest_weekly.json.gz
uvx gkm-bundle-parquet@2.0.0 select \
    --full clinvar-gkm_00-latest_weekly.json.gz \
    --bundle-schema https://w3id.org/clingen/schema/clinvar-gkm/1.2.0/clinvar-gkm-bundle.schema.json \
    --driver scv --ids clinvar.submission:SCV001142520.1 --out SCV001142520.json.gz
```

One id costs about as much as many: pass every id you need in one run (`--ids` takes a comma-separated list,
`--ids-file` a file of ids). On a local copy of the 2026-11 full bundle, this selection took about 9 minutes,
including the first `uvx` install and hashing the file. The mini-bundle loads like the delta; this block
continues from the Parquet blocks above (`scv_row`) and the model blocks (`va`, `catvrs`):

```python
with gzip.open("SCV001142520.json.gz", "rt") as f:
    mini = json.load(f)


def lookup(pointer):
    """resolve(), for the mini-bundle."""
    section, key = pointer.removeprefix("#/").split("/", 1)
    return mini[section][key]


scv_record = mini["scv"][scv_row["id"]]
risk = lookup(scv_record["proposition"])  # a ClinVar custom proposition: plain JSON
print(va.Statement(**scv_record).classification.name, "|",
      lookup(scv_record["contributions"][0]["contributor"])["name"])
print(risk["type"], risk["predicate"], risk["geneContextQualifier"]["name"])
print(catvrs.CategoricalVariant(**lookup(risk["subject"])).name)
print({section: len(records) for section, records in mini.items() if isinstance(records, dict)})
```

```text
risk factor | Center for Computational Genomics and Data Science, University of Alabama
ClinvarRiskFactorProposition isRiskFactorFor HFE
NM_000410.4(HFE):c.187C>G (p.His63Asp)
{'sequenceReference': 1, 'location': 1, 'allele': 1, 'gene': 2, 'variation': 1, 'condition': 1, 'submitter': 1, 'propositionClinvarCustom': 1, 'scv': 1}
```

!!! warning "Remote reads of big tables are slow"
    The tables are sorted by `id`, and each row group's id range is in the file footer, so a lookup by `id`
    reads only the row groups that can hold it. A filter on any other column (`scv.proposition` above) reads
    that column from every row group, one HTTP request each, and the CDN limits each client to about 55
    requests per 10 seconds. For anything beyond a handful of lookups, download the tables you need and query
    them locally ([Working at Scale](parquet/performance.md#local-or-remote)).

---

## Round trip

`model_dump(mode="json", exclude_none=True)` serializes a model back to JSON. Records carry no `null` fields
(except the open bound of a VRS `Range`, which survives), so `exclude_none=True` loses nothing. Compare every
record of the delta with its round trip (this uses `vrs`, `catvrs` and `va` from the blocks above):

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
location                          identical   176
allele                            identical   230
copyNumberChange                  identical     3
gene                              identical     5
variation                         identical  5471
condition                         identical   190
conditionSet                      identical   138
submitter                         identical    10
propositionPathogenicity          identical  3399
evidenceLine                      identical  6064
scv                               differs   17562
vcv                               identical  2941
rcv                               identical  2548
```

Every record comes back identical except for one field:

- **Contribution dates.** VA-Spec 1.1.0 types `Contribution.date` as a date-time. The records carry a date
  (`"2026-11-14"`); the model parses it as midnight and writes it back with a time:

    ```python
    dumped = statement.model_dump(mode="json", exclude_none=True)
    print(scv["contributions"][0]["date"], "->", dumped["contributions"][0]["date"])
    ```

    ```text
    2026-11-14 -> 2026-11-14T00:00:00
    ```

    Every SCV has contribution dates, so every SCV differs in those fields only. Compare dates by their
    first ten characters, or restore them after dumping.

The same sweep over the 1.1.0 sample sub-bundle (`nch-igm-bundle.json.gz`) gives the same result: every SCV
differs only in contribution dates, and every other record, apart from the plain-JSON custom propositions, is
identical.

Key order is not preserved: the models write fields in class-definition order. Compare parsed objects, not
strings.

---

## Large bundles { #large-bundles }

A full bundle is about 4.9 GB compressed and 68.5 GB decompressed, so a `json.load` of one does not fit in a
laptop's memory. Three ways to work with it:

- **Stream it.** [`ijson`](https://pypi.org/project/ijson/) reads one record at a time; `kvitems(f, "scv")`
  yields each `(id, record)` of a section. Build a model per record, keep what you need, and memory stays
  flat. One pass reads the whole file.
- **Query the Parquet** for the latest release to find the records you need, and cut just those out of the
  bundle with `gkm-bundle-parquet select`, as [above](#statements-propositions-and-variants).
- **Cut a sub-bundle.** The [Sub-Bundle Extraction](pipeline/sub-bundle.md) tool, which made the 1.1.0
  sample sub-bundle, extracts a self-contained bundle for a list of statements. It reads the project's
  BigQuery tables, not a published file, so it needs access to those datasets.

Streaming the delta's `scv` section, for example, to count classifications (`gzip`, `Counter` and `va` are
imported above):

```python
import ijson

classifications = Counter()
with gzip.open("clinvar-gkm-delta_2026-1115.json.gz", "rb") as f:
    for scv_id, record in ijson.kvitems(f, "scv", use_float=True):
        classifications[va.Statement(**record).classification.name] += 1
print(sum(classifications.values()), classifications.most_common(4))
```

```text
17562 [('Uncertain significance', 7388), ('Likely benign', 3389), ('Pathogenic', 2242), ('Likely pathogenic', 1986)]
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
