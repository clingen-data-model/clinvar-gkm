# Parquet Files

Links: [Monthly Full Bundles](monthly-full.md) · [Weekly Full Bundles](weekly-full.md) · [Weekly Deltas](weekly-deltas.md) · [How Releases Work](release-model.md)

!!! tip "Want to query the files, not just download them?"
    This page covers where the Parquet files live and how to keep a set current. [**Query the Data**](../parquet/index.md) teaches querying them: a live in-browser console, every table's columns, how the tables join, and runnable recipes.

!!! info "Parquet is derived from the bundle and overwritten every release"
    The JSON bundles are the release record. Parquet is a convenience: the tables hold the bundle's records, and the bundle can be rebuilt from them. **One** Parquet dataset is published per release line, rebuilt every release (weekly) from the newest weekly release and overwritten in place. There are no dated, per-delta or archived Parquet sets.

!!! warning "Two sets of tables during the move to 1.2"
    The 1.1 line's set, at `v1/1.1/parquet/`, is the one exported from BigQuery for the **2026-10-24** release (its `manifest.json` gives `builder: "BigQuery export"` and `source_release: "2026-10-24"`). It is not rebuilt, so it lags the bundles, and it is deleted when `v1/1.1/` is frozen. Its 22 tables have different columns; see [Moving from the 1.1 Tables](../parquet/migrating-from-1.1.md).

    This page describes the 1.2 line's set, at `v1/1.2/parquet/`: the 20 tables that [`gkm-bundle-parquet`](https://github.com/clingen-data-model/gkm-bundle-parquet) 2.0 builds from each 1.2 release's bundle, published from the first 1.2 release on. Parquet is built only from the bundle, never from BigQuery. Until the first 1.2 set is published, use the [weekly full bundles](weekly-full.md) for data newer than 2026-10-24, or [build the tables yourself](../parquet/build-your-own.md).

The dataset lives at one stable path, `v1/1.2/parquet/`, one file per section, with a `manifest.json` and a `table-spec.json` beside it:

```text
v1/1.2/parquet/
  {section}.parquet      20 files, one per bundle section
  manifest.json          build date, source release and dataset, builder, schema version, each file's size, rows and sha256,
                         the records sha256 the tables rebuild to, and the ClinVar source, attribution, disclaimer and license scope
  table-spec.json        the table spec: every table's columns, how each maps to the bundle, and the foreign keys
```

