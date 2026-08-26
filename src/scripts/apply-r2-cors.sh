#!/bin/bash
#
# apply-r2-cors.sh — apply the checked-in CORS policy (r2-cors.json) to the public
# clinvar-gkm R2 bucket, then print the resulting policy to confirm.
#
# WHY THIS EXISTS: the "Browse All Releases" widget on the Downloads page runs a
# cross-origin fetch() of index.json from the docs site. Without a bucket CORS
# policy, R2 returns index.json with no Access-Control-Allow-Origin header and the
# browser blocks the read, so the widget never populates. `*` for GET/HEAD is
# appropriate for a public, read-only data bucket (and lets third parties build
# tools against index.json too).
#
# REQUIRES an R2 API token with **Admin Read & Write** — the object-scoped upload
# token used by the release scripts CANNOT read or write bucket CORS config
# (GetBucketCors/PutBucketCors return AccessDenied). Create one at:
#   Cloudflare dashboard -> R2 -> Manage R2 API Tokens -> Create (Admin Read & Write),
# then configure it as an aws profile (default name below: r2admin).
#
# USAGE:
#   ./apply-r2-cors.sh [aws_profile]     # default profile: r2admin
#
# Alternatively, paste r2-cors.json's CORSRules into the dashboard:
#   R2 -> clinvar-gkm -> Settings -> CORS Policy.

set -o errexit
set -o nounset
set -o pipefail

R2_BUCKET="clinvar-gkm"
R2_ACCOUNT_ID="09208aa33790838db213a21f630c33e7"
R2_ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
R2_PROFILE="${1:-r2admin}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORS_FILE="${SCRIPT_DIR}/r2-cors.json"

[[ -f "${CORS_FILE}" ]] || { echo "ERROR: ${CORS_FILE} not found" >&2; exit 1; }

echo "Applying CORS policy from ${CORS_FILE} to bucket ${R2_BUCKET} (profile: ${R2_PROFILE})..."
aws s3api put-bucket-cors \
  --bucket "${R2_BUCKET}" \
  --endpoint-url "${R2_ENDPOINT}" \
  --profile "${R2_PROFILE}" \
  --cors-configuration "file://${CORS_FILE}"

echo "Applied. Current policy:"
aws s3api get-bucket-cors \
  --bucket "${R2_BUCKET}" \
  --endpoint-url "${R2_ENDPOINT}" \
  --profile "${R2_PROFILE}"

echo ""
echo "Verify the header is now served (should print an Access-Control-Allow-Origin line):"
echo "  curl -sI -H 'Origin: https://clingen-data-model.github.io' \\"
echo "    https://pub-f0ad0e0dac0345408dcc95bda20beb42.r2.dev/index.json | grep -i access-control-allow-origin"
