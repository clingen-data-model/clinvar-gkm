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
