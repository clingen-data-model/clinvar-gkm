# Weekly Deltas

Links: [Monthly Full Bundles](monthly-full.md) · [Weekly Full Bundles](weekly-full.md) · [Parquet Files](parquet.md) · [How Releases Work](release-model.md)

<div class="r2-browser" data-r2-type="deltas"></div>

A weekly delta is published for every ClinVar release. Each delta is a bundle, its `.sha256` checksum and its manifest. The current month's deltas sit directly in `v1/1.1/deltas/`; earlier months of the year are in `deltas/YYYY-MM/`, and prior years in `archive/YYYY/deltas/YYYY-MM/`:

```text
v1/1.1/deltas/
  clinvar-gkm-delta_2026-1018.json.gz             added + updated records (same section structure as the full bundle)
  clinvar-gkm-delta_2026-1018.json.gz.sha256
  clinvar-gkm-delta_2026-1018.manifest.json       per-section adds, updates, and deletes for this release
  2026-09/
    clinvar-gkm-delta_2026-0904.json.gz           a finished month, moved here when October's first release posted
    ...
```

A delta's folder changes when its month or year rolls over; its file name and bytes do not. The line's `index.json` lists every delta with its current `bundle.path` and `manifest` path, so look paths up there rather than composing them. Deltas carry no Parquet: Parquet is derived and published only for the latest release ([Parquet Files](parquet.md)).

??? example "Download a weekly delta with curl / Python"
    ```bash
    # A delta of the current month, its checksum and its manifest
    BASE="https://data.clinvar-gkm.org/v1/1.1/deltas"
    curl -O "${BASE}/clinvar-gkm-delta_2026-1018.json.gz"
    curl -O "${BASE}/clinvar-gkm-delta_2026-1018.json.gz.sha256"
    curl -O "${BASE}/clinvar-gkm-delta_2026-1018.manifest.json"
    sha256sum -c clinvar-gkm-delta_2026-1018.json.gz.sha256   # macOS: shasum -a 256 -c
    ```

    ```python
    import json
    import urllib.request

    BASE = "https://data.clinvar-gkm.org"

    # The newest delta, from the line's release index
    index = json.load(urllib.request.urlopen(f"{BASE}/v1/1.1/index.json"))
    newest = max(index["deltas"], key=lambda d: d["release"])
    for path in (newest["bundle"]["path"], newest["manifest"]):
        urllib.request.urlretrieve(f"{BASE}/{path}", path.rsplit("/", 1)[-1])
    ```

## Delta Bundle

The delta bundle has the **same shape as the monthly full** — a single JSON object with bundle sections at the root, each a keyed collection of objects. The difference is content: a delta contains only the records **added or updated** since its baseline release. Sections with no additions or updates are absent from the delta bundle. **Deleted records are not present in the bundle** — they are listed only in the manifest.

### The delta manifest { #manifestjson }

Each delta's manifest, `clinvar-gkm-delta_YYYY-MMDD.manifest.json`, describes exactly what changed and which monthly full the delta chain starts from:

```json
{
  "release": "2026-10-11",
  "baseline_release": "2026-10-04",
  "compare_release": "2026-10-11",
  "pipeline_version": "clinvar-gkm vX.Y.Z @ 2026-10-11T00:00:00Z",
  "checkpoint_full": { "path": "v1/1.1/clinvar-gkm_2026-10.json.gz", "release": "2026-10" },
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
| `checkpoint_full` | The official monthly that precedes this delta — the newest monthly whose `source_release` is earlier than `release` — as `{path, release}`, where `release` is the monthly's `YYYY-MM`. `path` is where the monthly was when the delta was published; after a year rollover, find it in `index.json` by `release`. `null` before the first monthly full is published |
| `sections` | Per-section change summary — `added` and `updated` counts plus a `deleted` list of primary keys |
| `counts` | Roll-up totals across all sections — `A` (added), `U` (updated), `D` (deleted) |

**Deletes live only in the manifest.** For each section, `deleted` is the list of keys that must be removed; the delta bundle itself carries only the added and updated records.

### Consumer Replay Model

A monthly full plus the deltas after it rebuild the state at any weekly release. Every official monthly has a **`source_release`** in `index.json`: the weekly release it was built from (the `2026-10` monthly has `source_release` `2026-09-28`). Each delta records the release it was diffed against (`baseline_release`) and the release it brings you to (`release`).

For each delta, apply the manifest's deletes first, then upsert every record present in the delta bundle, section by section.

### Rebuild a past week { #rebuild-a-past-week }

Weekly full bundles are kept only for the current month ([Weekly Full Bundles](weekly-full.md)). To rebuild the state at any weekly release W — a past week, or the newest one:

1. Take the **newest official monthly whose `source_release` ≤ W**.
2. Apply, in release order, **every delta whose `release` is later than that `source_release` and ≤ W**.
3. **Check the chain** as you go: the first delta's `baseline_release` equals the monthly's `source_release`, and each later delta's `baseline_release` equals the previous delta's `release`. A mismatch means a release is missing; stop rather than apply a partial chain.

The deltas to apply are chosen by **release date, not by month**. The `2026-10` monthly is built from `2026-09-28`, so rebuilding `2026-10-11` takes the `2026-10` monthly and applies the `2026-10-04` and `2026-10-11` deltas, both from the monthly's own month. (An earlier version of this page skipped deltas from the monthly's month; that missed them.)

A delta's `checkpoint_full` names the monthly that precedes it, so it is the right base for every delta up to the next monthly.

??? example "Python: rebuild the full bundle at a weekly release"
    ```python
    import gzip
    import json
    import urllib.request

    BASE = "https://data.clinvar-gkm.org"
    W = "2026-10-11"   # the weekly release to rebuild, YYYY-MM-DD


    def fetch_json(url):
        with urllib.request.urlopen(url) as r:
            return json.load(r)


    def fetch_json_gz(url):
        with urllib.request.urlopen(url) as r:
            return json.loads(gzip.decompress(r.read()))


    # 0. The current line's release index, via the root version manifest.
    root = fetch_json(f"{BASE}/index.json")
    line = next(v for v in root["versions"].values() if v["status"] == "current")
    index = fetch_json(f"{BASE}/{line['index'].lstrip('/')}")

    # Monthlies and deltas of the current year, plus those moved to archive/YYYY/.
    monthlies = list(index["datasets"]["monthly"])
    deltas = list(index["deltas"])
    for year in index.get("archives", {}).values():
        monthlies += year.get("monthly", [])
        deltas += year.get("deltas", [])

    # 1. The newest official monthly whose source_release <= W (skip the 00-latest copy).
    base = max(
        (m for m in monthlies
         if not m.get("latest") and m.get("source_release") and m["source_release"] <= W),
        key=lambda m: m["source_release"],
    )
    state = fetch_json_gz(f"{BASE}/{base['path']}")

    # 2. Every delta after the monthly's source_release, up to and including W, oldest first.
    chain = sorted(
        (d for d in deltas if base["source_release"] < d["release"] <= W),
        key=lambda d: d["release"],
    )

    # 3. Replay, checking the chain: each delta must build on the release before it.
    prev = base["source_release"]
    for d in chain:
        manifest = fetch_json(f"{BASE}/{d['manifest']}")
        if manifest["baseline_release"] != prev:
            raise SystemExit(
                f"broken chain at {manifest['release']}: "
                f"baseline {manifest['baseline_release']}, expected {prev}"
            )
        delta = fetch_json_gz(f"{BASE}/{d['bundle']['path']}")

        # 3a. Apply deletes (manifest only), then 3b. upsert added + updated records.
        for section, info in manifest["sections"].items():
            target = state.setdefault(section, {})
            for pk in info["deleted"]:
                target.pop(pk, None)
        for section, records in delta.items():
            if isinstance(records, dict):           # skip top-level scalars such as schema_version
                state.setdefault(section, {}).update(records)

        prev = manifest["release"]

    # `state` now holds the full bundle at release W (prev == W when W is a published release).
    ```

    The recipe shows the logic. A monthly full is about 4.8 GB compressed and much larger as Python objects, so for real use stream the sections to disk or a database instead of holding them in memory.
