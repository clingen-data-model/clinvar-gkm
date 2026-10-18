#!/bin/bash
# Upload the single LATEST ClinVar-GKM Parquet set to Cloudflare R2.
#
# Parquet is a derived convenience, not a public record (ADR 0008): it is recomputable from the JSON
# bundle, and only the latest state is published, at one stable path, rebuilt every release from the
# newest dataset:
#   datasets/parquet/00-latest/<section>.parquet
#   datasets/parquet/00-latest/source.json      — which release/dataset it was built from, schema version
# There are no dated Parquet sets (monthly or delta). Each section file is overwritten in place; after the
# upload, any *.parquet in 00-latest/ that is not in the local set is deleted (a renamed or dropped section),
# so there is no window with a missing file. index.json is regenerated.
#
# Usage:
#   ./upload-gkm-parquet-to-r2.sh <export_date> <dataset_version> <parquet_dir> [--dry-run] [--purge]
#
# --purge: purge the CDN cache for datasets/parquet/00-latest/ after the upload (needs CF_ZONE_ID +
# CF_PURGE_TOKEN; ADR 0005).
set -e

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <export_date> <dataset_version> <parquet_dir> [--dry-run] [--purge]"
  exit 1
fi
EXPORT_DATE="$1"; DATASET_VERSION="$2"; PARQUET_DIR="$3"; shift 3
[[ "$EXPORT_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { echo "ERROR: bad date '${EXPORT_DATE}'"; exit 1; }

DRY_RUN=false; PURGE=false
for arg in "$@"; do case "$arg" in
  --dry-run) DRY_RUN=true ;;
  --purge) PURGE=true ;;
  *) echo "ERROR: unknown arg '${arg}'"; exit 1 ;;
esac; done

R2_BUCKET="clinvar-gkm"
R2_ENDPOINT="https://09208aa33790838db213a21f630c33e7.r2.cloudflarestorage.com"
R2_PROFILE="r2"
R2_PUBLIC_URL="${R2_PUBLIC_URL:-https://data.clinvar-gkm.org}"
R2_PREFIX="${R2_PREFIX:-v1/}"
LATEST_PREFIX="datasets/parquet/00-latest/"
CF_PUBLIC_HOST="${CF_PUBLIC_HOST:-data.clinvar-gkm.org}"
CF_ZONE_ID="${CF_ZONE_ID:-}"
CF_PURGE_TOKEN="${CF_PURGE_TOKEN:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCHEMA_VERSION="$(sed -n 's/^SCHEMA_VERSION = "\(.*\)"$/\1/p' "${SCRIPT_DIR}/assemble-gkm-dicts.py")"

r2_upload() {
  local src="$1" dest="${R2_PREFIX}$2" content_type="${3:-application/vnd.apache.parquet}"
  if $DRY_RUN; then echo "  [dry-run] upload: ${dest}"; return; fi
  aws s3 cp "$src" "s3://${R2_BUCKET}/${dest}" --endpoint-url "${R2_ENDPOINT}" --profile "${R2_PROFILE}" \
    --content-type "${content_type}" --quiet
}
r2_ls() {
  aws s3 ls "s3://${R2_BUCKET}/${R2_PREFIX}$1" --endpoint-url "${R2_ENDPOINT}" --profile "${R2_PROFILE}" \
    2>/dev/null | awk '{print $NF}' || true
}
r2_rm() {
  if $DRY_RUN; then echo "  [dry-run] delete: ${R2_PREFIX}$1"; return; fi
  aws s3 rm "s3://${R2_BUCKET}/${R2_PREFIX}$1" --endpoint-url "${R2_ENDPOINT}" --profile "${R2_PROFILE}" --quiet
}

