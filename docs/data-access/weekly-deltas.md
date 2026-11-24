# Weekly Deltas

Links: [Monthly Full Bundles](monthly-full.md) · [Weekly Full Bundles](weekly-full.md) · [Parquet Files](parquet.md) · [How Releases Work](release-model.md)

Older release lines (1.1.x, 1.0.1) are on [Previous Releases](previous-releases.md).

<div class="r2-browser" data-r2-type="deltas"></div>

The list groups deltas by year, newest first: the current year is open, and each earlier year is a collapsible list under **Archived years**.

A weekly delta is published for every ClinVar release. Each delta is a bundle, its `.sha256` checksum and its manifest. The current month's deltas sit directly in `v1/1.2/deltas/`; earlier months of the year are in `deltas/YYYY-MM/`, and prior years in `archive/YYYY/deltas/YYYY-MM/`:

```text
v1/1.2/deltas/
  clinvar-gkm-delta_2026-1108.json.gz             added + updated records (same section structure as the full bundle)
  clinvar-gkm-delta_2026-1108.json.gz.sha256
  clinvar-gkm-delta_2026-1108.manifest.json       per-section adds, updates, and deletes for this release
  clinvar-gkm-delta_2026-1115.json.gz
  clinvar-gkm-delta_2026-1115.json.gz.sha256
  clinvar-gkm-delta_2026-1115.manifest.json
```

That is the 1.2 line in November 2026. When December's first release is published, November's deltas move to `v1/1.2/deltas/2026-11/`. The frozen 1.1 line shows the finished-month layout, for example `v1/1.1/deltas/2026-09/clinvar-gkm-delta_2026-0928.json.gz`.

A delta's folder changes when its month or year rolls over; its file name and bytes do not. The line's `index.json` lists every delta with its current `bundle.path` and `manifest` path, so look paths up there rather than composing them. Deltas carry no Parquet: Parquet is derived and published only for the latest release ([Parquet Files](parquet.md)).

