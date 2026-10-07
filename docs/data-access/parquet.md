# Parquet Files

Links: [Monthly Full Bundles](monthly-full.md) · [Weekly Deltas](weekly-deltas.md) · [How Releases Work](release-model.md)

Typed Parquet files are produced for each monthly full and organized by month, mirroring the JSON bundle lifecycle. Each monthly full lands in a dated directory `datasets/parquet/YYYY-MM/`, and `datasets/parquet/00-latest/` always points at the newest monthly full (stable URL). At year boundaries, prior-year month sets move to `archives/{YYYY}/parquet/YYYY-MM/` and are retained indefinitely. Because each month set is preserved, a delta chain's `checkpoint_full` monthly Parquet stays available for [reconstruction](#applying-deltas-keeping-a-parquet-set-current) after later months publish. The weekly delta Parquet (changed records only) lives separately under `deltas/<YYYY-MMDD>/parquet/`.

## Monthly full sets

<div class="r2-browser" data-r2-type="parquet-monthly"></div>

## Weekly Parquet deltas

Changed-rows delta Parquet (not a full set) — one group per weekly release, carrying only the sections that changed that week.

<div class="r2-browser" data-r2-type="parquet-weekly"></div>

## Available Parquet files

Each Parquet file contains one bundle section with typed, query-friendly columns extracted from the JSON objects. Every section includes an `id` column (the object identifier) and a `data` column (the full JSON object as a string), plus additional typed columns for key fields — enabling efficient filtering and aggregation without parsing JSON.

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
| `varcond-proposition.parquet` | Variant×condition propositions (Pathogenicity, ClinicalSignificance, Diagnostic, Prognostic) |
| `vartumor-proposition.parquet` | Variant×tumorType propositions (Oncogenicity) |
| `vartherapy-proposition.parquet` | Variant×therapy propositions (TherapeuticResponse) |
| `varcustom-proposition.parquet` | Custom variant×condition propositions |
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
    # 00-latest = the newest monthly full; swap for a dated month (e.g. .../parquet/2026-06) to pin a release.
    BASE="https://pub-f0ad0e0dac0345408dcc95bda20beb42.r2.dev/datasets/parquet/00-latest"
    mkdir -p clinvar-gkm-parquet && cd clinvar-gkm-parquet

    # Download specific sections
    curl -O "${BASE}/scv.parquet"
    curl -O "${BASE}/varcond-proposition.parquet"
    curl -O "${BASE}/condition.parquet"

    # Or download all 22 sections
    for section in sequenceReference location allele copyNumberCount copyNumberChange \
                   gene variation condition conditionSet therapy therapyGroup submitter \
                   varcond-proposition vartumor-proposition vartherapy-proposition varcustom-proposition \
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
      SELECT s.id, s.classification.name AS classification, p.predicate, p.object_condition_id
      FROM 'scv.parquet' s
      JOIN 'varcond-proposition.parquet' p ON s.proposition_id = p.id
      WHERE s.classification.name = 'Pathogenic'
        AND p.object_condition_id LIKE '%clinvar.trait:9580%'
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

Statement sections (`scv`, `vcv`, `rcv`) share a common set of typed columns:

| Column | Type | Description |
| --- | --- | --- |
| `id` | string | Statement identifier |
| `type` | string | Statement type |
| `proposition_id` | string | FK to the matching proposition Parquet — one of `varcond-proposition`, `vartumor-proposition`, `vartherapy-proposition`, `varcustom-proposition`, per the proposition's datatype |
| `classification` | struct (MappableConcept) | Use `classification.name` (or `classification.primaryCoding.code`) — e.g., "Pathogenic" |
| `strength` | struct (MappableConcept) | Use `strength.name` — e.g., "definitive", "likely" |
| `direction` | string | Evidence direction ("supports", "disputes", "neutral") |
| `quality` | struct (MappableConcept) | Use `quality.name` — submission level, e.g., "criteria provided" |
| `has_evidence_lines` | list\<string\> | FK references to evidence line Parquet (`evidenceLine` for SCV, `vcv_evidenceLine` for VCV, `rcv_evidenceLine` for RCV) |
| `extensions` | string | JSON array of extensions |
| `data` | string | Full JSON object |

SCV statements include additional columns: `description`, `contributions`, `reported_in`, `specified_by`.

The four proposition sections are typed per datatype: `varcond-proposition` (`subject_variant_id`, `predicate`, `object_condition_id`, `type`, `gene_context_name`, `mode_of_inheritance`, `penetrance`), `vartumor-proposition` (`object_tumor_type_id`, …), `vartherapy-proposition` (`object_therapy`, `condition_qualifier_id`, …), and `varcustom-proposition` (`custom_proposition_type`, `subject_id`, `object_id`, `qualifiers`) — enabling JOINs across statements, variants, and conditions without parsing JSON.

Every section includes `id` and `data` at minimum. Run `DESCRIBE` in DuckDB to see the full schema for any section.

