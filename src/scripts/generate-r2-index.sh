#!/bin/bash

# Regenerate index.json from the CURRENT Cloudflare R2 bucket state.
#
# Standalone generator called by BOTH uploaders (upload-gkm-to-r2.sh and
# upload-gkm-delta-to-r2.sh) so the published index is consistent regardless of
# which one ran last. Lists:
#   datasets.monthly — monthly full bundles in datasets/ (00-latest marked), each with its sha256
#                      read from the <file>.sha256 sidecar (null when there is none)
#   datasets.parquet — ONE entry: the latest derived Parquet set, datasets/parquet/00-latest/, with the
#                      release it was built from (its source.json). Parquet is derived from the bundle and
#                      regenerated every release; there are no per-release sets (ADR 0008).
#   archives         — prior-year monthly files under archives/{yyyy}/
#   deltas           — per-release delta dirs under deltas/ (00-latest marked), each with its bundle
#                      {path, size, sha256}
#
# Usage:
#   ./generate-r2-index.sh [--dry-run]

set -e

# --- Parse flags ---
DRY_RUN=false
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    *)
      echo "ERROR: Unknown argument '${arg}'"
      echo "Usage: $0 [--dry-run]"
      exit 1
      ;;
  esac
done

# --- R2 Configuration ---
R2_ACCOUNT_ID="09208aa33790838db213a21f630c33e7"
R2_BUCKET="clinvar-gkm"
R2_ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
R2_PROFILE="r2"
R2_PUBLIC_URL="${R2_PUBLIC_URL:-https://data.clinvar-gkm.org}"
# Per-major release prefix (ADR 0004). The per-line index + feed live under it
# (v1/index.json, v1/feed.xml) and every entry path it emits is prefixed with it, so
# consumers composing base_url + "/" + path land under v1/. The thin ROOT manifest
# (index.json) is the one object published at the bucket root — see Main below.
R2_PREFIX="${R2_PREFIX:-v1/}"

LATEST_MONTHLY="clinvar-gkm_00-latest.json.gz"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# The bundle schema version the pipeline emits (root manifest "schema"); env-overridable.
SCHEMA_VERSION="${SCHEMA_VERSION:-$(sed -n 's/^SCHEMA_VERSION = "\(.*\)"$/\1/p' "${SCRIPT_DIR}/assemble-gkm-dicts.py")}"

# =====================================================================
# Helper functions
# =====================================================================

r2_upload() {
  local src="$1" dest="$2" content_type="${3:-application/gzip}"
  if $DRY_RUN; then
    echo "  [dry-run] upload: ${dest}"
    return
  fi
  aws s3 cp "$src" "s3://${R2_BUCKET}/${dest}" \
    --endpoint-url "${R2_ENDPOINT}" \
    --profile "${R2_PROFILE}" \
    --content-type "${content_type}" \
    --quiet
}

r2_ls() {
  local prefix="$1"
  aws s3 ls "s3://${R2_BUCKET}/${prefix}" \
    --endpoint-url "${R2_ENDPOINT}" \
    --profile "${R2_PROFILE}" \
    2>/dev/null | awk '{print $NF}' || true
}

r2_ls_with_size() {
  # Returns "DATE SIZE FILENAME" lines for .json.gz files under a prefix
  local prefix="$1"
  aws s3 ls "s3://${R2_BUCKET}/${prefix}" \
    --endpoint-url "${R2_ENDPOINT}" \
    --profile "${R2_PROFILE}" \
    2>/dev/null | awk '/\.json\.gz$/ {print $1, $3, $4}' || true
}

# Newest immediate-file date (YYYY-MM-DD) under a prefix, or empty.
# Skips "PRE dir/" lines (they have no date in $1).
r2_newest_date_under() {
  local prefix="$1"
  aws s3 ls "s3://${R2_BUCKET}/${prefix}" \
    --endpoint-url "${R2_ENDPOINT}" \
    --profile "${R2_PROFILE}" \
    2>/dev/null \
    | awk '$1 ~ /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/ {print $1}' \
    | sort | tail -n1 || true
}

