# VRS-ification (`src/vrsify/`) — local fallback

A local VRS translation, kept as a manual fallback. **`src/scripts/run-release.sh` no longer runs it:** the release
uses the translation clinvar-ingest's Cloud Run job `clinvar-ingest-vrsify` writes for every release
(`vi-vrs-python.jsonl.gz`, vrs-python against a RefgetStore, no local services), and its stage 3 only checks that
output (`src/scripts/check-cloud-vrsify.sh`). See
[docs/pipeline/vrs-processing.md](../../docs/pipeline/vrs-processing.md).

This fallback resolves each variation's selected expression (SPDI / HGVS / gnomAD) into a GA4GH VRS object using
[vrs-python](https://github.com/ga4gh/vrs-python) + the
[variation-normalizer](https://github.com/cancervariants/variation-normalization),
against local SeqRepo / UTA / gene-normalizer services.

```
gs://clinvar-gkm/<date>/dev/vi.jsonl.gz
        │  vrsify.sh
        ▼
gs://clinvar-gkm/<date>/dev/vi-normalized-no-liftover.jsonl.gz
```

## What is vendored here

- **`vrsify.sh`** — the driver (adapted from clinvar-gk-python `misc/clinvar-vrsification`).
- **`requirements.txt`** — the resolver engine (`clinvar_gk_pilot`) pinned to an exact commit.
- **`log_conf.json`** — the resolver's logging config. `clinvar_gk_pilot` reads this from its
  `PROJECT_ROOT` at import, but it is not shipped as package data, so a pip install is missing
  it and errors at import. `vrsify.sh` copies this vendored copy next to the installed package
  if absent (a no-op for source-checkout runs).

The heavy engine is installed as a **pinned dependency**, not forked into this repo — so
the resolver stack (`ga4gh.vrs`, `variation-normalizer`, `gene-normalizer`, `cool-seq-tool`)
stays authoritative upstream while the pin makes the version explicit and reproducible.

## Prerequisites (one-time)

The resolver needs a Python environment and a running service topology. These are heavy
local dependencies (multi-GB sequence data, a Postgres UTA instance); they are **not**
provisioned by this repo.

1. **Python env** (Python ≥ 3.11):

   ```bash
   python3 -m venv .venv-vrsify && source .venv-vrsify/bin/activate
   pip install -r src/vrsify/requirements.txt
   ```

   To move an existing environment to a new pin, add `--force-reinstall --no-deps`:

   ```bash
   pip install --force-reinstall --no-deps -r src/vrsify/requirements.txt
   ```

   The resolver's version is always `0.0.0`, so a plain `pip install -r` reports "already
   satisfied" and keeps the installed commit. `--no-deps` leaves the other packages as they are.

2. **SeqRepo** — a local SeqRepo snapshot (the pin was validated against `2024-12-20`).

3. **variation-normalizer services** — UTA (Postgres) and gene-normalizer, typically via the
   upstream `variation-normalizer-compose.yaml`:

   ```bash
   podman compose -f variation-normalizer-compose.yaml up -d   # or: docker compose ...
   ```

   See the [clinvar-gk-python README](https://github.com/clingen-data-model/clinvar-gk-python)
   for first-time UTA volume initialization.

4. **Environment variables** (exported in the shell that runs `vrsify.sh`):

   ```bash
   export SEQREPO_ROOT_DIR=/usr/local/share/seqrepo/2024-12-20
   export SEQREPO_DATAPROXY_URL="seqrepo+file://${SEQREPO_ROOT_DIR}"
   export HGVS_SEQREPO_DIR="${SEQREPO_ROOT_DIR}"   # keeps hgvs off slow NCBI eutils
   export GENE_NORM_DB_URL=http://localhost:8000
   # only for the liftover path (not the default):
   # export UTA_DB_URL=postgresql://anonymous:anonymous@localhost:5434/uta/uta_20241220
   ```

   `vrsify.sh` fails fast if the first four are unset.

## Run

```bash
./src/vrsify/vrsify.sh YYYY-MM-DD
```

Env overrides: `PARALLELISM` (default 2); `VRSIFY_CMD` (default `clinvar-gk-pilot`; set to
`"uv run python clinvar_gk_pilot/main.py"` to run from an upstream checkout instead of the
installed console script).

`vrsify.sh` stops before resolving anything if the installed `clinvar-gk-pilot` is not the commit
pinned in `requirements.txt`. A custom `VRSIFY_CMD` is not checked.

## Using the output in a release

`vrsify.sh` writes no provenance file, so the cloud vrsify check that `run-release.sh` runs before every `gkm_vrs`
load (stage 3, or first thing from `--start-step 4`) cannot pass on its output; `--allow-unchecked-vrs` skips that
check. Stage 4 reads `vi-vrs-python.jsonl.gz`. Move any cloud output for the release (`vi-vrs-python.jsonl.gz` and
`vi-vrs-python.provenance.json`) aside, copy this output over, and run with the override:

```bash
gcloud storage cp gs://clinvar-gkm/YYYY-MM-DD/dev/vi-normalized-no-liftover.jsonl.gz \
  gs://clinvar-gkm/YYYY-MM-DD/dev/vi-vrs-python.jsonl.gz
./src/scripts/run-release.sh YYYY-MM-DD --start-step 4 --allow-unchecked-vrs   # plus the usual flags, e.g. --full-procs
```

## Version-invalidation

The resolver version is an input to the incremental pipeline: `gkm_vrs` carry-forward assumes
unchanged variations were translated by the **same** resolver. Output from this fallback carried
forward next to the cloud translation mixes two translators (for 2026-11-08 they differed only in the
`out.errors` text of 7 untranslatable variants). `vrsify.sh` reads only `vi.jsonl.gz`, not the
`vi-*.jsonl.gz` shards of `export-vi-table-to-gcs.sh --full`. See
[docs/pipeline/vrs-processing.md](../../docs/pipeline/vrs-processing.md).
