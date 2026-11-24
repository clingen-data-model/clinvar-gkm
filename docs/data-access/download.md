# Downloads

ClinVar-GKM is distributed as monthly and weekly full bundles plus weekly deltas (JSON), with one typed Parquet dataset of the latest release built from the bundle, free from Cloudflare R2 — no authentication, no egress fees. The layout follows NCBI's ClinVar FTP site. New here? See [How Releases Work](release-model.md). Releases of older lines (1.1.x, 1.0.1) are under [Previous Releases](#previous-releases) below.

!!! warning "1.2.0 starts a new version line, `v1/1.2/`"
    1.2.0 publishes into a new line folder, `v1/1.2/`, which starts with one checkpoint monthly and adds deltas from there. The 1.1.x releases stay, unchanged, in the frozen line `v1/1.1/` (monthlies, deltas and archive; its weekly fulls and Parquet set are removed at the freeze). Change `v1/1.1/` to `v1/1.2/` in your scripts, or read the current line from the root `index.json`. See [Version Lines](release-model.md#version-lines) and the [changelog](../reference/changelog.md).

!!! info "Before you use or share the data"
    These files carry ClinVar data from NCBI. ClinVar's disclaimer applies: the data is not for direct diagnostic use or medical decision-making without review by a genetics professional. Attribute ClinVar as the data source, cite ClinVar-GKM, and carry the attribution and disclaimer with any copy you redistribute. The CC0 dedication covers ClinGen's transformation only. See [Data Use and Citation](../data-use.md).

---

## Latest Release

!!! tip "Monthly full or weekly full?"
    The official monthly reflects the last release of the previous month; the newest weekly full is the current week. [Choose Your Data](../start/choose-your-data.md) compares every option, and [How Releases Work](release-model.md) gives the schedule.

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

Each release line has its own folder, `v{major}/{major}.{minor}/`; the current line is `v1/1.2/`, and the root `index.json` lists every line. The full directory tree, and the stable `00-latest` names, are on [How Releases Work](release-model.md#directory-structure).

Dated files move to another folder, or are deleted, when a month or year ends; [Month and Year Rollover](release-model.md#month-and-year-rollover) says which and when. Look up a dated file's current path in the line's `index.json` rather than writing it into a script.
{ #when-files-move }

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