# The sha256 from an object's <key>.sha256 sidecar as a JSON value: "<64 hex>", or null when there is none.
r2_sha256_json() {
  local sha
  sha="$(aws s3 cp "s3://${R2_BUCKET}/$1.sha256" - --endpoint-url "${R2_ENDPOINT}" --profile "${R2_PROFILE}" \
    2>/dev/null | awk '{print $1; exit}' || true)"
  if [[ "$sha" =~ ^[0-9a-f]{64}$ ]]; then printf '"%s"' "$sha"; else printf 'null'; fi
}

# JSON array of parquet section names (filename minus .parquet) under a prefix.
r2_parquet_sections_under() {
  local prefix="$1"
  local first=true
  local arr="["
  while IFS= read -r section; do
    [[ -z "$section" ]] && continue
    if ! $first; then arr+=","; fi
    first=false
    arr+=$(printf '"%s"' "$section")
  done < <(
    aws s3 ls "s3://${R2_BUCKET}/${prefix}" \
      --endpoint-url "${R2_ENDPOINT}" \
      --profile "${R2_PROFILE}" \
      2>/dev/null | awk '/\.parquet$/ {sub(/\.parquet$/, "", $NF); print $NF}' || true
  )
  arr+="]"
  echo "$arr"
}

# Minimal XML escaping for Atom feed text + attribute values.
xml_escape() {
  local s="$1"
  s="${s//&/&amp;}"
  s="${s//</&lt;}"
  s="${s//>/&gt;}"
  s="${s//\"/&quot;}"
  printf '%s' "$s"
}

# Build a JSON array of file objects from "DATE SIZE FILENAME" lines under a prefix.
# Each entry: {name, path, size, modified, latest}.
# Args: prefix (R2 path like "datasets/" or "archives/2025/")
#       latest_name (filename to mark "latest": true, or "" for none)
build_file_array() {
  local prefix="$1" latest_name="$2"
  local first=true
  local arr="["

  while IFS=' ' read -r modified size filename; do
    [[ -z "$filename" ]] && continue
    if ! $first; then arr+=","; fi
    first=false

    local is_latest="false"
    if [[ -n "$latest_name" && "$filename" == "$latest_name" ]]; then
      is_latest="true"
    fi

    arr+=$(printf '{"name":"%s","path":"%s%s","size":%s,"sha256":%s,"modified":"%s","latest":%s}' \
      "$filename" "$prefix" "$filename" "$size" "$(r2_sha256_json "${prefix}${filename}")" "$modified" "$is_latest")
  done < <(r2_ls_with_size "$prefix")

  arr+="]"
  echo "$arr"
}

# The latest derived Parquet set as a one-entry JSON array (or [] when there is none). Its source.json
# names the release it was built from. Consumers compose per-section URLs as <path><section>.parquet;
# `sections` lists them.
build_latest_parquet() {
  local dir="${R2_PREFIX}datasets/parquet/00-latest/"
  local sections
  sections="$(r2_parquet_sections_under "$dir")"
  if [[ "$sections" == "[]" ]]; then echo "[]"; return; fi
  local source_release
  source_release="$(aws s3 cp "s3://${R2_BUCKET}/${dir}source.json" - --endpoint-url "${R2_ENDPOINT}" \
    --profile "${R2_PROFILE}" 2>/dev/null | sed -n 's/^ *"release": *"\([0-9-]*\)".*/\1/p' | head -n1 || true)"
  local src_json="null"
  [[ -n "$source_release" ]] && src_json="\"${source_release}\""
  printf '[{"release":"latest","path":"%s","source_release":%s,"derived":true,"modified":"%s","sections":%s,"latest":true}]' \
    "$dir" "$src_json" "$(r2_newest_date_under "$dir")" "$sections"
}

