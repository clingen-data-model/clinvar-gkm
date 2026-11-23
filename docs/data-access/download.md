# Downloads

ClinVar-GKM is distributed as monthly and weekly full bundles plus weekly deltas (JSON), with one typed Parquet dataset of the latest release built from the bundle, free from Cloudflare R2 — no authentication, no egress fees. The layout follows NCBI's ClinVar FTP site. New here? See [How Releases Work](release-model.md). Releases of older lines (1.1.x, 1.0.1) are under [Previous Releases](#previous-releases) below.

!!! warning "1.2.0 starts a new version line, `v1/1.2/`"
    1.2.0 publishes into a new line folder, `v1/1.2/`, which starts with one checkpoint monthly and adds deltas from there. The 1.1.x releases stay, unchanged, in the frozen line `v1/1.1/` (monthlies, deltas and archive; its weekly fulls and Parquet set are removed at the freeze). Change `v1/1.1/` to `v1/1.2/` in your scripts, or read the current line from the root `index.json`. See [Version Lines](release-model.md#version-lines) and the [changelog](../reference/changelog.md).

!!! info "Before you use or share the data"
    These files carry ClinVar data from NCBI. ClinVar's disclaimer applies: the data is not for direct diagnostic use or medical decision-making without review by a genetics professional. Attribute ClinVar as the data source, cite ClinVar-GKM, and carry the attribution and disclaimer with any copy you redistribute. The CC0 dedication covers ClinGen's transformation only. See [Data Use and Citation](../data-use.md).

---

## Latest Release

!!! tip "Monthly full or weekly full?"
    `clinvar-gkm_00-latest.json.gz` is the newest **official monthly**: it reflects the **last release of the _previous_ month** — e.g. the `2026-11` monthly is built from the `2026-10-31` release, the last one before ClinVar's November monthly cut. For the **current week**, download `weekly/clinvar-gkm_00-latest_weekly.json.gz`, a full bundle of the newest release. See [Weekly Full Bundles](weekly-full.md).

<div class="r2-browser" data-r2-type="latest"></div>

<noscript>
The interactive release table needs JavaScript. Without it, fetch the release index directly:
<code>curl -fsS https://data.clinvar-gkm.org/v1/1.2/index.json | python3 -m json.tool</code>
— or grab the newest monthly and weekly fulls:
<code>curl -fO https://data.clinvar-gkm.org/v1/1.2/clinvar-gkm_00-latest.json.gz</code>
<code>curl -fO https://data.clinvar-gkm.org/v1/1.2/weekly/clinvar-gkm_00-latest_weekly.json.gz</code>
</noscript>

Browse history and archives: [Monthly Full Bundles](monthly-full.md) · [Weekly Full Bundles](weekly-full.md) · [Weekly Deltas](weekly-deltas.md) · [Parquet Files](parquet.md). Earlier release lines: [Previous Releases](previous-releases.md).

---

## Previous Releases

These docs describe the current line, `v1/1.2/`. The release lines frozen **before** it are listed here; each keeps its official monthlies and weekly deltas, unchanged, at the paths they had. Their files are listed on [Previous Releases](previous-releases.md).

<div class="r2-browser" data-r2-type="previous-summary"></div>

<noscript>
The list of earlier lines needs JavaScript. Without it, read the root version manifest, which lists every line, its status and the path of its own index:
<code>curl -fsS https://data.clinvar-gkm.org/index.json | python3 -m json.tool</code>
</noscript>

---

## Directory Structure

!!! note "Versioned layout"
    The root `index.json` is a thin **version manifest** that lists the release lines and points to each line's index. Each line has its own folder, `v{major}/{major}.{minor}/`. The current line is **`1.2`**, served under **`v1/1.2/`**, with its release index at `v1/1.2/index.json`. PATCH releases (1.2.x) add to the same folder; a new MINOR starts `v1/1.3/` and a new MAJOR starts `v2/2.0/`. A replaced line is frozen and kept indefinitely: its monthlies and deltas stay, unchanged. The 1.1.x releases are the frozen line `v1/1.1/`, and the 1.0.1 generation is the frozen line `v1/1.0/`; [Previous Releases](previous-releases.md) lists every frozen line and its files.

```text
index.json                                    version manifest (each line -> its index)
v1/
  1.2/                                        current line
    index.json                                release index for the line
    feed.xml                                  Atom feed of the line's releases
    README.txt                                plain-text guide to the line
    clinvar-gkm_00-latest.json.gz             newest official monthly full (stable URL)
    clinvar-gkm_YYYY-MM.json.gz               official monthly fulls, current year
    weekly/
      clinvar-gkm_00-latest_weekly.json.gz    newest weekly full (stable URL)
      clinvar-gkm_YYYY-MMDD.json.gz           weekly fulls, CURRENT MONTH ONLY
    deltas/
      clinvar-gkm-delta_YYYY-MMDD.json.gz     current month's weekly deltas
      clinvar-gkm-delta_YYYY-MMDD.manifest.json
      YYYY-MM/                                earlier months of the current year
    archive/
      YYYY/
        clinvar-gkm_YYYY-MM.json.gz           monthly fulls from prior years
        deltas/YYYY-MM/                       deltas from prior years
    parquet/
      {section}.parquet                       ONE Parquet dataset, the latest (built from the bundle; overwritten every release)
      manifest.json                           build date, source release, builder, per-file sha256
      table-spec.json                         every table's columns, types and derivations
  1.1/                                        frozen line: the 1.1.x releases (monthlies, deltas, MANIFEST.json; no weekly fulls, no Parquet)
  1.0/                                        frozen line: the 1.0.1 generation (bundles, delta manifests, MANIFEST.json; no Parquet)
```

Every bundle has a `<file>.sha256` sidecar (`sha256sum -c` format), like NCBI's `.md5` files. The `00-` prefix
of the stable names sorts them before the dated files in a directory listing, as in NCBI's
`ClinVarVCVRelease_00-latest.xml.gz`.

### When files move

- **New month.** When the first release of a new month is published, the finished month's deltas move from `deltas/` into `deltas/YYYY-MM/`, and the finished month's **weekly fulls are deleted**. The newest of them is kept until the new month's official monthly is published, because that monthly is normally a copy of it, and is deleted as soon as the monthly is up. A past week is rebuilt from a monthly plus deltas; see [Rebuild a past week](weekly-deltas.md#rebuild-a-past-week).
- **New year.** When the first release of a new year is published, the finished year's monthlies move into `archive/YYYY/` and its delta folders into `archive/YYYY/deltas/YYYY-MM/`.
- A move never changes a file's bytes, name or checksum, only its folder. Scripts that need a dated file should look up its current path in the line's `index.json`.

### How the layout mirrors NCBI

The bundles are built from ClinVar's XML releases, so the layout follows [NCBI's ClinVar XML folder](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/):

