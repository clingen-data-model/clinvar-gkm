# Sub-Bundle Extraction

`sub-bundle.py` pulls a list of statements — SCV, VCV, and/or RCV — out of a built release
dataset into a single, self-contained **sub-bundle**: a JSON object of named sections in which every
`#/section/key` [reference](../output-reference/id-references.md) resolves within the file. It is the practical companion
to the [ID References](../output-reference/id-references.md) model — useful for building worked examples, inspecting the
complete object graph behind a statement, and producing small fixtures for downstream testing.

The script lives at [`src/scripts/sub-bundle.py`](https://github.com/clingen-data-model/clinvar-gkm/blob/main/src/scripts/sub-bundle.py).

!!! note "Maintainer tool"
    This is a pipeline-maintainer utility, not a general-audience download. It reads the BigQuery
    `gkm_dict_*` tables of a built release directly, so it requires access to the project's BigQuery
    datasets. Consumers of a published `.json.gz` bundle already have every section and can resolve
    references locally — see [ID References](../output-reference/id-references.md#resolution-example)
    for the small `resolve()` helper.

---

## What it does

Given one or more statement identifiers, the script starts from each statement and **transitively
resolves every reference** it carries across the `gkm_dict_*` tables — proposition → variation → allele
→ location → sequenceReference / gene, condition / conditionSet, therapy / therapyGroup, submitter,
and evidence lines — until the graph is closed. The result is a bundle with the same section structure
as a full release, containing only the objects the requested statements need.

- **One combined bundle.** All requested statements are assembled into a single JSON object, not one
  document per statement. References shared across statements (a common variation, condition, or
  therapy) are emitted **once** — the output is deduplicated.
- **SCV, VCV, and RCV.** Identifiers may be mixed. A VCV or RCV statement pulls in its **contributing
  SCVs** (via each evidence line's `hasEvidenceItems` → `#/scv/`), so a VCV/RCV sub-bundle is
  self-contained all the way down to the VRS sequence references.
- **Bundle-faithful objects.** Each object is transformed exactly as the release export does — typed
  extension values (`value_string`, …) collapsed to a single `value`, and null/empty fields stripped.

---

## Requirements

- Access to a **built** release dataset — one that has the `gkm_dict_*` tables from a completed
  release (pipeline Stage 4). The script reads BigQuery directly; it does not operate on a published
  `.json.gz` bundle.
- The `bq` CLI authenticated to the dataset's project.

---

## Usage

```text
python3 src/scripts/sub-bundle.py --dataset <DATASET> [--project <PROJECT>]
                                   [--ids-file <FILE>] [--stdin] [--submitter <ID>]
                                   [-o <OUT>] [<id> ...]
```

| Option | Description |
|---|---|
| `--dataset` | **Required.** Built release dataset, e.g. `clinvar_2026_08_16_v2_5_0`. |
| `--project` | GCP project (default `clingen-dev`). |
| `<id> ...` | SCV/VCV/RCV identifiers as arguments (mixed). |
| `--ids-file` | Read identifiers from a file, one per line. |
| `--stdin` | Also read identifiers from standard input (or pass `-` as an argument). |
| `--submitter` | Include **every SCV** contributed by this submitter (`clinvar.submitter:{id}` or bare `{id}`). Repeatable, and combinable with explicit ids. |
| `-o`, `--out` | Write the bundle to a file (default: stdout). |

Each identifier may be a **full statement key** (`SCV004101425.2`, `VCV000012582.63-G-PATH-CP`,
`RCV000012345.8-G-PATH-CP`) or a **bare accession** (`VCV000012582.63`) to include every statement
under it. An `SCV` accession is normalized to its `clinvar.submission:` key automatically.

`--submitter` resolves every SCV whose `contributions[].contributor` cites that submitter. A large
submitter can contribute thousands of SCVs; to keep individual bundles manageable, select the SCV
keys once and split them across several `--ids-file` runs (see the last example).

### Examples

```bash
# A few statements, mixed types, to one bundle file
python3 src/scripts/sub-bundle.py --dataset clinvar_2026_08_16_v2_5_0 \
    SCV004101425.2 VCV000012582.63-G-PATH-CP RCV000012345.8-G-PATH-CP -o bundle.json

# Identifiers from a file
python3 src/scripts/sub-bundle.py --dataset clinvar_2026_08_16_v2_5_0 \
    --ids-file ids.txt -o bundle.json

# Identifiers piped on stdin
cat ids.txt | python3 src/scripts/sub-bundle.py --dataset clinvar_2026_08_16_v2_5_0 -

# Every SCV from a submitter (e.g. 196472 = IGM Clinical Laboratory, Nationwide Children's Hospital)
python3 src/scripts/sub-bundle.py --dataset clinvar_2026_08_16_v2_5_0 \
    --submitter 196472 -o nch-igm.json

# A large submitter split across two bundles: list the SCV keys, split, bundle each half
bq query --project_id=clingen-dev --use_legacy_sql=false --format=csv --quiet --max_rows=100000 \
  "SELECT id FROM \`clinvar_2026_08_16_v2_5_0.gkm_dict_scv\`
   WHERE EXISTS(SELECT 1 FROM UNNEST(contributions) c
                WHERE c.contributor='#/submitter/clinvar.submitter:196472')
   ORDER BY id" | tail -n +2 > nch_scvs.txt
split -n l/2 nch_scvs.txt nch_half_
python3 src/scripts/sub-bundle.py --dataset clinvar_2026_08_16_v2_5_0 --ids-file nch_half_aa -o nch-1.json
python3 src/scripts/sub-bundle.py --dataset clinvar_2026_08_16_v2_5_0 --ids-file nch_half_ab -o nch-2.json
```

---

## Output

The output is a single bundle object — the same `{ "<section>": { "<key>": <object> } }` shape as a
full release, ordered `sequenceReference` → … → `scv`/`vcv`/`rcv`. Every `#/…` pointer inside resolves
to a key present in the file.

Records are written **one per line** — each section is keyed on its own line and every object *value* is
emitted as a single compact line. The file stays one valid JSON document, but has roughly one line per
record rather than one per field, so a large sub-bundle (thousands of statements) is a few thousand lines
instead of hundreds of thousands — much easier to `grep`, diff, or scroll.

```json
{
  "sequenceReference": { "SQ.dLZ15tNO…": { ... } },
  "location":          { "ga4gh:SL.MVuZ…": { ... } },
  "allele":            { "ga4gh:VA.EE08…": { ... } },
  "gene":              { "ncbigene:672": { ... } },
  "variation":         { "clinvar:17662": { ... } },
  "condition":         { "clinvar.trait:76328": { ... } },
  "submitter":         { "clinvar.submitter:509268": { ... } },
  "varcond-proposition": { "SCV004101425-PATH": { ... } },
  "scv":               { "clinvar.submission:SCV004101425.2": { ... } }
}
```

A progress line on stderr reports how many statements matched and the per-section object counts.

---

## How it works

The script resolves the graph efficiently rather than one object at a time:

- **Batched breadth-first traversal.** Each round collects all pending references, groups them by
  source table, and issues **one query per table** — so a list of N statements is a handful of
  queries, not N× the work.
- **Prefix-routed proposition/evidence resolution.** A `#/varcond-proposition/` or `#/evidenceLine/`
  reference is resolved from the SCV-, VCV-, or RCV-specific table based on the key's `SCV`/`VCV`/`RCV`
  prefix.
- **Global dedup.** Every referenced object is fetched at most once across the whole run; the final
  bundle contains one copy of each.
