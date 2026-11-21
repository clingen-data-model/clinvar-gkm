# Previous Releases

Links: [Downloads](download.md) · [Monthly Full Bundles](monthly-full.md) · [Weekly Deltas](weekly-deltas.md) · [How Releases Work](release-model.md)

Each release line has its own folder, `v{major}/{major}.{minor}/`. When a new MINOR or MAJOR release starts a new line, the line it replaces is **frozen**: nothing in it changes again, and it is kept indefinitely. These docs describe the 1.1 line, `v1/1.1/`. This page lists the frozen lines released **before** 1.1, newest first, with their official monthly full bundles and their weekly deltas; today that is the 1.0.1 generation, `v1/1.0/`.

The 1.1 line was itself replaced by `v1/1.2/` in 1.2.0. For the current line, see the latest docs; their [Previous Releases](https://dataexchange.clinicalgenome.org/clinvar-gkm/data-access/previous-releases/) page lists `v1/1.1/` and every line frozen after it.

- **What a frozen line keeps:** its official monthlies, the `00-latest` copy of the newest one, its `archive/YYYY/` folders and every weekly delta with its manifest, all at the paths they had when the line was current, with the same bytes and `.sha256` sidecars. It gains a `MANIFEST.json` (every file's size and sha256) and a `README.txt`.
- **What a frozen line drops:** its weekly full bundles and its Parquet set, deleted at the freeze. Any past week is rebuilt from a monthly plus deltas ([Rebuild a past week](weekly-deltas.md#rebuild-a-past-week)).
- **Which schema it uses:** each line's bundles validate against that line's schema version, shown below. The [changelog](../reference/changelog.md) lists the changes between versions.

To keep reading one line, read releases only from its own `index.json`; see [Finding and pinning a version](../reference/versioning.md#finding-and-pinning-a-version).

!!! info "Before you use or share the data"
    The data use terms and the ClinVar disclaimer apply to every line; see [Data Use and Citation](../data-use.md).

---

## Frozen Lines Before 1.1

The list is read from the root `index.json`.

<div class="r2-browser" data-r2-type="previous"></div>

<noscript>
The list of frozen lines needs JavaScript. Without it, read the root version manifest, which lists every line, its
status and the path of its own index:
<code>curl -s https://data.clinvar-gkm.org/index.json | python3 -m json.tool</code>
— then the 1.0 line's index and plain-text guide:
<code>curl -s https://data.clinvar-gkm.org/v1/1.0/index.json | python3 -m json.tool</code>
<code>curl -s https://data.clinvar-gkm.org/v1/1.0/README.txt</code>
</noscript>