!!! note "Prerequisites"
    - **curl** and **`sha256sum`** (Linux, recent macOS) or **`shasum -a 256`** (any macOS), for the shell example.
    - **Python 3**, standard library only (tested with 3.14), for the Python examples.
    - A delta is a few MB to about 60 MB. [Rebuilding a past week](#rebuild-a-past-week) also downloads a monthly full (4.9 GB compressed, 68.5 GB decompressed), which `replay-bundle.py` streams.

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
    "sha256": "157ef338d1948cce…"
  },
  "sections": {
    "allele": { "added": 230,  "updated": 0,     "deleted": ["ga4gh:VA.zZ9dcuDMYuDkSzBwy7rLMI0R1zvZalla", "…"] },
    "scv":    { "added": 1023, "updated": 16539, "deleted": ["clinvar.submission:SCV007600890.1", "…"] },
    "vcv":    { "added": 2937, "updated": 4,     "deleted": ["VCV000183114.34-G-PATH", "…"] },
    "…": {}
  },
  "counts": { "A": 16335, "U": 22738, "D": 8296 },
  "schema_version": "1.2.0",
  "bundle": {
    "name": "clinvar-gkm-delta_2026-1115.json.gz",
    "path": "v1/1.2/deltas/clinvar-gkm-delta_2026-1115.json.gz",
    "size": 5355360,
    "sha256": "b370d3857ffd709b…"
  },
  "sha256": "b370d3857ffd709b…"
}
```

That is the 2026-11-15 manifest, cut to three of its 14 sections and the first key of each `deleted` list.

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

**A new ClinVar version is a new key.** SCV, VCV and RCV keys carry the ClinVar accession's version (`clinvar.submission:SCV000024262.157`, `VCV000183114.34-G-PATH`). When ClinVar bumps the version, the record's key changes, so the delta shows a **delete of the old key and an add of the new one**, not an update. In the 2026-11-15 delta, `clinvar.submission:SCV000024262.157` is in the `scv` deleted list and `clinvar.submission:SCV000024262.158` is a record of the bundle; 108 of the 128 deleted SCV keys, 2,394 of the 2,416 VCV keys and 1,224 of the 1,254 RCV keys come back under the same accession with a new version. A change that keeps the version is an update under the same key. To follow one accession across releases, match on the accession without its version, not on the key.

**Don't check a replay by the manifest's counts.** A section's `added` + `updated` can be larger than the number of records in the delta bundle. In the 2026-11-15 delta, `conditionSet` has `added` 149 and the bundle holds 138 records: condition sets with a single member are left out when the bundle is written. Every other section of that delta matches. Check a replay by comparing records, or against a published weekly full, not by counts.

### Consumer Replay Model

A monthly full plus the deltas after it rebuild the state at any weekly release. Every official monthly has a **`source_release`** in `index.json`: the weekly release it was built from (in the frozen `v1/1.1/` line, the `2026-10` monthly has `source_release` `2026-09-28`). Each delta records the release it was diffed against (`baseline_release`) and the release it brings you to (`release`).

For each delta, apply the manifest's deletes first, then upsert every record present in the delta bundle, section by section. To keep a local copy (a database of the records, or the Parquet tables) at the newest release this way, week after week, see [Keep Your Data Current](keep-current.md).

!!! warning "When the line changes, start again from the new line's monthly"
    Deltas apply only to a copy of the **same line**. A line's first delta builds on the end of the line before it: the 1.2 line's first delta (2026-11-08) has `baseline_release` 2026-10-31, the last release of the frozen 1.1 line, and both lines have a `2026-11` monthly with `source_release` 2026-10-31. So a copy built from 1.1 bundles passes a chain check on dates alone, and applying 1.2 deltas to it mixes 1.1.0 and 1.2.0 records.

    Before applying a delta, check that its manifest's `schema_version` equals your copy's `schema_version` (the bundle's root property; in the frozen 1.0 line the manifests have none). When it differs, or the root [`index.json`](https://data.clinvar-gkm.org/index.json) names a new `current` line, stop: download the new line's checkpoint monthly (the delta's `checkpoint_full`) and replay that line's deltas from it.

### Rebuild a past week { #rebuild-a-past-week }

Weekly full bundles are kept only for the current month ([Weekly Full Bundles](weekly-full.md)). To rebuild the state at any weekly release W — a past week, or the newest one:

1. Take the **newest official monthly whose `source_release` ≤ W**.
2. Apply, in release order, **every delta whose `release` is later than that `source_release` and ≤ W**.
3. **Check the chain** as you go: the first delta's `baseline_release` equals the monthly's `source_release`, and each later delta's `baseline_release` equals the previous delta's `release`. A mismatch means a release is missing; stop rather than apply a partial chain.
4. **Check the line**: each delta's `schema_version` equals the monthly's. Take the monthly and the deltas from the same line's `index.json`; a date match alone doesn't prove it (see above).

The deltas to apply are chosen by **release date, not by month**. In `v1/1.1/`, the `2026-10` monthly is built from `2026-09-28`, so rebuilding `2026-10-11` takes the `2026-10` monthly and applies the `2026-10-04` and `2026-10-11` deltas, both from the monthly's own month. (An earlier version of this page skipped deltas from the monthly's month; that missed them.)

A delta's `checkpoint_full` names the newest monthly whose `source_release` is on or before the delta's `baseline_release`, so it is the right base for that delta and every delta after it up to the next monthly. Its `release` is the monthly's `source_release`, the release the first delta of the chain must have as its `baseline_release`.

!!! note "A line starts at its first monthly"
    Each version line holds only its own releases. `v1/1.2/` starts with one **checkpoint monthly**, the first 1.2.0 full, and its deltas run forward from it: the first delta's `baseline_release` is that monthly's `source_release`. A week before the checkpoint is rebuilt from the frozen line that held it, `v1/1.1/` (its `index.json`), with 1.1.0 records. `replay-bundle.py` below works on any line: pass `--line`.

!!! note "Delta manifests in the frozen `v1/1.0/` line"
    The 1.0.1 delta manifests in `v1/1.0/` are kept byte-identical, so their paths still name the pre-1.1.0 `v1/datasets/` and `v1/deltas/` keys and every `checkpoint_full` says `2026-10`. For that line, pick the monthly from `v1/1.0/index.json` (each monthly's `source_release`) as above, not from `checkpoint_full`.

To write a week's full bundle to disk, use [`replay-bundle.py`](../assets/scripts/replay-bundle.py). It follows the rules above (the monthly, the deltas by release date, the chain check), checks each download's sha256 against `index.json`, keeps only the deltas' records in memory, streams the monthly once, and writes the bundle in the published layout with a `.sha256` sidecar. It needs only `python3` (3.9 or later, standard library):

```bash
curl -fsSO --retry 5 https://dataexchange.clinicalgenome.org/clinvar-gkm/1.2/assets/scripts/replay-bundle.py
python3 replay-bundle.py --release 2026-11-15 --plan
python3 replay-bundle.py --release 2026-11-15
```

The first lists the monthly and deltas it would use; the second downloads them, replays the deltas and writes `clinvar-gkm_2026-1115.replayed.json.gz`.

For a week of the frozen 1.1 line, add `--line v1/1.1`. The [Parquet for one weekly release](../parquet/build-your-own.md#parquet-for-one-weekly-release) section measures it and builds tables from the result.