The manifest also carries the data's provenance: `source` (ClinVar at NCBI, its data use policy and a citation), `attribution`, `disclaimer` and `license` (CC0 scope), matching [Data Use and Citation](../data-use.md). The manifest names the release the dataset was built from, so check it before comparing results with a bundle (the index's Parquet entry carries the same `source_release`). For an earlier state, see [Earlier releases](#earlier-releases).

## The latest set

<div class="r2-browser" data-r2-type="parquet-latest"></div>

## Available Parquet files

Each Parquet file holds one bundle section, one row per record. Every table has an `id` column, and every field of the record has a typed column named after it, so filtering and aggregation need no JSON parsing. The tables are generated from the bundle's JSON Schema, with no hand-chosen columns. The [column reference](../parquet/tables.md#column-reference) lists every column of every section.

Available Parquet files (20 sections):

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
| `evidenceLine.parquet` | Evidence line records of SCV, VCV and RCV statements |
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
    BASE="https://data.clinvar-gkm.org/v1/1.2/parquet"
    mkdir -p clinvar-gkm-parquet && cd clinvar-gkm-parquet
    curl -O "${BASE}/manifest.json"

    # Download specific sections
    curl -O "${BASE}/scv.parquet"
    curl -O "${BASE}/propositionPathogenicity.parquet"
    curl -O "${BASE}/condition.parquet"

    # Or download all 20 sections
    for section in sequenceReference location allele copyNumberCount copyNumberChange \
                   gene variation condition conditionSet therapy therapyGroup submitter \
                   propositionPathogenicity propositionOncogenicity propositionSomaticClinicalImpact propositionClinvarCustom \
                   evidenceLine scv vcv rcv; do
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
      SELECT s.id, s.classification.name AS classification, p.predicate, p.object
      FROM 'scv.parquet' s
      JOIN 'propositionPathogenicity.parquet' p ON s.proposition = p.id
      WHERE s.classification.name = 'Pathogenic'
        AND p.object = 'clinvar.trait:9580'
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

    # Load only the columns you need: a dotted path reads one field of a struct
    scv = pd.read_parquet("scv.parquet", columns=["id", "classification.name", "proposition"])

    # The struct field comes back named by its last segment
    pathogenic = scv[scv["name"] == "Pathogenic"]
    print(f"{len(pathogenic)} pathogenic SCVs")
    print(pathogenic.iloc[0]["proposition"])
    ```

### Column Reference

The complete per-table reference — every column, type and description for all 20 sections — is in [Query the Data → The 20 Tables](../parquet/tables.md#column-reference). A summary:

Statement sections (`scv`, `vcv`, `rcv`) share a common set of typed columns:

| Column | Type | Description |
| --- | --- | --- |
| `id` | string | Statement identifier |
| `type` | string | Statement type |
| `proposition` | string | The proposition's id |
| `proposition_section` | string | The table that holds it: `propositionPathogenicity`, `propositionOncogenicity`, `propositionSomaticClinicalImpact` or `propositionClinvarCustom`; `read_parquet('proposition*.parquet', union_by_name = true)` covers all four |
| `classification` | struct (MappableConcept) | Use `classification.name` (or `classification.primaryCoding.code`) — e.g., "Pathogenic" |
| `strength` | struct (MappableConcept) | Use `strength.name` — e.g., "Definitive", "Likely" |
| `direction` | string | Evidence direction ("supports", "disputes", "neutral") |
| `quality` | struct (MappableConcept) | Use `quality.name` — submission or aggregate level, e.g., "criteria provided" |
| `hasEvidenceLines` | list\<string\> | Ids of the statement's evidence lines, all in `evidenceLine` |
| `extensions` | list\<struct\> | Named ClinVar attributes, each value in the `value_<kind>` field for its kind (e.g. `value_string`) |

SCV statements include additional columns: `description`, `contributions`, `reportedIn` and `specifiedBy`. `reportedIn` is a list of citation Documents, one per ClinVar citation, and `specifiedBy.reportedIn` is the assertion method's Document; see [`scv`](../parquet/tables.md#scv).

The four proposition tables share `id`, `type`, `subject`, `predicate`, `object`, `object_section` and `geneContextQualifier`, and add the qualifiers their types allow (`modeOfInheritanceQualifier`, `penetranceQualifier`, `conditionQualifier`), so read them together with `union_by_name = true`. See [Gene context](../parquet/tables.md#gene-context) for what the gene context is (one representative gene per variant, not a submitter-asserted gene), and [The columns](../parquet/tables.md#proposition-columns) for each column.

Run `DESCRIBE` in DuckDB to see the full schema for any section.

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
        p.geneContextQualifier.name AS gene,
        c.name AS condition_name,
        c.primaryCoding.code AS condition_code
    FROM 'scv.parquet' s
    JOIN 'propositionPathogenicity.parquet' p ON s.proposition = p.id
    LEFT JOIN 'condition.parquet' c
           ON c.id = CASE WHEN p.object_section = 'condition' THEN p.object END
    WHERE p.geneContextQualifier.primaryCoding.code = '672'    -- BRCA1 (NCBI Gene 672)
    ORDER BY s.classification.name;
    ```

    **Classification summary for a gene:**

    ```sql
    -- Count SCVs by classification and review status for BRCA2
    SELECT
        p.geneContextQualifier.name AS gene,
        s.classification.name AS classification,
        s.quality.name AS review_status,
        s.direction,
        COUNT(*) AS scv_count
    FROM 'scv.parquet' s
    JOIN 'propositionPathogenicity.parquet' p ON s.proposition = p.id
    WHERE p.geneContextQualifier.primaryCoding.code = '675'    -- BRCA2
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
    JOIN 'propositionPathogenicity.parquet' p ON s.proposition = p.id
    LEFT JOIN 'condition.parquet' c
           ON c.id = CASE WHEN p.object_section = 'condition' THEN p.object END
    WHERE p.geneContextQualifier.primaryCoding.code = '7157'   -- TP53
      AND s.quality.name IN ('criteria provided', 'expert panel')
    ORDER BY s.classification.name;
    ```

    **Cross-gene comparison — classification breakdown for multiple genes:**

    ```sql
    -- Compare pathogenicity classification distributions across genes
    SELECT
        p.geneContextQualifier.name AS gene,
        s.classification.name AS classification,
        COUNT(*) AS n
    FROM 'scv.parquet' s
    JOIN 'propositionPathogenicity.parquet' p ON s.proposition = p.id
    WHERE p.geneContextQualifier.primaryCoding.code IN ('672', '675', '7157', '4292')   -- BRCA1, BRCA2, TP53, MLH1
      AND s.quality.name = 'criteria provided'
    GROUP BY ALL
    ORDER BY gene, n DESC;
    ```

    The gene filters use the NCBI Gene number in `geneContextQualifier.primaryCoding.code`, not the symbol in `.name`: a few SCVs carry a submitted symbol there with no normalized gene (see [Gene context](../parquet/tables.md#gene-context)).

    **Submitter names and assertion methods** are typed columns too: join `submitter` on the contributor id, and read `specifiedBy.name`:

    ```sql
    -- SCVs with submitter name and assertion method
    SELECT
        s.id AS scv_id,
        s.classification.name AS classification,
        p.geneContextQualifier.name AS gene,
        sub.name AS submitter,
        s.specifiedBy.name AS method
    FROM 'scv.parquet' s
    JOIN 'propositionPathogenicity.parquet' p ON s.proposition = p.id
    LEFT JOIN 'submitter.parquet' sub
           ON sub.id = [c.contributor FOR c IN s.contributions IF c.activityType = 'submitted'][1]
    WHERE p.geneContextQualifier.primaryCoding.code = '672'    -- BRCA1
      AND s.classification.name = 'Pathogenic'
      AND s.quality.name = 'expert panel'
    LIMIT 20;
    ```

To get whole records back as JSON, use `to_json()` on a row, or rebuild the bundle from the tables with `gkm-bundle-parquet rebuild`; see [The whole record](../parquet/table-anatomy.md#whole-records).

## Earlier releases { #earlier-releases }

Only the current Parquet dataset of each live line is published; it is overwritten every release, and weekly deltas, archives and frozen lines carry no Parquet. To work with an earlier state:

- **Build it from the bundles.** Every official monthly stays published (in `archive/YYYY/` after its year ends) with a `.sha256` sidecar, and so does every delta. Rebuild the bundle for the week you need with the [replay recipe](weekly-deltas.md#rebuild-a-past-week), then build its tables with [`gkm-bundle-parquet`](../parquet/build-your-own.md) (on [PyPI](https://pypi.org/project/gkm-bundle-parquet/)), the tool that builds the published set. A full build needs a large machine; see [Build Your Own](../parquet/build-your-own.md#a-full-bundle). The columns come from the bundle's own schema version, so a bundle of schema 1.1.0 gives a wider set of tables than the 1.2.0 tables described here.
- **Take only what you need.** `gkm-bundle-parquet select` cuts a [mini-bundle](../parquet/build-your-own.md#cut-a-mini-bundle) (one variant, gene or submitter and everything it refers to) from any published bundle, without a large machine.
- **The 1.0.1 generation** is the frozen line `v1/1.0/`: its bundles and delta manifests, with no Parquet.

Parquet downloaded from an earlier release keeps its old tables and columns; see the [changelog](../reference/changelog.md) for what changed, and [Moving from the 1.1 Tables](../parquet/migrating-from-1.1.md) for the 1.1 tables.
