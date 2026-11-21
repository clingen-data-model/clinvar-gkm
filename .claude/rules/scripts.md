---
description: Shell + release-tooling conventions (bash 3.2, R2/Cloudflare, bq and gh CLI gotchas)
paths:
  - "src/scripts/**"
---

# Shell script & release-tooling conventions

The release orchestration lives in `src/scripts/` (`run-release.sh`, `release-gkm*.sh`,
`upload-gkm*-to-r2.sh`, `generate-*.sh`, oracle scripts). Validate scripts with `bash -n` + `shellcheck`.

## macOS bash 3.2

The default macOS shell is bash 3.2. **No** `mapfile`, **no** associative arrays (`declare -A`). Use indexed
arrays and "key val" pair lists.

## Cloudflare R2

- Public bucket `clinvar-gkm`, S3 endpoint `https://09208aa33790838db213a21f630c33e7.r2.cloudflarestorage.com`,
  `--profile r2`; public read URL `https://data.clinvar-gkm.org`.
- **Reads go through Cloudflare's CDN** at `data.clinvar-gkm.org` (dedicated zone `clinvar-gkm.org` —
  ClinGen's `clinicalgenome.org` can't host it). Cache Rules + a rate-limit rule give fee protection;
  immutable dated artifacts are cached hard, so **never overwrite a published dated path** without purging.
  The uploaders take `--purge` (needs a zone-scoped `CF_PURGE_TOKEN` + `CF_ZONE_ID`) for that case. `R2_PUBLIC_URL`
  is env-overridable in the uploaders + `generate-r2-index.sh` (it sets the index `base_url`). Full runbook:
  [ADR 0005](../../docs/decisions/0005-r2-custom-domain-and-cdn.md).
- R2 does **not** implement `GetObjectTagging` (breaks multipart server-side copy) nor
  `x-amz-tagging-directive` (breaks single-part copy with `--copy-props none`). Use a **size-aware copy**:
  objects ≥2 GB via `aws s3 cp --copy-props none`; smaller via `aws s3api copy-object`.
- The object-scoped `r2` token **cannot** read/write bucket config (`PutBucketCors` → AccessDenied). Bucket
  CORS is applied out-of-band (`apply-r2-cors.sh` with an admin token, or the dashboard); policy checked in at
  `src/scripts/r2-cors.json`.

## CLI gotchas

- `bq query` defaults to `--max_rows=100` — pass a large `--max_rows` when a result set can exceed 100 rows
  (silently truncates otherwise).
- `gh api graphql` variables: use `-F name=value` for typed (Int/Bool) variables and `-f` for strings; an
  `Int!` variable passed via `-f` fails. When in doubt, inline the literal into the query.
- Keep `bq` and gcloud pointed at the same project (`export CLOUDSDK_CORE_PROJECT`) so the bq wrapper doesn't
  prepend a mismatched `--project_id`.

## Release model (context)

Incremental by default (carry-forward UNION delta); the monthly full bundle is triggered by ClinVar's monthly
XML index (see `docs/superpowers/specs/2026-08-24-clinvar-index-monthly-trigger-design.md` and
[ADR 0002](../../docs/decisions/0002-monthly-full-anchored-to-clinvar-index.md)). Never touch live R2 without
explicit user confirmation.

**Everything before the VRS translation runs in clinvar-ingest (pipeline v2.7.0+).** It runs `dataset_diff_on`,
`variation_identity_incremental` and `variation_vrs_changed`, exports `<date>/dev/vi.jsonl.gz`, and its Cloud Run job
`clinvar-ingest-vrsify` (clingen-dev, us-east1, every 15 min) writes `vi-vrs-python.jsonl.gz` + `.provenance.json`.
`run-release.sh` never runs those; it has four steps: 1 `check-cloud-vrsify.sh` (read-only, fails fast, stops unless
the provenance names the current `vi.jsonl.gz` with the same md5 + size; a same-content re-export only changes the
generation), 2 version stamp + `vrs-to-bq-table.sh`, 3 publish, 4 Parquet. `--start-step` is 1–4 and 2 still runs
the check. The job takes each release once and never replaces its output, so a changed `vi.jsonl.gz` needs a manual
re-translation upstream. The procs' SQL stays in `src/procedures/` until a cross-repo move to clinvar-ingest.
`export-vi-table-to-gcs.sh` is not part of the release; it stays only because clinvar-ingest's export-failure message
names it as the manual recovery.

## Publish-layer cleanup & bundle conformance (learned in 1.0.1)