These examples demonstrate cross-section JOINs using typed columns. Most analytical queries can be answered without parsing JSON — the varcond proposition's `gene_context_name` column carries the gene symbol directly, and the condition's `primaryCoding` struct carries the MedGen code. (These queries join `scv.parquet` to `varcond-proposition.parquet`, the variant×condition group that holds pathogenicity and clinical-significance propositions; the other three proposition groups — `vartumor`, `vartherapy`, `varcustom` — have their own typed columns.)

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
    JOIN 'varcond-proposition.parquet' p ON s.proposition_id = p.id
    LEFT JOIN 'condition.parquet' c ON p.object_condition_id = c.id
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
    JOIN 'varcond-proposition.parquet' p ON s.proposition_id = p.id
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
    JOIN 'varcond-proposition.parquet' p ON s.proposition_id = p.id
    LEFT JOIN 'condition.parquet' c ON p.object_condition_id = c.id
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
    JOIN 'varcond-proposition.parquet' p ON s.proposition_id = p.id
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
    JOIN 'varcond-proposition.parquet' p ON s.proposition_id = p.id
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

## Reconstitute a full Parquet view for any week in a month

The monthly full Parquet set is a month-start baseline. To get a complete Parquet view as of any **week** in a month, bootstrap from the checkpoint monthly full set, then apply each weekly delta in order — up to the week you want. Each weekly delta Parquet carries only the **added and updated** rows for a section; that week's `manifest.json` carries the `sections.<section>.deleted` ids. Applying one week is, per section: **drop every row whose `id` appears in the delta or in that section's `deleted` list, then append the delta rows.** Apply the weeks oldest→newest until you reach the target week, verifying `baseline_release == prior compare_release` at each step; if the chain breaks, re-bootstrap from the monthly full rather than applying a partial chain.

