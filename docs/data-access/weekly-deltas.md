# Weekly Deltas

Links: [Monthly Full Bundles](monthly-full.md) · [Parquet Files](parquet.md) · [How Releases Work](release-model.md)

<div class="r2-browser" data-r2-type="deltas"></div>

A weekly delta is published for every ClinVar release under `deltas/<YYYY-MMDD>/`. Each release directory contains three artifact kinds:

```text
deltas/2026-0706/
  clinvar-gkm-delta_2026-0706.json.gz   added + updated records (same section structure as the full bundle)
  manifest.json                         per-section adds, updates, and deletes for this release
  parquet/<section>.parquet             typed Parquet for the changed records only
```

The most recent delta is mirrored at `deltas/00-latest/` under stable filenames (`clinvar-gkm-delta_00-latest.json.gz`, `manifest.json`, `parquet/<section>.parquet`).

??? example "Download a weekly delta with curl / Python"
    ```bash
    # Latest weekly delta + its manifest (stable URLs)
    curl -O https://pub-f0ad0e0dac0345408dcc95bda20beb42.r2.dev/deltas/00-latest/clinvar-gkm-delta_00-latest.json.gz
    curl -O https://pub-f0ad0e0dac0345408dcc95bda20beb42.r2.dev/deltas/00-latest/manifest.json
    ```

    ```python
    import urllib.request

    BASE = "https://pub-f0ad0e0dac0345408dcc95bda20beb42.r2.dev"

    # Latest weekly delta + manifest
    urllib.request.urlretrieve(
        f"{BASE}/deltas/00-latest/clinvar-gkm-delta_00-latest.json.gz",
        "clinvar-gkm-delta_00-latest.json.gz"
    )
    urllib.request.urlretrieve(
        f"{BASE}/deltas/00-latest/manifest.json",
        "manifest.json"
    )

    # A specific weekly delta (release 2026-07-06 -> dir 2026-0706)
    urllib.request.urlretrieve(
        f"{BASE}/deltas/2026-0706/clinvar-gkm-delta_2026-0706.json.gz",
        "clinvar-gkm-delta_2026-0706.json.gz"
    )
    ```

## Delta Bundle

The delta bundle has the **same shape as the monthly full** — a single JSON object with bundle sections at the root, each a keyed collection of objects. The difference is content: a delta contains only the records **added or updated** since its baseline release. Sections with no additions or updates are absent from the delta bundle. **Deleted records are not present in the bundle** — they are listed only in the manifest.

### manifest.json

The manifest describes exactly what changed and which full bundle the delta chain roots at:

```json
{
  "release": "2026-07-06",
  "baseline_release": "2026-06-29",
  "compare_release": "2026-07-06",
  "pipeline_version": "clinvar-gkm vX.Y.Z @ 2026-07-06T00:00:00Z",
  "checkpoint_full": { "path": "datasets/clinvar-gkm_2026-06.json.gz", "release": "2026-06" },
  "sections": {
    "allele":  { "added": 812,  "updated": 34,  "deleted": ["ga4gh:VA.oldDigest1"] },
    "scv":     { "added": 1203, "updated": 517, "deleted": ["clinvar.submission:SCV000000001.1"] },
    "vcv":     { "added": 44,   "updated": 96,  "deleted": [] }
  },
  "counts": { "A": 2063, "U": 647, "D": 2 }
}
```

| Field | Description |
| --- | --- |
| `release` | The ClinVar release date this delta represents |
| `baseline_release` | The prior release this delta was diffed against — `null` only on the very first release |
| `compare_release` | The release the changes are computed to (equals `release`) |
| `pipeline_version` | The pipeline build stamp that produced the delta |
| `checkpoint_full` | The monthly full bundle this delta chain replays onto — `{path, release}`; `null` before the first monthly full is published |
| `sections` | Per-section change summary — `added` and `updated` counts plus a `deleted` list of primary keys |
| `counts` | Roll-up totals across all sections — `A` (added), `U` (updated), `D` (deleted) |

**Deletes live only in the manifest.** For each section, `deleted` is the list of keys that must be removed; the delta bundle itself carries only the added and updated records.

### Consumer Replay Model

To reconstruct the current state, bootstrap from the monthly full that the latest delta's manifest names in `checkpoint_full`, then replay the contiguous weekly deltas published after it. For each delta, apply the manifest's deletes first, then upsert every record present in the delta bundle — section by section.

`checkpoint_full` tells you *which* monthly full to start from (`{path, release}`, where `release` is the `YYYY-MM` of the full). Replay only the deltas from later months — the deltas within the checkpoint's own month are already reflected in the monthly full. Verify chain integrity as you replay: each delta's `baseline_release` must equal the previous delta's `compare_release`. A mismatch means a weekly release is missing from the chain — re-bootstrap from the monthly full rather than applying a partial chain.

??? example "Python: rebuild the current full bundle from deltas"
    ```python
    import gzip
    import json
    import urllib.request

    BASE = "https://pub-f0ad0e0dac0345408dcc95bda20beb42.r2.dev"


    def fetch_json(url):
        with urllib.request.urlopen(url) as r:
            return json.load(r)


    def fetch_json_gz(url):
        with urllib.request.urlopen(url) as r:
            return json.loads(gzip.decompress(r.read()))


    # 1. The latest delta's manifest names the monthly full to bootstrap from.
    latest = fetch_json(f"{BASE}/deltas/00-latest/manifest.json")
    checkpoint = latest["checkpoint_full"]        # {"path": "datasets/clinvar-gkm_2026-06.json.gz",
                                                  #  "release": "2026-06"}  (None on initial rollout,
                                                  #  before any monthly full exists)

    # 2. Load that monthly full as the baseline state: {section: {key: record}}.
    state = fetch_json_gz(f"{BASE}/{checkpoint['path']}")
    checkpoint_month = checkpoint["release"]      # "2026-06"

    # 3. From the index, take the dated weekly deltas published AFTER the checkpoint month,
    #    oldest -> newest. (A delta dir is named YYYY-MMDD packed as "2026-0706", so the first
    #    7 chars are its YYYY-MM.) Skip the "latest" mirror and any delta in the checkpoint
    #    month or earlier — those are already folded into the monthly full.
    index = fetch_json(f"{BASE}/index.json")
    deltas = sorted(
        (d for d in index["deltas"]
         if d["release"] != "latest" and d["release"][:7] > checkpoint_month),
        key=lambda d: d["release"],
    )

    # 4. Replay each delta onto the baseline, verifying the chain as we go.
    prev_compare = None
    for d in deltas:
        manifest = fetch_json(f"{BASE}/{d['manifest']}")

        # Chain check: after the first, each delta must build on the previous compare_release.
        # The first delta builds on the checkpoint month's final release. A mismatch => a
        # missing week; re-bootstrap from the monthly full.
        if prev_compare is not None and manifest["baseline_release"] != prev_compare:
            raise SystemExit(
                f"broken chain before {manifest['release']}: re-bootstrap from a monthly full"
            )

        dirname = d["path"].strip("/").split("/")[-1]            # "2026-0706"
        delta = fetch_json_gz(f"{BASE}/{d['path']}clinvar-gkm-delta_{dirname}.json.gz")

        # 4a. Apply deletes (manifest only), then 4b. upsert added + updated records.
        for section, info in manifest["sections"].items():
            target = state.setdefault(section, {})
            for pk in info["deleted"]:
                target.pop(pk, None)
        for section, records in delta.items():
            state.setdefault(section, {}).update(records)

        prev_compare = manifest["compare_release"]

    # `state` now reflects the most recent weekly release.
    ```
