# Set Up Your Tools

The examples on this site use a small set of free tools. This page lists them, how to install them on macOS and Linux, and the versions the examples were tested with. Pages with examples link here for their prerequisites and add anything specific to them.

Nothing here needs an account or credentials: the data is public at `https://data.clinvar-gkm.org`, with no sign-in.

!!! info "Tested with"
    macOS 15 (zsh) on **2026-11-23**: curl 8.7.1, DuckDB CLI 1.5.4, Python 3.14.5, `duckdb` 1.5.4 for Python, jq 1.7.1, uv 0.6.14, `gkm-bundle-parquet` 2.0.0, and the GA4GH library versions below. Other recent versions usually work; when one doesn't, install the tested version.

---

## What you need, by task

| To… | You need |
| --- | --- |
| Run SQL in the browser console | Nothing: a web browser |
| Download files and check them | `curl`, and `sha256sum` or `shasum` |
| Query Parquet on your machine | The DuckDB CLI, or Python with `duckdb` |
| Read a JSON bundle | Python 3 (standard library), `gunzip`; `jq` for the shell examples |
| Load records into the GA4GH data models | Python 3.11 or later, with the GA4GH libraries |
| Build your own tables or mini-bundles | `uv` (for `uvx gkm-bundle-parquet`) |

---

## Command-line tools

| Tool | What for | macOS | Linux (Debian, Ubuntu) | Tested |
| --- | --- | --- | --- | --- |
| `curl` | Downloads | Included | `sudo apt install curl` | 8.7.1 |
| `gunzip` | Reading `.gz` bundles | Included | Included | — |
| `sha256sum` or `shasum` | Checking a download against its `.sha256` file | `shasum` included; `sha256sum` on recent macOS | `sha256sum` included | — |
| `jq` | Reading JSON in the shell | `brew install jq` | `sudo apt install jq` | 1.7.1 |
| DuckDB CLI | SQL on Parquet | `brew install duckdb` | [DuckDB installation](https://duckdb.org/docs/installation/) | 1.5.4 |
| `uv` (gives `uvx`) | Running `gkm-bundle-parquet` | `brew install uv` | [uv installation](https://docs.astral.sh/uv/getting-started/installation/) | 0.6.14 |
| Python 3 | Python examples | `brew install python`, or [python.org](https://www.python.org/downloads/) | `sudo apt install python3 python3-venv` | 3.14.5 |

`brew` is [Homebrew](https://brew.sh/). On macOS, `python3` without Homebrew first asks to install Apple's command-line developer tools, which include it.

### Check a download

Every bundle, full or delta, has a `.sha256` file beside it. This downloads the newest weekly delta of the line (a few MB; its path is looked up in `index.json`, because a delta moves when its month ends) and its checksum file, then checks it with whichever command your system has:

```bash
DELTA=$(curl -fsS https://data.clinvar-gkm.org/v1/1.2/index.json | jq -r '.deltas | max_by(.release) | .bundle.path')
curl -fO "https://data.clinvar-gkm.org/${DELTA}"
curl -fO "https://data.clinvar-gkm.org/${DELTA}.sha256"

sha256sum -c "$(basename "${DELTA}").sha256"        # Linux, recent macOS
shasum -a 256 -c "$(basename "${DELTA}").sha256"    # any macOS
```

Each check prints the file name followed by `OK` when the file is intact. A full bundle is checked the same way, with its URL in place of the delta's.

### DuckDB and remote files

DuckDB reads `https://…` URLs through its `httpfs` extension, which it downloads and loads the first time a query reads a URL. That needs access to DuckDB's extension repository. Where it is blocked, see [installing extensions](https://duckdb.org/docs/stable/extensions/installing_extensions), or download the file and query it locally.

The server in front of `data.clinvar-gkm.org` allows about **55 requests per 10 seconds** per client and answers more with `HTTP 429`. A query that filters a table on `id` makes a few requests; a scan of a large table makes hundreds. Explore remotely, and download the tables you query repeatedly.

---

## Python and the GA4GH libraries

Use a virtual environment, so these versions don't change the Python your system uses:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -q "duckdb==1.5.4"
pip install -q "ga4gh.vrs==2.4.0a6" "ga4gh.cat_vrs==0.8.0a6" "ga4gh.va_spec==0.5.0a7" "ga4gh.gkm==0.4.1"
```

The first `pip install` is all the SQL examples need. The second installs the GA4GH reference libraries (vrs-python, cat-vrs-python, va-spec-python) and the GKM Toolkit, at the versions that read ClinVar-GKM 1.2.0 records: they are **pre-releases**, because the latest stable releases implement older schema versions and reject most records. They need **Python 3.11 or later**. [Working in Python](../working-in-python.md) explains the versions and uses the libraries.

Check the install:

```bash
python -c '
from importlib.metadata import version
for package in ("duckdb", "ga4gh.vrs", "ga4gh.cat_vrs", "ga4gh.va_spec", "ga4gh.gkm"):
    print(f"{package:14} {version(package)}")
'
```

```text
duckdb         1.5.4
ga4gh.vrs      2.4.0a6
ga4gh.cat_vrs  0.8.0a6
ga4gh.va_spec  0.5.0a7
ga4gh.gkm      0.4.1
```

---

## gkm-bundle-parquet

`gkm-bundle-parquet` builds Parquet tables and mini-bundles from a bundle; it is the tool that builds the published tables. `uvx` runs a pinned release with nothing else to install:

```bash
uvx gkm-bundle-parquet@2.0.0 version
```

```text
gkm-bundle-parquet 2.0.0: table spec sections 2.0, policy 2.0; duckdb 1.5.4
…
```

Without uv, `pip install gkm-bundle-parquet==2.0.0` in a virtual environment gives a `gkm-bundle-parquet` command. See [Build Your Own Tables and Mini-Bundles](../parquet/build-your-own.md#install).

---

## Check everything at once

```bash
for tool in curl jq duckdb python3 uv; do
  printf '%-8s ' "$tool"; command -v "$tool" >/dev/null && "$tool" --version 2>&1 | head -1 || echo "not found"
done
command -v sha256sum >/dev/null && echo "sha256sum found" || echo "use: shasum -a 256"
```

---

## Disk, memory and time

| Data | Download | On disk | Memory |
| --- | --- | --- | --- |
| A query in the browser console | A few MB per query | None | The browser's |
| One small Parquet table (`condition`, `gene`, `submitter`, …) | Under 6 MB each | Same | Little |
| All 20 Parquet tables | 4.6 GB | 4.6 GB | Depends on the query; see [Working at Scale](../parquet/performance.md) |
| A weekly delta | Usually 2 to 30 MB | Same, compressed | Small enough to load whole with `json.load` |
| A full bundle | 4.9 GB, a few minutes on a fast connection | 4.9 GB compressed; **68.5 GB** if decompressed | Too large to load whole: stream it |

**A full bundle must be streamed.** Each record is on its own line, so a script can read it with `gunzip -c bundle.json.gz | …` one line at a time, in a few MB of memory; [Count records in a full bundle](../data-access/download.md#count-records-in-a-full-bundle) shows how, in about a minute. Loading one with `json.load` needs far more memory than a laptop has. Building the full set of Parquet tables yourself needs about 65 GB of memory and 65 GB of working disk; [Build Your Own Tables and Mini-Bundles](../parquet/build-your-own.md) has the figures.
