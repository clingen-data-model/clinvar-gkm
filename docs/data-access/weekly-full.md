# Weekly Full Bundles

Links: [Monthly Full Bundles](monthly-full.md) · [Weekly Deltas](weekly-deltas.md) · [Parquet Files](parquet.md) · [How Releases Work](release-model.md)

Older release lines (1.1.x, 1.0.1) are on [Previous Releases](previous-releases.md).

A weekly full bundle is published for every ClinVar weekly release. It has the same content and structure as a monthly full, built from that week's release, so the newest one is the current state with no replay. The weekly fulls live in `v1/1.2/weekly/`, the counterpart of NCBI's [`xml/weekly_release/`](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/weekly_release/):

```text
v1/1.2/weekly/
  clinvar-gkm_00-latest_weekly.json.gz        newest weekly full (stable URL)
  clinvar-gkm_YYYY-MMDD.json.gz               one per weekly release of the CURRENT month
  clinvar-gkm_YYYY-MMDD.json.gz.sha256
```

!!! warning "Weekly fulls are kept for the current month only"
    When the first release of a new month is published, the previous month's weekly fulls are **deleted**, as NCBI deletes its weekly releases. The newest of them stays until the new month's official monthly is published (the monthly is normally a copy of it), and is deleted as soon as the monthly is up. They are a convenience copy, not the record: the official monthly that follows is built from the month's last release, and every past week can be rebuilt exactly from a monthly plus deltas. See [Rebuild a past week](weekly-deltas.md#rebuild-a-past-week). Don't hard-code a dated weekly URL in a script that runs after the month ends.

<div class="r2-browser" data-r2-type="weekly"></div>

!!! note "Prerequisites"
    - **curl**, and **`sha256sum`** (Linux, recent macOS) or **`shasum -a 256`** (any macOS) to check the download.
    - **Disk.** A weekly full is about 4.9 GB compressed and 68.5 GB decompressed. Read it streamed
      (`gunzip -c`) rather than decompressing it to disk; see [Count records in a full bundle](download.md#count-records-in-a-full-bundle).

??? example "Download a weekly full with curl"
    ```bash
    # Newest weekly full (stable URL)
    curl -fO https://data.clinvar-gkm.org/v1/1.2/weekly/clinvar-gkm_00-latest_weekly.json.gz

    # Or a dated weekly full, with its checksum. index.json lists the current month's weekly fulls
    # (they are deleted when the month ends); this takes the newest, or pick one by its "release" date.
    W=$(curl -fsS https://data.clinvar-gkm.org/v1/1.2/index.json | python3 -c '
    import json, sys
    weekly = [w for w in json.load(sys.stdin)["datasets"]["weekly"] if not w["latest"]]
    print(max(weekly, key=lambda w: w["release"])["path"])')
    curl -fO "https://data.clinvar-gkm.org/${W}"
    curl -fO "https://data.clinvar-gkm.org/${W}.sha256"
    sha256sum -c "$(basename "${W}").sha256"      # macOS: shasum -a 256 -c
    ```

!!! tip "Monthly, weekly full, or monthly plus deltas?"
    - **The current state:** the newest weekly full.
    - **A fixed monthly snapshot that matches ClinVar's monthly release:** the official monthly.
    - **Keeping a local copy current without re-downloading a full bundle every week:** the monthly plus the [weekly deltas](weekly-deltas.md), all from one line. When a new line starts, start again from its first monthly ([Consumer Replay Model](weekly-deltas.md#consumer-replay-model)).
