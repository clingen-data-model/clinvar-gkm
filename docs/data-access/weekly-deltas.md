# Weekly Deltas

Links: [Monthly Full Bundles](monthly-full.md) · [Weekly Full Bundles](weekly-full.md) · [Parquet Files](parquet.md) · [How Releases Work](release-model.md)

Older release lines (1.1.x, 1.0.1) are on [Previous Releases](previous-releases.md).

<div class="r2-browser" data-r2-type="deltas"></div>

The list groups deltas by year, newest first: the current year is open, and each earlier year is a collapsible list under **Archived years**.

A weekly delta is published for every ClinVar release. Each delta is a bundle, its `.sha256` checksum and its manifest. The current month's deltas sit directly in `v1/1.2/deltas/`; earlier months of the year are in `deltas/YYYY-MM/`, and prior years in `archive/YYYY/deltas/YYYY-MM/`:

```text
v1/1.2/deltas/
  clinvar-gkm-delta_2026-1206.json.gz             added + updated records (same section structure as the full bundle)
  clinvar-gkm-delta_2026-1206.json.gz.sha256
  clinvar-gkm-delta_2026-1206.manifest.json       per-section adds, updates, and deletes for this release
  2026-11/
    clinvar-gkm-delta_2026-1108.json.gz           a finished month, moved here when December's first release posted
    ...
```

A delta's folder changes when its month or year rolls over; its file name and bytes do not. The line's `index.json` lists every delta with its current `bundle.path` and `manifest` path, so look paths up there rather than composing them. Deltas carry no Parquet: Parquet is derived and published only for the latest release ([Parquet Files](parquet.md)).

!!! note "Prerequisites"
    - **curl** and **`sha256sum`** (Linux, recent macOS) or **`shasum -a 256`** (any macOS), for the shell example.
    - **Python 3**, standard library only (tested with 3.14), for the Python examples.
    - A delta is a few MB to about 60 MB. The [replay recipe](#rebuild-a-past-week) also downloads a monthly full (4.9 GB compressed, 68.5 GB decompressed) and holds it in memory as Python objects, which needs several hundred GB of memory: it shows the logic, and real use streams the sections to disk or a database.

??? example "Download a weekly delta with curl / Python"
    ```bash
    # The newest delta, its checksum and its manifest. index.json lists every delta with its current path
    # (a delta moves to its month's folder when the month ends); pick another by its "release" date.
    HOST="https://data.clinvar-gkm.org"
    read -r BUNDLE MANIFEST <<< "$(curl -fsS "${HOST}/v1/1.2/index.json" | python3 -c '
    import json, sys
    d = max(json.load(sys.stdin)["deltas"], key=lambda d: d["release"])
    print(d["bundle"]["path"], d["manifest"])')"
    curl -fO "${HOST}/${BUNDLE}"
    curl -fO "${HOST}/${BUNDLE}.sha256"
    curl -fO "${HOST}/${MANIFEST}"
    sha256sum -c "$(basename "${BUNDLE}").sha256"   # macOS: shasum -a 256 -c
    ```

    ```python
    import json
    import urllib.request

    BASE = "https://data.clinvar-gkm.org"

    # The newest delta, from the line's release index
    index = json.load(urllib.request.urlopen(f"{BASE}/v1/1.2/index.json"))
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
  "release": "2026-11-15",
  "baseline_release": "2026-11-08",
  "compare_release": "2026-11-15",
  "pipeline_version": "1.2.0",
  "checkpoint_full": {
    "path": "v1/1.2/clinvar-gkm_2026-11.json.gz",
    "release": "2026-10-31",
    "month": "2026-11",
    "sha256": "5d41402abc4b2a76…"
  },
  "sections": {
    "allele":  { "added": 812,  "updated": 34,  "deleted": ["ga4gh:VA.oldDigest1"] },
    "scv":     { "added": 1203, "updated": 517, "deleted": ["clinvar.submission:SCV000000001.1"] },
    "vcv":     { "added": 44,   "updated": 96,  "deleted": [] }
  },
  "counts": { "A": 2063, "U": 647, "D": 2 },
  "schema_version": "1.2.0",
  "bundle": {
    "name": "clinvar-gkm-delta_2026-1115.json.gz",
    "path": "v1/1.2/deltas/clinvar-gkm-delta_2026-1115.json.gz",
    "size": 104857600,
    "sha256": "9e107d9d372bb682…"
  },
  "sha256": "9e107d9d372bb682…"
}
```

| Field | Description |
| --- | --- |
| `release` | The ClinVar release date this delta represents |
| `baseline_release` | The prior release this delta was diffed against — `null` only on the very first release |
| `compare_release` | The release the changes are computed to (equals `release`) |
| `pipeline_version` | The pipeline build stamp that produced the delta (`git describe` of the pipeline code) |
| `checkpoint_full` | The official monthly this delta's chain replays onto — the newest monthly whose `source_release` is on or before this delta's `baseline_release` — as `{path, release, month, sha256}`. `release` is that monthly's **`source_release`** (a `YYYY-MM-DD` release date, comparable with `baseline_release`), `month` is its `YYYY-MM` label, and `sha256` is its checksum. `path` is where the monthly was when the delta was published; after a year rollover, find it in `index.json` by `month`. Every line starts with a monthly, so a delta always has one (the first delta of a line is refused unless its `baseline_release` is that monthly's `source_release`) |
| `sections` | Per-section change summary — `added` and `updated` counts plus a `deleted` list of primary keys |
| `counts` | Roll-up totals across all sections — `A` (added), `U` (updated), `D` (deleted) |
| `schema_version` | The delta bundle's own `schema_version` |
| `bundle` | The delta bundle as published: `{name, path, size, sha256}`. `path` is its folder at publish time; after a month rollover, find its current path in `index.json` |
| `sha256` | The delta bundle's sha256 (the same value as `bundle.sha256` and the `.sha256` sidecar) |

