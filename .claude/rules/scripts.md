---
description: Shell + release-tooling conventions (bash 3.2, R2/Cloudflare, bq and gh CLI gotchas)
paths:
  - "src/scripts/**"
  - "src/vrsify/**"
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
  sections in the BQ NDJSON export. Mirror the same collapse in the typed-Parquet `data` columns
  (`parquet-schemas/*.sql`, pattern:
  `collapse_ext_values(TO_JSON_STRING(JSON_STRIP_NULLS(TO_JSON((SELECT AS STRUCT t.*)), remove_empty => TRUE)))`)
  for EVERY extension-bearing section (scv, vcv, rcv, variation, evidence lines, propositions).
- **Omit zero-entry sections** — an empty `"section": {}` fails the bundle schema's per-section
  `minProperties: 1`. The assembler opens a section lazily on its first entry so a delta section with no changes
  is dropped.
- **conditionSet single-member filter** — drop `ConceptSet`s with `ARRAY_LENGTH(concepts) <= 1` (va-spec
  `minItems: 2`). They are unreferenced orphans (every producer references the lone member directly as
  `#/condition/`, never the set). Filter in BOTH the NDJSON (`extract_ndjson_where`) and typed-Parquet
  (`conditionSet.sql WHERE`) exports.

**Conformance validation (do this, not a shortcut):** validate the REAL published full + delta bundles with the
official GA4GH **gkm-toolkit** `validate_bundle_schema` plus a registry built by `load_registry` over the whole
`schema/` tree (dual-keyed: full `$id` AND root-relative path). Do NOT trust `sub-bundle.py` output as proof —
it runs its own recursive collapse and so **masks** export/assembler cleanup bugs that the real bundles carry.
`$id`/`schema_version` version bump on a schema-affecting change: bump the 4 `schema/clinvar-gkm/*-source.yaml`
+ `clinvar-gkm-bundle.schema.json` + `SCHEMA_VERSION` in `assemble-gkm-dicts.py`, regen `json/` via
`make -C schema/clinvar-gkm`; the generator's `$defs` ordering is non-deterministic, so revert the pure-reorder
churn and keep only the real diff. A new `x.y.z` git tag makes the w3id `$id`s resolve (dynamic rule; no
`.htaccess` change).