# Build the deltas JSON array — one object per release dir under deltas/.
# Each entry: {release, path, manifest, bundle: {path, size, sha256}, modified, latest}, where
# `modified` is the newest file date under the delta dir and `sha256` comes from the bundle's
# .sha256 sidecar (null when there is none). deltas/00-latest is marked latest.
build_deltas_array() {
  local first=true
  local arr="["

  while IFS= read -r dir; do
    dir="${dir%/}"
    [[ -z "$dir" ]] && continue

    if ! $first; then arr+=","; fi
    first=false

    local release path is_latest
    if [[ "$dir" == "00-latest" ]]; then
      release="latest"
      is_latest="true"
    else
      # Dir name is YYYY-MMDD -> release date YYYY-MM-DD
      release="${dir:0:4}-${dir:5:2}-${dir:7:2}"
      is_latest="false"
    fi
    path="${R2_PREFIX}deltas/${dir}/"

    local modified b_size b_name bundle_json="null"
    modified="$(r2_newest_date_under "${R2_PREFIX}deltas/${dir}/")"
    read -r _ b_size b_name < <(r2_ls_with_size "${path}" | head -n1) || true
    if [[ -n "${b_name:-}" ]]; then
      bundle_json=$(printf '{"path":"%s%s","size":%s,"sha256":%s}' \
        "$path" "$b_name" "$b_size" "$(r2_sha256_json "${path}${b_name}")")
    fi

    arr+=$(printf '{"release":"%s","path":"%s","manifest":"%smanifest.json","bundle":%s,"modified":"%s","latest":%s}' \
      "$release" "$path" "$path" "$bundle_json" "$modified" "$is_latest")
  done < <(r2_ls "${R2_PREFIX}deltas/" 2>/dev/null)

  arr+="]"
  echo "$arr"
}

# =====================================================================
# Main
# =====================================================================

echo "--- Generating ${R2_PREFIX}index.json + root manifest + ${R2_PREFIX}feed.xml ---"

INDEX_TMP="/tmp/clinvar-gkm-index.json"

# datasets.monthly (weekly section dropped — full is month-end only now)
DS_MONTHLY=$(build_file_array "${R2_PREFIX}datasets/" "${LATEST_MONTHLY}")

# datasets.parquet — the single latest derived set (no per-release sets)
DS_PARQUET=$(build_latest_parquet)

# archives — per-year discovery (monthly bundles)
ARCHIVES_JSON="{"
FIRST_YEAR=true
while IFS= read -r year_dir; do
  year_dir="${year_dir%/}"
  [[ -z "$year_dir" ]] && continue

  if ! $FIRST_YEAR; then ARCHIVES_JSON+=","; fi
  FIRST_YEAR=false

  ARCH_MONTHLY=$(build_file_array "${R2_PREFIX}archives/${year_dir}/")
  ARCHIVES_JSON+=$(printf '"%s":{"monthly":%s}' "$year_dir" "$ARCH_MONTHLY")
done < <(r2_ls "${R2_PREFIX}archives/" 2>/dev/null)
ARCHIVES_JSON+="}"

# deltas — per-release dirs
DELTAS_JSON=$(build_deltas_array)

# ---------------------------------------------------------------------
# Output 1: per-line index -> ${R2_PREFIX}index.json
# Today's index shape, but every entry path is now under ${R2_PREFIX}.
# ---------------------------------------------------------------------
cat > "$INDEX_TMP" <<INDEXEOF
{
  "description": "ClinVar-GKM release index",
  "updated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "base_url": "${R2_PUBLIC_URL}",
  "schema_version": "${SCHEMA_VERSION}",
  "parquet_note": "Parquet is derived from the JSON bundle and regenerated every release; only the latest set is published (ADR 0008).",
  "datasets": {
    "monthly": ${DS_MONTHLY},
    "parquet": ${DS_PARQUET}
  },
  "archives": ${ARCHIVES_JSON},
  "deltas": ${DELTAS_JSON}
}
INDEXEOF

r2_upload "$INDEX_TMP" "${R2_PREFIX}index.json" "application/json"
echo "  ${R2_PREFIX}index.json uploaded."

# ---------------------------------------------------------------------
# Output 2: thin ROOT manifest -> index.json (bucket root, ADR 0004)
# Lists the active major lines; each points at its own per-line index.
# The major / index are hardcoded for the single v1 line today (a future major adds entries
# here); "schema" is the bundle schema version the pipeline emits (SCHEMA_VERSION).
# ---------------------------------------------------------------------
MANIFEST_TMP="/tmp/clinvar-gkm-manifest.json"
cat > "$MANIFEST_TMP" <<MANIFESTEOF
{
  "manifest_version": 1,
  "updated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "base_url": "${R2_PUBLIC_URL}",
  "active": ["1"],
  "versions": {
    "1": {"schema": "${SCHEMA_VERSION}", "status": "current", "eol": null, "index": "v1/index.json"}
  }
}
MANIFESTEOF