**Deletes live only in the manifest.** For each section, `deleted` is the list of keys that must be removed; the delta bundle itself carries only the added and updated records.

### Consumer Replay Model

A monthly full plus the deltas after it rebuild the state at any weekly release. Every official monthly has a **`source_release`** in `index.json`: the weekly release it was built from (in the frozen `v1/1.1/` line, the `2026-10` monthly has `source_release` `2026-09-28`). Each delta records the release it was diffed against (`baseline_release`) and the release it brings you to (`release`).

For each delta, apply the manifest's deletes first, then upsert every record present in the delta bundle, section by section.

### Rebuild a past week { #rebuild-a-past-week }

Weekly full bundles are kept only for the current month ([Weekly Full Bundles](weekly-full.md)). To rebuild the state at any weekly release W — a past week, or the newest one:

1. Take the **newest official monthly whose `source_release` ≤ W**.
2. Apply, in release order, **every delta whose `release` is later than that `source_release` and ≤ W**.
3. **Check the chain** as you go: the first delta's `baseline_release` equals the monthly's `source_release`, and each later delta's `baseline_release` equals the previous delta's `release`. A mismatch means a release is missing; stop rather than apply a partial chain.

The deltas to apply are chosen by **release date, not by month**. In `v1/1.1/`, the `2026-10` monthly is built from `2026-09-28`, so rebuilding `2026-10-11` takes the `2026-10` monthly and applies the `2026-10-04` and `2026-10-11` deltas, both from the monthly's own month. (An earlier version of this page skipped deltas from the monthly's month; that missed them.)

A delta's `checkpoint_full` names the newest monthly whose `source_release` is on or before the delta's `baseline_release`, so it is the right base for that delta and every delta after it up to the next monthly. Its `release` is the monthly's `source_release`, the release the first delta of the chain must have as its `baseline_release`.

!!! note "A line starts at its first monthly"
    Each version line holds only its own releases. `v1/1.2/` starts with one **checkpoint monthly**, the first 1.2.0 full, and its deltas run forward from it: the first delta's `baseline_release` is that monthly's `source_release`. A week before the checkpoint is rebuilt from the frozen line that held it, `v1/1.1/` (its `index.json`), with 1.1.0 records. The recipe below works on any line: set `LINE`.

!!! note "Delta manifests in the frozen `v1/1.0/` line"
    The 1.0.1 delta manifests in `v1/1.0/` are kept byte-identical, so their paths still name the pre-1.1.0 `v1/datasets/` and `v1/deltas/` keys and every `checkpoint_full` says `2026-10`. For that line, pick the monthly from `v1/1.0/index.json` (each monthly's `source_release`) as above, not from `checkpoint_full`.

??? example "Python: rebuild the full bundle at a weekly release"
    ```python
    import gzip
    import json
    import urllib.request

    BASE = "https://data.clinvar-gkm.org"
    W = None       # the weekly release to rebuild, YYYY-MM-DD; None = the line's newest
    LINE = None    # None = the current line; or a frozen one, e.g. "v1/1.1"


    def fetch_json(url):
        with urllib.request.urlopen(url) as r:
            return json.load(r)


    def fetch_json_gz(url):
        with urllib.request.urlopen(url) as r:
            return json.loads(gzip.decompress(r.read()))


    # 0. The line's release index, via the root version manifest.
    root = fetch_json(f"{BASE}/index.json")
    line = next(v for v in root["versions"].values()
                if v["line"] == LINE or (LINE is None and v["status"] == "current"))
    index = fetch_json(f"{BASE}/{line['index'].lstrip('/')}")
    W = W or index["latest_release"]

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

    The recipe shows the logic. It holds the whole bundle in memory (about 92 million records, far more than a 16 GB machine has) and writes no file, so use the script below to rebuild a week for real.

To write a week's full bundle to disk without holding it in memory, use [`replay-bundle.py`](../assets/scripts/replay-bundle.py). It follows the rules above (the monthly, the deltas by release date, the chain check), checks each download's sha256 against `index.json`, keeps only the deltas' records in memory, streams the monthly once, and writes the bundle in the published layout with a `.sha256` sidecar. It needs only `python3` (3.9 or later, standard library):

```bash
curl -fsSO --retry 5 https://dataexchange.clinicalgenome.org/clinvar-gkm/1.2/assets/scripts/replay-bundle.py
python3 replay-bundle.py --release 2026-11-15 --plan
python3 replay-bundle.py --release 2026-11-15
```

The first lists the monthly and deltas it would use; the second downloads them, replays the deltas and writes `clinvar-gkm_2026-1115.replayed.json.gz`.

For a week of the frozen 1.1 line, add `--line v1/1.1`. The [Parquet for one weekly release](../parquet/build-your-own.md#parquet-for-one-weekly-release) section measures it and builds tables from the result.
