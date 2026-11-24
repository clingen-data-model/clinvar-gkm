# Quick Start

This page follows one ClinVar variant, **variation 10** (the HFE p.His63Asp variant, `clinvar:10`), from its name to the classifications ClinVar gives it and the conditions they are about, first in SQL and then as JSON. It takes about ten minutes, and nothing larger than a 61 MB download.

!!! note "Prerequisites"
    - **Steps 1 to 4:** a web browser. The queries run in the query console on [Query with SQL](../parquet/index.md), which needs nothing installed.
    - **To run the queries on your machine, and the join that lists the conditions:** the DuckDB CLI (tested with 1.5.4). The browser console was tested in Chrome on 2026-11-23.
    - **Step 5:** `curl`, `gunzip` and Python 3 (standard library only; tested with 3.14.5), and about 61 MB of disk.

    [Set Up Your Tools](setup.md) has install commands for each.

The counts and versions shown are from the **2026-11-15 release**. ClinVar updates this variant often, so the version number in its ids (`.143` below) and the counts may be higher when you run the queries.

---

## Step 1: Open the console

The console runs SQL **in your browser**, against the published Parquet tables of the current release. Open it on [Query with SQL](../parquet/index.md), paste a query below into the text box, and press **Run**.

Each query names the table by its URL under `https://data.clinvar-gkm.org/v1/1.2/parquet/`, the current line's tables, so it runs unchanged in the console and in DuckDB on your machine. The console runs one query every 10 seconds and stops any query that runs longer than 15 seconds; each query in Steps 2 to 4 reads only a few small parts of the files and finishes in a few seconds. If one is stopped, wait for the countdown and press **Run** again.

## Step 2: Find the variant

ClinVar's variation 10 has the id `clinvar:10` in the `variation` table:

```sql
SELECT id, name
FROM 'https://data.clinvar-gkm.org/v1/1.2/parquet/variation.parquet'
WHERE id = 'clinvar:10';
```

```text
id          name
clinvar:10  NM_000410.4(HFE):c.187C>G (p.His63Asp)
```

Every row of this table is a GA4GH Cat-VRS `CategoricalVariant`, the standard's type for a ClinVar-style variant. [Key Concepts](concepts.md) explains it.

## Step 3: See what ClinVar says about it

ClinVar's classification of the variant, the summary at the top of its ClinVar page, is a set of **VCV statements**. Their ids start with the variant's VCV accession: the variation id padded to nine digits (`clinvar:10` → `VCV000000010`). The query asks for every id from `VCV000000010.` up to `VCV000000010/` (`/` is the character after `.`), which is every id that starts with `VCV000000010.`. Tables are sorted by `id`, so a range like this reads only the small part of the file that holds those ids, which keeps it fast in the browser.

```sql
SELECT id,
       classification.name AS classification,
       quality.name AS quality
FROM 'https://data.clinvar-gkm.org/v1/1.2/parquet/vcv.parquet'
WHERE id >= 'VCV000000010.' AND id < 'VCV000000010/'   -- ids that start with VCV000000010.
ORDER BY id;
```

```text
id                            classification                                quality
VCV000000010.143-G-NP         not provided                                  no classification
VCV000000010.143-G-NP-NOCL    not provided                                  no classification
VCV000000010.143-G-OTH        other                                         criteria provided
VCV000000010.143-G-OTH-CP     other                                         criteria provided
VCV000000010.143-G-PATH       Conflicting classifications of pathogenicity  criteria provided
VCV000000010.143-G-PATH-CP    Conflicting classifications of pathogenicity  criteria provided
VCV000000010.143-G-PATH-FLAG  no classifications from unflagged records     flagged
VCV000000010.143-G-PATH-NOCP  Pathogenic                                    no assertion criteria provided
VCV000000010.143-G-RF         risk factor                                   no assertion criteria provided
VCV000000010.143-G-RF-NOCP    risk factor                                   no assertion criteria provided
```

Each id reads `<accession>.<version>-<lane>-<type>[-<level>]`:

- **`G`** is the germline lane.
- **`PATH`**, **`RF`**, **`OTH`** and **`NP`** are the kinds of classification: pathogenicity, risk factor, other, and not provided.
- An id with no level (`…-G-PATH`) is ClinVar's overall call for that kind. The ids with a level (`-CP` criteria provided, `-NOCP` no assertion criteria, `-FLAG` flagged) group the submissions by review level. The overall call comes from the highest level present, here `-CP`.

## Step 4: See why it is conflicting

The overall pathogenicity call is *Conflicting classifications of pathogenicity*. The statement carries ClinVar's review status, and a count of what the submissions said:

```sql
SELECT id,
       [e.value_string FOR e IN extensions IF e.name = 'clinvarReviewStatus'][1] AS review_status,
       [e.value_string FOR e IN classification.extensions IF e.name = 'conflictingExplanation'][1] AS submissions
FROM 'https://data.clinvar-gkm.org/v1/1.2/parquet/vcv.parquet'
WHERE id >= 'VCV000000010.' AND id < 'VCV000000010/'
  AND id LIKE '%-G-PATH';
```

```text
id                       review_status                                   submissions
VCV000000010.143-G-PATH  criteria provided, conflicting classifications  Pathogenic(41); Likely pathogenic(2); Pathogenic, low penetrance(1); Uncertain significance(2)
```

What a statement claims (this variant causes these conditions) is its **proposition**. A VCV proposition's id is the statement id without the version:

```sql
SELECT id, subject, predicate, object
FROM 'https://data.clinvar-gkm.org/v1/1.2/parquet/propositionPathogenicity.parquet'
WHERE id = 'VCV000000010-G-PATH';
```

```text
id                   subject     predicate    object
VCV000000010-G-PATH  clinvar:10  isCausalFor  clinvar.conditionset:vcv-48e5fe986b5c30669858fd0b2177c4e6
```