r2_upload "$MANIFEST_TMP" "index.json" "application/json"
echo "  index.json (root manifest) uploaded."

# ---------------------------------------------------------------------
# Output 3: minimal Atom 1.0 feed -> ${R2_PREFIX}feed.xml
# Entries = monthly fulls (datasets/) + dated deltas (deltas/), newest
# first, capped at 25. Derived from the same read-only R2 listings above.
# ---------------------------------------------------------------------
FEED_TMP="/tmp/clinvar-gkm-feed.xml"
FEED_NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
FEED_SELF="${R2_PUBLIC_URL}/${R2_PREFIX}feed.xml"

# "MODIFIED<tab>TYPE<tab>LABEL<tab>PATH" records, newest first (lexical desc on the
# leading YYYY-MM-DD date), capped at 25.
FEED_RECORDS="$(
  {
    # monthly fulls (skip the 00-latest pointer)
    while IFS=' ' read -r m_date _ m_file; do
      [[ -z "$m_file" ]] && continue
      [[ "$m_file" == *"00-latest"* ]] && continue
      m_label="${m_file#clinvar-gkm_}"
      m_label="${m_label%.json.gz}"
      printf '%s\tmonthly\t%s\t%sdatasets/%s\n' \
        "$m_date" "$m_label" "$R2_PREFIX" "$m_file"
    done < <(r2_ls_with_size "${R2_PREFIX}datasets/")

    # dated deltas (skip the 00-latest pointer); dir is YYYY-MMDD
    while IFS= read -r d_dir; do
      d_dir="${d_dir%/}"
      [[ -z "$d_dir" ]] && continue
      [[ "$d_dir" == "00-latest" ]] && continue
      [[ "$d_dir" =~ ^[0-9]{4}-[0-9]{4}$ ]] || continue
      d_rel="${d_dir:0:4}-${d_dir:5:2}-${d_dir:7:2}"
      d_date="$(r2_newest_date_under "${R2_PREFIX}deltas/${d_dir}/")"
      [[ -z "$d_date" ]] && d_date="$d_rel"
      printf '%s\tdelta\t%s\t%sdeltas/%s/clinvar-gkm-delta_%s.json.gz\n' \
        "$d_date" "$d_rel" "$R2_PREFIX" "$d_dir" "$d_dir"
    done < <(r2_ls "${R2_PREFIX}deltas/")
  } | sort -r | head -n 25
)"

{
  echo '<?xml version="1.0" encoding="UTF-8"?>'
  echo '<feed xmlns="http://www.w3.org/2005/Atom">'
  echo '  <title>ClinVar-GKM Releases</title>'
  echo "  <id>$(xml_escape "${FEED_SELF}")</id>"
  echo "  <updated>${FEED_NOW}</updated>"
  echo "  <link rel=\"self\" href=\"$(xml_escape "${FEED_SELF}")\"/>"
  echo "  <link rel=\"alternate\" href=\"$(xml_escape "${R2_PUBLIC_URL}/${R2_PREFIX}index.json")\"/>"
  while IFS=$'\t' read -r f_date f_type f_label f_path; do
    [[ -z "$f_date" ]] && continue
    f_href="${R2_PUBLIC_URL}/${f_path}"
    echo '  <entry>'
    echo "    <title>$(xml_escape "ClinVar-GKM ${f_type} ${f_label}")</title>"
    echo "    <id>$(xml_escape "${f_href}")</id>"
    echo "    <updated>${f_date}T00:00:00Z</updated>"
    echo "    <link href=\"$(xml_escape "${f_href}")\"/>"
    echo '  </entry>'
  done <<< "${FEED_RECORDS}"
  echo '</feed>'
} > "$FEED_TMP"

r2_upload "$FEED_TMP" "${R2_PREFIX}feed.xml" "application/atom+xml"
echo "  ${R2_PREFIX}feed.xml uploaded."

if ! $DRY_RUN; then
  rm -f "$INDEX_TMP" "$MANIFEST_TMP" "$FEED_TMP"
fi
