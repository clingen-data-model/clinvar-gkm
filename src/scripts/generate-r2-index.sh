#!/bin/bash

# Regenerate index.json from the CURRENT Cloudflare R2 bucket state.
#
# Standalone generator called by BOTH uploaders (upload-gkm-to-r2.sh and
# upload-gkm-delta-to-r2.sh) so the published index is consistent regardless of
# which one ran last. Lists:
#   datasets.monthly — monthly full bundles in datasets/ (00-latest marked)
#   datasets.parquet — dated Parquet month sets under datasets/parquet/ (00-latest marked)
#   archives         — prior-year monthly files + parquet month sets under archives/{yyyy}/
#   deltas           — per-release delta dirs under deltas/ (00-latest marked)
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
R2_PUBLIC_URL="https://pub-f0ad0e0dac0345408dcc95bda20beb42.r2.dev"
# Per-major release prefix (ADR 0004). The per-line index + feed live under it
# (v1/index.json, v1/feed.xml) and every entry path it emits is prefixed with it, so
# consumers composing base_url + "/" + path land under v1/. The thin ROOT manifest
# (index.json) is the one object published at the bucket root — see Main below.
R2_PREFIX="${R2_PREFIX:-v1/}"

LATEST_MONTHLY="clinvar-gkm_00-latest.json.gz"

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

    arr+=$(printf '{"name":"%s","path":"%s%s","size":%s,"modified":"%s","latest":%s}' \
      "$filename" "$prefix" "$filename" "$size" "$modified" "$is_latest")
  done < <(r2_ls_with_size "$prefix")

  arr+="]"
  echo "$arr"
}

# Build a JSON array of Parquet month-set objects under a prefix.
# Each entry: {release, path, modified, latest}. A dir named 00-latest is marked
# latest; a dir named YYYY-MM becomes release=YYYY-MM. Consumers compose
# per-section URLs as <path><section>.parquet.
# Args: prefix (e.g. "datasets/parquet/" or "archives/2025/parquet/")
build_parquet_array() {
  local prefix="$1"
  local first=true
  local arr="["

  while IFS= read -r dir; do
    dir="${dir%/}"
    [[ -z "$dir" ]] && continue

    local release is_latest
    if [[ "$dir" == "00-latest" ]]; then
      release="latest"
      is_latest="true"
    elif [[ "$dir" =~ ^[0-9]{4}-[0-9]{2}$ ]]; then
      release="$dir"
      is_latest="false"
    else
      continue
    fi

    if ! $first; then arr+=","; fi
    first=false

    local modified
    modified="$(r2_newest_date_under "${prefix}${dir}/")"

    arr+=$(printf '{"release":"%s","path":"%s%s/","modified":"%s","latest":%s}' \
      "$release" "$prefix" "$dir" "$modified" "$is_latest")
  done < <(r2_ls "$prefix")

  arr+="]"
  echo "$arr"
}

# Build the deltas JSON array — one object per release dir under deltas/.
# Each entry: {release, path, manifest, modified, parquet, latest}, where
# `modified` is the newest file date under the delta dir and `parquet` is the
# array of section names under its parquet/ subdir. deltas/00-latest is marked latest.
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

    local modified parquet_sections
    modified="$(r2_newest_date_under "${R2_PREFIX}deltas/${dir}/")"
    parquet_sections="$(r2_parquet_sections_under "${R2_PREFIX}deltas/${dir}/parquet/")"

    arr+=$(printf '{"release":"%s","path":"%s","manifest":"%smanifest.json","modified":"%s","parquet":%s,"latest":%s}' \
      "$release" "$path" "$path" "$modified" "$parquet_sections" "$is_latest")
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

# datasets.parquet — dated month sets + 00-latest under datasets/parquet/
DS_PARQUET=$(build_parquet_array "${R2_PREFIX}datasets/parquet/")

# archives — per-year discovery (monthly bundles + dated parquet month sets)
ARCHIVES_JSON="{"
FIRST_YEAR=true
while IFS= read -r year_dir; do
  year_dir="${year_dir%/}"
  [[ -z "$year_dir" ]] && continue

  if ! $FIRST_YEAR; then ARCHIVES_JSON+=","; fi
  FIRST_YEAR=false

  ARCH_MONTHLY=$(build_file_array "${R2_PREFIX}archives/${year_dir}/")
  ARCH_PARQUET=$(build_parquet_array "${R2_PREFIX}archives/${year_dir}/parquet/")
  ARCHIVES_JSON+=$(printf '"%s":{"monthly":%s,"parquet":%s}' \
    "$year_dir" "$ARCH_MONTHLY" "$ARCH_PARQUET")
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
# The major / schema / index are hardcoded for the single v1 line today;
# a future major adds entries here.
# ---------------------------------------------------------------------
MANIFEST_TMP="/tmp/clinvar-gkm-manifest.json"
cat > "$MANIFEST_TMP" <<MANIFESTEOF
{
  "manifest_version": 1,
  "updated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "base_url": "${R2_PUBLIC_URL}",
  "active": ["1"],
  "versions": {
    "1": {"schema": "1.0.0", "status": "current", "eol": null, "index": "v1/index.json"}
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