The proposition says variant `clinvar:10` *is causal for* a **condition set**: the conditions the submissions named.

### Run the same queries on your machine

The queries run unchanged in the DuckDB CLI: start `duckdb` and paste one in, or pass it with `-c`:

```bash
duckdb -c "
SELECT id, classification.name AS classification, quality.name AS quality
FROM 'https://data.clinvar-gkm.org/v1/1.2/parquet/vcv.parquet'
WHERE id >= 'VCV000000010.' AND id < 'VCV000000010/'
ORDER BY id"
```

Joins can take longer than the console's 15-second limit, so run them on your machine. This one follows the proposition to the names of its conditions:

```bash
duckdb -c "
SELECT c.name AS condition
FROM (SELECT object
      FROM 'https://data.clinvar-gkm.org/v1/1.2/parquet/propositionPathogenicity.parquet'
      WHERE id = 'VCV000000010-G-PATH') p
JOIN 'https://data.clinvar-gkm.org/v1/1.2/parquet/conditionSet.parquet' cs ON cs.id = p.object
CROSS JOIN unnest(cs.concepts) AS t(member)
JOIN 'https://data.clinvar-gkm.org/v1/1.2/parquet/condition.parquet' c ON c.id = member.id
ORDER BY condition"
```

```text
condition
Cardiomyopathy
Hemochromatosis type 1
Hereditary hemochromatosis
Neuroendocrine neoplasm
See cases
Variegate porphyria
not provided
```

The proposition is filtered inside a subquery, so DuckDB reads only the part of the 400 MB `propositionPathogenicity` file that holds that id; `conditionSet` and `condition` are small (7 MB together). [Working at Scale](../parquet/performance.md) explains when a remote query is cheap.

DuckDB installs its `httpfs` extension the first time a query reads a URL. The server allows about 55 requests per 10 seconds; a query that filters on `id`, like these, stays well under that.

## Step 5: Read the same statement as JSON

The Parquet tables are built from the **bundle**: one JSON file in which each record is stored once under its id, in a section named for its kind (`variation`, `vcv`, `scv`, …). A full bundle is 4.9 GB, but a **weekly delta** holds only the records that changed that week, in the same format. ClinVar updated variation 10 to version 143 in the 2026-11-08 release, so that week's delta (61 MB) has its VCV statements.

A delta's path changes when its month ends, so this looks it up in the line's `index.json`, then downloads it:

```bash
DELTA=$(curl -fsS https://data.clinvar-gkm.org/v1/1.2/index.json | python3 -c '
import json, sys
index = json.load(sys.stdin)
deltas = index["deltas"] + [d for year in index.get("archives", {}).values() for d in year.get("deltas", [])]
print(next(d["bundle"]["path"] for d in deltas if d["release"] == "2026-11-08"))')
curl -fO "https://data.clinvar-gkm.org/${DELTA}"
```

Each record in a bundle is on its own line, so a few lines of Python can stream the file and print the two records wanted: the overall pathogenicity statement and the evidence line it points to. This continues from the download above, in the same directory:

```bash
gunzip -c clinvar-gkm-delta_2026-1108.json.gz | python3 -c '
import json, sys
wanted = ["VCV000000010.143-G-PATH", "VCV000000010.143-G-PATH.contributing"]
found = {}
for line in sys.stdin:
    key, _, record = line.strip().partition(": ")
    if key.strip("\"") in wanted:
        found[key.strip("\"")] = json.loads(record.rstrip(","))
for key in wanted:
    print(json.dumps(found[key], indent=2))
'
```

The first record printed is the statement (shown here with a few small objects on one line):

```json
{
  "classification": {
    "conceptType": "Classification",
    "extensions": [
      {
        "name": "conflictingExplanation",
        "value": "Pathogenic(41); Likely pathogenic(2); Pathogenic, low penetrance(1); Uncertain significance(2)"
      }
    ],
    "name": "Conflicting classifications of pathogenicity",
    "primaryCoding": { "code": "conflicting classifications of pathogenicity", "system": "ClinVar" },
    "type": "MappableConcept"
  },
  "direction": "neutral",
  "extensions": [
    { "name": "clinvarReviewStatus", "value": "criteria provided, conflicting classifications" }
  ],
  "hasEvidenceLines": [
    "#/evidenceLine/VCV000000010.143-G-PATH.contributing",
    "#/evidenceLine/VCV000000010.143-G-PATH.non-contributing"
  ],
  "id": "VCV000000010.143-G-PATH",
  "proposition": "#/propositionPathogenicity/VCV000000010-G-PATH",
  "quality": { "conceptType": "Quality", "name": "criteria provided", "type": "MappableConcept" },
  "type": "Statement"
}
```

These are the values the SQL in Steps 3 and 4 read. In the bundle, a record points to another with a **`#/section/id`** string: `#/propositionPathogenicity/VCV000000010-G-PATH` is the record with that id in the `propositionPathogenicity` section. The second record printed is the evidence line `#/evidenceLine/VCV000000010.143-G-PATH.contributing`, which points down to the `-CP` statement, and that statement's evidence line points to the 46 submissions (SCVs) behind the call. A full bundle resolves every pointer; a delta holds only what changed that week, so the proposition and the variant itself are not in this file.

---

## Next steps

- **Understand what you just read:** [Key Concepts](concepts.md), then [Output Format](../output-reference/overview.md).
- **Pick the files for your work:** [Choose Your Data](choose-your-data.md).
- **More queries:** [Query with SQL](../parquet/index.md) and [Recipes](../parquet/recipes.md), which include listing the submitters behind a conflicting call.
- **Load records into the GA4GH Python libraries:** [Working in Python](../working-in-python.md).
