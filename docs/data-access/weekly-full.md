# Weekly Full Bundles

Links: [Monthly Full Bundles](monthly-full.md) · [Weekly Deltas](weekly-deltas.md) · [Parquet Files](parquet.md) · [How Releases Work](release-model.md)

A weekly full bundle is published for every ClinVar weekly release. It has the same content and structure as a monthly full, built from that week's release, so the newest one is the current state with no replay. The weekly fulls live in `v1/1.1/weekly/`, the counterpart of NCBI's [`xml/weekly_release/`](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/weekly_release/):

```text
v1/1.1/weekly/
  clinvar-gkm_00-latest_weekly.json.gz        newest weekly full (stable URL)
  clinvar-gkm_YYYY-MMDD.json.gz               one per weekly release of the CURRENT month
  clinvar-gkm_YYYY-MMDD.json.gz.sha256
```

!!! warning "Weekly fulls are kept for the current month only"
    When the first release of a new month is published, the previous month's weekly fulls are **deleted**, as NCBI deletes its weekly releases. They are a convenience copy, not the record: the official monthly that follows is built from the month's last release, and every past week can be rebuilt exactly from a monthly plus deltas. See [Rebuild a past week](weekly-deltas.md#rebuild-a-past-week). Don't hard-code a dated weekly URL in a script that runs after the month ends.

<div class="r2-browser" data-r2-type="weekly"></div>

??? example "Download a weekly full with curl"
    ```bash
    # Newest weekly full (stable URL)
    curl -O https://data.clinvar-gkm.org/v1/1.1/weekly/clinvar-gkm_00-latest_weekly.json.gz

    # Or a specific week of the current month, with its checksum
    curl -O https://data.clinvar-gkm.org/v1/1.1/weekly/clinvar-gkm_2026-1018.json.gz
    curl -O https://data.clinvar-gkm.org/v1/1.1/weekly/clinvar-gkm_2026-1018.json.gz.sha256
    sha256sum -c clinvar-gkm_2026-1018.json.gz.sha256      # macOS: shasum -a 256 -c
    ```

!!! tip "Monthly, weekly full, or monthly plus deltas?"
    - **The current state:** the newest weekly full.
    - **A fixed monthly snapshot that matches ClinVar's monthly release:** the official monthly.
    - **Keeping a local copy current without re-downloading a full bundle every week:** the monthly plus the [weekly deltas](weekly-deltas.md).