echo "=== ClinVar-GKM latest Parquet upload (built from ${EXPORT_DATE}, ${DATASET_VERSION}) ==="
$DRY_RUN && echo "  Mode: DRY RUN"
SECTIONS=()
if [[ -d "${PARQUET_DIR}" ]]; then
  for f in "${PARQUET_DIR}"/*.parquet; do
    [[ -f "$f" ]] && SECTIONS+=("$(basename "$f" .parquet)")
  done
fi
if [[ ${#SECTIONS[@]} -eq 0 ]]; then
  if $DRY_RUN; then echo "  [dry-run] (no local Parquet in ${PARQUET_DIR}; would upload <section>.parquet)"
  else echo "ERROR: no *.parquet in ${PARQUET_DIR}" >&2; exit 1; fi
fi

echo "--- Uploading ${#SECTIONS[@]} sections -> ${R2_PREFIX}${LATEST_PREFIX} ---"
for section in "${SECTIONS[@]+"${SECTIONS[@]}"}"; do
  r2_upload "${PARQUET_DIR}/${section}.parquet" "${LATEST_PREFIX}${section}.parquet"
done

# Provenance of the derived set: which release and dataset it was built from.
SOURCE_JSON="$(mktemp)"
{
  printf '{\n  "derived": true,\n  "note": "Derived from the JSON bundle and regenerated every release; not a release record.",\n'
  printf '  "release": "%s",\n  "dataset": "clinvar_%s_%s",\n' "${EXPORT_DATE}" "${EXPORT_DATE//-/_}" "${DATASET_VERSION}"
  printf '  "schema_version": "%s",\n  "generated_at": "%s",\n  "sections": [' "${SCHEMA_VERSION}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  first=true
  for section in "${SECTIONS[@]+"${SECTIONS[@]}"}"; do
    $first || printf ', '; first=false; printf '"%s"' "$section"
  done
  printf ']\n}\n'
} > "${SOURCE_JSON}"
r2_upload "${SOURCE_JSON}" "${LATEST_PREFIX}source.json" "application/json"
rm -f "${SOURCE_JSON}"

# Remove sections that are no longer produced (after the upload: no window with a missing file).
echo "--- Removing stale sections from ${R2_PREFIX}${LATEST_PREFIX} ---"
removed=0
while IFS= read -r fn; do
  [[ "$fn" == *.parquet ]] || continue
  [[ -f "${PARQUET_DIR}/${fn}" ]] && continue
  if $DRY_RUN && [[ ${#SECTIONS[@]} -eq 0 ]]; then continue; fi
  r2_rm "${LATEST_PREFIX}${fn}"
  removed=$((removed + 1))
done < <(r2_ls "${LATEST_PREFIX}")
echo "  ${removed} stale section file(s) $($DRY_RUN && echo 'to remove' || echo 'removed')."

INDEX_ARGS=(); $DRY_RUN && INDEX_ARGS+=("--dry-run")
"${SCRIPT_DIR}/generate-r2-index.sh" "${INDEX_ARGS[@]+"${INDEX_ARGS[@]}"}"

if $PURGE; then
  if $DRY_RUN; then echo "  [dry-run] purge: ${CF_PUBLIC_HOST}/${R2_PREFIX}${LATEST_PREFIX}"
  elif [[ -z "$CF_ZONE_ID" || -z "$CF_PURGE_TOKEN" ]]; then
    echo "  WARNING: --purge set but CF_ZONE_ID/CF_PURGE_TOKEN not set; skipping CDN purge."
  else
    curl -fsS -X POST "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/purge_cache" \
      -H "Authorization: Bearer ${CF_PURGE_TOKEN}" -H "Content-Type: application/json" \
      --data "{\"prefixes\":[\"${CF_PUBLIC_HOST}/${R2_PREFIX}${LATEST_PREFIX}\"]}" >/dev/null 2>&1 \
      && echo "  Purge requested." || echo "  WARNING: CDN purge request failed (continuing)."
  fi
fi

echo "=== Latest Parquet: ${R2_PUBLIC_URL}/${R2_PREFIX}${LATEST_PREFIX} ==="
