# Monthly Full Bundles

Links: [Weekly Full Bundles](weekly-full.md) · [Weekly Deltas](weekly-deltas.md) · [Parquet Files](parquet.md) · [How Releases Work](release-model.md)

The official monthly full bundle is a gzip-compressed JSON file containing every variation, statement, proposition, condition, and supporting reference record for a release. It lines up with ClinVar's monthly `ClinVarVCVRelease_YYYY-MM`: `clinvar-gkm_YYYY-MM` is built from the newest weekly release **before** ClinVar's monthly cut, and the line's `index.json` names that release as the monthly's `source_release`. For example, the `2026-10` monthly has `source_release` `2026-09-28`.

The monthlies of the current year sit at the top of the line folder, `v1/1.1/`; `clinvar-gkm_00-latest.json.gz` is a stable URL for the newest one. When the first release of a new year is published, the finished year's monthlies move to `v1/1.1/archive/YYYY/`, where they are kept. Monthlies and deltas are the durable record: every past week can be rebuilt from them ([Rebuild a past week](weekly-deltas.md#rebuild-a-past-week)).

<div class="r2-browser" data-r2-type="monthly"></div>

!!! note "Prerequisites"
    The curl recipe needs only a shell. The Python recipe uses **Python 3** and only the standard library. New to Python? Install it from [python.org/downloads](https://www.python.org/downloads/) or your OS package manager.

??? example "Download a monthly full with curl"
    ```bash
    # Newest official monthly full (stable URL)
    curl -O https://data.clinvar-gkm.org/v1/1.1/clinvar-gkm_00-latest.json.gz

    # Or a specific month of the current year, with its checksum
    curl -O https://data.clinvar-gkm.org/v1/1.1/clinvar-gkm_2026-10.json.gz
    curl -O https://data.clinvar-gkm.org/v1/1.1/clinvar-gkm_2026-10.json.gz.sha256
    sha256sum -c clinvar-gkm_2026-10.json.gz.sha256      # macOS: shasum -a 256 -c

    # Decompress
    gunzip clinvar-gkm_00-latest.json.gz
    ```

??? example "Download a monthly full with Python"
    ```python
    import urllib.request

    BASE = "https://data.clinvar-gkm.org/v1/1.1"

    # Download the newest official monthly full bundle
    urllib.request.urlretrieve(
        f"{BASE}/clinvar-gkm_00-latest.json.gz",
        "clinvar-gkm_00-latest.json.gz"
    )

    # Download a specific monthly of the current year
    urllib.request.urlretrieve(
        f"{BASE}/clinvar-gkm_2026-10.json.gz",
        "clinvar-gkm_2026-10.json.gz"
    )

    # A prior year's monthly is under archive/YYYY/ (2026's monthlies move there when the first
    # release of 2027 is published)
    urllib.request.urlretrieve(
        f"{BASE}/archive/2026/clinvar-gkm_2026-07.json.gz",
        "clinvar-gkm_2026-07.json.gz"
    )
    ```

!!! tip "Validate a downloaded bundle"
    Every JSON bundle conforms to the [ClinVar-GKM bundle schema](../output-reference/overview.md#bundle-schema)
    (JSON Schema Draft 2020-12) — the same schema covers the monthly full, weekly deltas, and sub-bundle
    extracts. Every published bundle passes strict validation against it before release; see
    [Release Validation](../reference/release-validation.md). The
    [GKM Toolkit](https://ga4gh.github.io/gkm-starter-kit/latest/tools/gkm-toolkit/) validates a downloaded
    bundle the same way, given the ClinVar-GKM schemas; see
    [Validate a bundle](../working-in-python.md#validate-a-bundle).