`assemble-gkm-dicts.py` + `gkm_json_cleanup.py` are the **single publish-layer cleanup point** every bundle
record flows through (full AND delta). The `gkm_dict_*` BQ tables keep their raw shape; cleanup happens here,
so these changes never affect delta/change-log/oracle correctness. Keep this centralized — don't scatter
record cleanup across the BQ export functions.

- **`strip_empty`** drops null / `{}` / `[]` *keys* but **keeps list elements** (SQL arrays hold no NULL
  elements; dropping them would change array length). Consequence: an all-empty array element like `[{}]`
  **survives** — so the *producing proc* must emit `NULL`/`[]`, never `[{}]` (see sql-procedures.md).
- **`collapse_ext_values`** renames a typed extension `value_<type>` → polymorphic `value` in every object
  with a `name` sibling, **recursively, in every section** (incl. nested `classification.extensions`). Apply it
  wherever extensions can appear — the old bug was collapsing only the top-level `extensions` column of a few
  sections in the BQ NDJSON export.
- **`orjson` sets the bundle's text** (compact, raw UTF-8, record keys sorted at every depth), so the assembler
  requires it and stops without it. The stdlib's `json.dumps` writes the same data in different text, so an
  unchanged record would no longer have the same bytes in every release. A checkout without `venv/3.12` uses
  whatever `python3` is active.
- **Canonical list order** — `order_unordered_arrays` sorts the arrays in `gkm_json_cleanup.UNORDERED_ARRAYS`
  (today `condition.aliases`) by each element's key-sorted JSON text, so replays are byte-exact. Add an array only
  when the data shows its order changing between releases AND every schema marks it `ordered: false` (the unit test
  checks the schema tree); never sort an `ordered: true` array.
- **Omit zero-entry sections** — an empty `"section": {}` fails the bundle schema's per-section
  `minProperties: 1`. The assembler opens a section lazily on its first entry so a delta section with no changes
  is dropped.
- **conditionSet single-member filter** — drop `ConceptSet`s with `ARRAY_LENGTH(concepts) <= 1` (va-spec
  `minItems: 2`). They are unreferenced orphans (every producer references the lone member directly as
  `#/condition/`, never the set). Filtered in the NDJSON export (`extract_ndjson_where`).

**Parquet derives from the bundle.** The published Parquet set is built only by gkm-bundle-parquet, from the
published bundle (`run-release.sh` step 4, `release-gkm-parquet.sh`). BigQuery exports no Parquet, so there is no Parquet
SQL to keep in step with the assembler. The default tables are generated from the bundle schema, so a schema change
here changes them with no Parquet-specific work. If Parquet needs a fact the bundle doesn't carry, add it to the
bundle (and its schema) first; never add Parquet-only logic to this repo. The tool checks every build against its
bundle (`verify --bundle-recompute`, `verify --roundtrip`).

**Conformance validation (do this, not a shortcut):** validate every record of the REAL full + delta bundles with
`validate-bundle.sh` (default engine rs = jsonschema-rs, the validator of record), against the bundle schema with a
registry over the whole `schema/` tree (dual-keyed: full `$id` AND root-relative path). Do NOT trust `sub-bundle.py`
output as proof — it runs its own recursive collapse and so **masks** export/assembler cleanup bugs that the real
bundles carry. `release-gkm-delta.sh` and `release-gkm.sh` run it (`--engine rs`) on every delta and full before
upload, and `run-release.sh` builds both with `--no-upload` first so a failure leaves R2 untouched. The official
GA4GH gkm-toolkit (`--engine toolkit`, python-jsonschema) gives the same verdicts but is too slow for a 1.2.0 full
(~17 h on 64 vCPUs: it re-evaluates every allOf/$ref layer for each `unevaluatedProperties`), so: keep
`test_validate_bundle_rs.py`'s equivalence tests passing (both engines name the same failing records, including
violations planted inside the layered variation/vcv/scv profiles), and at each version release run the toolkit on a
stratified sample of the line's first full (`sample-bundle.py`, then `validate-bundle.sh --engine toolkit`). The rs
engine compiles the bundle schema per section (the whole schema takes jsonschema-rs minutes to compile) and reads
only the assembler's one-record-per-line layout, stopping on any other line.
`$id`/`schema_version` version bump on a schema-affecting change: bump the 4 `schema/clinvar-gkm/*-source.yaml`
+ `clinvar-gkm-bundle.schema.json` + `SCHEMA_VERSION` in `assemble-gkm-dicts.py`, regen `json/` via
`make -C schema/clinvar-gkm`; the generator's `$defs` ordering is non-deterministic, so revert the pure-reorder
churn and keep only the real diff. A new `x.y.z` git tag makes the w3id `$id`s resolve (dynamic rule; no
`.htaccess` change).
