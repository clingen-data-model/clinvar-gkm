# Parquet Files

Links: [Monthly Full Bundles](monthly-full.md) · [Weekly Full Bundles](weekly-full.md) · [Weekly Deltas](weekly-deltas.md) · [How Releases Work](release-model.md)

!!! tip "Want to query the files, not just download them?"
    This page covers where the Parquet files live and how to keep a set current. [**Query the Data**](../parquet/index.md) teaches querying them: a live in-browser console, every table's columns, how the tables join, and runnable recipes.

!!! info "Parquet is derived from the bundle and overwritten every release"
    The JSON bundles are the release record. Parquet is a convenience: every value in it can be recomputed from the bundle. **One** Parquet dataset is published, rebuilt every release (weekly) from the newest weekly release and overwritten in place. There are no dated, per-delta or archived Parquet sets.

The dataset lives at one stable path, `v1/1.1/parquet/`, one file per section, with a `manifest.json` beside it:

```text
v1/1.1/parquet/
  {section}.parquet      22 files, one per bundle section
  manifest.json          when the dataset was built, from which release, by which tool version
```

The manifest names the release the dataset was built from, so check it before comparing results with a bundle (the index's Parquet entry carries the same `source_release`). For an earlier state, see [Earlier releases](#earlier-releases).

## The latest set

<div class="r2-browser" data-r2-type="parquet-latest"></div>

## Available Parquet files

Each Parquet file contains one bundle section with typed, query-friendly columns extracted from the JSON objects. Nearly every section includes an `id` column (the object identifier) and a `data` column (the full JSON object as a string), plus additional typed columns for key fields — enabling efficient filtering and aggregation without parsing JSON. The exception: `therapy` and `therapyGroup` name the id column `key` and hold the JSON object in `value`. Before 1.1.0, `condition` had no `data` column and `therapy` / `therapyGroup` had only `key` and `value`. The [column reference](../parquet/tables.md#column-reference) lists every column of every section.

Available Parquet files (22 sections):

| File | Description |
| --- | --- |
| `sequenceReference.parquet` | NCBI RefSeq sequence references |
| `location.parquet` | VRS SequenceLocation records |
| `allele.parquet` | VRS Allele records |
| `copyNumberCount.parquet` | VRS CopyNumberCount records |
| `copyNumberChange.parquet` | VRS CopyNumberChange records |
| `gene.parquet` | Gene records (MappableConcept with NCBI Gene / HGNC codings) |
| `variation.parquet` | CategoricalVariant records (Cat-VRS) |
| `condition.parquet` | Condition records (traits) |
| `conditionSet.parquet` | ConditionSet records (trait sets) |
| `therapy.parquet` | Therapy records (drug therapies, content-addressed) |
| `therapyGroup.parquet` | TherapyGroup records (combination therapies) |
| `submitter.parquet` | Submitter organization records |
| `propositionPathogenicity.parquet` | Pathogenicity propositions |
| `propositionOncogenicity.parquet` | Oncogenicity propositions |
| `propositionSomaticClinicalImpact.parquet` | Somatic clinical impact propositions (ClinicalSignificance, and the Diagnostic, Prognostic and TherapeuticResponse targets of SCI evidence lines) |
| `propositionClinvarCustom.parquet` | ClinVar custom propositions (the `Clinvar*` types) |
| `evidenceLine.parquet` | SCV evidence line records |
| `vcv_evidenceLine.parquet` | VCV evidence line records |
| `rcv_evidenceLine.parquet` | RCV evidence line records |
| `scv.parquet` | SCV statement records |
| `vcv.parquet` | VCV aggregate statement records |
| `rcv.parquet` | RCV aggregate statement records |

## Working with Parquet Files

Download the Parquet files you need, then query them locally. The R2 hosting has rate limits and is designed for file downloads, not as a remote query endpoint for tools like DuckDB.

!!! note "Prerequisites"
    The examples below use the **[DuckDB CLI](https://duckdb.org/docs/installation/)** and/or **Python with `pandas` + `pyarrow`** (`pip install pandas pyarrow`). If you don't already have these tools, install them from the linked pages first — each subsection also shows its own one-line install command.

### Download

Download individual sections or all files at once:

??? example "Download sections with curl"
    ```bash
    # The one published Parquet dataset, overwritten every release; manifest.json names its release.
    BASE="https://data.clinvar-gkm.org/v1/1.1/parquet"
    mkdir -p clinvar-gkm-parquet && cd clinvar-gkm-parquet
    curl -O "${BASE}/manifest.json"

    # Download specific sections
    curl -O "${BASE}/scv.parquet"
    curl -O "${BASE}/propositionPathogenicity.parquet"
    curl -O "${BASE}/condition.parquet"

    # Or download all 22 sections
    for section in sequenceReference location allele copyNumberCount copyNumberChange \
                   gene variation condition conditionSet therapy therapyGroup submitter \
                   propositionPathogenicity propositionOncogenicity propositionSomaticClinicalImpact propositionClinvarCustom \
                   evidenceLine vcv_evidenceLine rcv_evidenceLine \
                   scv vcv rcv; do
      curl -O "${BASE}/${section}.parquet"
    done
    ```

### Query

[DuckDB](https://duckdb.org/) is the fastest way to explore Parquet files — it queries them directly with no data loading step. `pandas` + `pyarrow` works well when you want DataFrames.

??? example "Query with DuckDB / pandas"
    ```bash
    # Install DuckDB
    brew install duckdb   # macOS
    # or: pip install duckdb
    ```

    ```bash
    # Query SCV statements
    duckdb -c "
      SELECT id, classification.name AS classification, direction, strength.name AS strength, quality.name AS quality
      FROM 'scv.parquet'
      WHERE classification.name = 'Pathogenic'
      LIMIT 10;
    "
    ```

    ```bash
    # Count classifications across all SCVs
    duckdb -c "
      SELECT classification.name AS classification, direction, COUNT(*) as n
      FROM 'scv.parquet'
      GROUP BY classification.name, direction
      ORDER BY n DESC;
    "
    ```

    ```bash
    # Join SCVs with propositions to find pathogenic variants for a specific condition
    duckdb -c "
      SELECT s.id, s.classification.name AS classification, p.predicate, p.object_id
      FROM 'scv.parquet' s
      JOIN 'propositionPathogenicity.parquet' p ON s.proposition_id = p.id
      WHERE s.classification.name = 'Pathogenic'
        AND p.object_id = 'clinvar.trait:9580'
      LIMIT 10;
    "
    ```

    ```bash
    # Inspect the schema of any section
    duckdb -c "DESCRIBE SELECT * FROM 'scv.parquet';"
    ```

    DuckDB also works from Python:

    ```python
    import duckdb

    df = duckdb.sql("""
        SELECT id, classification.name AS classification, direction, strength.name AS strength, quality.name AS quality
        FROM 'scv.parquet'
        WHERE classification.name = 'Pathogenic'
        LIMIT 100
    """).df()

    print(df)
    ```

    With `pandas` / `pyarrow`:

    ```python
    import pandas as pd

    # Load a section into a DataFrame
    scv = pd.read_parquet("scv.parquet")

    # Filter pathogenic SCVs — classification is a MappableConcept struct (dict), so read .name
    pathogenic = scv[scv["classification"].map(lambda c: c and c.get("name")) == "Pathogenic"]
    print(f"{len(pathogenic)} pathogenic SCVs")

    # Access the full JSON when you need nested fields
    import json
    record = json.loads(pathogenic.iloc[0]["data"])
    print(record["proposition"])
    ```

### Column Reference

The complete per-table reference — every column, type and description for all 22 sections — is in [Query the Data → The 22 Tables](../parquet/tables.md#column-reference). A summary:

Statement sections (`scv`, `vcv`, `rcv`) share a common set of typed columns:

| Column | Type | Description |
| --- | --- | --- |
| `id` | string | Statement identifier |
| `type` | string | Statement type |
| `proposition_id` | string | FK to the matching proposition Parquet — one of `propositionPathogenicity`, `propositionOncogenicity`, `propositionSomaticClinicalImpact`, `propositionClinvarCustom`, by the proposition's type; `read_parquet('proposition*.parquet')` covers all four |
| `classification` | struct (MappableConcept) | Use `classification.name` (or `classification.primaryCoding.code`) — e.g., "Pathogenic" |
| `strength` | struct (MappableConcept) | Use `strength.name` — e.g., "definitive", "likely" |
| `direction` | string | Evidence direction ("supports", "disputes", "neutral") |
| `quality` | struct (MappableConcept) | Use `quality.name` — submission level, e.g., "criteria provided" |
| `has_evidence_lines` | list\<string\> | FK references to evidence line Parquet (`evidenceLine` for SCV, `vcv_evidenceLine` for VCV, `rcv_evidenceLine` for RCV) |
| `extensions` | string | JSON array of extensions |
| `data` | string | Full JSON object |

SCV statements include additional columns: `description`, `contributions`, `reportedIn` and `specifiedBy`. `reportedIn` is a list of citation Documents, one per ClinVar citation, and `specifiedBy.reportedIn` is the assertion method's Document. From 1.1.0 each Document also has `name`, `documentType` and `extensions`; see [`scv`](../parquet/tables.md#scv).

The four proposition tables share **one column schema** (from 1.1.0): `id`, `type`, `predicate`, `subject_variant_id`, `object_id`, `object_type`, `condition_qualifier_id`, `gene_context_id`, `gene_context_name`, `submitted_gene_symbols`, `gene_context_source`, `mode_of_inheritance`, `penetrance` and `data`, so `read_parquet('proposition*.parquet')` reads them as one table. This enables JOINs across statements, variants, and conditions without parsing JSON. See [Gene context](../parquet/tables.md#gene-context) for what the gene context is (one representative gene per variant, not a submitter-asserted gene), and [The shared columns](../parquet/tables.md#proposition-columns) for each column.

Run `DESCRIBE` in DuckDB to see the full schema for any section.

These examples demonstrate cross-section JOINs using typed columns. Most analytical queries can be answered without parsing JSON — the proposition's `gene_context_name` column carries the gene symbol directly, and the condition's `primaryCoding` struct carries the MedGen code. (These queries join `scv.parquet` to `propositionPathogenicity.parquet`; swap in `read_parquet('proposition*.parquet')` to include every kind of claim, since the four tables have the same columns.)

For how the sections join — including the columns that point at more than one table, where a single-table join silently drops rows — see [Joining Tables](../parquet/joining.md); for task-oriented queries, see [Recipes](../parquet/recipes.md).

??? example "Example cross-section queries (SQL)"
    **All SCVs for a gene — detailed view:**

    ```sql
    -- SCVs for BRCA1: classification, review status, condition
    SELECT
        s.id AS scv_id,
        s.classification.name AS classification,
        s.direction,
        s.strength.name AS strength,
        s.quality.name AS review_status,
        p.gene_context_name AS gene,
        c.name AS condition_name,
        c.primaryCoding.code AS condition_code
    FROM 'scv.parquet' s
    JOIN 'propositionPathogenicity.parquet' p ON s.proposition_id = p.id
    LEFT JOIN 'condition.parquet' c ON p.object_id = c.id
    WHERE p.gene_context_name = 'BRCA1'
    ORDER BY s.classification.name;
    ```

    **Classification summary for a gene:**

    ```sql
    -- Count SCVs by classification and review status for BRCA2
    SELECT
        p.gene_context_name AS gene,
        s.classification.name AS classification,
        s.quality.name AS review_status,
        s.direction,
        COUNT(*) AS scv_count
    FROM 'scv.parquet' s
    JOIN 'propositionPathogenicity.parquet' p ON s.proposition_id = p.id
    WHERE p.gene_context_name = 'BRCA2'
    GROUP BY ALL
    ORDER BY scv_count DESC;
    ```

    **Restrict to submissions with criteria provided:**

    ```sql
    -- Only expert panel and criteria-provided SCVs for a gene
    SELECT
        s.id AS scv_id,
        s.classification.name AS classification,
        s.quality.name AS review_status,
        c.name AS condition_name
    FROM 'scv.parquet' s
    JOIN 'propositionPathogenicity.parquet' p ON s.proposition_id = p.id
    LEFT JOIN 'condition.parquet' c ON p.object_id = c.id
    WHERE p.gene_context_name = 'TP53'
      AND s.quality.name IN ('criteria provided', 'reviewed by expert panel')
    ORDER BY s.classification.name;
    ```

    **Cross-gene comparison — classification breakdown for multiple genes:**

    ```sql
    -- Compare pathogenicity classification distributions across genes
    SELECT
        p.gene_context_name AS gene,
        s.classification.name AS classification,
        COUNT(*) AS n
    FROM 'scv.parquet' s
    JOIN 'propositionPathogenicity.parquet' p ON s.proposition_id = p.id
    WHERE p.gene_context_name IN ('BRCA1', 'BRCA2', 'TP53', 'MLH1')
      AND s.quality.name = 'criteria provided'
    GROUP BY gene, s.classification.name
    ORDER BY gene, n DESC;
    ```

    **Accessing fields not in typed columns** — some fields, like submitter names, HGVS expressions, and assertion methods, are only available in the `data` column (full JSON string). Use DuckDB's `json_extract_string` to access them:

    ```sql
    -- SCVs with submitter name and assertion method (from JSON)
    SELECT
        s.id AS scv_id,
        s.classification.name AS classification,
        p.gene_context_name AS gene,
        json_extract_string(s.data, '$.contributions[0].agent.name') AS submitter,
        json_extract_string(s.data, '$.specifiedBy.name') AS method
    FROM 'scv.parquet' s
    JOIN 'propositionPathogenicity.parquet' p ON s.proposition_id = p.id
    WHERE p.gene_context_name = 'BRCA1'
      AND s.classification.name = 'Pathogenic'
      AND s.quality.name = 'reviewed by expert panel'
    LIMIT 20;
    ```

When to use each access path:

| Approach | Best for | Tradeoff |
| --- | --- | --- |
| Typed columns only | Filtering, counting, grouping, JOINs on classification, gene, condition, review status | Fast; covers most analytical questions |
| Typed columns + `json_extract_string` | Ad-hoc queries needing submitter names, HGVS, methods | Slightly slower; syntax is verbose |
| Parse `data` column in application code | Bulk processing needing many nested fields | Full flexibility; requires application-side JSON parsing |

## Earlier releases { #earlier-releases }

Only the current Parquet dataset is published; it is overwritten every release, and weekly deltas, archives and frozen lines carry no Parquet. To work with an earlier state:

- **Rebuild it from the bundles.** Every official monthly stays published (in `archive/YYYY/` after its year ends) with a `.sha256` sidecar, and so does every delta. Rebuild the bundle for the week you need with the [replay recipe](weekly-deltas.md#rebuild-a-past-week), then read the sections you need.
- **Convert a bundle to Parquet with `clinvar-gkm-parquet` (planned).** [`clinvar-gkm-parquet`](https://github.com/clingen-data-model/clinvar-gkm-parquet) is a separate, versioned tool that builds this Parquet layout from a published bundle and writes the same `manifest.json`. It is in design and not yet released; until it is, earlier Parquet can't be downloaded or rebuilt in this layout.
- **The 1.0.1 generation** is the frozen line `v1/1.0/`: its bundles and delta manifests, with no Parquet.

Parquet downloaded from an earlier release keeps its old tables and columns; see the [changelog](../reference/changelog.md) for what changed.
