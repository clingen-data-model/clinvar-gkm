# Monthly Full Bundles

Links: [Weekly Deltas](weekly-deltas.md) · [Parquet Files](parquet.md) · [How Releases Work](release-model.md)

The monthly full bundle is a gzip-compressed JSON file containing every variation, statement, proposition, condition, and supporting reference record for a release. `clinvar-gkm_00-latest.json.gz` is a stable URL that always points at the newest monthly full; dated bundles (`clinvar-gkm_YYYY-MM.json.gz`) pin a specific month. Prior-year bundles are retained indefinitely under `archives/{YYYY}/`.

<div class="r2-browser" data-r2-type="monthly"></div>

!!! note "Prerequisites"
    The curl recipe needs only a shell. The Python recipe uses **Python 3** and only the standard library. New to Python? Install it from [python.org/downloads](https://www.python.org/downloads/) or your OS package manager.

??? example "Download a monthly full with curl"
    ```bash
    # Latest monthly full bundle (stable URL)
    curl -O https://pub-f0ad0e0dac0345408dcc95bda20beb42.r2.dev/datasets/clinvar-gkm_00-latest.json.gz

    # Or a specific month (dated, checkpoint-addressable)
    curl -O https://pub-f0ad0e0dac0345408dcc95bda20beb42.r2.dev/datasets/clinvar-gkm_2026-06.json.gz

    # Decompress
    gunzip clinvar-gkm_00-latest.json.gz
    ```

??? example "Download a monthly full with Python"
    ```python
    import urllib.request

    BASE = "https://pub-f0ad0e0dac0345408dcc95bda20beb42.r2.dev"

    # Download latest monthly full bundle
    urllib.request.urlretrieve(
        f"{BASE}/datasets/clinvar-gkm_00-latest.json.gz",
        "clinvar-gkm_00-latest.json.gz"
    )

    # Download a specific monthly full bundle
    urllib.request.urlretrieve(
        f"{BASE}/datasets/clinvar-gkm_2026-06.json.gz",
        "clinvar-gkm_2026-06.json.gz"
    )

    # Download an archived full bundle from a prior year
    urllib.request.urlretrieve(
        f"{BASE}/archives/2025/clinvar-gkm_2025-03.json.gz",
        "clinvar-gkm_2025-03.json.gz"
    )
    ```

!!! tip "Validate a downloaded bundle"
    Every JSON bundle conforms to the [ClinVar-GKM bundle schema](../output-reference/overview.md#bundle-schema)
    (JSON Schema Draft 2020-12) — the same schema covers the monthly full, weekly deltas, and sub-bundle
    extracts. The [GKM Toolkit](https://ga4gh.github.io/gkm-starter-kit/latest/tools/gkm-toolkit/) validates
    a bundle against it in one call.
