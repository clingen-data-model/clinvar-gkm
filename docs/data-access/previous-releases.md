# Previous Releases

Links: [Downloads](download.md) · [Monthly Full Bundles](monthly-full.md) · [Weekly Deltas](weekly-deltas.md) · [How Releases Work](release-model.md)

Each release line has its own folder, `v{major}/{major}.{minor}/`. When a new MINOR or MAJOR release starts a new line, the line it replaces is **frozen**: nothing in it changes again, and it is kept indefinitely. This page lists the frozen lines released **before** the line these docs describe, newest first, with their official monthly full bundles and their weekly deltas: in the latest docs, every frozen line. The other Get the Data pages describe this docs version's own line.

- **What a frozen line keeps:** its official monthlies, the `00-latest` copy of the newest one, its `archive/YYYY/` folders and every weekly delta with its manifest, all at the paths they had when the line was current, with the same bytes and `.sha256` sidecars. It gains a `MANIFEST.json` (every file's size and sha256) and a `README.txt`.
- **What a frozen line drops:** its weekly full bundles and its Parquet set, deleted at the freeze. Any past week is rebuilt from a monthly plus deltas ([Rebuild a past week](weekly-deltas.md#rebuild-a-past-week)), and Parquet is rebuilt from a monthly bundle with [`gkm-bundle-parquet`](../parquet/build-your-own.md).
- **Parquet for a frozen line:** [Parquet for Previous Releases](../parquet/previous-releases.md) gives the commands and the column set.
- **Which schema it uses:** each line's bundles validate against that line's schema version, shown below. The [changelog](../reference/changelog.md) lists the changes between versions.

To keep reading one line, read releases only from its own `index.json`; see [Finding and pinning a version](../reference/versioning.md#finding-and-pinning-a-version). The docs that describe a line are in the version selector in the header: the `1.1` docs describe `v1/1.1/`, and their copy of this page lists the lines before 1.1.

!!! info "Before you use or share the data"
    The data use terms and the ClinVar disclaimer apply to every line; see [Data Use and Citation](../data-use.md).

---

## Frozen Lines

The list is read from the root `index.json`, so a line appears here as soon as it is frozen. It shows only lines older than the one these docs describe.

<div class="r2-browser" data-r2-type="previous"></div>

<noscript>
The list of frozen lines needs JavaScript. Without it, read the root version manifest, which lists every line, its
status and the path of its own index:
<code>curl -s https://data.clinvar-gkm.org/index.json | python3 -m json.tool</code>
— then a frozen line's index and plain-text guide, for example:
<code>curl -s https://data.clinvar-gkm.org/v1/1.1/index.json | python3 -m json.tool</code>
<code>curl -s https://data.clinvar-gkm.org/v1/1.0/README.txt</code>
</noscript>
