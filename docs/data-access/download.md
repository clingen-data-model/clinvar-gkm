# Downloads

ClinVar-GKM is distributed as monthly and weekly full bundles plus weekly deltas (JSON), with one typed Parquet dataset of the latest release, free from Cloudflare R2 — no authentication, no egress fees. The layout follows NCBI's ClinVar FTP site. New here? See [How Releases Work](release-model.md).

!!! warning "1.1.0 moved every download URL"
    1.1.0 (released <!-- YYYY-MM-DD at tag -->) moved every download URL to `v1/1.1/` and renamed the proposition sections — see the [changelog migration notes](../reference/changelog.md#110).

!!! info "Before you use or share the data"
    These files carry ClinVar data from NCBI. ClinVar's disclaimer applies: the data is not for direct diagnostic use or medical decision-making without review by a genetics professional. Attribute ClinVar as the data source, cite ClinVar-GKM, and carry the attribution and disclaimer with any copy you redistribute. The CC0 dedication covers ClinGen's transformation only. See [Data Use and Citation](../data-use.md).

---

## Latest Release

!!! tip "Monthly full or weekly full?"
    `clinvar-gkm_00-latest.json.gz` is the newest **official monthly**: it reflects the **last release of the _previous_ month** — e.g. the `2026-10` monthly is built from the `2026-09-28` release, the last one before ClinVar's October monthly cut. For the **current week**, download `weekly/clinvar-gkm_00-latest_weekly.json.gz`, a full bundle of the newest release. See [Weekly Full Bundles](weekly-full.md).

<div class="r2-browser" data-r2-type="latest"></div>

<noscript>
The interactive release table needs JavaScript. Without it, fetch the release index directly:
<code>curl -s https://data.clinvar-gkm.org/v1/1.1/index.json | python3 -m json.tool</code>
— or grab the newest monthly and weekly fulls:
<code>curl -O https://data.clinvar-gkm.org/v1/1.1/clinvar-gkm_00-latest.json.gz</code>
<code>curl -O https://data.clinvar-gkm.org/v1/1.1/weekly/clinvar-gkm_00-latest_weekly.json.gz</code>
</noscript>

Browse history and archives: [Monthly Full Bundles](monthly-full.md) · [Weekly Full Bundles](weekly-full.md) · [Weekly Deltas](weekly-deltas.md) · [Parquet Files](parquet.md).

---

## Directory Structure

!!! note "Versioned layout"
    The root `index.json` is a thin **version manifest** that lists the release lines and points to each line's index. Each line has its own folder, `v{major}/{major}.{minor}/`. The current line is **`1.1`**, served under **`v1/1.1/`**, with its release index at `v1/1.1/index.json`. PATCH releases (1.1.x) add to the same folder; a new MINOR starts `v1/1.2/` and a new MAJOR starts `v2/2.0/`. A replaced line is frozen and kept indefinitely: its files stay, unchanged. The 1.0.1 generation is the frozen line `v1/1.0/`.

```text
index.json                                    version manifest (each line -> its index)
v1/
  1.1/                                        current line
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
      {section}.parquet                       ONE Parquet dataset, the latest (derived; overwritten every release)
      manifest.json                           build date, source release, builder, per-file sha256
  1.0/                                        frozen line: the 1.0.1 generation (bundles, delta manifests, MANIFEST.json; no Parquet)
```

Every bundle has a `<file>.sha256` sidecar (`sha256sum -c` format), like NCBI's `.md5` files.

### When files move

- **New month.** When the first release of a new month is published, the finished month's deltas move from `deltas/` into `deltas/YYYY-MM/`, and the finished month's **weekly fulls are deleted**. The newest of them is kept until the new month's official monthly is published, because that monthly is normally a copy of it, and is deleted as soon as the monthly is up. A past week is rebuilt from a monthly plus deltas; see [Rebuild a past week](weekly-deltas.md#rebuild-a-past-week).
- **New year.** When the first release of a new year is published, the finished year's monthlies move into `archive/YYYY/` and its delta folders into `archive/YYYY/deltas/YYYY-MM/`.
- A move never changes a file's bytes, name or checksum, only its folder. Scripts that need a dated file should look up its current path in the line's `index.json`.

### How the layout mirrors NCBI

The bundles are built from ClinVar's XML releases, so the layout follows [NCBI's ClinVar XML folder](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/):

| NCBI ClinVar XML | ClinVar-GKM `v1/1.1/` |
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

## Feedback

This project is in active development and we welcome community feedback. If you encounter data quality issues, have questions about the output format, or want to suggest improvements:

- Open an issue on [GitHub](https://github.com/clingen-data-model/clinvar-gkm/issues)
- Include the release date and specific records involved