| NCBI ClinVar XML | ClinVar-GKM `v1/1.2/` |
| --- | --- |
| `xml/` — monthly releases and `ClinVarVCVRelease_00-latest.xml.gz` | top level — official monthlies and `clinvar-gkm_00-latest.json.gz` |
| `xml/weekly_release/` — the current month's weekly releases and `00-latest_weekly` | `weekly/` — the current month's weekly fulls and `clinvar-gkm_00-latest_weekly.json.gz` |
| `xml/archive/YYYY/` — monthly releases of prior years | `archive/YYYY/` — monthlies of prior years |
| `.md5` sidecars | `.sha256` sidecars |
| — | `deltas/` — weekly deltas (ClinVar-GKM only) |
| — | `parquet/` — one derived Parquet dataset (ClinVar-GKM only) |

Each ClinVar-GKM monthly `clinvar-gkm_YYYY-MM` lines up with ClinVar's `ClinVarVCVRelease_YYYY-MM`, and each weekly full or delta with the ClinVar weekly release of the same date.

### Troubleshooting

- **HTTP 403.** The CDN serves only the root `index.json` and paths under `/v1/`; a path allowlist answers every other path with 403, not 404. A 403 usually means a URL from before the current layout, such as a bucket-root `datasets/…` path. Look up the file's current path in the line's `index.json`.
- **HTTP 404 under `/v1/`.** The file is not there: a weekly full deleted at month end, a delta moved to `deltas/YYYY-MM/`, or a monthly moved to `archive/YYYY/`. See [When files move](#when-files-move).
- **HTTP 429.** Requests are rate-limited. Download whole files and query them locally rather than issuing many small range requests.

---

## File Format

Each file is a gzip-compressed JSON object: `schema_version` first, then the bundle sections in a fixed order,
each a keyed collection of records of one class (see [Output Format](../output-reference/overview.md)). Each
record is written on its own line as compact JSON (raw UTF-8) with its object keys **sorted at every depth**, and
the lists whose order carries no meaning and is not stable in ClinVar's source (a condition's `aliases`) are
written sorted, so a record that has not changed has the same bytes in every release. The order of records
within a section is not fixed and differs between releases.

### Count records in a full bundle { #count-records-in-a-full-bundle }

A full bundle is about 4.9 GB compressed and 68.5 GB decompressed, too large to load whole, but each record is
on its own line, so a script can stream it. This counts the records of each section of the newest monthly,
`clinvar-gkm_00-latest.json.gz` (from [Monthly Full Bundles](monthly-full.md)), in about a minute and 20 MB of
memory on a laptop. It needs only Python 3 and `gunzip`, which macOS and Linux include:

```bash
gunzip -c clinvar-gkm_00-latest.json.gz | python3 -c "
import sys
counts = {}
for line in sys.stdin:
    if line.startswith('  \"') and line.rstrip().endswith('{'):  # a section opens
        section = line.split('\"')[1]
        counts[section] = 0
    elif line.startswith('    \"'):                            # one record
        counts[section] += 1
for section, n in counts.items():
    print(f'{section}: {n:,}')
"
```

---

## Feedback

This project is in active development and we welcome community feedback. If you encounter data quality issues, have questions about the output format, or want to suggest improvements:

- Open an issue on [GitHub](https://github.com/clingen-data-model/clinvar-gkm/issues)
- Include the release date and specific records involved