This is the same contiguity rule as the [JSON replay](weekly-deltas.md#consumer-replay-model) — only the per-section apply differs (a keyed Parquet upsert instead of a dict merge).

### Applying Deltas (keeping a Parquet set current)

The weekly delta ships typed Parquet too, so you can maintain a current Parquet set without re-downloading the full monthly bundle. The model mirrors the [JSON replay](weekly-deltas.md#consumer-replay-model): start from the checkpoint monthly full, then apply each weekly delta in order.

Each delta is a per-section **keyed upsert plus a delete list**:

- `deltas/<YYYY-MMDD>/parquet/<section>.parquet` holds the **added and updated** rows for that section (keyed by `id`). Sections with no adds/updates have no file.
- `deltas/<YYYY-MMDD>/manifest.json` holds the **deletes** — `sections.<section>.deleted` is the list of `id` values removed this release. Deletes are **not** in the Parquet.

Every section Parquet — full and delta alike — exposes an `id` column, and the manifest's `deleted` keys are those same `id` values, so applying a delta is: **drop from the full every row whose `id` appears in the delta or in the delete list, then append the delta rows.** Because the full and delta Parquet for a section are produced by the identical schema, their columns line up exactly (`UNION ALL BY NAME`).

??? example "Download the checkpoint full + delta pieces"
    ```bash
    BASE="https://pub-f0ad0e0dac0345408dcc95bda20beb42.r2.dev"

    # 1. The checkpoint monthly full named by the delta's manifest (e.g. 2026-06).
    curl -s "${BASE}/deltas/00-latest/manifest.json" -o manifest.json
    CKPT=$(python3 -c "import json;print(json.load(open('manifest.json'))['checkpoint_full']['release'])")

    # 2. The checkpoint full Parquet set -> full/, and the delta set -> delta/.
    mkdir -p full delta
    for section in sequenceReference location allele copyNumberCount copyNumberChange \
                   gene variation condition conditionSet therapy therapyGroup submitter \
                   varcond-proposition vartumor-proposition vartherapy-proposition varcustom-proposition \
                   evidenceLine vcv_evidenceLine rcv_evidenceLine scv vcv rcv; do
      curl -sf "${BASE}/datasets/parquet/${CKPT}/${section}.parquet" -o "full/${section}.parquet"  || true
      curl -sf "${BASE}/deltas/00-latest/parquet/${section}.parquet" -o "delta/${section}.parquet" || true
    done
    ```

??? example "Apply one week (DuckDB)"
    ```python
    import duckdb, json, os, shutil

    con = duckdb.connect()
    manifest = json.load(open("manifest.json"))

    # Start from a copy of the checkpoint full set; overwrite only the changed sections.
    shutil.copytree("full", "updated", dirs_exist_ok=True)

    for section, info in manifest["sections"].items():
        full    = f"full/{section}.parquet"      # checkpoint (baseline) section
        delta   = f"delta/{section}.parquet"     # added + updated rows (may be absent)
        out     = f"updated/{section}.parquet"
        deleted = info["deleted"]                # ids removed this release
        has_delta = os.path.exists(delta)

        if not os.path.exists(full):
            # Section new since the checkpoint: the delta rows ARE the section.
            if has_delta:
                shutil.copyfile(delta, out)
            continue

        if not has_delta:
            # Deletes only — filter the baseline, nothing to append.
            con.execute("""
                COPY (SELECT * FROM read_parquet(?) WHERE id NOT IN (SELECT unnest(?)))
                TO ? (FORMAT PARQUET)
            """, [full, deleted, out])
        else:
            # Drop updated + deleted keys from the baseline, then append the delta rows.
            con.execute("""
                COPY (
                    SELECT * FROM read_parquet(?)                        -- baseline full
                    WHERE id NOT IN (SELECT id FROM read_parquet(?))     -- drop updated keys
                      AND id NOT IN (SELECT unnest(?))                   -- drop deleted keys
                    UNION ALL BY NAME
                    SELECT * FROM read_parquet(?)                        -- append added + updated
                ) TO ? (FORMAT PARQUET)
            """, [full, delta, deleted, delta, out])

    # `updated/<section>.parquet` now reflects the release the manifest names.
    ```

??? example "Chain to a specific week (Python)"
    ```python
    import duckdb, json, os, urllib.request

    BASE = "https://pub-f0ad0e0dac0345408dcc95bda20beb42.r2.dev"
    TARGET_WEEK = "2026-07-20"   # ClinVar release date (YYYY-MM-DD) to reconstruct up to (inclusive)

    SECTIONS = [
        "sequenceReference", "location", "allele", "copyNumberCount", "copyNumberChange",
        "gene", "variation", "condition", "conditionSet", "therapy", "therapyGroup", "submitter",
        "varcond-proposition", "vartumor-proposition", "vartherapy-proposition", "varcustom-proposition",
        "evidenceLine", "vcv_evidenceLine", "rcv_evidenceLine", "scv", "vcv", "rcv",
    ]

    con = duckdb.connect()


    def fetch_json(url):
        with urllib.request.urlopen(url) as r:
            return json.load(r)


    # 1. The latest manifest names the checkpoint monthly full to bootstrap from.
    checkpoint = fetch_json(f"{BASE}/deltas/00-latest/manifest.json")["checkpoint_full"]
    checkpoint_month = checkpoint["release"]     # "2026-06"

    # 2. Download the checkpoint full Parquet set into updated/ as the starting state.
    os.makedirs("updated", exist_ok=True)
    for section in SECTIONS:
        try:
            urllib.request.urlretrieve(
                f"{BASE}/datasets/parquet/{checkpoint_month}/{section}.parquet",
                f"updated/{section}.parquet",
            )
        except Exception:
            pass   # a section absent from the checkpoint first appears when a delta introduces it

    # 3. From the index, take the dated weekly deltas AFTER the checkpoint month, oldest -> newest,
    #    up to and including TARGET_WEEK.
    index = fetch_json(f"{BASE}/index.json")
    deltas = sorted(
        (d for d in index["deltas"]
         if d["release"] != "latest"
         and d["release"][:7] > checkpoint_month
         and d["release"] <= TARGET_WEEK),
        key=lambda d: d["release"],
    )

    # 4. Replay each delta's Parquet (added/updated rows) + manifest deletes, verifying the chain.
    prev_compare = None
    for d in deltas:
        manifest = fetch_json(f"{BASE}/{d['manifest']}")
        if prev_compare is not None and manifest["baseline_release"] != prev_compare:
            raise SystemExit(
                f"broken chain before {manifest['release']}: re-bootstrap from a monthly full"
            )

        present = set(d.get("parquet") or [])   # sections with a delta Parquet this week
        for section, info in manifest["sections"].items():
            out = f"updated/{section}.parquet"
            deleted = info["deleted"]
            delta_local = None
            if section in present:
                delta_local = f"updated/.delta_{section}.parquet"
                urllib.request.urlretrieve(
                    f"{BASE}/{d['path']}parquet/{section}.parquet", delta_local
                )

            if not os.path.exists(out):
                # Section new since the checkpoint: the delta rows ARE the section.
                if delta_local:
                    os.replace(delta_local, out)
                continue

            tmp = out + ".tmp"
            if delta_local is None:
                # Deletes only — filter the baseline, nothing to append.
                con.execute("""
                    COPY (SELECT * FROM read_parquet(?) WHERE id NOT IN (SELECT unnest(?)))
                    TO ? (FORMAT PARQUET)
                """, [out, deleted, tmp])
            else:
                con.execute("""
                    COPY (
                        SELECT * FROM read_parquet(?)
                        WHERE id NOT IN (SELECT id FROM read_parquet(?))
                          AND id NOT IN (SELECT unnest(?))
                        UNION ALL BY NAME
                        SELECT * FROM read_parquet(?)
                    ) TO ? (FORMAT PARQUET)
                """, [out, delta_local, deleted, delta_local, tmp])
            os.replace(tmp, out)
            if delta_local and os.path.exists(delta_local):
                os.remove(delta_local)

        prev_compare = manifest["compare_release"]

    # updated/<section>.parquet now reflects the TARGET_WEEK release.
    ```

A single-file convenience alternative: because the pipeline also refreshes `datasets/parquet/00-latest/` on every monthly full, you can skip replay entirely and pull the current full set directly — replay is for reconstructing a *specific* historical release or minimizing download size between monthly fulls.
